from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "evals/scripts/generate_run_matrix.py"


class GenerateRunMatrixTest(unittest.TestCase):
    def test_matrix_is_balanced_and_deterministic(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            tasks = temp_path / "tasks.csv"
            tasks.write_text("task_id\nA\nB\n", encoding="utf-8")
            outputs = []
            for name in ("one.csv", "two.csv"):
                output = temp_path / name
                subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT),
                        "--tasks", str(tasks),
                        "--conditions", "baseline,causeloom",
                        "--repetitions", "3",
                        "--seed", "329",
                        "--output", str(output),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                outputs.append(output.read_text(encoding="utf-8"))
            self.assertEqual(outputs[0], outputs[1])
            rows = list(csv.DictReader(outputs[0].splitlines()))
            self.assertEqual(len(rows), 12)
            self.assertEqual(len({row["run_id"] for row in rows}), 12)
            counts = Counter((row["task_id"], row["condition"]) for row in rows)
            self.assertTrue(all(value == 3 for value in counts.values()))

    def test_accepts_research_suite_task_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            tasks = temp_path / "research.csv"
            tasks.write_text(
                "suite_task_id,upstream_task_id\nM01,one\nX01,two\n",
                encoding="utf-8",
            )
            output = temp_path / "matrix.csv"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--tasks", str(tasks),
                    "--conditions", "baseline,causeloom",
                    "--repetitions", "3",
                    "--output", str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            with output.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 12)
            self.assertEqual({row["task_id"] for row in rows}, {"M01", "X01"})

    def test_condition_plan_supports_incremental_task_scope(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            tasks = temp_path / "tasks.csv"
            tasks.write_text("task_id\nA\nB\n", encoding="utf-8")
            plan = temp_path / "plan.json"
            plan.write_text(
                json.dumps(
                    {
                        "default_conditions": ["causeloom"],
                        "task_conditions": {
                            "B": ["baseline", "causeloom"]
                        },
                    }
                ),
                encoding="utf-8",
            )
            output = temp_path / "matrix.csv"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--tasks", str(tasks),
                    "--condition-plan", str(plan),
                    "--repetitions", "3",
                    "--seed", "329",
                    "--output", str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            with output.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 9)
            counts = Counter((row["task_id"], row["condition"]) for row in rows)
            self.assertEqual(
                counts,
                Counter({("A", "causeloom"): 3, ("B", "baseline"): 3, ("B", "causeloom"): 3}),
            )


if __name__ == "__main__":
    unittest.main()
