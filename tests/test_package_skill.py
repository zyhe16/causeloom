from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/package_skill.py"


class PackageSkillTest(unittest.TestCase):
    def test_install_zip_has_expected_layout(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "skill.zip"
            subprocess.run(
                [sys.executable, str(SCRIPT), "--root", str(ROOT), "--output", str(output)],
                check=True,
                capture_output=True,
                text=True,
            )
            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
            expected = {
                "causeloom/SKILL.md",
                "causeloom/agents/openai.yaml",
                "causeloom/LICENSE",
                "causeloom/VERSION",
            }
            self.assertEqual(names, expected)


if __name__ == "__main__":
    unittest.main()
