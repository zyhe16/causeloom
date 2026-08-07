from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = ROOT / "docs" / "benchmarks"


class BenchmarkPublicationTest(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(
            (BENCHMARKS / "results.json").read_text(encoding="utf-8")
        )

    def test_published_metrics_are_internally_consistent(self):
        rows = self.data["full_13_task_context"]["conditions"]
        self.assertEqual(
            [row["name"] for row in rows],
            ["No-skill baseline", "Causeloom"],
        )
        for row in rows:
            self.assertEqual(row["runs"], 39)
            self.assertEqual(row["a5_runs"] + row["a3_runs"], 39)
            self.assertLessEqual(row["exception_free_reward_1"], row["reward_1"])
            self.assertLessEqual(row["reward_1"], row["runs"])
            self.assertLessEqual(row["timeouts"], row["runs"])

        by_name = {row["name"]: row for row in rows}
        self.assertEqual(by_name["Causeloom"]["reward_1"], 27)
        self.assertEqual(by_name["Causeloom"]["exception_free_reward_1"], 25)
        self.assertEqual(by_name["Causeloom"]["mean_tokens_per_attempted_run"], 523594)
        self.assertEqual(by_name["Causeloom"]["mean_tokens_per_successful_run"], 539583)
        self.assertEqual(by_name["Causeloom"]["a3_runs"], 0)

    def test_readme_discloses_limits_and_single_chart_exists(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        normalized_readme = " ".join(readme.split())
        self.assertIn("descriptive evidence, not a fully matched causal estimate", normalized_readme)
        self.assertIn("does not make hosted model trajectories deterministic", normalized_readme)
        self.assertIn("Code-quality review", readme)
        svg = (ROOT / "docs" / "assets" / "benchmark-full.svg").read_text(
            encoding="utf-8"
        )
        self.assertIn('<title id="title">13-task benchmark results</title>', svg)
        self.assertEqual(
            sorted(path.name for path in (ROOT / "docs" / "assets").glob("benchmark-*.svg")),
            ["benchmark-full.svg"],
        )


if __name__ == "__main__":
    unittest.main()
