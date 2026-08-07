# Benchmark evidence

This directory contains the public, chart-ready summary of Causeloom's frozen
Terminal-Bench 2.0 evaluation. Public comparisons are intentionally limited to
Causeloom and the same agent receiving no additional skill.

## Result view

The public chart covers thirteen tasks with three repetitions: 39 attempts per
condition. The evaluation was completed in two phases to avoid spending tokens
on unnecessary reruns. Causeloom uses 39 a5 trials; the no-skill baseline uses
27 a5 trials and 12 completed a3 trials.

The phases share the task selection, model family, repetitions, and run-order
seed. The reused a3 cells have an earlier timeout contract, and a shared seed
does not make a hosted model deterministic. Treat the combined chart as
descriptive evidence rather than a fully matched causal estimate.

The mean-token fields in [`results.json`](results.json) come from preserved raw
records: the arithmetic mean across all attempted runs and the arithmetic mean
among runs with official reward 1. Tokens are cost diagnostics, not quality
scores.

## Code-quality evidence

The README also summarizes an exploratory, post-hoc review of 15 pre-rc.3
Causeloom code artifacts across five code-bearing tasks. That review inspected
final code structure and representative successes and failures but was not
blinded and did not assign a subjective numeric score. It is therefore reported
separately from official verifier reward.

## Reproduce the figure

```bash
python docs/benchmarks/generate_charts.py
```

The generator uses only the Python standard library and writes
[`benchmark-full.svg`](../assets/benchmark-full.svg).

## Audit provenance

- Model: `gpt-5.6-sol`
- Reasoning effort: `high`
- Codex CLI: `0.146.0`
- Run-order seed: `329`
- Evaluated pre-publication policy SHA-256:
  `1f94841a1edc6767277c666b5b0e57ba00f8b61046010c40d10fc9c38882df2e`
- Published Causeloom 0.3.0 policy SHA-256 is recorded in `results.json` and
  `evals/conditions/CHECKSUMS.sha256`.
- Historical a3 audit SHA-256:
  `ec597ac1ce5b73b4d2063fecf2e56fb9c3e7b01628d890272002c4b84569910e`
- Incremental a5 audit SHA-256:
  `40cf0f2db3088e8e256f0efe2d8fd75cfa5222df7d44e33150281b23cc5d8239`

Complete Harbor results, Codex event streams, rollout sessions, trajectories,
verifier logs, final code, and private calibration conditions are retained
locally and excluded from Git.
