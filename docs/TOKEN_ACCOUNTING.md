# Token accounting

Token usage is a first-class benchmark output because a longer policy can improve quality while also increasing context and generation cost.

## Normalized fields

Every scored run supports:

```text
input_tokens
cached_input_tokens
cache_write_input_tokens
output_tokens
reasoning_tokens
total_tokens
token_usage_source
token_usage_adapter
```

The normalized total is:

```text
total_tokens = input_tokens + output_tokens
```

Cached-input tokens are part of input usage. Reasoning tokens are part of output usage. Cache-write input tokens describe prompt-cache activity. These detail fields are **not** added to the total again.

## Codex CLI

For Codex CLI runs, preserve the raw `codex exec --json` JSONL. `extract_codex_usage.py` reads `turn.completed.usage` and maps current Codex fields as follows:

| Codex JSONL field | Normalized field |
|---|---|
| `input_tokens` | `input_tokens` |
| `cached_input_tokens` | `cached_input_tokens` |
| `cache_write_input_tokens` | `cache_write_input_tokens` |
| `output_tokens` | `output_tokens` |
| `reasoning_output_tokens` | `reasoning_tokens` |
| input + output | `total_tokens` |

The source is recorded as `agent_log` and the adapter as `codex_exec_jsonl`.

## ChatGPT desktop app

The desktop workflow supports two sources:

1. a saved local Codex session JSONL containing `total_token_usage`, recorded with adapter `codex_session_jsonl`;
2. manual transcription from `/status`, recorded with adapter `desktop_status_manual`.

Because local session formats can change and some versions may omit detailed token events, missing fields should remain blank. Do not fabricate an input/output split from a total-only display.

## Run boundary

Measure the complete run from the initial model-visible task and selected skill through the final response. For fair comparisons:

- start a fresh session for every repetition;
- keep the same surface, model, reasoning effort, and common instructions;
- include skill-loading overhead when the client reports it;
- do not include reviewer scoring or grader-only checks in model token usage;
- do not mix cumulative account usage from `/usage` with per-session usage from `/status`.

## Sources

`token_usage_source` uses:

```text
provider_reported
agent_log
estimated
unavailable
```

`token_usage_adapter` records the concrete collection path, such as:

```text
codex_exec_jsonl
codex_session_jsonl
desktop_status_manual
synthetic_fixture
```

Use `estimated` only when a documented tokenizer or reproducible method was required. Exact client logs are preferable. Use `unavailable` rather than inventing precision.

## Reports

The generated Markdown and JSON reports include:

- token coverage by condition;
- total measured tokens;
- median input, cached-input, cache-write, output, reasoning, and total tokens;
- median total tokens among qualified runs;
- tokens per qualified success when every valid run has usable totals;
- source and adapter counts.

Efficiency is interpreted only after correctness. A small failed run is not a successful token optimization.
