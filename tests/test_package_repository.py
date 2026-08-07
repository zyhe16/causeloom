from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/package_repository.py"


class PackageRepositoryTest(unittest.TestCase):
    def test_source_zip_has_public_repo_layout_and_exclusions(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "source.zip"
            subprocess.run(
                [sys.executable, str(SCRIPT), "--root", str(ROOT), "--output", str(output)],
                check=True,
                capture_output=True,
                text=True,
                timeout=15,
            )
            with zipfile.ZipFile(output) as archive:
                names = archive.namelist()
            prefix = "causeloom/"
            self.assertIn(prefix + "SKILL.md", names)
            self.assertIn(prefix + "README.md", names)
            self.assertIn(prefix + "evals/scripts/summarize_results.py", names)
            self.assertIn(prefix + "evals/conditions/causeloom/POLICY.md", names)
            self.assertFalse(
                any(name.startswith(prefix + "evals/private-conditions/") for name in names)
            )
            self.assertIn(prefix + "evals/research-suite.csv", names)
            self.assertIn(prefix + "evals/RESEARCH_SUITE.md", names)
            self.assertIn(prefix + "tests/test_token_validation.py", names)
            self.assertFalse(any("/__pycache__/" in name for name in names))
            self.assertFalse(any(name.endswith((".pyc", ".pyo")) for name in names))
            self.assertFalse(any(name.startswith(prefix + "dist/") for name in names))
            self.assertEqual(
                [name for name in names if name.endswith("/SKILL.md")],
                [prefix + "SKILL.md"],
            )


if __name__ == "__main__":
    unittest.main()
