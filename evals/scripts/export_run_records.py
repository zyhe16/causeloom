#!/usr/bin/env python3
"""Flatten automatically captured run-record.json files into the scoring CSV template."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def value(mapping: dict[str, Any], key: str, default: Any = "") -> Any:
    result = mapping.get(key, default)
    return "" if result is None else result


def flatten(record: dict[str, Any]) -> dict[str, Any]:
    scores = record.get("scores", {})
    diagnostics = record.get("diagnostics", {})
    tokens = record.get("token_usage", {})
    return {
        "run_id": value(record, "run_id"),
        "task_id": value(record, "task_id"),
        "condition": value(record, "condition"),
        "repetition": value(record, "repetition"),
        "client": value(record, "client"),
        "client_version": value(record, "client_version"),
        "thread_id": value(record, "thread_id"),
        "model": value(record, "model"),
        "model_version": value(record, "model_version"),
        "skill_sha256": value(record, "skill_sha256"),
        "repo_sha256_or_commit": value(record, "repo_sha256_or_commit"),
        "valid_run": "yes" if record.get("valid_run", False) else "no",
        "environment_failure": "yes" if record.get("environment_failure", False) else "no",
        "goal_achieved": "yes" if record.get("goal_achieved", False) else "no",
        "public_checks_pass": value(record, "public_checks_pass", "na"),
        "hidden_checks_pass": value(record, "hidden_checks_pass", "na"),
        "critical_failure": "yes" if record.get("critical_failure", False) else "no",
        "functional_correctness": value(scores, "functional_correctness", 0),
        "requirement_fidelity": value(scores, "requirement_fidelity", 0),
        "architecture_root_cause": value(scores, "architecture_root_cause", 0),
        "ownership_discipline": value(scores, "ownership_discipline", 0),
        "verification_quality": value(scores, "verification_quality", 0),
        "safety_robustness": value(scores, "safety_robustness", 0),
        "communication_clarity": value(scores, "communication_clarity", 0),
        "clarification_behavior": value(record, "clarification_behavior", "not_applicable"),
        "files_changed": value(diagnostics, "files_changed", 0),
        "net_lines_added": value(diagnostics, "net_lines_added", 0),
        "net_lines_removed": value(diagnostics, "net_lines_removed", 0),
        "new_production_dependencies": value(diagnostics, "new_production_dependencies", 0),
        "new_configuration_keys": value(diagnostics, "new_configuration_keys", 0),
        "new_abstractions": value(diagnostics, "new_abstractions", 0),
        "tool_calls": value(diagnostics, "tool_calls", 0),
        "input_tokens": value(tokens, "input_tokens"),
        "cached_input_tokens": value(tokens, "cached_input_tokens"),
        "cache_write_input_tokens": value(tokens, "cache_write_input_tokens"),
        "output_tokens": value(tokens, "output_tokens"),
        "reasoning_tokens": value(tokens, "reasoning_tokens"),
        "total_tokens": value(tokens, "total_tokens"),
        "token_usage_source": value(tokens, "token_usage_source", "unavailable"),
        "token_usage_adapter": value(tokens, "token_usage_adapter", "unavailable"),
        "elapsed_seconds": value(diagnostics, "elapsed_seconds", 0),
        "notes": "UNSCORED automatic capture; review patch, checks, and final response before analysis.",
    }


def template_fieldnames(template: Path | None = None) -> list[str]:
    root = Path(__file__).resolve().parents[2]
    path = template or root / "evals/templates/scored-runs.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        return next(csv.reader(handle))


def write_review_row(
    record: dict[str, Any], output: Path, *, template: Path | None = None
) -> None:
    """Write one reviewer-ready unscored CSV row for a captured run."""

    fieldnames = template_fieldnames(template)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(flatten(record))


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--template", type=Path, default=root / "evals/templates/scored-runs.csv"
    )
    args = parser.parse_args()

    fieldnames = template_fieldnames(args.template)
    paths = sorted(args.work_root.rglob("run-record.json"))
    if not paths:
        raise SystemExit(f"No run-record.json files found under {args.work_root}")
    rows = [flatten(json.loads(path.read_text(encoding="utf-8"))) for path in paths]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} unscored rows to {args.output}")
    print("Human scoring is required before validation or summary generation.")


if __name__ == "__main__":
    main()
