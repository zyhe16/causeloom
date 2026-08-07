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
        benchmark = self.data["benchmark"]
        self.assertEqual(benchmark["model"], "gpt-5.6-luna")
        self.assertEqual(benchmark["reasoning_effort"], "max")
        self.assertEqual(benchmark["planned_runs"], 78)
        self.assertEqual(benchmark["audit_violations"], 0)
        self.assertEqual(benchmark["audit_warnings"], 0)

        rows = self.data["matched_13_task_result"]["conditions"]
        self.assertEqual(
            [row["name"] for row in rows],
            ["No-skill baseline", "Causeloom"],
        )
        for row in rows:
            self.assertEqual(row["runs"], 39)
            self.assertEqual(row["timeouts"], 0)
            self.assertEqual(row["exception_free_reward_1"], row["reward_1"])
            self.assertEqual(
                row["mean_tokens_per_attempted_run"],
                round(row["total_tokens"] / row["runs"]),
            )

        by_name = {row["name"]: row for row in rows}
        self.assertEqual(by_name["No-skill baseline"]["reward_1"], 21)
        self.assertEqual(by_name["Causeloom"]["reward_1"], 28)
        self.assertEqual(
            by_name["Causeloom"]["mean_tokens_per_attempted_run"], 2491074
        )
        self.assertLess(
            by_name["Causeloom"]["total_tokens"],
            by_name["No-skill baseline"]["total_tokens"],
        )

    def test_task_and_category_totals_match_overall_result(self):
        tasks = self.data["task_results"]
        self.assertEqual(len(tasks), 13)
        self.assertEqual(sum(row["baseline_reward_1"] for row in tasks), 21)
        self.assertEqual(sum(row["causeloom_reward_1"] for row in tasks), 28)

        categories = self.data["category_results"]
        self.assertEqual(sum(row["runs_per_condition"] for row in categories), 39)
        self.assertEqual(sum(row["baseline_reward_1"] for row in categories), 21)
        self.assertEqual(sum(row["causeloom_reward_1"] for row in categories), 28)
        extreme = next(row for row in categories if row["category"] == "Extreme systems")
        self.assertEqual((extreme["baseline_reward_1"], extreme["causeloom_reward_1"]), (7, 12))

    def test_causeloom_only_successes_are_matched_and_consistent(self):
        rows = self.data["causeloom_only_successes"]["tasks"]
        self.assertEqual([row["task_id"] for row in rows], ["X03", "C02"])
        self.assertEqual(sum(row["baseline_reward_1"] for row in rows), 0)
        self.assertEqual(sum(row["causeloom_reward_1"] for row in rows), 4)
        for row in rows:
            self.assertEqual(row["runs_per_condition"], 3)
            self.assertGreater(row["causeloom_reward_1"], row["baseline_reward_1"])

    def test_readme_and_charts_publish_only_the_matched_luna_result(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        normalized = " ".join(readme.split())
        self.assertIn("fully matched run", normalized)
        self.assertIn("GPT-5.6 Luna, max reasoning", normalized)
        self.assertIn("[benchmark](#results)", readme)
        self.assertIn("**33.3% relative improvement**", normalized)
        self.assertIn("Code-quality review", readme)
        self.assertIn("### 5. Use the simplest batching rule", readme)
        self.assertNotIn("GPT-5.6 Sol", readme)
        self.assertNotIn("two batches", readme)
        self.assertNotIn("20/39 (51.3%)", readme)
        self.assertNotIn("27/39 (69.2%)", readme)

        expected = {
            "benchmark-full.svg": "Matched 13-task benchmark results",
            "benchmark-luna-by-category.svg": "Matched benchmark results by task category",
            "benchmark-luna-only-wins.svg": "Tasks solved only by Causeloom",
        }
        assets = ROOT / "docs" / "assets"
        self.assertEqual(
            sorted(path.name for path in assets.glob("benchmark-*.svg")),
            sorted(expected),
        )
        for filename, title in expected.items():
            svg = (assets / filename).read_text(encoding="utf-8")
            self.assertIn(f'<title id="title">{title}</title>', svg)
            self.assertIn('role="img" aria-labelledby="title desc"', svg)


if __name__ == "__main__":
    unittest.main()
