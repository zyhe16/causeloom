# Evaluation kit

This directory contains a no-API benchmark for comparing Causeloom with the same
coding agent receiving no additional policy through Codex CLI or ChatGPT desktop.

## Conditions

```text
baseline
causeloom
```

The Causeloom policy snapshot and checksum are under `conditions/`.

## Research matrix

```bash
make research-matrix
```

This creates a randomized 78-run order for thirteen upstream tasks, two
conditions, and three repetitions. Harbor supplies the task containers and
official graders. Complete the preflights in `RESEARCH_SUITE.md` before model
execution.

## Scripts

| Script | Purpose |
|---|---|
| `generate_run_matrix.py` | Produce a balanced randomized matrix |
| `prepare_research_benchmark.py` | Digest-lock and adapt upstream tasks for agent-only egress control |
| `reuse_research_preflight.py` | Reuse model-free evidence only after executable task-content equivalence is proven |
| `prepare_codex_benchmark_config.py` | Copy a verified model selection into an isolated config without CLI overrides |
| `finalize_research_preflight.py` | Validate oracle, no-op, isolation, and grader-randomness gates |
| `run_research_benchmark.py` | Run locked task queues with bounded concurrency |
| `audit_research_benchmark.py` | Audit terminal artifacts, identities, validity, rewards, and token coverage |
| `extract_codex_usage.py` | Normalize usage from exec or session JSONL |
| `collect_diff_metrics.py` | Measure tracked and untracked changes |
| `validate_results.py` | Validate scored CSV and token invariants |
| `summarize_results.py` | Produce Markdown, JSON, and normalized CSV reports |

## Task suite and scoring

The benchmark uses the thirteen-task Terminal-Bench 2.0 selection in
`research-suite.csv`: the original 3-medium/7-extreme core plus three
preregistered coverage tasks. Read `RESEARCH_SUITE.md` for provenance,
contamination caveats, and Harbor preflight requirements.

Correctness is a qualification gate. Engineering outcome and blinded quality
come before cost diagnostics; tokens are never part of the quality score. Raw
usage artifacts are retained. See `../docs/TOKEN_ACCOUNTING.md`.

For an accelerated run, `prepare_research_benchmark.py --worker-slots 13`
freezes one sequential queue per task. `run_research_benchmark.py --max-workers
N` may then cap active queues without changing the lock or run identities.
Record every attempted cap because concurrency changes host contention.

The completed public summary, chart-ready data, audit hashes, and a3/a5
comparability limits are in [`../docs/benchmarks`](../docs/benchmarks/).
