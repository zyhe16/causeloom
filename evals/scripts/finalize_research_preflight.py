#!/usr/bin/env python3
"""Validate and record the model-free research benchmark gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


RANDOM_CALL = re.compile(
    r"(?:\brandom\.(?!seed\b)|\bnumpy\.random\.|\bnp\.random\."
    r"|\btorch\.(?:rand|randn|randint|randperm)\b|\bsecrets\."
    r"|\buuid\.uuid4\b|\$RANDOM\b|\bshuf\b|/dev/u?random)"
)
SEED_CALL = re.compile(
    r"(?:\brandom\.seed\b|\bnumpy\.random\.seed\b|\bnp\.random\.seed\b"
    r"|\btorch\.manual_seed\b)"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rewards(job_dir: Path) -> dict[str, float]:
    result: dict[str, float] = {}
    for path in sorted(job_dir.rglob("reward.txt")):
        result[path.parent.parent.name] = float(path.read_text(encoding="utf-8").strip())
    return result


def probes(job_dir: Path) -> dict[str, dict[str, bool]]:
    result: dict[str, dict[str, bool]] = {}
    for path in sorted(job_dir.rglob("isolation-probe.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        result[path.parent.parent.name] = data
    return result


def audit_randomness(tasks_root: Path) -> dict[str, object]:
    seeded: dict[str, list[str]] = {}
    unseeded: dict[str, list[str]] = {}
    for path in sorted(tasks_root.glob("*/tests/**/*")):
        if not path.is_file() or path.suffix.lower() not in {".py", ".sh", ".bash"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        hits = [line.strip() for line in text.splitlines() if RANDOM_CALL.search(line)]
        if not hits:
            continue
        relative = path.relative_to(tasks_root).as_posix()
        target = seeded if SEED_CALL.search(text) else unseeded
        target[relative] = hits
    return {"seeded_random_sources": seeded, "unseeded_random_sources": unseeded}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root", type=Path, default=Path("work/research-benchmark-dynamic")
    )
    parser.add_argument("--tasks-root", type=Path)
    parser.add_argument("--oracle-job", default="oracle-final")
    parser.add_argument("--nop-job", default="nop-final")
    parser.add_argument("--isolation-job", default="isolation-final")
    args = parser.parse_args()
    tasks_root = args.tasks_root or args.root / "tasks-a5"
    preflight = args.root / "preflight"
    oracle_dir = preflight / args.oracle_job
    nop_dir = preflight / args.nop_job
    isolation_dir = preflight / args.isolation_job

    oracle_rewards = rewards(oracle_dir)
    nop_rewards = rewards(nop_dir)
    isolation = probes(isolation_dir)
    randomness = audit_randomness(tasks_root)
    lock_path = args.root / "benchmark-lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    expected_tasks = len(lock.get("tasks", []))
    if len(oracle_rewards) != expected_tasks or set(oracle_rewards.values()) != {1.0}:
        raise SystemExit(f"Oracle gate failed: {oracle_rewards}")
    if len(nop_rewards) != expected_tasks or set(nop_rewards.values()) != {0.0}:
        raise SystemExit(f"No-op gate failed: {nop_rewards}")
    if len(isolation) != expected_tasks or not all(
        all(checks.values()) for checks in isolation.values()
    ):
        raise SystemExit(f"Isolation gate failed: {isolation}")
    if randomness["unseeded_random_sources"]:
        raise SystemExit(f"Unseeded grader randomness: {randomness}")

    evidence = {
        "schema_version": 1,
        "status": "model-free-ready",
        "benchmark_lock_sha256": sha256(lock_path),
        "oracle": {"job": args.oracle_job, "rewards": oracle_rewards},
        "nop": {"job": args.nop_job, "rewards": nop_rewards},
        "isolation": {"job": args.isolation_job, "checks": isolation},
        "grader_randomness": randomness,
    }
    output = preflight / "MODEL_FREE_READY.json"
    output.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Wrote model-free readiness evidence to {output}")


if __name__ == "__main__":
    main()
