#!/usr/bin/env python3
"""Create Markdown, JSON, and normalized CSV evaluation reports."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from eval_common import (
    WEIGHTS,
    is_qualified,
    mean,
    median,
    normalize_token_usage,
    optional_float,
    optional_int,
    parse_bool,
    read_csv,
    weighted_score,
)
from validate_results import validate_rows

NUMERIC_DIAGNOSTICS = (
    "files_changed",
    "net_lines_added",
    "net_lines_removed",
    "new_production_dependencies",
    "new_configuration_keys",
    "new_abstractions",
    "tool_calls",
    "elapsed_seconds",
)


def fmt(value: float | None, digits: int = 2) -> str:
    if value is None or math.isnan(float(value)):
        return "—"
    return f"{float(value):.{digits}f}"


def percent(value: float | None) -> str:
    if value is None or math.isnan(float(value)):
        return "—"
    return f"{float(value):.1%}"


def percentile(sorted_values: list[float], proportion: float) -> float:
    if not sorted_values:
        return math.nan
    position = (len(sorted_values) - 1) * proportion
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def task_means(rows: list[dict[str, object]], metric: str) -> dict[str, dict[str, float]]:
    grouped: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        value = row.get(metric)
        if isinstance(value, (int, float)) and not math.isnan(float(value)):
            grouped[str(row["task_id"])][str(row["condition"])].append(float(value))
    return {
        task: {condition: mean(values) for condition, values in conditions.items()}
        for task, conditions in grouped.items()
    }


def paired_bootstrap(
    per_task: dict[str, dict[str, float]],
    reference: str,
    comparison: str,
    samples: int,
    rng: random.Random,
) -> dict[str, object]:
    pairs = [
        (values[reference], values[comparison])
        for values in per_task.values()
        if reference in values and comparison in values
    ]
    if not pairs:
        return {"difference": None, "ci95": [None, None], "paired_tasks": 0}
    observed = mean(ref - comp for ref, comp in pairs)
    boot: list[float] = []
    for _ in range(samples):
        sample = [pairs[rng.randrange(len(pairs))] for _ in range(len(pairs))]
        boot.append(mean(ref - comp for ref, comp in sample))
    boot.sort()
    return {
        "difference": observed,
        "ci95": [percentile(boot, 0.025), percentile(boot, 0.975)],
        "paired_tasks": len(pairs),
    }


def json_number(value: float | int | None) -> float | int | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def aggregate_condition(condition_rows: list[dict[str, object]]) -> dict[str, object]:
    valid = [row for row in condition_rows if row["valid_for_analysis"]]
    qualified = [row for row in valid if row["qualified"]]
    token_rows = [row for row in valid if row["token_usage"]["available"]]
    qualified_token_rows = [row for row in qualified if row["token_usage"]["available"]]
    coverage = len(token_rows) / len(valid) if valid else math.nan
    total_measured = sum(int(row["token_usage"]["total_tokens"]) for row in token_rows)
    tokens_per_success: float | None = None
    if valid and len(token_rows) == len(valid) and qualified:
        tokens_per_success = total_measured / len(qualified)

    return {
        "valid_runs": len(valid),
        "qualified_runs": len(qualified),
        "qualified_success_rate": json_number(len(qualified) / len(valid) if valid else math.nan),
        "critical_failures": sum(
            parse_bool(str(row.get("critical_failure", "false"))) for row in valid
        ),
        "mean_quality_all": json_number(mean(float(row["quality_score"]) for row in valid)),
        "median_quality_all": json_number(median(float(row["quality_score"]) for row in valid)),
        "mean_quality_qualified": json_number(mean(float(row["quality_score"]) for row in qualified)),
        "mean_ownership_qualified": json_number(
            mean(float(row["ownership_discipline"]) for row in qualified)
        ),
        "median_net_lines_added_qualified": json_number(
            median(float(row["net_lines_added"]) for row in qualified)
        ),
        "median_tool_calls_qualified": json_number(
            median(float(row["tool_calls"]) for row in qualified)
        ),
        "median_elapsed_seconds_qualified": json_number(
            median(float(row["elapsed_seconds"]) for row in qualified)
        ),
        "token_usage": {
            "coverage_rate_valid": json_number(coverage),
            "measured_runs": len(token_rows),
            "total_measured_tokens_valid": total_measured,
            "median_input_tokens_valid": json_number(
                median(float(row["token_usage"]["input_tokens"]) for row in token_rows if row["token_usage"]["input_tokens"] is not None)
            ),
            "median_cached_input_tokens_valid": json_number(
                median(float(row["token_usage"]["cached_input_tokens"]) for row in token_rows if row["token_usage"]["cached_input_tokens"] is not None)
            ),
            "median_cache_write_input_tokens_valid": json_number(
                median(float(row["token_usage"]["cache_write_input_tokens"]) for row in token_rows if row["token_usage"]["cache_write_input_tokens"] is not None)
            ),
            "median_output_tokens_valid": json_number(
                median(float(row["token_usage"]["output_tokens"]) for row in token_rows if row["token_usage"]["output_tokens"] is not None)
            ),
            "median_reasoning_tokens_valid": json_number(
                median(float(row["token_usage"]["reasoning_tokens"]) for row in token_rows if row["token_usage"]["reasoning_tokens"] is not None)
            ),
            "median_total_tokens_valid": json_number(
                median(float(row["token_usage"]["total_tokens"]) for row in token_rows)
            ),
            "median_total_tokens_qualified": json_number(
                median(float(row["token_usage"]["total_tokens"]) for row in qualified_token_rows)
            ),
            "tokens_per_qualified_success": json_number(tokens_per_success),
            "source_counts": dict(sorted(Counter(str(row["token_usage"]["token_usage_source"]) for row in valid).items())),
            "adapter_counts": dict(sorted(Counter(str(row["token_usage"].get("token_usage_adapter", "") or "unspecified") for row in valid).items())),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--reference", default="causeloom")
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=329)
    parser.add_argument("--title", default="Evaluation summary")
    parser.add_argument("--dataset-note", default="")
    parser.add_argument("--generated-at", default="")
    args = parser.parse_args()

    if args.bootstrap_samples < 100:
        raise SystemExit("Use at least 100 bootstrap samples")
    raw_rows = read_csv(args.input)
    errors, warnings = validate_rows(raw_rows)
    if errors:
        raise SystemExit("Invalid input:\n- " + "\n- ".join(errors))

    rows: list[dict[str, object]] = []
    for raw in raw_rows:
        row: dict[str, object] = dict(raw)
        valid = parse_bool(raw.get("valid_run", "true"), default=True)
        environment_failure = parse_bool(raw.get("environment_failure", "false"))
        row["valid_for_analysis"] = valid and not environment_failure
        row["qualified"] = is_qualified(raw)
        row["qualified_numeric"] = 1.0 if row["qualified"] else 0.0
        row["quality_score"] = weighted_score(raw)
        for column in WEIGHTS:
            row[column] = optional_float(raw.get(column))
        for column in NUMERIC_DIAGNOSTICS:
            row[column] = optional_float(raw.get(column))
        row["token_usage"] = normalize_token_usage(raw)
        rows.append(row)

    conditions = sorted({str(row["condition"]) for row in rows})
    if args.reference not in conditions:
        raise SystemExit(f"Reference condition {args.reference!r} not present")

    aggregates = {
        condition: aggregate_condition([row for row in rows if row["condition"] == condition])
        for condition in conditions
    }
    valid_rows = [row for row in rows if row["valid_for_analysis"]]
    qualified_task_means = task_means(valid_rows, "qualified_numeric")
    quality_task_means = task_means(valid_rows, "quality_score")
    rng = random.Random(args.seed)
    comparisons: dict[str, object] = {}
    for condition in conditions:
        if condition == args.reference:
            continue
        comparisons[condition] = {
            "qualified_rate": paired_bootstrap(
                qualified_task_means, args.reference, condition, args.bootstrap_samples, rng
            ),
            "quality_score": paired_bootstrap(
                quality_task_means, args.reference, condition, args.bootstrap_samples, rng
            ),
        }

    generated_at = args.generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    summary = {
        "title": args.title,
        "dataset_note": args.dataset_note,
        "generated_at": generated_at,
        "input_file": str(args.input),
        "reference_condition": args.reference,
        "bootstrap_samples": args.bootstrap_samples,
        "seed": args.seed,
        "warnings": warnings,
        "token_accounting": {
            "total_formula": "input_tokens + output_tokens",
            "cached_input_tokens_are_subset": True,
            "cache_write_input_tokens_are_detail": True,
            "reasoning_tokens_are_subset": True,
            "tokens_per_qualified_success_requires_complete_coverage": True,
        },
        "conditions": aggregates,
        "paired_differences": comparisons,
    }

    lines = [f"# {args.title}", ""]
    if args.dataset_note:
        lines.extend([f"> {args.dataset_note}", ""])
    lines.extend([
        f"Generated: `{generated_at}`",
        "",
        "## Quality and qualification",
        "",
        "| Condition | Valid runs | Qualified success | Critical failures | Mean quality | Mean quality among qualified | Ownership among qualified | Median net lines added among qualified | Median tool calls among qualified | Median elapsed seconds among qualified |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for condition in conditions:
        item = aggregates[condition]
        lines.append(
            f"| {condition} | {item['valid_runs']} | {percent(item['qualified_success_rate'])} | "
            f"{item['critical_failures']} | {fmt(item['mean_quality_all'])} | "
            f"{fmt(item['mean_quality_qualified'])} | {fmt(item['mean_ownership_qualified'])} | "
            f"{fmt(item['median_net_lines_added_qualified'], 1)} | "
            f"{fmt(item['median_tool_calls_qualified'], 1)} | "
            f"{fmt(item['median_elapsed_seconds_qualified'], 1)} |"
        )

    lines.extend([
        "",
        "## Token usage",
        "",
        "Normalized total tokens equal input plus output tokens. Cached-input, cache-write, and reasoning-token fields are informational details and are not added again.",
        "",
        "| Condition | Coverage | Total tokens | Median input | Median cached | Median cache-write | Median output | Median reasoning | Median total | Median total/qualified | Tokens/success | Adapter counts |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ])
    for condition in conditions:
        token = aggregates[condition]["token_usage"]
        adapter_counts = ", ".join(f"{key}: {value}" for key, value in token["adapter_counts"].items()) or "—"
        lines.append(
            f"| {condition} | {percent(token['coverage_rate_valid'])} | "
            f"{token['total_measured_tokens_valid']:,} | "
            f"{fmt(token['median_input_tokens_valid'], 1)} | "
            f"{fmt(token['median_cached_input_tokens_valid'], 1)} | "
            f"{fmt(token['median_cache_write_input_tokens_valid'], 1)} | "
            f"{fmt(token['median_output_tokens_valid'], 1)} | "
            f"{fmt(token['median_reasoning_tokens_valid'], 1)} | "
            f"{fmt(token['median_total_tokens_valid'], 1)} | "
            f"{fmt(token['median_total_tokens_qualified'], 1)} | "
            f"{fmt(token['tokens_per_qualified_success'], 1)} | {adapter_counts} |"
        )

    lines.extend([
        "",
        f"## Task-paired bootstrap differences versus `{args.reference}`",
        "",
        "Positive values favor the reference condition.",
        "",
        "| Comparison | Qualified-rate difference | 95% CI | Quality-score difference | 95% CI | Paired tasks |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for condition in conditions:
        if condition == args.reference:
            continue
        pair = comparisons[condition]
        q = pair["qualified_rate"]
        s = pair["quality_score"]
        lines.append(
            f"| {condition} | {fmt(q['difference'], 3)} | "
            f"[{fmt(q['ci95'][0], 3)}, {fmt(q['ci95'][1], 3)}] | "
            f"{fmt(s['difference'])} | [{fmt(s['ci95'][0])}, {fmt(s['ci95'][1])}] | "
            f"{min(q['paired_tasks'], s['paired_tasks'])} |"
        )

    lines.extend([
        "",
        "## Interpretation cautions",
        "",
        "- Correctness and the qualification gate come before ownership or token efficiency.",
        "- `tokens per qualified success` is omitted unless every valid run in the condition has a usable token total.",
        "- Estimated token counts must remain labeled and should not be treated as provider-equivalent exact usage.",
        "- Confidence intervals describe this frozen task suite, model, and execution setup—not every coding environment.",
        "- Inspect task-level failures because aggregate scores can hide underimplementation or critical regressions.",
        "",
    ])

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    normalized_fields = list(raw_rows[0].keys()) + [
        "qualified",
        "quality_score",
        "normalized_input_tokens",
        "normalized_cached_input_tokens",
        "normalized_cache_write_input_tokens",
        "normalized_output_tokens",
        "normalized_reasoning_tokens",
        "normalized_total_tokens",
        "normalized_token_usage_source",
    ]
    with (args.output_dir / "normalized-runs.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=normalized_fields)
        writer.writeheader()
        for raw, row in zip(raw_rows, rows):
            usage = row["token_usage"]
            enriched = dict(raw)
            enriched.update(
                {
                    "qualified": "yes" if row["qualified"] else "no",
                    "quality_score": f"{float(row['quality_score']):.4f}",
                    "normalized_input_tokens": usage["input_tokens"] if usage["input_tokens"] is not None else "",
                    "normalized_cached_input_tokens": usage["cached_input_tokens"] if usage["cached_input_tokens"] is not None else "",
                    "normalized_cache_write_input_tokens": usage["cache_write_input_tokens"] if usage["cache_write_input_tokens"] is not None else "",
                    "normalized_output_tokens": usage["output_tokens"] if usage["output_tokens"] is not None else "",
                    "normalized_reasoning_tokens": usage["reasoning_tokens"] if usage["reasoning_tokens"] is not None else "",
                    "normalized_total_tokens": usage["total_tokens"] if usage["total_tokens"] is not None else "",
                    "normalized_token_usage_source": usage["token_usage_source"],
                }
            )
            writer.writerow(enriched)

    print(f"Wrote {args.output_dir / 'summary.md'}")
    print(f"Wrote {args.output_dir / 'summary.json'}")
    print(f"Wrote {args.output_dir / 'normalized-runs.csv'}")


if __name__ == "__main__":
    main()
