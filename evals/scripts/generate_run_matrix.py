#!/usr/bin/env python3
"""Generate a balanced, deterministic, randomized evaluation run matrix."""

from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", required=True, type=Path)
    condition_source = parser.add_mutually_exclusive_group(required=True)
    condition_source.add_argument(
        "--conditions", help="Comma-separated condition names used for every task"
    )
    condition_source.add_argument(
        "--condition-plan",
        type=Path,
        help="JSON file with default_conditions and optional task_conditions",
    )
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--seed", type=int, default=329)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    if args.repetitions < 1:
        raise SystemExit("--repetitions must be at least 1")
    if args.condition_plan is not None:
        plan = json.loads(args.condition_plan.read_text(encoding="utf-8"))
        default_conditions = plan.get("default_conditions", [])
        task_conditions = plan.get("task_conditions", {})
        if not isinstance(default_conditions, list) or not isinstance(
            task_conditions, dict
        ):
            raise SystemExit("condition plan must define list default_conditions and object task_conditions")
    else:
        assert args.conditions is not None
        default_conditions = [
            value.strip() for value in args.conditions.split(",") if value.strip()
        ]
        task_conditions = {}

    def validate_conditions(values: object, label: str) -> list[str]:
        if not isinstance(values, list) or not values or not all(
            isinstance(value, str) and value.strip() for value in values
        ):
            raise SystemExit(f"{label} must be a non-empty list of condition names")
        normalized = [value.strip() for value in values]
        if len(set(normalized)) != len(normalized):
            raise SystemExit(f"{label} must contain unique condition names")
        return normalized

    default_conditions = validate_conditions(default_conditions, "default_conditions")
    task_conditions = {
        str(task_id): validate_conditions(values, f"task_conditions.{task_id}")
        for task_id, values in task_conditions.items()
    }

    with args.tasks.open(newline="", encoding="utf-8") as handle:
        task_ids = []
        for row in csv.DictReader(handle):
            task_id = (row.get("task_id") or row.get("suite_task_id") or "").strip()
            if task_id:
                task_ids.append(task_id)
    if not task_ids or len(set(task_ids)) != len(task_ids):
        raise SystemExit(
            "tasks must contain unique non-empty task_id or suite_task_id values"
        )
    unknown_plan_tasks = set(task_conditions) - set(task_ids)
    if unknown_plan_tasks:
        raise SystemExit(
            f"condition plan contains unknown task IDs: {sorted(unknown_plan_tasks)}"
        )

    rows: list[dict[str, str | int]] = []
    for task_id in task_ids:
        conditions = task_conditions.get(task_id, default_conditions)
        for repetition in range(1, args.repetitions + 1):
            for condition in conditions:
                rows.append(
                    {
                        "run_id": f"{task_id}-{condition}-r{repetition}",
                        "task_id": task_id,
                        "condition": condition,
                        "repetition": repetition,
                    }
                )

    random.Random(args.seed).shuffle(rows)
    for order, row in enumerate(rows, start=1):
        row["execution_order"] = order

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["execution_order", "run_id", "task_id", "condition", "repetition"],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} randomized runs to {args.output}")


if __name__ == "__main__":
    main()
