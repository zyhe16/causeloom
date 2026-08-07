#!/usr/bin/env python3
"""Launch bounded, resume-safe task workers for the research benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import threading
import time
import tomllib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


CONDITION_PATHS = {
    "causeloom": Path("evals/conditions/causeloom/POLICY.md"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_condition_hashes(lock_data: dict[str, object]) -> None:
    expected_hashes = lock_data.get("condition_sha256")
    if not isinstance(expected_hashes, dict):
        raise ValueError("Lock is missing condition_sha256")
    if set(expected_hashes) != {"baseline", *CONDITION_PATHS}:
        raise ValueError("Lock condition hashes do not match launcher conditions")
    if expected_hashes["baseline"] is not None:
        raise ValueError("Baseline condition hash must be null")
    for condition, path in CONDITION_PATHS.items():
        if not path.is_file():
            raise ValueError(f"Condition policy not found: {path}")
        actual = sha256_file(path)
        if actual.lower() != str(expected_hashes[condition]).lower():
            raise ValueError(f"Condition policy hash mismatch: {condition}")


def completed_run(job_root: Path, run_id: str) -> bool:
    matches = list((job_root / run_id).rglob("result.json"))
    if not matches:
        return False
    try:
        parsed = [json.loads(path.read_text(encoding="utf-8")) for path in matches]
        return all(
            isinstance(result, dict) and result.get("finished_at")
            for result in parsed
        ) and not any(
            retryable_infrastructure_exception(result) for result in parsed
        )
    except (OSError, json.JSONDecodeError):
        return False


def exception_infos(value: object) -> list[dict[str, object]]:
    found: list[dict[str, object]] = []
    if isinstance(value, dict):
        exception = value.get("exception_info")
        if isinstance(exception, dict):
            found.append(exception)
        for child in value.values():
            found.extend(exception_infos(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(exception_infos(child))
    return found


def retryable_infrastructure_exception(result: object) -> bool:
    infrastructure_markers = (
        "docker compose command failed",
        "all predefined address pools have been fully subnetted",
        "failed to create network",
        "no space left on device",
        "cannot connect to the docker daemon",
        "docker daemon",
        "container was killed due to oom",
    )
    for exception in exception_infos(result):
        exception_type = str(exception.get("exception_type", ""))
        message = str(exception.get("exception_message", "")).lower()
        if exception_type == "AgentTimeoutError":
            continue
        if any(marker in message for marker in infrastructure_markers):
            return True
    return False


def retryable_infrastructure_run(job_root: Path, run_id: str) -> bool:
    matches = list((job_root / run_id).rglob("result.json"))
    if not matches:
        return False
    try:
        return any(
            retryable_infrastructure_exception(
                json.loads(path.read_text(encoding="utf-8"))
            )
            for path in matches
        )
    except (OSError, json.JSONDecodeError):
        return False


def archive_existing_attempt(
    job_root: Path, archive_root: Path, run_id: str, reason: str
) -> Path:
    source = job_root / run_id
    if not source.is_dir():
        raise FileNotFoundError(f"Run directory not found for archival: {source}")
    run_archive = archive_root / run_id
    run_archive.mkdir(parents=True, exist_ok=True)
    attempt = 1
    while (run_archive / f"attempt-{attempt:03d}").exists():
        attempt += 1
    target = run_archive / f"attempt-{attempt:03d}"
    shutil.move(str(source), str(target))
    receipt = {
        "run_id": run_id,
        "reason": reason,
        "source": source.as_posix(),
        "archive": target.as_posix(),
        "archived_unix": time.time(),
    }
    (target / "ARCHIVE_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return target


def validate_worker_plan(
    workers: dict[str, list[dict[str, str]]],
    worker_tasks: dict[str, list[str]],
    tasks: dict[str, dict[str, object]],
    expected_runs: int,
) -> int:
    if not workers or set(workers) != set(worker_tasks):
        raise ValueError("Lock workers and worker_tasks must define the same slots")
    assigned_tasks = [task for task_ids in worker_tasks.values() for task in task_ids]
    if len(assigned_tasks) != len(set(assigned_tasks)) or set(assigned_tasks) != set(tasks):
        raise ValueError("Worker task assignments must cover each task exactly once")
    all_runs = [run for runs in workers.values() for run in runs]
    if len(all_runs) != expected_runs:
        raise ValueError(
            f"Lock must define exactly {expected_runs} runs, found {len(all_runs)}"
        )
    run_ids = [run["run_id"] for run in all_runs]
    if len(set(run_ids)) != len(run_ids):
        raise ValueError("Lock contains duplicate run IDs")
    for worker_id, runs in workers.items():
        allowed_tasks = set(worker_tasks[worker_id])
        if not runs or any(run["task_id"] not in allowed_tasks for run in runs):
            raise ValueError(f"Worker {worker_id} contains a run for an unassigned task")
    return len(all_runs)


def harbor_command(
    harbor: Path,
    task_path: Path,
    jobs_root: Path,
    run: dict[str, str],
    codex_version: str,
    codex_binary: Path,
    codex_binary_sha256: str,
    codex_config: Path,
    offline_compose: Path,
    common_instruction: Path,
    auth_json: Path,
    base_url: str,
) -> list[str]:
    run_id = run["run_id"]
    command = [
        str(harbor),
        "run",
        "--env",
        "evals.harbor.offline_docker:OfflineDockerEnvironment",
        "--path",
        str(task_path),
        "--agent",
        "evals.harbor.offline_codex:OfflineConfiguredCodex",
        "--agent-kwarg",
        f"version={codex_version}",
        "--agent-kwarg",
        f"codex_binary_path={codex_binary}",
        "--agent-kwarg",
        f"codex_binary_sha256={codex_binary_sha256}",
        "--agent-kwarg",
        f"codex_config_path={codex_config}",
        "--agent-kwarg",
        "web_search=disabled",
        "--agent-env",
        f"CODEX_AUTH_JSON_PATH={auth_json}",
        "--agent-env",
        f"OPENAI_BASE_URL={base_url}",
        "--extra-docker-compose",
        str(offline_compose),
        "--extra-instruction-path",
        str(common_instruction),
        "--artifact",
        "/app",
        "--job-name",
        run_id,
        "--jobs-dir",
        str(jobs_root),
        "--n-concurrent",
        "1",
        "--cpus",
        "limit",
        "--memory",
        "limit",
        "--max-retries",
        "0",
        "--yes",
        "--quiet",
    ]
    condition_path = CONDITION_PATHS.get(run["condition"])
    if condition_path is not None:
        command.extend(["--extra-instruction-path", str(condition_path)])
    return command


def write_status(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
    )
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    for attempt in range(50):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 49:
                raise
            time.sleep(0.1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--lock",
        type=Path,
        default=Path("work/research-benchmark-dynamic/benchmark-lock.json"),
    )
    parser.add_argument(
        "--attempt-archive-root",
        type=Path,
        help="Preserved retryable/interrupted attempts; defaults beside the lock",
    )
    parser.add_argument(
        "--harbor", type=Path, default=Path("work/harbor-venv/Scripts/harbor.exe")
    )
    parser.add_argument("--codex-version", default="0.146.0")
    parser.add_argument("--codex-config", type=Path, required=True)
    parser.add_argument("--codex-binary", type=Path, required=True)
    parser.add_argument("--codex-binary-sha256", required=True)
    parser.add_argument("--expected-model", default="gpt-5.6-sol")
    parser.add_argument("--expected-reasoning-effort", default="high")
    parser.add_argument(
        "--auth-json", type=Path, default=Path.home() / ".codex" / "auth.json"
    )
    parser.add_argument(
        "--base-url", default="http://model-relay:10101/v1"
    )
    parser.add_argument(
        "--common-instruction",
        type=Path,
        default=Path("evals/harbor/common-instructions.md"),
    )
    parser.add_argument(
        "--jobs-root",
        type=Path,
        default=Path("work/research-benchmark-dynamic/jobs"),
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--max-workers",
        type=int,
        help="Maximum worker slots to execute concurrently; defaults to every locked slot",
    )
    parser.add_argument(
        "--stop-on-infrastructure-error",
        action="store_true",
        help="Stop scheduling new trials after a Harbor process returns nonzero",
    )
    args = parser.parse_args()

    lock_data = json.loads(args.lock.read_text(encoding="utf-8"))
    workers: dict[str, list[dict[str, str]]] = lock_data["workers"]
    tasks = {task["suite_task_id"]: task for task in lock_data["tasks"]}
    worker_tasks: dict[str, list[str]] = lock_data["worker_tasks"]
    try:
        expected_runs = lock_data.get("planned_runs")
        if not isinstance(expected_runs, int) or expected_runs < 1:
            raise ValueError("Lock is missing a positive planned_runs value")
        planned_runs = validate_worker_plan(
            workers, worker_tasks, tasks, expected_runs
        )
        validate_condition_hashes(lock_data)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    max_workers = args.max_workers if args.max_workers is not None else len(workers)
    if max_workers < 1 or max_workers > len(workers):
        raise SystemExit(f"--max-workers must be between 1 and {len(workers)}")
    if not args.harbor.is_file():
        raise SystemExit(f"Harbor executable not found: {args.harbor}")
    if not args.auth_json.is_file():
        raise SystemExit(f"Codex auth file not found: {args.auth_json}")
    if not args.codex_binary.is_file():
        raise SystemExit(f"Codex Linux binary not found: {args.codex_binary}")
    if not args.codex_config.is_file():
        raise SystemExit(f"Codex config not found: {args.codex_config}")
    config = tomllib.loads(args.codex_config.read_text(encoding="utf-8"))
    if set(config) != {"model", "model_reasoning_effort"}:
        raise SystemExit("Codex config must contain only model and reasoning effort")
    if config.get("model") != args.expected_model:
        raise SystemExit("Codex config does not contain the expected model; restart first")
    if config.get("model_reasoning_effort") != args.expected_reasoning_effort:
        raise SystemExit(
            "Codex config does not contain the expected reasoning effort; restart first"
        )
    offline_compose = Path(str(lock_data["offline_compose_path"]))
    if not offline_compose.is_file():
        raise SystemExit(f"Offline compose overlay not found: {offline_compose}")
    if not args.execute:
        print(
            f"Validated {len(workers)} worker slots, concurrency {max_workers}, "
            f"and {planned_runs} runs. Pass --execute after all preflights pass."
        )
        return

    ready_path = args.lock.parent / "preflight" / "MODEL_FREE_READY.json"
    if not ready_path.is_file():
        raise SystemExit(f"Refusing model runs without preflight marker: {ready_path}")
    ready = json.loads(ready_path.read_text(encoding="utf-8"))
    lock_sha256 = hashlib.sha256(args.lock.read_bytes()).hexdigest()
    if ready.get("benchmark_lock_sha256") != lock_sha256:
        raise SystemExit("Preflight marker does not match the current benchmark lock")
    binary_sha256 = sha256_file(args.codex_binary)
    if binary_sha256.lower() != args.codex_binary_sha256.lower():
        raise SystemExit("Codex Linux binary hash does not match --codex-binary-sha256")

    args.jobs_root.mkdir(parents=True, exist_ok=True)
    attempt_archive_root = (
        args.attempt_archive_root
        if args.attempt_archive_root is not None
        else args.lock.parent / "invalid-infrastructure-attempts"
    )
    status_path = args.lock.parent / "status.json"
    status_lock = threading.Lock()
    previous_status: dict[str, object] = {}
    if args.resume and status_path.is_file():
        try:
            previous_status = json.loads(status_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previous_status = {}
    launcher_history = list(previous_status.get("launcher_history", []))
    if previous_status.get("launcher_pid") is not None:
        launcher_history.append(
            {
                "launcher_pid": previous_status.get("launcher_pid"),
                "started_unix": previous_status.get("started_unix"),
                "finished_unix": previous_status.get("finished_unix"),
                "worker_count": previous_status.get("worker_count"),
                "state": previous_status.get("state"),
            }
        )
    status: dict[str, object] = {
        "started_unix": time.time(),
        "launcher_pid": os.getpid(),
        "model": config["model"],
        "reasoning_effort": config["model_reasoning_effort"],
        "codex_version": args.codex_version,
        "worker_count": max_workers,
        "worker_slots": len(workers),
        "planned_runs": planned_runs,
        "state": "running",
        "launcher_history": launcher_history,
        "runs": previous_status.get("runs", {}),
    }
    stop_event = threading.Event()

    def update_run(run_id: str, run_status: dict[str, object]) -> None:
        with status_lock:
            runs = status["runs"]
            assert isinstance(runs, dict)
            runs[run_id] = run_status
            write_status(status_path, status)

    def run_worker(worker_id: str, runs: list[dict[str, str]]) -> None:
        for run in runs:
            if stop_event.is_set():
                return
            suite_id = run["task_id"]
            task_path = Path(str(tasks[suite_id]["adapted_path"]))
            run_id = run["run_id"]
            if args.resume and completed_run(args.jobs_root, run_id):
                with status_lock:
                    recorded_runs = status["runs"]
                    assert isinstance(recorded_runs, dict)
                    previous_state = recorded_runs.get(run_id)
                update_run(
                    run_id,
                    {
                        "state": "already_completed",
                        "previous_state": previous_state,
                    },
                )
                continue
            archived_attempt: str | None = None
            existing_run = args.jobs_root / run_id
            if args.resume and existing_run.is_dir():
                reason = (
                    "retryable_infrastructure_exception"
                    if retryable_infrastructure_run(args.jobs_root, run_id)
                    else "interrupted_incomplete_attempt"
                )
                archived_attempt = str(
                    archive_existing_attempt(
                        args.jobs_root, attempt_archive_root, run_id, reason
                    )
                )
            command = harbor_command(
                args.harbor,
                task_path,
                args.jobs_root,
                run,
                args.codex_version,
                args.codex_binary.resolve(),
                args.codex_binary_sha256,
                args.codex_config.resolve(),
                offline_compose.resolve(),
                args.common_instruction,
                args.auth_json.resolve(),
                args.base_url,
            )
            log_dir = args.lock.parent / "launcher-logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / f"{run_id}.log"
            update_run(
                run_id,
                {
                    "state": "running",
                    "worker": worker_id,
                    "started_unix": time.time(),
                    "log": str(log_path),
                    "archived_attempt": archived_attempt,
                },
            )
            with log_path.open("w", encoding="utf-8") as log:
                child_env = os.environ.copy()
                repo_root = str(Path.cwd().resolve())
                existing_pythonpath = child_env.get("PYTHONPATH")
                child_env["PYTHONPATH"] = (
                    repo_root
                    if not existing_pythonpath
                    else repo_root + os.pathsep + existing_pythonpath
                )
                child_env["PYTHONUTF8"] = "1"
                child_env["PYTHONIOENCODING"] = "utf-8"
                result = subprocess.run(
                    command,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=child_env,
                    check=False,
                )
            nested_infrastructure_error = retryable_infrastructure_run(
                args.jobs_root, run_id
            )
            infrastructure_error = result.returncode != 0 or nested_infrastructure_error
            update_run(
                run_id,
                {
                    "state": (
                        "infrastructure_error" if infrastructure_error else "completed"
                    ),
                    "worker": worker_id,
                    "finished_unix": time.time(),
                    "return_code": result.returncode,
                    "nested_infrastructure_error": nested_infrastructure_error,
                    "log": str(log_path),
                },
            )
            if infrastructure_error and args.stop_on_infrastructure_error:
                stop_event.set()

    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="tbench") as executor:
        futures = {
            executor.submit(run_worker, worker_id, runs): worker_id
            for worker_id, runs in workers.items()
        }
        for future in as_completed(futures):
            future.result()

    with status_lock:
        status["finished_unix"] = time.time()
        status["state"] = (
            "stopped_after_infrastructure_error" if stop_event.is_set() else "finished"
        )
        write_status(status_path, status)
    if stop_event.is_set():
        raise SystemExit("Stopped after a Harbor infrastructure error")


if __name__ == "__main__":
    main()
