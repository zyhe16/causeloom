#!/usr/bin/env python3
"""Minimal parser and validator for the repository's simple SKILL.md frontmatter."""

from __future__ import annotations

import re
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def parse_skill(path: Path) -> tuple[dict[str, object], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: missing opening YAML frontmatter delimiter")
    try:
        raw_frontmatter, body = text[4:].split("\n---\n", 1)
    except ValueError as exc:
        raise ValueError(f"{path}: missing closing YAML frontmatter delimiter") from exc

    result: dict[str, object] = {}
    current_map: dict[str, str] | None = None
    for number, raw_line in enumerate(raw_frontmatter.splitlines(), start=2):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if raw_line.startswith("  "):
            if current_map is None or ":" not in raw_line:
                raise ValueError(f"{path}:{number}: unsupported nested frontmatter")
            key, value = raw_line.strip().split(":", 1)
            current_map[key.strip()] = unquote(value)
            continue
        if ":" not in raw_line:
            raise ValueError(f"{path}:{number}: expected key: value")
        key, value = raw_line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not value:
            nested: dict[str, str] = {}
            result[key] = nested
            current_map = nested
        else:
            result[key] = unquote(value)
            current_map = None
    return result, body


def validate_skill(path: Path, *, check_parent_name: bool = True) -> list[str]:
    errors: list[str] = []
    try:
        metadata, body = parse_skill(path)
    except (OSError, ValueError) as exc:
        return [str(exc)]

    name = str(metadata.get("name", ""))
    description = str(metadata.get("description", ""))
    if not name:
        errors.append("frontmatter name is required")
    elif not NAME_RE.fullmatch(name):
        errors.append("name must be lowercase alphanumeric words separated by single hyphens")
    elif len(name) > 64:
        errors.append("name must be at most 64 characters")
    if check_parent_name and path.parent.name != name:
        errors.append(f"parent directory {path.parent.name!r} does not match skill name {name!r}")
    if not description:
        errors.append("frontmatter description is required")
    elif len(description) > 1024:
        errors.append("description must be at most 1024 characters")
    if not body.strip():
        errors.append("skill body must not be empty")
    if len(body.splitlines()) > 500:
        errors.append("skill body should remain under 500 lines")
    unexpected = sorted(set(metadata) - {"name", "description"})
    if unexpected:
        errors.append(
            "frontmatter supports only name and description; unexpected: "
            + ", ".join(unexpected)
        )
    return errors
