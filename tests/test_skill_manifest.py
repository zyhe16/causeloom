from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from skill_manifest import parse_skill, validate_skill  # noqa: E402

CONDITIONS = ROOT / "evals/conditions"


class SkillManifestTest(unittest.TestCase):
    def test_manifest_is_valid_and_versioned(self):
        errors = validate_skill(ROOT / "SKILL.md", check_parent_name=False)
        self.assertEqual(errors, [])
        metadata, body = parse_skill(ROOT / "SKILL.md")
        self.assertEqual(metadata["name"], "causeloom")
        self.assertEqual(set(metadata), {"name", "description"})
        self.assertEqual((ROOT / "VERSION").read_text().strip(), "0.3.0")
        self.assertLessEqual(len(body.splitlines()), 500)

    def test_repository_has_only_one_discoverable_skill_file(self):
        skill_files = sorted(
            path.relative_to(ROOT).as_posix()
            for path in ROOT.rglob("SKILL.md")
            if not {"dist", "results", "work"}.intersection(
                path.relative_to(ROOT).parts
            )
        )
        self.assertEqual(skill_files, ["SKILL.md"])

    def test_frozen_causeloom_condition_matches_canonical_skill(self):
        canonical = (ROOT / "SKILL.md").read_bytes()
        frozen = (CONDITIONS / "causeloom/POLICY.md").read_bytes()
        self.assertEqual(canonical, frozen)

    def test_all_frozen_condition_checksums_match(self):
        expected: dict[str, str] = {}
        for line in (CONDITIONS / "CHECKSUMS.sha256").read_text(encoding="utf-8").splitlines():
            digest, relative = line.split(maxsplit=1)
            expected[relative] = digest

        actual_paths = sorted(CONDITIONS.glob("*/POLICY.md"))
        self.assertEqual(
            set(expected),
            {path.relative_to(CONDITIONS).as_posix() for path in actual_paths},
        )
        for path in actual_paths:
            relative = path.relative_to(CONDITIONS).as_posix()
            with self.subTest(condition=relative):
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected[relative])

if __name__ == "__main__":
    unittest.main()
