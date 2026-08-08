#!/usr/bin/env python3
"""Copy only the selected model settings into an isolated Codex config."""

from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path


STANDARD_MODEL = "gpt-5.6-luna"
STANDARD_REASONING_EFFORT = "max"
STANDARD_ROOT = Path("work/research-benchmark-standard")


def prepare(
    source: Path,
    output: Path,
    expected_model: str,
    expected_reasoning_effort: str,
) -> None:
    config = tomllib.loads(source.read_text(encoding="utf-8"))
    model = config.get("model")
    effort = config.get("model_reasoning_effort")
    if model != expected_model:
        raise ValueError(f"Expected model {expected_model!r}, found {model!r}")
    if effort != expected_reasoning_effort:
        raise ValueError(
            f"Expected reasoning effort {expected_reasoning_effort!r}, found {effort!r}"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        f"model = {json.dumps(model)}\n"
        f"model_reasoning_effort = {json.dumps(effort)}\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source", type=Path, default=Path.home() / ".codex" / "config.toml"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=STANDARD_ROOT / "codex.config.toml",
    )
    parser.add_argument("--expected-model", default=STANDARD_MODEL)
    parser.add_argument(
        "--expected-reasoning-effort", default=STANDARD_REASONING_EFFORT
    )
    args = parser.parse_args()
    prepare(
        args.source,
        args.output,
        args.expected_model,
        args.expected_reasoning_effort,
    )
    print(f"Wrote isolated Codex config to {args.output}")


if __name__ == "__main__":
    main()
