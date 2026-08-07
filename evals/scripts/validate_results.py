#!/usr/bin/env python3
"""Validate scored run data, including normalized token-accounting invariants."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from eval_common import (
    CLARIFICATION_BEHAVIORS,
    FALSE_VALUES,
    NA_VALUES,
    PASS_VALUES,
    TOKEN_SOURCES,
    TRUE_VALUES,
    WEIGHTS,
    normalize_token_usage,
    optional_float,
    optional_int,
    parse_bool,
    read_csv,
)

BOOLEAN_COLUMNS = ("valid_run", "environment_failure", "goal_achieved", "critical_failure")
NONNEGATIVE_INTEGER_COLUMNS = (
    "repetition",
    "files_changed",
    "net_lines_added",
    "net_lines_removed",
    "new_production_dependencies",
    "new_configuration_keys",
    "new_abstractions",
    "tool_calls",
)


def validate_rows(rows: list[dict[str, str]], *, strict_token_coverage: bool = False) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    seen_run_ids: set[str] = set()

    if not rows:
        return ["no scored rows found"], warnings

    for index, row in enumerate(rows, start=2):
        prefix = row.get("run_id", "").strip() or f"CSV row {index}"
        for required in ("run_id", "task_id", "condition"):
            if not row.get(required, "").strip():
                errors.append(f"{prefix}: {required} is required")
        run_id = row.get("run_id", "").strip()
        if run_id:
            if run_id in seen_run_ids:
                errors.append(f"{prefix}: duplicate run_id")
            seen_run_ids.add(run_id)

        for column in BOOLEAN_COLUMNS:
            value = row.get(column, "").strip().lower()
            if value not in TRUE_VALUES | FALSE_VALUES | NA_VALUES:
                errors.append(f"{prefix}: {column} has invalid boolean value {row.get(column)!r}")

        for column in ("public_checks_pass", "hidden_checks_pass"):
            if row.get(column, "").strip().lower() not in PASS_VALUES | FALSE_VALUES:
                errors.append(f"{prefix}: {column} must be yes/no/na")

        clarification = row.get("clarification_behavior", "").strip().lower()
        if clarification not in CLARIFICATION_BEHAVIORS:
            errors.append(
                f"{prefix}: clarification_behavior must be one of "
                f"{sorted(CLARIFICATION_BEHAVIORS)}"
            )

        for column in WEIGHTS:
            try:
                value = optional_float(row.get(column))
            except ValueError:
                errors.append(f"{prefix}: {column} is not numeric")
                continue
            if math.isnan(value) or not 0 <= value <= 5:
                errors.append(f"{prefix}: {column} must be between 0 and 5")

        for column in NONNEGATIVE_INTEGER_COLUMNS:
            try:
                value = optional_int(row.get(column))
            except ValueError as exc:
                errors.append(f"{prefix}: {column}: {exc}")
                continue
            if value is not None and value < 0:
                errors.append(f"{prefix}: {column} must be nonnegative")

        try:
            elapsed = optional_float(row.get("elapsed_seconds"))
            if not math.isnan(elapsed) and elapsed < 0:
                errors.append(f"{prefix}: elapsed_seconds must be nonnegative")
        except ValueError:
            errors.append(f"{prefix}: elapsed_seconds is not numeric")

        try:
            usage = normalize_token_usage(row)
        except ValueError as exc:
            errors.append(f"{prefix}: token usage: {exc}")
            continue

        source = str(usage["token_usage_source"])
        if source not in TOKEN_SOURCES:
            errors.append(f"{prefix}: token_usage_source must be one of {sorted(TOKEN_SOURCES)}")
        numeric_fields = (
            usage["input_tokens"],
            usage["cached_input_tokens"],
            usage["cache_write_input_tokens"],
            usage["output_tokens"],
            usage["reasoning_tokens"],
            usage["total_tokens"],
        )
        if any(value is not None and int(value) < 0 for value in numeric_fields):
            errors.append(f"{prefix}: token counts must be nonnegative")
        if source == "unavailable" and any(value is not None for value in numeric_fields):
            errors.append(f"{prefix}: token fields must be blank when source is unavailable")
        if source != "unavailable" and not usage["available"]:
            errors.append(f"{prefix}: token source {source!r} requires a usable total")
        if source != "unavailable" and not str(usage.get("token_usage_adapter", "")).strip():
            warnings.append(f"{prefix}: token_usage_adapter is blank")
        if usage["cached_input_tokens"] is not None:
            if usage["input_tokens"] is None:
                errors.append(f"{prefix}: cached_input_tokens requires input_tokens")
            elif int(usage["cached_input_tokens"]) > int(usage["input_tokens"]):
                errors.append(f"{prefix}: cached_input_tokens cannot exceed input_tokens")
        if usage["reasoning_tokens"] is not None:
            if usage["output_tokens"] is None:
                errors.append(f"{prefix}: reasoning_tokens requires output_tokens")
            elif int(usage["reasoning_tokens"]) > int(usage["output_tokens"]):
                errors.append(f"{prefix}: reasoning_tokens cannot exceed output_tokens")
        if (
            usage["explicit_total_tokens"] is not None
            and usage["derived_total_tokens"] is not None
            and usage["explicit_total_tokens"] != usage["derived_total_tokens"]
        ):
            errors.append(
                f"{prefix}: total_tokens must equal input_tokens + output_tokens; "
                "cached and reasoning details are not additive"
            )
        if source == "estimated":
            warnings.append(f"{prefix}: token usage is estimated; document the method in notes")
        if source == "unavailable":
            warnings.append(f"{prefix}: token usage unavailable")
            try:
                valid = parse_bool(row.get("valid_run", "true"), default=True)
                environment_failure = parse_bool(row.get("environment_failure", "false"))
            except ValueError:
                valid = False
                environment_failure = True
            if strict_token_coverage and valid and not environment_failure:
                errors.append(f"{prefix}: strict token coverage requires tokens for every valid run")

    return errors, warnings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--strict-token-coverage", action="store_true")
    parser.add_argument("--warnings-as-errors", action="store_true")
    args = parser.parse_args()

    rows = read_csv(args.input)
    errors, warnings = validate_rows(rows, strict_token_coverage=args.strict_token_coverage)
    if args.warnings_as_errors:
        errors.extend(f"warning promoted to error: {warning}" for warning in warnings)

    report = {
        "input": str(args.input),
        "rows": len(rows),
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
    }
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print(f"Validated {len(rows)} scored runs")


if __name__ == "__main__":
    main()
