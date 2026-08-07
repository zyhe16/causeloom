#!/usr/bin/env python3
"""Audit a completed research benchmark from preserved Harbor/Codex artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from codex_events import parse_cli_events, parse_desktop_session, read_jsonl


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def median(values: list[int | float]) -> float | None:
    return statistics.median(values) if values else None


def nested_identity(session: Path) -> tuple[set[str], set[str], set[str], set[str]]:
    events, errors = read_jsonl(session)
    if errors:
        raise ValueError(f"session parse errors in {session}: {errors}")
    models: set[str] = set()
    efforts: set[str] = set()
    versions: set[str] = set()
    thread_ids: set[str] = set()
    for event in events:
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        if event.get("type") == "session_meta":
            if payload.get("cli_version"):
                versions.add(str(payload["cli_version"]))
            for key in ("id", "session_id"):
                if payload.get(key):
                    thread_ids.add(str(payload[key]))
        if event.get("type") == "turn_context":
            if payload.get("model"):
                models.add(str(payload["model"]))
            if payload.get("effort"):
                efforts.add(str(payload["effort"]))
    return models, efforts, versions, thread_ids


def top_reward(result: dict[str, Any]) -> float | None:
    evals = result.get("stats", {}).get("evals", {})
    for item in evals.values():
        if not isinstance(item, dict):
            continue
        rewards = item.get("reward_stats", {}).get("reward", {})
        if isinstance(rewards, dict) and rewards:
            return float(next(iter(rewards)))
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sqlite-output", type=Path)
    parser.add_argument("--skill", type=Path, default=Path("SKILL.md"))
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path("evals/conditions/causeloom/POLICY.md"),
    )
    parser.add_argument(
        "--codex-config",
        type=Path,
        default=Path("work/research-benchmark-dynamic/codex.config.toml"),
    )
    args = parser.parse_args()

    root = args.root.resolve()
    lock_path = root / "benchmark-lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    status = json.loads((root / "status.json").read_text(encoding="utf-8"))
    ready = json.loads(
        (root / "preflight" / "MODEL_FREE_READY.json").read_text(encoding="utf-8")
    )
    run_specs = {
        run["run_id"]: run
        for queue in lock["workers"].values()
        for run in queue
    }

    violations: list[str] = []
    warnings: list[str] = []
    records: list[dict[str, Any]] = []
    artifact_counts: Counter[str] = Counter()
    identity = {
        "models": set(),
        "efforts": set(),
        "cli_versions": set(),
        "binary_sha256": set(),
        "thread_ids": set(),
    }

    for run_id, spec in run_specs.items():
        job = root / "jobs" / run_id
        if not job.is_dir():
            violations.append(f"{run_id}: missing job directory")
            continue
        result_paths = sorted(job.rglob("result.json"))
        top_path = job / "result.json"
        nested_paths = [path for path in result_paths if path != top_path]
        if len(result_paths) != 2 or len(nested_paths) != 1 or not top_path.is_file():
            violations.append(
                f"{run_id}: expected one top and one nested result, found {len(result_paths)}"
            )
            continue
        artifact_counts["top_results"] += 1
        artifact_counts["nested_results"] += 1
        top = json.loads(top_path.read_text(encoding="utf-8"))
        nested = json.loads(nested_paths[0].read_text(encoding="utf-8"))
        if not top.get("finished_at") or not nested.get("finished_at"):
            violations.append(f"{run_id}: non-terminal result")

        reward = float(nested.get("verifier_result", {}).get("rewards", {}).get("reward", 0))
        aggregate_reward = top_reward(top)
        if aggregate_reward != reward:
            violations.append(
                f"{run_id}: top/nested reward mismatch {aggregate_reward} != {reward}"
            )

        trial = nested_paths[0].parent
        expected = {
            "app_exports": trial / "artifacts" / "app",
            "artifact_manifests": trial / "artifacts" / "manifest.json",
            "trajectories": trial / "agent" / "trajectory.json",
            "codex_streams": trial / "agent" / "codex.txt",
        }
        for name, path in expected.items():
            if path.exists():
                artifact_counts[name] += 1
            else:
                violations.append(f"{run_id}: missing {name}: {path}")
        sessions = sorted((trial / "agent" / "sessions").rglob("*.jsonl"))
        if len(sessions) != 1:
            violations.append(f"{run_id}: expected one rollout session, found {len(sessions)}")
            continue
        artifact_counts["rollout_sessions"] += 1
        models, efforts, versions, session_threads = nested_identity(sessions[0])
        identity["models"].update(models)
        identity["efforts"].update(efforts)
        identity["cli_versions"].update(versions)
        identity["thread_ids"].update(session_threads)

        kwargs = nested.get("config", {}).get("agent", {}).get("kwargs", {})
        if kwargs.get("codex_binary_sha256"):
            identity["binary_sha256"].add(str(kwargs["codex_binary_sha256"]).lower())

        cli = parse_cli_events([expected["codex_streams"]])
        session_usage = parse_desktop_session(sessions[0])
        if cli["usage"] is not None:
            usage = cli["usage"]
            token_adapter = "codex_exec_jsonl"
        else:
            usage = session_usage["usage"]
            token_adapter = "codex_session_jsonl"
        if usage is None:
            violations.append(f"{run_id}: no trustworthy token usage")
            usage = {
                "input_tokens": 0,
                "cached_input_tokens": 0,
                "cache_write_input_tokens": 0,
                "output_tokens": 0,
                "reasoning_tokens": 0,
                "total_tokens": 0,
            }
            token_adapter = "unavailable"
        else:
            artifact_counts["token_covered_runs"] += 1
        thread_ids = set(cli["thread_ids"]) | session_threads
        if not thread_ids:
            violations.append(f"{run_id}: missing thread identifier")
        else:
            artifact_counts["thread_identifiers"] += 1

        stats = top.get("stats", {})
        for source_key, usage_key in (
            ("n_input_tokens", "input_tokens"),
            ("n_cache_tokens", "cached_input_tokens"),
            ("n_output_tokens", "output_tokens"),
        ):
            if stats.get(source_key) is not None and int(stats[source_key]) != int(usage[usage_key]):
                warnings.append(
                    f"{run_id}: Harbor {source_key} {stats[source_key]} != raw {usage_key} {usage[usage_key]}"
                )

        started = timestamp(str(nested["started_at"]))
        finished = timestamp(str(nested["finished_at"]))
        exception = nested.get("exception_info")
        exception_type = ""
        if isinstance(exception, dict):
            exception_type = str(exception.get("exception_type", ""))
        records.append(
            {
                "run_id": run_id,
                "task_id": spec["task_id"],
                "condition": spec["condition"],
                "repetition": int(spec["repetition"]),
                "reward": reward,
                "exception_type": exception_type,
                "timed_out": exception_type == "AgentTimeoutError",
                "started_at": started.isoformat(),
                "finished_at": finished.isoformat(),
                "elapsed_seconds": (finished - started).total_seconds(),
                "token_adapter": token_adapter,
                "tokens": usage,
            }
        )

    condition_names = sorted({str(spec["condition"]) for spec in run_specs.values()})
    conditions: dict[str, Any] = {}
    for condition in condition_names:
        rows = [record for record in records if record["condition"] == condition]
        conditions[condition] = {
            "runs": len(rows),
            "reward_1": sum(record["reward"] == 1 for record in rows),
            "reward_0": sum(record["reward"] == 0 for record in rows),
            "timeout_flagged": sum(record["timed_out"] for record in rows),
            "exception_free_reward_1": sum(
                record["reward"] == 1 and not record["exception_type"] for record in rows
            ),
            "exception_free_runs": sum(not record["exception_type"] for record in rows),
            "total_tokens": sum(record["tokens"]["total_tokens"] for record in rows),
            "median_input_tokens": median([record["tokens"]["input_tokens"] for record in rows]),
            "median_cached_input_tokens": median(
                [record["tokens"]["cached_input_tokens"] for record in rows]
            ),
            "median_output_tokens": median([record["tokens"]["output_tokens"] for record in rows]),
            "median_reasoning_tokens": median(
                [record["tokens"]["reasoning_tokens"] for record in rows]
            ),
            "median_total_tokens": median([record["tokens"]["total_tokens"] for record in rows]),
            "median_elapsed_seconds": median([record["elapsed_seconds"] for record in rows]),
        }

    task_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        task_rows[record["task_id"]].append(record)
    tasks = {
        task: {
            "runs": len(rows),
            "reward_1": sum(record["reward"] == 1 for record in rows),
            "reward_0": sum(record["reward"] == 0 for record in rows),
            "timeout_flagged": sum(record["timed_out"] for record in rows),
        }
        for task, rows in sorted(task_rows.items())
    }
    task_condition = {
        task: {
            condition: {
                "runs": len(cell),
                "reward_1": sum(record["reward"] == 1 for record in cell),
                "timeout_flagged": sum(record["timed_out"] for record in cell),
            }
            for condition in condition_names
            for cell in [[record for record in rows if record["condition"] == condition]]
        }
        for task, rows in sorted(task_rows.items())
    }

    archive_receipts = sorted(
        (root / "invalid-infrastructure-attempts").rglob("ARCHIVE_RECEIPT.json")
    )
    archive_reasons = Counter()
    for receipt in archive_receipts:
        archive_reasons[
            json.loads(receipt.read_text(encoding="utf-8")).get("reason", "unknown")
        ] += 1

    all_started = [timestamp(record["started_at"]) for record in records]
    all_finished = [timestamp(record["finished_at"]) for record in records]
    totals = {
        key: sum(record["tokens"][key] for record in records)
        for key in (
            "input_tokens",
            "cached_input_tokens",
            "cache_write_input_tokens",
            "output_tokens",
            "reasoning_tokens",
            "total_tokens",
        )
    }
    adapters = Counter(record["token_adapter"] for record in records)
    exceptions = Counter(record["exception_type"] or "none" for record in records)
    rewards = Counter(str(record["reward"]) for record in records)

    history = list(status.get("launcher_history", []))
    history.append(
        {
            "launcher_pid": status.get("launcher_pid"),
            "started_unix": status.get("started_unix"),
            "finished_unix": status.get("finished_unix"),
            "worker_count": status.get("worker_count"),
            "state": status.get("state"),
        }
    )
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "frozen_identity": {
            "model": sorted(identity["models"]),
            "reasoning_effort": sorted(identity["efforts"]),
            "codex_cli": sorted(identity["cli_versions"]),
            "codex_binary_sha256": sorted(identity["binary_sha256"]),
            "canonical_skill_sha256": sha256_file(args.skill),
            "causeloom_policy_sha256": sha256_file(args.policy),
            "benchmark_lock_sha256": sha256_file(lock_path),
            "ready_lock_sha256": ready.get("benchmark_lock_sha256"),
            "run_order_seed": lock.get("run_order_seed"),
            "planned_runs": len(run_specs),
        },
        "completion": {
            "terminal_runs": len(records),
            "current_infrastructure_invalid": 0,
            "timeout_flagged": exceptions.get("AgentTimeoutError", 0),
            "exception_free": exceptions.get("none", 0),
            "reward_1": rewards.get("1.0", 0),
            "reward_0": rewards.get("0.0", 0),
            "accepted_attempt_span_seconds": (
                max(all_finished) - min(all_started)
            ).total_seconds()
            if records
            else None,
            "sum_trial_elapsed_seconds": sum(record["elapsed_seconds"] for record in records),
            "median_trial_elapsed_seconds": median(
                [record["elapsed_seconds"] for record in records]
            ),
            "min_trial_elapsed_seconds": min(
                (record["elapsed_seconds"] for record in records), default=None
            ),
            "max_trial_elapsed_seconds": max(
                (record["elapsed_seconds"] for record in records), default=None
            ),
        },
        "artifacts": dict(sorted(artifact_counts.items())),
        "identity_counts": {
            "unique_thread_ids": len(identity["thread_ids"]),
        },
        "tokens": {
            **totals,
            "coverage": artifact_counts["token_covered_runs"],
            "adapter_counts": dict(sorted(adapters.items())),
            "formula": "input_tokens + output_tokens",
            "cached_and_reasoning_are_nonadditive_details": True,
        },
        "exceptions": dict(sorted(exceptions.items())),
        "conditions": conditions,
        "tasks": tasks,
        "task_condition": task_condition,
        "archived_infrastructure_attempts": {
            "count": len(archive_receipts),
            "reasons": dict(sorted(archive_reasons.items())),
        },
        "concurrency_history": history,
        "warnings": warnings,
        "violations": violations,
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if args.sqlite_output is not None:
        args.sqlite_output.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(args.sqlite_output) as database:
            database.executescript(
                """
                DROP TABLE IF EXISTS condition_summary;
                DROP TABLE IF EXISTS task_summary;
                DROP TABLE IF EXISTS concurrency_history;
                CREATE TABLE condition_summary (
                    condition TEXT PRIMARY KEY,
                    runs INTEGER NOT NULL,
                    reward_1 INTEGER NOT NULL,
                    reward_0 INTEGER NOT NULL,
                    pass_rate REAL NOT NULL,
                    timeout_flagged INTEGER NOT NULL,
                    exception_free_runs INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    median_total_tokens REAL NOT NULL,
                    median_elapsed_seconds REAL NOT NULL
                );
                CREATE TABLE task_summary (
                    task TEXT PRIMARY KEY,
                    total_pass INTEGER NOT NULL,
                    timeouts INTEGER NOT NULL
                );
                CREATE TABLE task_condition_summary (
                    task TEXT NOT NULL,
                    condition TEXT NOT NULL,
                    reward_1 INTEGER NOT NULL,
                    timeouts INTEGER NOT NULL,
                    PRIMARY KEY (task, condition)
                );
                CREATE TABLE concurrency_history (
                    launcher_pid INTEGER PRIMARY KEY,
                    concurrency_cap INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    started_unix REAL,
                    finished_unix REAL
                );
                """
            )
            for condition, summary in conditions.items():
                database.execute(
                    "INSERT INTO condition_summary VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        condition,
                        summary["runs"],
                        summary["reward_1"],
                        summary["reward_0"],
                        summary["reward_1"] / summary["runs"],
                        summary["timeout_flagged"],
                        summary["exception_free_runs"],
                        summary["total_tokens"],
                        summary["median_total_tokens"],
                        summary["median_elapsed_seconds"],
                    ),
                )
            for task, summary in tasks.items():
                cells = task_condition[task]
                database.execute(
                    "INSERT INTO task_summary VALUES (?, ?, ?)",
                    (
                        task,
                        summary["reward_1"],
                        summary["timeout_flagged"],
                    ),
                )
                for condition, cell in cells.items():
                    database.execute(
                        "INSERT INTO task_condition_summary VALUES (?, ?, ?, ?)",
                        (
                            task,
                            condition,
                            cell["reward_1"],
                            cell["timeout_flagged"],
                        ),
                    )
            for launch in history:
                database.execute(
                    "INSERT INTO concurrency_history VALUES (?, ?, ?, ?, ?)",
                    (
                        launch.get("launcher_pid"),
                        launch.get("worker_count"),
                        launch.get("state"),
                        launch.get("started_unix"),
                        launch.get("finished_unix"),
                    ),
                )
            database.commit()
    print(
        f"Audited {len(records)}/{len(run_specs)} terminal runs; "
        f"{len(violations)} violation(s), {len(warnings)} warning(s); wrote {args.output}"
    )


if __name__ == "__main__":
    main()
