#!/usr/bin/env python3
"""Materialize a digest-locked, offline-agent Terminal-Bench evaluation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import tomllib
from pathlib import Path


DATASET = "terminal-bench@2.0"
MODEL_RELAY_IMAGE = "causeloom/model-relay:0.1.1"
ADAPTATION_VERSION = "a6"
AGENT_TIMEOUT_MULTIPLIER = 4.0
EXPECTED_TASKS = 13
CONDITIONS = ("baseline", "causeloom")
REPETITIONS = 3
SCHEDULER_MODE = "global-work-conserving"
MAX_PARALLEL_RUNS_PER_TASK = 2
SCHEDULER_MEMORY_BUDGET_GB = 20.0
DOOM_WAD_SHA256 = "1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771"
DOOM_WAD_SOURCE_IMAGE = (
    "alexgshaw/make-mips-interpreter@"
    "sha256:082fc8821b317f30fdfbf8d08d528874ce331c03e8083aef0406d48cdd7132a2"
)
FIVE_WORKER_TASKS = {
    "worker-01": ["M01", "X04", "C01"],
    "worker-02": ["M02", "X06", "C02"],
    "worker-03": ["M03", "X01", "C03"],
    "worker-04": ["X02", "X03"],
    "worker-05": ["X05", "X07"],
}


def environment_memory_gb(task_toml: str) -> float:
    parsed = tomllib.loads(task_toml)
    value = parsed.get("environment", {}).get("memory")
    if not isinstance(value, str):
        raise ValueError("Task environment must define memory as a string")
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([MG])B?\s*", value, re.I)
    if match is None:
        raise ValueError(f"Unsupported task memory value: {value!r}")
    amount = float(match.group(1))
    return amount if match.group(2).upper() == "G" else amount / 1024.0


def build_worker_tasks(suite_ids: list[str], worker_slots: int) -> dict[str, list[str]]:
    if worker_slots == 5:
        assignments = {key: list(value) for key, value in FIVE_WORKER_TASKS.items()}
        if {task for tasks in assignments.values() for task in tasks} != set(suite_ids):
            raise ValueError("Five-worker assignments must cover each suite task exactly once")
        return assignments
    if worker_slots == len(suite_ids):
        return {
            f"worker-{index:02d}": [suite_id]
            for index, suite_id in enumerate(suite_ids, start=1)
        }
    raise ValueError(
        f"worker_slots must be 5 or match the {len(suite_ids)} suite tasks"
    )


def adapt_task_toml(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    section_match = re.search(
        r"(?ms)^\[agent\]\s*\n(?P<body>.*?)(?=^\[|\Z)", text
    )
    if section_match is None:
        raise ValueError(f"Missing [agent] section in {path}")
    agent_section = section_match.group("body")
    if "network_mode" in agent_section:
        raise ValueError(f"Upstream task already defines agent network_mode: {path}")

    timeout_match = re.search(
        r"(?m)^(?P<prefix>\s*timeout_sec\s*=\s*)"
        r"(?P<value>\d+(?:\.\d+)?)\s*$",
        agent_section,
    )
    if timeout_match is None:
        raise ValueError(f"Missing numeric agent timeout_sec in {path}")
    original_timeout = timeout_match.group("value")
    adapted_timeout = float(original_timeout) * AGENT_TIMEOUT_MULTIPLIER
    replacement_timeout = (
        f"{adapted_timeout:.1f}"
        if "." in original_timeout
        else str(int(adapted_timeout))
    )
    adapted_agent_section = (
        'network_mode = "no-network"\n'
        + agent_section[: timeout_match.start("value")]
        + replacement_timeout
        + agent_section[timeout_match.end("value") :]
    )
    path.write_text(
        text[: section_match.start("body")]
        + adapted_agent_section
        + text[section_match.end("body") :],
        encoding="utf-8",
    )


def preinstall_offline_dependencies(
    task_id: str, task_root: Path, assets_root: Path
) -> list[str]:
    apt_packages: dict[str, list[str]] = {
        "sqlite-with-gcov": ["fossil", "gcc", "jimsh", "tclsh", "make", "tzdata"],
        "make-doom-for-mips": [
            "clang",
            "gcc-mips-linux-gnu",
            "g++-mips-linux-gnu",
            "llvm",
            "llvm-dev",
            "lld",
        ],
    }
    pip_packages: dict[str, list[str]] = {
        "kv-store-grpc": ["grpcio==1.73.0", "grpcio-tools==1.73.0"],
    }
    selected_apt = apt_packages.get(task_id, [])
    selected_pip = pip_packages.get(task_id, [])
    selected = selected_apt + selected_pip
    if not selected:
        return []

    dockerfile = task_root / "environment" / "Dockerfile"
    text = dockerfile.read_text(encoding="utf-8")
    block = "\n# Offline benchmark adaptation: infrastructure only, no solution code.\n"
    if selected_apt:
        block += (
            "RUN apt-get update -y && DEBIAN_FRONTEND=noninteractive apt-get install -y "
            + " ".join(selected_apt)
            + "\n"
        )
    if selected_pip:
        block += "RUN pip install --no-cache-dir " + " ".join(selected_pip) + "\n"
    dockerfile.write_text(text + block, encoding="utf-8")

    if task_id == "make-doom-for-mips":
        wad_source = assets_root / "doom1.wad"
        if sha256_file(wad_source) != DOOM_WAD_SHA256:
            raise ValueError(f"Invalid offline Doom WAD: {wad_source}")
        offline_deps = task_root / "environment" / "offline-deps"
        offline_deps.mkdir()
        shutil.copyfile(wad_source, offline_deps / "doom1.wad")
        docker_text = dockerfile.read_text(encoding="utf-8")
        dead_download = (
            "RUN curl https://distro.ibiblio.org/slitaz/sources/packages/d/doom1.wad "
            "> doom.wad"
        )
        if dead_download not in docker_text:
            raise ValueError("Expected upstream Doom WAD download was not found")
        dockerfile.write_text(
            docker_text.replace(
                dead_download,
                "COPY offline-deps/doom1.wad /app/doom.wad",
                1,
            ),
            encoding="utf-8",
        )

    task_toml = task_root / "task.toml"
    task_text = task_toml.read_text(encoding="utf-8")
    filtered = "\n".join(
        line for line in task_text.splitlines() if not line.strip().startswith("docker_image")
    )
    task_toml.write_text(filtered + "\n", encoding="utf-8")
    return selected


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        file_digest = bytes.fromhex(sha256_file(path))
        digest.update(file_digest)
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
        file_digest = bytes.fromhex(sha256_file(path))
        digest.update(file_digest)
    return digest.hexdigest()


def component_digest(root: Path, name: str) -> str | None:
    path = root / name
    if not path.exists():
        return None
    return tree_digest(path) if path.is_dir() else sha256_file(path)


def write_offline_compose(path: Path) -> None:
    compose = {
        "services": {
            "main": {"networks": ["agent-internal", "default"]},
            "model-relay": {
                "image": MODEL_RELAY_IMAGE,
                "environment": {
                    "TARGET_HOST": "host.docker.internal",
                    "TARGET_PORT": "10101",
                    "LOCAL_AUTHORITY": "127.0.0.1:10101",
                },
                "extra_hosts": ["host.docker.internal:host-gateway"],
                "networks": ["agent-internal", "default"],
                "read_only": True,
                "cap_drop": ["ALL"],
                "security_opt": ["no-new-privileges:true"],
                "tmpfs": ["/tmp:size=8m,mode=1777"],
            },
        },
        "networks": {"agent-internal": {"internal": True}, "default": {}},
    }
    path.write_text(
        json.dumps(compose, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_condition_hashes(conditions_root: Path) -> dict[str, str | None]:
    return {
        "baseline": None,
        "causeloom": sha256_file(
            conditions_root / "causeloom" / "POLICY.md"
        ),
    }


def load_condition_plan(
    path: Path | None, suite_ids: list[str]
) -> tuple[dict[str, list[str]], dict[str, object] | None]:
    if path is None:
        return {task_id: list(CONDITIONS) for task_id in suite_ids}, None
    plan = json.loads(path.read_text(encoding="utf-8"))
    default = plan.get("default_conditions")
    overrides = plan.get("task_conditions", {})
    if not isinstance(default, list) or not isinstance(overrides, dict):
        raise ValueError(
            "Condition plan must define default_conditions and task_conditions"
        )
    unknown_tasks = set(overrides) - set(suite_ids)
    if unknown_tasks:
        raise ValueError(f"Condition plan has unknown task IDs: {sorted(unknown_tasks)}")
    result: dict[str, list[str]] = {}
    for task_id in suite_ids:
        values = overrides.get(task_id, default)
        if not isinstance(values, list) or not values or not all(
            isinstance(value, str) and value in CONDITIONS for value in values
        ):
            raise ValueError(f"Invalid conditions for {task_id}: {values}")
        if len(values) != len(set(values)):
            raise ValueError(f"Duplicate conditions for {task_id}: {values}")
        result[task_id] = list(values)
    return result, plan


def prepare(
    suite_path: Path,
    matrix_path: Path,
    upstream_root: Path,
    output_root: Path,
    conditions_root: Path,
    assets_root: Path,
    worker_slots: int = 5,
    condition_plan_path: Path | None = None,
    max_parallel_runs_per_task: int = MAX_PARALLEL_RUNS_PER_TASK,
    scheduler_memory_budget_gb: float = SCHEDULER_MEMORY_BUDGET_GB,
) -> dict[str, object]:
    if max_parallel_runs_per_task < 1:
        raise ValueError("max_parallel_runs_per_task must be positive")
    if scheduler_memory_budget_gb <= 0:
        raise ValueError("scheduler_memory_budget_gb must be positive")
    suite = read_rows(suite_path)
    matrix = read_rows(matrix_path)
    if len(suite) != EXPECTED_TASKS:
        raise ValueError(f"Expected {EXPECTED_TASKS} tasks, found {len(suite)}")
    ordered_suite_ids = [row["suite_task_id"] for row in suite]
    suite_ids = set(ordered_suite_ids)
    condition_plan, condition_plan_data = load_condition_plan(
        condition_plan_path, ordered_suite_ids
    )
    expected_runs = sum(
        len(condition_plan[task_id]) * REPETITIONS for task_id in ordered_suite_ids
    )
    if len(matrix) != expected_runs:
        raise ValueError(f"Expected {expected_runs} runs, found {len(matrix)}")
    if {row["task_id"] for row in matrix} != suite_ids:
        raise ValueError("Matrix task IDs do not match research suite")
    for task_id in ordered_suite_ids:
        task_rows = [row for row in matrix if row["task_id"] == task_id]
        actual = {(row["condition"], int(row["repetition"])) for row in task_rows}
        expected = {
            (condition, repetition)
            for condition in condition_plan[task_id]
            for repetition in range(1, REPETITIONS + 1)
        }
        if actual != expected or len(task_rows) != len(expected):
            raise ValueError(f"Matrix does not match condition plan for {task_id}")
        for row in task_rows:
            expected_run_id = (
                f"{task_id}-{row['condition']}-r{int(row['repetition'])}"
            )
            if row["run_id"] != expected_run_id:
                raise ValueError(f"Invalid run ID for {task_id}: {row['run_id']}")

    tasks_root = output_root / f"tasks-{ADAPTATION_VERSION}"
    tasks_root.mkdir(parents=True, exist_ok=True)
    task_locks: list[dict[str, object]] = []
    task_runs: dict[str, list[dict[str, str]]] = {}

    for row in suite:
        suite_id = row["suite_task_id"]
        upstream_id = row["upstream_task_id"]
        source = upstream_root / upstream_id
        if not source.is_dir():
            raise FileNotFoundError(f"Missing upstream task: {source}")

        upstream_digest = tree_digest(source)
        destination = tasks_root / (
            f"{suite_id}--{upstream_id}--{ADAPTATION_VERSION}--{upstream_digest[:12]}"
        )
        if destination.exists():
            marker = destination / ".research-adaptation.json"
            if not marker.is_file():
                raise FileExistsError(
                    f"Refusing to reuse unmarked task directory: {destination}"
                )
            existing = json.loads(marker.read_text(encoding="utf-8"))
            if (
                existing.get("upstream_digest") != upstream_digest
                or existing.get("adaptation_version", ADAPTATION_VERSION)
                != ADAPTATION_VERSION
            ):
                raise ValueError(f"Stale adapted task directory: {destination}")
        else:
            shutil.copytree(source, destination)
            adapt_task_toml(destination / "task.toml")
            preinstalled_packages = preinstall_offline_dependencies(
                upstream_id, destination, assets_root
            )
            marker_payload = {
                "dataset": DATASET,
                "adaptation_version": ADAPTATION_VERSION,
                "suite_task_id": suite_id,
                "upstream_task_id": upstream_id,
                "upstream_digest": upstream_digest,
                "adaptation": {
                    "agent_network_mode": "no-network",
                    "agent_timeout_multiplier": AGENT_TIMEOUT_MULTIPLIER,
                    "network_overlay": "dynamic-public-with-fixed-model-relay",
                    "preinstalled_packages": preinstalled_packages,
                },
            }
            (destination / ".research-adaptation.json").write_text(
                json.dumps(marker_payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

        task_toml = (destination / "task.toml").read_text(encoding="utf-8")
        docker_image = next(
            (
                line.split("=", 1)[1].strip().strip('"')
                for line in task_toml.splitlines()
                if line.strip().startswith("docker_image")
            ),
            None,
        )
        task_locks.append(
            {
                "suite_task_id": suite_id,
                "upstream_task_id": upstream_id,
                "tier": row["tier"],
                "source_path": source.as_posix(),
                "adapted_path": destination.as_posix(),
                "upstream_digest": upstream_digest,
                "adapted_digest": tree_digest(destination),
                "execution_digest": execution_tree_digest(destination),
                "instruction_sha256": component_digest(source, "instruction.md"),
                "task_toml_sha256": component_digest(source, "task.toml"),
                "environment_sha256": component_digest(source, "environment"),
                "tests_sha256": component_digest(source, "tests"),
                "solution_sha256": component_digest(source, "solution"),
                "docker_image": docker_image,
                "environment_memory_gb": environment_memory_gb(task_toml),
            }
        )
        task_runs[suite_id] = sorted(
            (item for item in matrix if item["task_id"] == suite_id),
            key=lambda item: int(item["execution_order"]),
        )

    worker_tasks = build_worker_tasks(ordered_suite_ids, worker_slots)
    worker_plan = {
        worker_id: sorted(
            (run for task_id in task_ids for run in task_runs[task_id]),
            key=lambda item: int(item["execution_order"]),
        )
        for worker_id, task_ids in worker_tasks.items()
    }
    if len(worker_plan) != worker_slots:
        raise ValueError(f"Expected {worker_slots} worker slots")
    if sum(len(runs) for runs in worker_plan.values()) != expected_runs:
        raise ValueError(f"Worker plan must contain exactly {expected_runs} runs")
    if (
        len({run["run_id"] for runs in worker_plan.values() for run in runs})
        != expected_runs
    ):
        raise ValueError(f"Worker plan must contain {expected_runs} unique run IDs")

    compose_path = output_root / "docker-compose.offline.json"
    output_root.mkdir(parents=True, exist_ok=True)
    write_offline_compose(compose_path)
    lock: dict[str, object] = {
        "schema_version": 2,
        "dataset": DATASET,
        "adaptation_version": ADAPTATION_VERSION,
        "agent_timeout_multiplier": AGENT_TIMEOUT_MULTIPLIER,
        "run_order_seed": 329,
        "planned_runs": expected_runs,
        "matrix_sha256": sha256_file(matrix_path),
        "suite_sha256": sha256_file(suite_path),
        "condition_plan_sha256": (
            sha256_file(condition_plan_path) if condition_plan_path is not None else None
        ),
        "condition_plan": condition_plan_data,
        "condition_sha256": load_condition_hashes(conditions_root),
        "common_instruction_sha256": sha256_file(
            suite_path.parent / "harbor" / "common-instructions.md"
        ),
        "network_policy": {
            "container_network": "internal",
            "environment_and_verifier_network": "public",
            "agent_network": "no-network-plus-fixed-model-relay",
            "model_relay": MODEL_RELAY_IMAGE,
            "model_relay_target": "host.docker.internal:10101",
            "general_proxy": False,
            "web_search": "disabled",
            "mcp_servers": [],
        },
        "scheduler": {
            "mode": SCHEDULER_MODE,
            "max_parallel_runs_per_task": max_parallel_runs_per_task,
            "memory_budget_gb": scheduler_memory_budget_gb,
            "priority": "seeded-global-execution-order",
        },
        "offline_compose_path": compose_path.as_posix(),
        "offline_assets": {
            "doom1.wad": {
                "sha256": DOOM_WAD_SHA256,
                "source_image": DOOM_WAD_SOURCE_IMAGE,
            }
        },
        "tasks": task_locks,
        "workers": worker_plan,
        "worker_slots": worker_slots,
        "worker_tasks": worker_tasks,
    }
    (output_root / "benchmark-lock.json").write_text(
        json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return lock


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", type=Path, default=Path("evals/research-suite.csv"))
    parser.add_argument("--matrix", type=Path, default=Path("work/research-runs.csv"))
    parser.add_argument(
        "--upstream-root",
        type=Path,
        default=Path("work/upstream/terminal-bench"),
    )
    parser.add_argument(
        "--output-root", type=Path, default=Path("work/research-benchmark-dynamic")
    )
    parser.add_argument(
        "--conditions-root", type=Path, default=Path("evals/conditions")
    )
    parser.add_argument(
        "--assets-root", type=Path, default=Path("work/upstream-assets")
    )
    parser.add_argument(
        "--condition-plan",
        type=Path,
        help="Optional per-task condition plan used to validate a partial matrix",
    )
    parser.add_argument(
        "--worker-slots",
        type=int,
        default=5,
        help="Freeze five balanced task queues or one queue per suite task",
    )
    parser.add_argument(
        "--max-parallel-runs-per-task",
        type=int,
        default=MAX_PARALLEL_RUNS_PER_TASK,
        help="Freeze the per-task concurrency cap for work-conserving scheduling",
    )
    parser.add_argument(
        "--scheduler-memory-budget-gb",
        type=float,
        default=SCHEDULER_MEMORY_BUDGET_GB,
        help="Freeze the aggregate task-container memory budget",
    )
    args = parser.parse_args()
    lock = prepare(
        args.suite,
        args.matrix,
        args.upstream_root,
        args.output_root,
        args.conditions_root,
        args.assets_root,
        args.worker_slots,
        args.condition_plan,
        args.max_parallel_runs_per_task,
        args.scheduler_memory_budget_gb,
    )
    print(
        f"Prepared {len(lock['tasks'])} tasks and "
        f"{sum(len(value) for value in lock['workers'].values())} runs "
        f"across {len(lock['workers'])} worker slots"
    )


if __name__ == "__main__":
    main()
