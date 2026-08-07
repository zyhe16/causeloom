#!/usr/bin/env python3
"""Parse Codex CLI JSONL and optional local desktop rollout token events."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

TOKEN_KEYS = (
    "input_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "reasoning_tokens",
)
TOOL_ITEM_TYPES = {
    "command_execution",
    "file_change",
    "mcp_tool_call",
    "web_search",
    "computer_use",
    "image_generation",
}


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    events: list[dict[str, Any]] = []
    errors: list[str] = []
    if not path.is_file():
        return events, [f"missing JSONL file: {path}"]
    for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {number}: {exc}")
            continue
        if isinstance(value, dict):
            events.append(value)
        else:
            errors.append(f"line {number}: expected JSON object")
    return events, errors


def _integer(value: Any) -> int:
    if value in (None, ""):
        return 0
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return max(number, 0)


def normalize_usage(usage: dict[str, Any]) -> dict[str, int]:
    input_tokens = _integer(usage.get("input_tokens"))
    cached_input_tokens = _integer(usage.get("cached_input_tokens"))
    cache_write_input_tokens = _integer(usage.get("cache_write_input_tokens"))
    output_tokens = _integer(usage.get("output_tokens"))
    reasoning_tokens = _integer(
        usage.get("reasoning_output_tokens", usage.get("reasoning_tokens"))
    )
    return {
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_input_tokens,
        "cache_write_input_tokens": cache_write_input_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning_tokens,
        "total_tokens": input_tokens + output_tokens,
    }


def add_usage(left: dict[str, int], right: dict[str, int]) -> dict[str, int]:
    return {key: left.get(key, 0) + right.get(key, 0) for key in left}


def empty_usage() -> dict[str, int]:
    return {
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "cache_write_input_tokens": 0,
        "output_tokens": 0,
        "reasoning_tokens": 0,
        "total_tokens": 0,
    }


def parse_cli_events(paths: Iterable[Path]) -> dict[str, Any]:
    """Aggregate per-turn usage from one or more `codex exec --json` logs."""

    usage = empty_usage()
    usage_events = 0
    tool_calls = 0
    thread_ids: list[str] = []
    final_messages: list[str] = []
    errors: list[str] = []
    event_count = 0

    for path in paths:
        events, parse_errors = read_jsonl(path)
        errors.extend(f"{path.name}: {error}" for error in parse_errors)
        event_count += len(events)
        for event in events:
            event_type = str(event.get("type", ""))
            if event_type == "thread.started" and event.get("thread_id"):
                thread_id = str(event["thread_id"])
                if thread_id not in thread_ids:
                    thread_ids.append(thread_id)
            if event_type == "turn.completed" and isinstance(event.get("usage"), dict):
                usage = add_usage(usage, normalize_usage(event["usage"]))
                usage_events += 1
            if event_type == "item.completed" and isinstance(event.get("item"), dict):
                item = event["item"]
                item_type = str(item.get("type", ""))
                if item_type in TOOL_ITEM_TYPES:
                    tool_calls += 1
                if item_type == "agent_message" and isinstance(item.get("text"), str):
                    final_messages.append(item["text"])

    return {
        "usage": usage if usage_events else None,
        "usage_events": usage_events,
        "tool_calls": tool_calls,
        "thread_ids": thread_ids,
        "thread_id": thread_ids[-1] if thread_ids else "",
        "final_message": final_messages[-1] if final_messages else "",
        "event_count": event_count,
        "parse_errors": errors,
    }


def parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _walk_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _walk_dicts(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_dicts(nested)


def _extract_cumulative_usage(event: dict[str, Any]) -> dict[str, int] | None:
    """Find a cumulative total_token_usage object in a local rollout event."""

    for candidate in _walk_dicts(event):
        total = candidate.get("total_token_usage")
        if isinstance(total, dict) and any(key in total for key in TOKEN_KEYS):
            return normalize_usage(total)
        if candidate.get("type") == "token_count":
            info = candidate.get("info")
            if isinstance(info, dict):
                total = info.get("total_token_usage")
                if isinstance(total, dict):
                    return normalize_usage(total)
    return None


def _event_timestamp(event: dict[str, Any]) -> datetime | None:
    for key in ("timestamp", "created_at", "createdAt", "time"):
        parsed = parse_timestamp(event.get(key))
        if parsed is not None:
            return parsed
    return None


def parse_desktop_session(path: Path, *, since: datetime | None = None) -> dict[str, Any]:
    """Extract usage from a user-selected local Codex desktop rollout JSONL.

    Direct per-turn usage events are preferred. Otherwise the function uses the
    last cumulative `total_token_usage` value. A fresh desktop chat per benchmark
    run is therefore the most reliable manual protocol.
    """

    events, errors = read_jsonl(path)
    direct_usage = empty_usage()
    direct_count = 0
    cumulative: list[tuple[datetime | None, dict[str, int]]] = []
    final_messages: list[str] = []
    thread_id = ""

    for event in events:
        timestamp = _event_timestamp(event)
        if since is not None and timestamp is not None and timestamp < since:
            continue
        event_type = str(event.get("type", ""))
        if event_type == "thread.started" and event.get("thread_id"):
            thread_id = str(event["thread_id"])
        if event_type == "turn.completed" and isinstance(event.get("usage"), dict):
            direct_usage = add_usage(direct_usage, normalize_usage(event["usage"]))
            direct_count += 1
        found = _extract_cumulative_usage(event)
        if found is not None:
            cumulative.append((timestamp, found))
        for candidate in _walk_dicts(event):
            if not thread_id and candidate.get("thread_id"):
                thread_id = str(candidate["thread_id"])
            role = candidate.get("role")
            content = candidate.get("content")
            if role == "assistant" and isinstance(content, str):
                final_messages.append(content)
            if candidate.get("type") == "agent_message" and isinstance(candidate.get("text"), str):
                final_messages.append(candidate["text"])

    if direct_count:
        usage: dict[str, int] | None = direct_usage
        method = "summed direct turn.completed usage events"
    elif cumulative:
        usage = cumulative[-1][1]
        method = "last cumulative total_token_usage value from a fresh desktop chat"
    else:
        usage = None
        method = "no trustworthy usage event found"

    return {
        "usage": usage,
        "method": method,
        "thread_id": thread_id,
        "final_message": final_messages[-1] if final_messages else "",
        "event_count": len(events),
        "parse_errors": errors,
    }
