#!/usr/bin/env python3
"""Extract normalized token usage from Codex CLI or local session JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from codex_events import parse_cli_events, parse_desktop_session


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path, nargs="+")
    parser.add_argument("--format", choices=("exec", "session"), required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.format == "exec":
        parsed = parse_cli_events([path.expanduser().resolve() for path in args.input])
        result = {
            "usage": parsed["usage"],
            "usage_events": parsed["usage_events"],
            "thread_id": parsed["thread_id"],
            "tool_calls": parsed["tool_calls"],
            "parse_errors": parsed["parse_errors"],
            "token_usage_source": "agent_log" if parsed["usage"] is not None else "unavailable",
            "token_usage_adapter": "codex_exec_jsonl" if parsed["usage"] is not None else "unavailable",
        }
    else:
        if len(args.input) != 1:
            raise SystemExit("Session format accepts exactly one JSONL input")
        parsed = parse_desktop_session(args.input[0].expanduser().resolve())
        result = {
            "usage": parsed["usage"],
            "method": parsed["method"],
            "thread_id": parsed["thread_id"],
            "parse_errors": parsed["parse_errors"],
            "token_usage_source": "agent_log" if parsed["usage"] is not None else "unavailable",
            "token_usage_adapter": "codex_session_jsonl" if parsed["usage"] is not None else "unavailable",
        }

    output = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
