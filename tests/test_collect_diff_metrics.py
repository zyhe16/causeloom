from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "evals/scripts/collect_diff_metrics.py"


class CollectDiffMetricsTest(unittest.TestCase):
    def test_counts_tracked_and_untracked_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp) / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "eval@example.invalid"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Evaluation Fixture"], cwd=repo, check=True)
            (repo / "tracked.txt").write_text("a\nb\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "baseline"], cwd=repo, check=True)

            (repo / "tracked.txt").write_text("a\nc\nd\n", encoding="utf-8")
            (repo / "new.txt").write_text("x\ny\n", encoding="utf-8")
            (repo / "blob.bin").write_bytes(b"\x00\x01")

            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--repo", str(repo)],
                check=True,
                capture_output=True,
                text=True,
            )
            result = json.loads(completed.stdout)
            self.assertEqual(result["files_changed"], 3)
            self.assertEqual(result["net_lines_added"], 4)
            self.assertEqual(result["net_lines_removed"], 1)
            self.assertEqual(result["binary_files_changed"], 1)
            self.assertEqual(result["untracked_paths"], ["blob.bin", "new.txt"])


if __name__ == "__main__":
    unittest.main()
