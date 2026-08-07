#!/usr/bin/env python3
"""Validate the canonical Agent Skill manifest without third-party packages."""

from __future__ import annotations

import argparse
from pathlib import Path

from skill_manifest import parse_skill, validate_skill


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_dir", type=Path, nargs="?", default=Path("."))
    args = parser.parse_args()

    skill_dir = args.skill_dir.resolve()
    path = skill_dir / "SKILL.md"
    # A source checkout can have any local folder name. The install archive and
    # recommended clone path still use the exact frontmatter name.
    errors = validate_skill(path, check_parent_name=False)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)

    metadata, body = parse_skill(path)

    print(
        f"Valid skill: {metadata['name']} "
        f"({len(body.splitlines())} body lines, {len(str(metadata['description']))} description characters)"
    )


if __name__ == "__main__":
    main()
