from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals/scripts"))

from codex_events import parse_cli_events, parse_desktop_session  # noqa: E402


class CodexEventsTest(unittest.TestCase):
    def test_cli_parser_sums_turns_without_double_counting_details(self):
        with tempfile.TemporaryDirectory() as temp:
            first = Path(temp) / "one.jsonl"
            second = Path(temp) / "two.jsonl"
            first.write_text(
                "\n".join(
                    [
                        json.dumps({"type": "thread.started", "thread_id": "thread-1"}),
                        json.dumps({"type": "item.completed", "item": {"type": "command_execution"}}),
                        json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "Question?"}}),
                        json.dumps({"type": "turn.completed", "usage": {"input_tokens": 100, "cached_input_tokens": 40, "cache_write_input_tokens": 7, "output_tokens": 20, "reasoning_output_tokens": 5}}),
                    ]
                ) + "\n",
                encoding="utf-8",
            )
            second.write_text(
                json.dumps({"type": "turn.completed", "usage": {"input_tokens": 60, "cached_input_tokens": 10, "cache_write_input_tokens": 3, "output_tokens": 10, "reasoning_tokens": 2}}) + "\n",
                encoding="utf-8",
            )
            result = parse_cli_events([first, second])
            self.assertEqual(result["thread_id"], "thread-1")
            self.assertEqual(result["tool_calls"], 1)
            self.assertEqual(result["usage"]["input_tokens"], 160)
            self.assertEqual(result["usage"]["cached_input_tokens"], 50)
            self.assertEqual(result["usage"]["cache_write_input_tokens"], 10)
            self.assertEqual(result["usage"]["output_tokens"], 30)
            self.assertEqual(result["usage"]["reasoning_tokens"], 7)
            self.assertEqual(result["usage"]["total_tokens"], 190)

    def test_desktop_parser_uses_last_cumulative_total(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "rollout.jsonl"
            rows = [
                {"timestamp": "2026-08-04T10:00:00Z", "payload": {"type": "token_count", "info": {"total_token_usage": {"input_tokens": 100, "cached_input_tokens": 30, "cache_write_input_tokens": 4, "output_tokens": 20, "reasoning_output_tokens": 4}}}},
                {"timestamp": "2026-08-04T10:01:00Z", "payload": {"type": "token_count", "info": {"total_token_usage": {"input_tokens": 250, "cached_input_tokens": 80, "cache_write_input_tokens": 9, "output_tokens": 50, "reasoning_output_tokens": 10}}}},
            ]
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            result = parse_desktop_session(path)
            self.assertEqual(result["usage"]["cache_write_input_tokens"], 9)
            self.assertEqual(result["usage"]["total_tokens"], 300)
            self.assertIn("cumulative", result["method"])


if __name__ == "__main__":
    unittest.main()
