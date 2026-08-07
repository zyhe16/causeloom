from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "evals/scripts/summarize_results.py"
TEMPLATE = ROOT / "evals/templates/scored-runs.csv"


class SummarizeResultsTest(unittest.TestCase):
    def test_outputs_include_normalized_token_usage(self):
        header = TEMPLATE.read_text(encoding="utf-8").strip().split(",")
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            scored = temp_path / "runs.csv"
            rows = []
            for condition, input_tokens, output_tokens in (
                ("baseline", 100, 50),
                ("causeloom", 120, 40),
            ):
                row = {key: "" for key in header}
                row.update({
                    "run_id": f"T-{condition}-r1",
                    "task_id": "T",
                    "condition": condition,
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
                    "net_lines_removed": "0",
                    "new_production_dependencies": "0",
                    "new_configuration_keys": "0",
                    "new_abstractions": "0",
                    "tool_calls": "2",
                    "input_tokens": str(input_tokens),
                    "cached_input_tokens": "20",
                    "cache_write_input_tokens": "5",
                    "output_tokens": str(output_tokens),
                    "reasoning_tokens": "10",
                    "total_tokens": str(input_tokens + output_tokens),
                    "token_usage_source": "provider_reported",
                    "token_usage_adapter": "codex_exec_jsonl",
                    "elapsed_seconds": "2",
                })
                for score in (
                    "functional_correctness", "requirement_fidelity", "architecture_root_cause",
                    "ownership_discipline", "verification_quality", "safety_robustness",
                    "communication_clarity",
                ):
                    row[score] = "4"
                rows.append(row)
            with scored.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=header)
                writer.writeheader()
                writer.writerows(rows)

            output = temp_path / "out"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--input", str(scored),
                    "--output-dir", str(output),
                    "--reference", "causeloom",
                    "--bootstrap-samples", "100",
                    "--generated-at", "2026-08-04T00:00:00Z",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            data = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            baseline = data["conditions"]["baseline"]["token_usage"]
            self.assertEqual(baseline["total_measured_tokens_valid"], 150)
            self.assertEqual(baseline["tokens_per_qualified_success"], 150)
            self.assertTrue(data["token_accounting"]["cached_input_tokens_are_subset"])
            self.assertTrue((output / "summary.md").is_file())
            self.assertTrue((output / "normalized-runs.csv").is_file())


if __name__ == "__main__":
    unittest.main()
