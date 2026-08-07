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

    def test_task_agent_phase_is_no_network_and_timeout_is_quadrupled(self):
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
            self.assertIn("[agent]\nnetwork_mode = \"no-network\"\ntimeout_sec = 40.0", adapted)
            self.assertIn("[verifier]\ntimeout_sec = 10.0", adapted)
            self.assertIn("[environment]\nbuild_timeout_sec = 5.0", adapted)

    def test_task_agent_phase_requires_a_numeric_timeout(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "task.toml"
            path.write_text("[agent]\n\n[environment]\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "agent timeout_sec"):
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

    def test_worker_assignments_support_five_or_one_slot_per_task(self):
        suite_ids = [
            "M01", "M02", "M03", "X01", "X02", "X03", "X04", "X05",
            "X06", "X07", "C01", "C02", "C03",
        ]
        five = MODULE.build_worker_tasks(suite_ids, 5)
        thirteen = MODULE.build_worker_tasks(suite_ids, 13)
        self.assertEqual(five, MODULE.FIVE_WORKER_TASKS)
        self.assertEqual(len(thirteen), 13)
        self.assertTrue(all(len(tasks) == 1 for tasks in thirteen.values()))
        self.assertEqual(
            {task for tasks in thirteen.values() for task in tasks}, set(suite_ids)
        )
        with self.assertRaises(ValueError):
            MODULE.build_worker_tasks(suite_ids, 8)

    def test_checked_in_matrix_supports_five_two_task_workers(self):
        matrix = ROOT / "work/research-runs.csv"
        if not matrix.exists():
            self.skipTest("generated matrix is intentionally ignored")
        with matrix.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        task_runs: dict[str, list[dict[str, str]]] = {}
        for row in rows:
            task_runs.setdefault(row["task_id"], []).append(row)
        workers = {
            worker: [run for task in tasks for run in task_runs[task]]
            for worker, tasks in MODULE.FIVE_WORKER_TASKS.items()
        }
        self.assertEqual(len(workers), 5)
        self.assertEqual(sorted(len(runs) for runs in workers.values()), [12, 12, 18, 18, 18])
        self.assertEqual(
            sorted(len(tasks) for tasks in MODULE.FIVE_WORKER_TASKS.values()),
            [2, 2, 3, 3, 3],
        )
        self.assertEqual(len({row["run_id"] for row in rows}), 78)


if __name__ == "__main__":
    unittest.main()
