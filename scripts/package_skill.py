#!/usr/bin/env python3
"""Build a reproducible install-only ZIP from the public repository."""

from __future__ import annotations

import argparse
import hashlib
import zipfile
from pathlib import Path

from skill_manifest import parse_skill, validate_skill

PACKAGE_FILES = (
    "SKILL.md",
    "agents/openai.yaml",
    "LICENSE",
    "VERSION",
)
FIXED_TIME = (2026, 8, 7, 0, 0, 0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    skill_path = root / "SKILL.md"
    errors = validate_skill(skill_path, check_parent_name=False)
    if errors:
        raise SystemExit("Cannot package invalid skill:\n- " + "\n- ".join(errors))
    metadata, _ = parse_skill(skill_path)
    name = str(metadata["name"])

    missing = [item for item in PACKAGE_FILES if not (root / item).is_file()]
    if missing:
        raise SystemExit("Missing package files: " + ", ".join(missing))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in sorted(PACKAGE_FILES):
            data = (root / relative).read_bytes()
            info = zipfile.ZipInfo(f"{name}/{relative}", date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)

    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(f"Wrote {args.output} ({args.output.stat().st_size} bytes)")
    print(f"SHA-256 {digest}")


if __name__ == "__main__":
    main()
