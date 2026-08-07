#!/usr/bin/env python3
"""Build a reproducible GitHub-style source ZIP for public release."""

from __future__ import annotations

import argparse
import hashlib
import os
import stat
import zipfile
from pathlib import Path

from skill_manifest import parse_skill, validate_skill

FIXED_TIME = (2026, 8, 7, 0, 0, 0)
EXCLUDED_DIRS = {
    ".git",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".vscode",
    "__pycache__",
    "dist",
    "results",
    "venv",
    "work",
}
EXCLUDED_FILES = {".coverage", ".DS_Store", "Thumbs.db"}
EXCLUDED_SUFFIXES = {".log", ".pyc", ".pyo", ".sqlite"}


def include(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    if relative.parts[:2] == ("evals", "private-conditions"):
        return False
    if any(part in EXCLUDED_DIRS for part in relative.parts):
        return False
    if path.name in EXCLUDED_FILES or path.suffix in EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def iter_included_files(root: Path):
    """Yield package files without descending into excluded artifact trees."""
    for directory, dirnames, filenames in os.walk(root):
        current = Path(directory)
        relative = current.relative_to(root)
        if relative.parts == ("evals",):
            dirnames[:] = [name for name in dirnames if name != "private-conditions"]
        dirnames[:] = sorted(name for name in dirnames if name not in EXCLUDED_DIRS)
        for filename in sorted(filenames):
            path = current / filename
            if include(path, root):
                yield path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    errors = validate_skill(root / "SKILL.md", check_parent_name=False)
    if errors:
        raise SystemExit("Cannot package invalid repository:\n- " + "\n- ".join(errors))

    metadata, _body = parse_skill(root / "SKILL.md")
    name = str(metadata["name"])
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    archive_root = name
    files = sorted(iter_included_files(root))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = path.relative_to(root).as_posix()
            data = path.read_bytes()
            info = zipfile.ZipInfo(f"{archive_root}/{relative}", date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = path.stat().st_mode
            permissions = 0o755 if mode & stat.S_IXUSR else 0o644
            info.external_attr = (stat.S_IFREG | permissions) << 16
            archive.writestr(info, data)

    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(f"Wrote {args.output} ({len(files)} files, {args.output.stat().st_size} bytes)")
    print(f"SHA-256 {digest}")


if __name__ == "__main__":
    main()
