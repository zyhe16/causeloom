from __future__ import annotations

import csv
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evals" / "research-suite.csv"


class ResearchSuiteTest(unittest.TestCase):
    def test_preregistered_suite_shape_and_provenance(self):
        with MANIFEST.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 13)
        self.assertEqual(
            Counter(row["tier"] for row in rows),
            {"medium": 3, "extreme": 7, "coverage": 3},
        )
        self.assertEqual(len({row["suite_task_id"] for row in rows}), 13)
        self.assertEqual(len({row["upstream_task_id"] for row in rows}), 13)
        upstream_ids = {row["upstream_task_id"] for row in rows}
        self.assertTrue(
            {"git-multibranch", "sqlite-with-gcov", "make-doom-for-mips"}
            <= upstream_ids
        )
        self.assertTrue({"pypi-server", "build-cython-ext"}.isdisjoint(upstream_ids))
        self.assertTrue(
            {
                "modernize-scientific-stack",
                "kv-store-grpc",
                "fix-code-vulnerability",
            }
            <= upstream_ids
        )

        for row in rows:
            self.assertEqual(row["upstream_benchmark"], "Terminal-Bench")
            self.assertEqual(row["upstream_version"], "2.0")
            self.assertTrue(row["task_url"].endswith("/" + row["upstream_task_id"]))
            position, total = (int(value) for value in row["paper_empirical_order"].split("/"))
            self.assertEqual(total, 89)
            self.assertGreaterEqual(position, 1)
            self.assertLessEqual(position, total)

        medium = [row for row in rows if row["tier"] == "medium"]
        self.assertTrue(all(row["author_difficulty"] == "medium" for row in medium))

        extreme = [row for row in rows if row["tier"] == "extreme"]
        self.assertTrue(all(int(row["paper_empirical_order"].split("/")[0]) >= 52 for row in extreme))

        coverage = [row for row in rows if row["tier"] == "coverage"]
        self.assertEqual(
            [row["upstream_task_id"] for row in coverage],
            [
                "modernize-scientific-stack",
                "kv-store-grpc",
                "fix-code-vulnerability",
            ],
        )


if __name__ == "__main__":
    unittest.main()
