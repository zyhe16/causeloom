#!/usr/bin/env python3
"""Collect deterministic Git diff diagnostics for a completed task run."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, text=True, capture_output=True
    ).stdout


def count_text_lines(data: bytes) -> int:
    """Count logical lines without requiring a particular text encoding."""

    if not data:
        return 0
    return data.count(b"\n") + (0 if data.endswith(b"\n") else 1)


def collect_diff_metrics(repo: Path, *, base: str = "HEAD") -> dict[str, object]:
    repo = repo.resolve()
    numstat = git(repo, "diff", "--numstat", base)
    tracked_files_changed = 0
    lines_added = 0
    lines_removed = 0
    binary_files = 0
    for line in numstat.splitlines():
        added, removed, _path = line.split("\t", 2)
        tracked_files_changed += 1
        if added == "-" or removed == "-":
            binary_files += 1
        else:
            lines_added += int(added)
            lines_removed += int(removed)

    untracked = [
        value
        for value in git(repo, "ls-files", "--others", "--exclude-standard").splitlines()
        if value
    ]
    for relative in untracked:
        path = repo / relative
        if not path.is_file():
            continue
        data = path.read_bytes()
        if b"\0" in data:
            binary_files += 1
        else:
            lines_added += count_text_lines(data)

    return {
        "files_changed": tracked_files_changed + len(untracked),
        "net_lines_added": lines_added,
        "net_lines_removed": lines_removed,
        "binary_files_changed": binary_files,
        "untracked_paths": untracked,
    }


def write_patch(repo: Path, output: Path, *, base: str = "HEAD") -> None:
    """Write a patch that includes tracked and newly created text files."""

    repo = repo.resolve()
    # Intent-to-add makes untracked files visible to git diff without staging content.
    subprocess.run(["git", "add", "-N", "."], cwd=repo, check=True, capture_output=True)
    try:
        patch = git(repo, "diff", "--binary", base)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(patch, encoding="utf-8")
    finally:
        subprocess.run(["git", "reset", "-q"], cwd=repo, check=True, capture_output=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--base", default="HEAD")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--patch-output", type=Path)
    args = parser.parse_args()

    result = collect_diff_metrics(args.repo, base=args.base)
    output = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    if args.patch_output:
        write_patch(args.repo, args.patch_output, base=args.base)


if __name__ == "__main__":
    main()
