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

## Standard benchmark profile

New benchmark preparation and execution use one standard profile:

| Setting | Standard |
|---|---|
| Model | `gpt-5.6-luna` |
| Reasoning effort | `max` |
| Codex CLI | `0.146.0` |
| Matrix | 13 tasks x 2 conditions x 3 repetitions = 78 runs |
| Run-order seed | `329` |
| Agent timeout | None |
| Task queues | 13, one per task |
| Concurrent workers | 8 |
| Per-task concurrency | 2 repetitions |
| Declared-memory cap | 20 GB |
| Run root | `work/research-benchmark-standard` |

`make research-prepare` creates an `a7` lock with these execution settings.
`prepare_codex_benchmark_config.py` accepts only Luna/max by default and writes
the isolated config beside that lock. The runner reads the eight-worker cap
from the lock; passing `--max-workers` is an explicit nonstandard override that
must be reported.

After the required model-free preflights and readiness marker, the standard
entrypoints need no benchmark-setting flags:

```bash
python evals/scripts/prepare_codex_benchmark_config.py
python evals/scripts/run_research_benchmark.py \
  --execute \
  --stop-on-infrastructure-error
```

The runner defaults to the pinned Codex 0.146.0 Linux binary and SHA-256 used by
the published Luna run. It still validates every file and locked identity before
starting.

The agent phase has no watchdog. Harbor verifier, environment-build, and agent
setup timeouts remain enabled because they detect broken infrastructure rather
than limit model work.

## Scripts

| Script | Purpose |
|---|---|
| `generate_run_matrix.py` | Produce a balanced randomized matrix |
| `prepare_research_benchmark.py` | Digest-lock and adapt upstream tasks for agent-only egress control |
| `reuse_research_preflight.py` | Reuse model-free evidence only after executable task-content equivalence is proven |
| `prepare_codex_benchmark_config.py` | Copy a verified model selection into an isolated config without CLI overrides |
| `finalize_research_preflight.py` | Validate oracle, no-op, isolation, and grader-randomness gates |
| `run_research_benchmark.py` | Run locked trials with bounded, resource-aware concurrency |
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

Newly prepared locks use a work-conserving global scheduler. The seeded global
execution order remains the priority, but the runner may start a later eligible
trial when the next trial is blocked by a per-task or memory cap. By default,
up to two independent repetitions of one task may run concurrently, aggregate
declared task memory may not exceed 20 GB, and eight workers are the hard
process cap. These values are frozen into the lock and must not be changed
after preflight. Record any explicit override because concurrency changes host
contention and makes wall-clock comparisons non-equivalent.

The completed matched Luna a6 summary, chart-ready data, and audit hashes are
in [`../docs/benchmarks`](../docs/benchmarks/). That historical run used longer
agent limits; all 78 trials finished before them. The current a7 standard
removes the agent timeout entirely.
