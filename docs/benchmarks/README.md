# Benchmark evidence

This directory contains the public, chart-ready summary of Causeloom's matched
Terminal-Bench 2.0 evaluation. Public comparisons are limited to Causeloom and
the same agent receiving no additional skill.

## Published result

The benchmark uses thirteen tasks, two conditions, and three repetitions: 39
attempts per condition and 78 total. Every run used GPT-5.6 Luna at max
reasoning, Codex CLI 0.146.0, the same seed and a6 timeout contract, a fresh
Harbor container and Codex home, and no general internet access during the
agent phase.

The a6 contract deliberately gives each agent four times the upstream time
limit. A shorter limit would confound task-solving ability with speed by
censoring agents before they can finish. This benchmark therefore measures
completion under a generous fixed budget and reports elapsed time separately.
All 78 runs finished within that budget.

Causeloom earned 28/39 official-verifier passes (71.8%) versus 21/39 (53.8%)
for the no-skill baseline. All 78 attempts were exception-free and none reached
the agent time limit. The mechanical closeout found zero violations and zero
warnings.

The arithmetic-mean token fields in [`results.json`](results.json) come from
the 78 preserved raw Codex streams. Normalized total tokens equal input plus
output; cached-input and reasoning fields are non-additive details. Tokens are
cost diagnostics, not quality scores.

## Code-quality evidence

The README includes a post-hoc Codex review of three shortened code comparisons
from the same matched Luna run. It uses preserved final artifacts and verifier
traces. The review was not blinded and did not assign a subjective numeric
score, so it remains separate from official verifier reward.

## Reproduce the figures

```bash
python docs/benchmarks/generate_charts.py
```

The standard-library generator writes three accessible SVGs:

- the matched overall pass-rate comparison;
- pass rates by preregistered task category; and
- task cells where Causeloom passed at least once and the baseline passed zero.

## Audit provenance

- Suite: `Terminal-Bench 2.0`.
- Model: `gpt-5.6-luna`.
- Reasoning effort: `max`.
- Codex CLI: `0.146.0`.
- Run-order seed: `329`.
- Evaluated and published policy SHA-256:
  `d4c313db9a48368c3ae0044c6f4686feb774c8d1a5c03d5b5d9b837d54753797`.
- Benchmark lock SHA-256:
  `f4931e14c505914c37b184b337aa4c7b40e1501191a089312a90d3c23194d6a1`.
- Closeout audit SHA-256:
  `1643df7726dbb4a2c80a0fbf93e27b7d064b852d22841f145cd85225ee2589ee`.

Complete Harbor results, Codex event streams, rollout sessions, trajectories,
verifier logs, and final code are retained locally under
`work/research-benchmark-gpt56-luna-max-a6/` and excluded from Git.

> [!NOTE]
> This directory documents the completed a6 evidence exactly as it ran. New
> benchmark preparation uses the a7 standard in `evals/`: Luna/max, thirteen
> one-task queues, eight workers, and no agent timeout.

## Limits

Official reward measures functional completion, not blinded engineering
quality. Terminal-Bench 2.0 is public and may be contaminated for current
models. The result covers one model and thirteen tasks; broader claims need
other models, private holdouts, and a blinded review.
