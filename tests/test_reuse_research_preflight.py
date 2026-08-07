from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "evals/scripts/reuse_research_preflight.py"
SPEC = importlib.util.spec_from_file_location("reuse_research_preflight", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ReuseResearchPreflightTest(unittest.TestCase):
    def test_execution_digest_ignores_only_adaptation_marker(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "task.txt").write_text("same", encoding="utf-8")
            marker = root / ".research-adaptation.json"
            marker.write_text('{"version": 1}', encoding="utf-8")
            first = MODULE.execution_tree_digest(root)
            marker.write_text('{"version": 2}', encoding="utf-8")
            self.assertEqual(first, MODULE.execution_tree_digest(root))
            cache = root / "tests" / "__pycache__" / "test.cpython-311.pyc"
            cache.parent.mkdir(parents=True)
            cache.write_bytes(b"runtime residue")
            self.assertEqual(first, MODULE.execution_tree_digest(root))
            (root / "task.txt").write_text("changed", encoding="utf-8")
            self.assertNotEqual(first, MODULE.execution_tree_digest(root))


if __name__ == "__main__":
    unittest.main()
