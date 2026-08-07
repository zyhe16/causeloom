#!/usr/bin/env python3
"""Freeze the canonical skill into the evaluation condition and refresh checksums."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def refresh_checksums(conditions_root: Path) -> Path:
    entries: list[str] = []
    for skill_path in sorted(conditions_root.glob("*/POLICY.md")):
        digest = hashlib.sha256(skill_path.read_bytes()).hexdigest()
        relative = skill_path.relative_to(conditions_root).as_posix()
        entries.append(f"{digest}  {relative}")
    if not entries:
        raise SystemExit(f"No condition POLICY.md files found under {conditions_root}")
    checksum_file = conditions_root / "CHECKSUMS.sha256"
    checksum_file.write_text("\n".join(entries) + "\n", encoding="utf-8")
    return checksum_file


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill", type=Path, default=Path("SKILL.md"))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("evals/conditions/causeloom"),
    )
    args = parser.parse_args()

    data = args.skill.read_bytes()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    target = args.output_dir / "POLICY.md"
    target.write_bytes(data)
    checksum_file = refresh_checksums(args.output_dir.parent)
    digest = hashlib.sha256(data).hexdigest()
    print(f"Snapshotted {args.skill} to {target}")
    print(f"SHA-256 {digest}")
    print(f"Refreshed {checksum_file}")


if __name__ == "__main__":
    main()
