from __future__ import annotations

import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "evals/scripts/prepare_research_benchmark.py"
SPEC = importlib.util.spec_from_file_location("prepare_research_benchmark", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PrepareResearchBenchmarkTest(unittest.TestCase):
    def test_environment_memory_is_normalized_to_gigabytes(self):
        self.assertEqual(
            MODULE.environment_memory_gb('[environment]\nmemory = "4G"\n'), 4.0
        )
        self.assertEqual(
            MODULE.environment_memory_gb('[environment]\nmemory = "2048M"\n'), 2.0
        )
        with self.assertRaisesRegex(ValueError, "Unsupported task memory"):
            MODULE.environment_memory_gb('[environment]\nmemory = "unlimited"\n')

    def test_tree_digest_is_stable_and_path_sensitive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a").mkdir()
            (root / "a" / "file.txt").write_text("same", encoding="utf-8")
            first = MODULE.tree_digest(root)
            self.assertEqual(first, MODULE.tree_digest(root))
            (root / "a" / "file.txt").rename(root / "other.txt")
            self.assertNotEqual(first, MODULE.tree_digest(root))

    def test_offline_compose_isolates_main_behind_fixed_relay(self):
        with tempfile.TemporaryDirectory() as temp:
            compose_path = Path(temp) / "compose.json"
            MODULE.write_offline_compose(compose_path)
            compose = json.loads(compose_path.read_text(encoding="utf-8"))
            self.assertEqual(
                compose["services"]["main"]["networks"],
                ["agent-internal", "default"],
            )
            self.assertTrue(compose["networks"]["agent-internal"]["internal"])
            self.assertEqual(
                compose["services"]["model-relay"]["networks"],
                ["agent-internal", "default"],
            )
            self.assertNotIn("ports", compose["services"]["model-relay"])

    def test_task_agent_phase_is_no_network_and_has_no_timeout(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "task.toml"
            path.write_text(
                "[verifier]\n"
                "timeout_sec = 10.0\n\n"
                "[agent]\n"
                "timeout_sec = 10.0\n\n"
                "[environment]\n"
                "build_timeout_sec = 5.0\n",
                encoding="utf-8",
            )
            MODULE.adapt_task_toml(path)
            adapted = path.read_text(encoding="utf-8")
            self.assertIn('network_mode = "no-network"', adapted)
            agent_section = adapted.split("[agent]", 1)[1].split(
                "[environment]", 1
            )[0]
            self.assertNotIn("timeout_sec", agent_section)
            self.assertIn("[verifier]\ntimeout_sec = 10.0", adapted)
            self.assertIn("[environment]\nbuild_timeout_sec = 5.0", adapted)

    def test_task_agent_phase_accepts_an_already_unlimited_task(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "task.toml"
            path.write_text("[agent]\n\n[environment]\n", encoding="utf-8")
            MODULE.adapt_task_toml(path)
            adapted = path.read_text(encoding="utf-8")
            agent_section = adapted.split("[agent]", 1)[1].split(
                "[environment]", 1
            )[0]
            self.assertIn('network_mode = "no-network"', agent_section)
            self.assertNotIn("timeout_sec", agent_section)

    def test_task_agent_phase_rejects_a_non_numeric_timeout(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "task.toml"
            path.write_text(
                '[agent]\ntimeout_sec = "forever"\n\n[environment]\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "must be numeric"):
                MODULE.adapt_task_toml(path)

    def test_only_declared_infrastructure_is_preinstalled(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "environment").mkdir()
            (root / "environment" / "Dockerfile").write_text(
                "FROM ubuntu:24.04\n", encoding="utf-8"
            )
            (root / "task.toml").write_text(
                '[environment]\ndocker_image = "mutable:tag"\n', encoding="utf-8"
            )
            packages = MODULE.preinstall_offline_dependencies(
                "sqlite-with-gcov", root, root / "assets"
            )
            self.assertEqual(
                packages, ["fossil", "gcc", "jimsh", "tclsh", "make", "tzdata"]
            )
            self.assertNotIn(
                "docker_image", (root / "task.toml").read_text(encoding="utf-8")
            )
            dockerfile = (root / "environment" / "Dockerfile").read_text(
                encoding="utf-8"
            )
            self.assertIn("infrastructure only, no solution code", dockerfile)

    def test_grpc_dependencies_are_preinstalled_without_solution_code(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "environment").mkdir()
            (root / "environment" / "Dockerfile").write_text(
                "FROM python:3.13-slim-bookworm\nWORKDIR /app\n",
                encoding="utf-8",
            )
            (root / "task.toml").write_text(
                '[environment]\ndocker_image = "mutable:tag"\n', encoding="utf-8"
            )
            packages = MODULE.preinstall_offline_dependencies(
                "kv-store-grpc", root, root / "assets"
            )
            self.assertEqual(
                packages, ["grpcio==1.73.0", "grpcio-tools==1.73.0"]
            )
            dockerfile = (root / "environment" / "Dockerfile").read_text(
                encoding="utf-8"
            )
            self.assertIn(
                "pip install --no-cache-dir grpcio==1.73.0 grpcio-tools==1.73.0",
                dockerfile,
            )
            self.assertNotIn("server.py", dockerfile)
            self.assertNotIn(
                "docker_image", (root / "task.toml").read_text(encoding="utf-8")
            )

    def test_worker_assignments_use_one_slot_per_task(self):
        suite_ids = [
            "M01", "M02", "M03", "X01", "X02", "X03", "X04", "X05",
            "X06", "X07", "C01", "C02", "C03",
        ]
        thirteen = MODULE.build_worker_tasks(suite_ids)
        self.assertEqual(len(thirteen), 13)
        self.assertTrue(all(len(tasks) == 1 for tasks in thirteen.values()))
        self.assertEqual(
            {task for tasks in thirteen.values() for task in tasks}, set(suite_ids)
        )
        self.assertEqual(MODULE.STANDARD_MAX_WORKERS, 8)
        self.assertEqual(MODULE.ADAPTATION_VERSION, "a7")
        self.assertEqual(MODULE.LOCK_SCHEMA_VERSION, 3)

    def test_checked_in_matrix_supports_one_queue_per_task(self):
        matrix = ROOT / "work/research-runs.csv"
        if not matrix.exists():
            self.skipTest("generated matrix is intentionally ignored")
        with matrix.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        task_runs: dict[str, list[dict[str, str]]] = {}
        for row in rows:
            task_runs.setdefault(row["task_id"], []).append(row)
        worker_tasks = MODULE.build_worker_tasks(list(task_runs))
        workers = {
            worker: [run for task in tasks for run in task_runs[task]]
            for worker, tasks in worker_tasks.items()
        }
        self.assertEqual(len(workers), 13)
        self.assertTrue(all(len(tasks) == 1 for tasks in worker_tasks.values()))
        self.assertTrue(all(len(runs) == 6 for runs in workers.values()))
        self.assertEqual(len({row["run_id"] for row in rows}), 78)


if __name__ == "__main__":
    unittest.main()
