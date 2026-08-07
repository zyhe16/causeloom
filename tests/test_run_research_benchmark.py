from __future__ import annotations

import importlib.util
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RUNNER = load("run_research_benchmark", ROOT / "evals/scripts/run_research_benchmark.py")
CONFIG = load(
    "prepare_codex_benchmark_config",
    ROOT / "evals/scripts/prepare_codex_benchmark_config.py",
)


class RunResearchBenchmarkTest(unittest.TestCase):
    def test_condition_hashes_must_match_locked_policies(self):
        original = RUNNER.CONDITION_PATHS
        try:
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                paths = {}
                expected = {"baseline": None}
                for condition in ("causeloom",):
                    path = root / f"{condition}.md"
                    data = f"{condition}\n".encode()
                    path.write_bytes(data)
                    paths[condition] = path
                    expected[condition] = hashlib.sha256(data).hexdigest()
                RUNNER.CONDITION_PATHS = paths
                RUNNER.validate_condition_hashes({"condition_sha256": expected})
                paths["causeloom"].write_text("changed", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "causeloom"):
                    RUNNER.validate_condition_hashes({"condition_sha256": expected})
        finally:
            RUNNER.CONDITION_PATHS = original

    def test_completed_run_requires_a_parseable_terminal_result(self):
        with tempfile.TemporaryDirectory() as temp:
            jobs = Path(temp)
            result = jobs / "M01-causeloom-r1" / "trial" / "result.json"
            result.parent.mkdir(parents=True)
            result.write_text("{}", encoding="utf-8")
            self.assertFalse(
                RUNNER.completed_run(jobs, "M01-causeloom-r1")
            )
            result.write_text('{"reward": 1}', encoding="utf-8")
            self.assertFalse(
                RUNNER.completed_run(jobs, "M01-causeloom-r1")
            )
            result.write_text(
                '{"reward": 1, "finished_at": "2026-08-06T00:00:00Z"}',
                encoding="utf-8",
            )
            self.assertTrue(
                RUNNER.completed_run(jobs, "M01-causeloom-r1")
            )

    def test_completed_run_retries_docker_infrastructure_but_not_agent_timeout(self):
        with tempfile.TemporaryDirectory() as temp:
            jobs = Path(temp)
            result = jobs / "X02-baseline-r1" / "trial" / "result.json"
            result.parent.mkdir(parents=True)
            result.write_text(
                '{"finished_at":"2026-08-06T00:00:00Z",'
                '"exception_info":{"exception_type":"RuntimeError",'
                '"exception_message":"Docker compose command failed: all predefined '
                'address pools have been fully subnetted"}}',
                encoding="utf-8",
            )
            self.assertTrue(
                RUNNER.retryable_infrastructure_run(jobs, "X02-baseline-r1")
            )
            self.assertFalse(RUNNER.completed_run(jobs, "X02-baseline-r1"))
            result.write_text(
                '{"finished_at":"2026-08-06T00:00:00Z",'
                '"exception_info":{"exception_type":"AgentTimeoutError",'
                '"exception_message":"Agent timed out"}}',
                encoding="utf-8",
            )
            self.assertFalse(
                RUNNER.retryable_infrastructure_run(jobs, "X02-baseline-r1")
            )
            self.assertTrue(RUNNER.completed_run(jobs, "X02-baseline-r1"))

    def test_archive_existing_attempt_preserves_raw_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            jobs = root / "jobs"
            source = jobs / "X02-baseline-r1"
            source.mkdir(parents=True)
            (source / "raw.txt").write_text("evidence", encoding="utf-8")
            target = RUNNER.archive_existing_attempt(
                jobs, root / "archive", "X02-baseline-r1", "infrastructure"
            )
            self.assertFalse(source.exists())
            self.assertEqual((target / "raw.txt").read_text(), "evidence")
            self.assertTrue((target / "ARCHIVE_RECEIPT.json").is_file())

    def test_status_write_retries_transient_windows_replace_error(self):
        with tempfile.TemporaryDirectory() as temp:
            status = Path(temp) / "status.json"
            original_replace = Path.replace
            calls = 0

            def flaky_replace(source, target):
                nonlocal calls
                calls += 1
                if calls < 3:
                    raise PermissionError("temporarily locked")
                return original_replace(source, target)

            with mock.patch.object(Path, "replace", new=flaky_replace), mock.patch.object(
                RUNNER.time, "sleep"
            ) as sleep:
                RUNNER.write_status(status, {"state": "running"})

            self.assertEqual(calls, 3)
            self.assertEqual(sleep.call_count, 2)
            self.assertEqual(status.read_text(encoding="utf-8"), '{\n  "state": "running"\n}\n')

    def test_worker_plan_accepts_thirteen_task_slots_with_bounded_concurrency(self):
        tasks = {f"T{index:02d}": {} for index in range(13)}
        worker_tasks = {
            f"worker-{index + 1:02d}": [task_id]
            for index, task_id in enumerate(tasks)
        }
        workers = {}
        for worker_id, task_ids in worker_tasks.items():
            task_id = task_ids[0]
            workers[worker_id] = [
                {
                    "run_id": f"{task_id}-condition-r{repetition}",
                    "task_id": task_id,
                    "condition": "condition",
                    "repetition": str(repetition),
                }
                for repetition in range(1, 7)
            ]
        self.assertEqual(
            RUNNER.validate_worker_plan(workers, worker_tasks, tasks, 78), 78
        )

    def test_worker_plan_rejects_duplicate_run_ids(self):
        tasks = {"M01": {}}
        worker_tasks = {"worker-01": ["M01"]}
        workers = {
            "worker-01": [
                {"run_id": "same", "task_id": "M01"} for _ in range(12)
            ]
        }
        with self.assertRaisesRegex(ValueError, "duplicate run IDs"):
            RUNNER.validate_worker_plan(workers, worker_tasks, tasks, 12)

    def test_harbor_command_inherits_model_and_effort_from_config(self):
        command = RUNNER.harbor_command(
            Path("harbor"),
            Path("task"),
            Path("jobs"),
            {
                "run_id": "M01-baseline-r1",
                "task_id": "M01",
                "condition": "baseline",
                "repetition": "1",
            },
            "0.146.0",
            Path("codex"),
            "a" * 64,
            Path("config.toml"),
            Path("compose.json"),
            Path("common.md"),
            Path("auth.json"),
            "http://model-relay:10101/v1",
        )
        self.assertNotIn("--model", command)
        self.assertFalse(any("reasoning_effort" in item for item in command))
        self.assertIn("evals.harbor.offline_codex:OfflineConfiguredCodex", command)
        self.assertIn("web_search=disabled", command)

    def test_isolated_config_copies_only_verified_selection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.toml"
            output = root / "output.toml"
            source.write_text(
                'model = "gpt-5.6-sol"\n'
                'model_reasoning_effort = "high"\n'
                '[mcp_servers.example]\ncommand = "should-not-copy"\n',
                encoding="utf-8",
            )
            CONFIG.prepare(source, output, "gpt-5.6-sol", "high")
            self.assertEqual(
                output.read_text(encoding="utf-8"),
                'model = "gpt-5.6-sol"\nmodel_reasoning_effort = "high"\n',
            )


if __name__ == "__main__":
    unittest.main()
