#!/usr/bin/env python3
"""Reuse model-free preflights only when executable task content is identical."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


MODEL_FREE_JOBS = ("oracle-final", "nop-final", "isolation-final")
LOCK_FIELDS = (
    "dataset",
    "suite_sha256",
    "common_instruction_sha256",
    "network_policy",
    "offline_assets",
)
TASK_FIELDS = (
    "upstream_task_id",
    "upstream_digest",
    "instruction_sha256",
    "task_toml_sha256",
    "environment_sha256",
    "tests_sha256",
    "solution_sha256",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def execution_tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative_path = path.relative_to(root)
        if (
            relative_path.as_posix() == ".research-adaptation.json"
            or "__pycache__" in relative_path.parts
            or path.suffix.lower() in {".pyc", ".pyo"}
        ):
            continue
        relative = relative_path.as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(bytes.fromhex(sha256_file(path)))
    return digest.hexdigest()


def validate_equivalence(
    source_lock: dict[str, object], target_lock: dict[str, object]
) -> dict[str, str]:
    for field in LOCK_FIELDS:
        if source_lock.get(field) != target_lock.get(field):
            raise ValueError(f"Benchmark lock field differs: {field}")
    source_tasks = {
        task["suite_task_id"]: task for task in source_lock.get("tasks", [])
    }
    target_tasks = {
        task["suite_task_id"]: task for task in target_lock.get("tasks", [])
    }
    if not source_tasks or set(source_tasks) != set(target_tasks):
        raise ValueError("Benchmark task IDs differ")
    execution_digests: dict[str, str] = {}
    for task_id in sorted(source_tasks):
        source = source_tasks[task_id]
        target = target_tasks[task_id]
        for field in TASK_FIELDS:
            if source.get(field) != target.get(field):
                raise ValueError(f"Task {task_id} field differs: {field}")
        source_digest = execution_tree_digest(Path(str(source["adapted_path"])))
        target_digest = execution_tree_digest(Path(str(target["adapted_path"])))
        if source_digest != target_digest:
            raise ValueError(f"Task {task_id} executable content differs")
        expected_target_digest = target.get("execution_digest")
        if expected_target_digest is not None and expected_target_digest != target_digest:
            raise ValueError(f"Task {task_id} lock execution digest is stale")
        execution_digests[task_id] = target_digest
    return execution_digests


def reuse(source_root: Path, target_root: Path) -> Path:
    source_lock_path = source_root / "benchmark-lock.json"
    target_lock_path = target_root / "benchmark-lock.json"
    source_lock = json.loads(source_lock_path.read_text(encoding="utf-8"))
    target_lock = json.loads(target_lock_path.read_text(encoding="utf-8"))
    execution_digests = validate_equivalence(source_lock, target_lock)

    source_ready = source_root / "preflight" / "MODEL_FREE_READY.json"
    if not source_ready.is_file():
        raise FileNotFoundError(f"Source readiness marker not found: {source_ready}")
    target_preflight = target_root / "preflight"
    target_preflight.mkdir(parents=True, exist_ok=True)
    for job in MODEL_FREE_JOBS:
        source = source_root / "preflight" / job
        target = target_preflight / job
        if not source.is_dir():
            raise FileNotFoundError(f"Source preflight job not found: {source}")
        if target.exists():
            raise FileExistsError(f"Refusing to overwrite target preflight job: {target}")
        shutil.copytree(source, target)

    receipt = {
        "schema_version": 1,
        "source_root": source_root.as_posix(),
        "source_lock_sha256": sha256_file(source_lock_path),
        "source_ready_sha256": sha256_file(source_ready),
        "target_lock_sha256": sha256_file(target_lock_path),
        "excluded_non_execution_files": [
            ".research-adaptation.json",
            "**/__pycache__/**",
            "**/*.pyc",
            "**/*.pyo",
        ],
        "execution_digests": execution_digests,
        "copied_jobs": list(MODEL_FREE_JOBS),
    }
    output = target_preflight / "REUSED_MODEL_FREE_EVIDENCE.json"
    output.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Reused model-free preflight evidence in {target_preflight}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--target-root", type=Path, required=True)
    args = parser.parse_args()
    reuse(args.source_root, args.target_root)


if __name__ == "__main__":
    main()
