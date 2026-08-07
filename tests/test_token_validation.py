from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals/scripts"))

from validate_results import validate_rows  # noqa: E402


def valid_row() -> dict[str, str]:
    row = {
        "run_id": "T-baseline-r1",
        "task_id": "T",
        "condition": "baseline",
        "repetition": "1",
        "valid_run": "yes",
        "environment_failure": "no",
        "goal_achieved": "yes",
        "public_checks_pass": "yes",
        "hidden_checks_pass": "yes",
        "critical_failure": "no",
        "clarification_behavior": "not_applicable",
        "files_changed": "1",
        "net_lines_added": "2",
        "net_lines_removed": "1",
        "new_production_dependencies": "0",
        "new_configuration_keys": "0",
        "new_abstractions": "0",
        "tool_calls": "3",
        "input_tokens": "100",
        "cached_input_tokens": "40",
        "cache_write_input_tokens": "12",
        "output_tokens": "50",
        "reasoning_tokens": "20",
        "total_tokens": "150",
        "token_usage_source": "provider_reported",
        "token_usage_adapter": "codex_exec_jsonl",
        "elapsed_seconds": "1.5",
    }
    for column in (
        "functional_correctness", "requirement_fidelity", "architecture_root_cause",
        "ownership_discipline", "verification_quality", "safety_robustness",
        "communication_clarity",
    ):
        row[column] = "4"
    return row


class TokenValidationTest(unittest.TestCase):
    def test_valid_subset_details_are_not_double_counted(self):
        errors, _warnings = validate_rows([valid_row()], strict_token_coverage=True)
        self.assertEqual(errors, [])

    def test_total_must_equal_input_plus_output_only(self):
        row = valid_row()
        row["total_tokens"] = "210"  # incorrectly adds cached and reasoning details
        errors, _warnings = validate_rows([row])
        self.assertTrue(any("not additive" in error for error in errors))

    def test_cached_and_reasoning_must_fit_parent_totals(self):
        row = valid_row()
        row["cached_input_tokens"] = "101"
        row["reasoning_tokens"] = "51"
        errors, _warnings = validate_rows([row])
        self.assertTrue(any("cached_input_tokens cannot exceed" in error for error in errors))
        self.assertTrue(any("reasoning_tokens cannot exceed" in error for error in errors))

    def test_unavailable_must_not_claim_numeric_tokens(self):
        row = valid_row()
        row["token_usage_source"] = "unavailable"
        errors, _warnings = validate_rows([row])
        self.assertTrue(any("must be blank" in error for error in errors))

    def test_clarification_behavior_must_use_rubric_vocabulary(self):
        row = valid_row()
        row["clarification_behavior"] = "kind_of_asked"
        errors, _warnings = validate_rows([row])
        self.assertTrue(any("clarification_behavior" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
