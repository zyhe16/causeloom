#!/usr/bin/env python3
"""Shared parsing, qualification, scoring, and normalized token accounting."""

from __future__ import annotations

import csv
import math
import statistics
from pathlib import Path
from typing import Iterable

WEIGHTS = {
    "functional_correctness": 30.0,
    "requirement_fidelity": 15.0,
    "architecture_root_cause": 15.0,
    "ownership_discipline": 15.0,
    "verification_quality": 10.0,
    "safety_robustness": 10.0,
    "communication_clarity": 5.0,
}

TRUE_VALUES = {"1", "true", "yes", "y"}
FALSE_VALUES = {"0", "false", "no", "n"}
NA_VALUES = {"", "na", "n/a", "none", "not_applicable"}
PASS_VALUES = TRUE_VALUES | NA_VALUES
TOKEN_SOURCES = {"provider_reported", "agent_log", "estimated", "unavailable"}
CLARIFICATION_BEHAVIORS = {
    "correctly_asked",
    "correctly_inferred",
    "unnecessary_question",
    "missing_question",
    "not_applicable",
}


def parse_bool(value: str, *, default: bool = False) -> bool:
    normalized = str(value).strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    if normalized in NA_VALUES:
        return default
    raise ValueError(f"invalid boolean value: {value!r}")


def check_passes(value: str) -> bool:
    return str(value).strip().lower() in PASS_VALUES


def optional_float(value: str | int | float | None) -> float:
    if value is None or str(value).strip() == "":
        return math.nan
    return float(value)


def optional_int(value: str | int | float | None) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    numeric = float(value)
    if not numeric.is_integer():
        raise ValueError(f"expected an integer, got {value!r}")
    return int(numeric)


def mean(values: Iterable[float]) -> float:
    data = [float(value) for value in values if not math.isnan(float(value))]
    return statistics.fmean(data) if data else math.nan


def median(values: Iterable[float]) -> float:
    data = [float(value) for value in values if not math.isnan(float(value))]
    return statistics.median(data) if data else math.nan


def weighted_score(row: dict[str, str]) -> float:
    total = 0.0
    for column, weight in WEIGHTS.items():
        score = optional_float(row.get(column))
        if math.isnan(score) or not 0.0 <= score <= 5.0:
            raise ValueError(f"{row.get('run_id', '<unknown>')}: {column} must be between 0 and 5")
        total += score / 5.0 * weight
    return total


def is_qualified(row: dict[str, str]) -> bool:
    return (
        parse_bool(row.get("valid_run", "true"), default=True)
        and not parse_bool(row.get("environment_failure", "false"))
        and parse_bool(row.get("goal_achieved", "false"))
        and check_passes(row.get("public_checks_pass", "na"))
        and check_passes(row.get("hidden_checks_pass", "na"))
        and not parse_bool(row.get("critical_failure", "false"))
    )


def normalize_token_usage(row: dict[str, str]) -> dict[str, object]:
    """Return provider-neutral totals without double-counting detail fields.

    Legacy prompt/completion columns are accepted as aliases. Cached-input and
    reasoning tokens are informational subsets of input/output totals.
    """

    raw_input = row.get("input_tokens", "") or row.get("prompt_tokens", "")
    raw_output = row.get("output_tokens", "") or row.get("completion_tokens", "")
    input_tokens = optional_int(raw_input)
    output_tokens = optional_int(raw_output)
    cached_input_tokens = optional_int(row.get("cached_input_tokens"))
    cache_write_input_tokens = optional_int(row.get("cache_write_input_tokens"))
    reasoning_tokens = optional_int(row.get("reasoning_tokens"))
    explicit_total = optional_int(row.get("total_tokens"))
    source = str(row.get("token_usage_source", "")).strip().lower()
    adapter = str(row.get("token_usage_adapter", "")).strip()

    any_numeric = any(
        value is not None
        for value in (
            input_tokens, output_tokens, cached_input_tokens, cache_write_input_tokens,
            reasoning_tokens, explicit_total
        )
    )
    if not source:
        source = "unavailable" if not any_numeric else "unspecified"

    derived_total: int | None = None
    if input_tokens is not None and output_tokens is not None:
        derived_total = input_tokens + output_tokens
    total_tokens = explicit_total if explicit_total is not None else derived_total

    return {
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_input_tokens,
        "cache_write_input_tokens": cache_write_input_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning_tokens,
        "total_tokens": total_tokens,
        "explicit_total_tokens": explicit_total,
        "derived_total_tokens": derived_total,
        "token_usage_source": source,
        "token_usage_adapter": adapter,
        "available": total_tokens is not None,
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))
