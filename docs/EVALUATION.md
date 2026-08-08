# Systematic evaluation protocol

## Research question

Does Causeloom improve complete task success and engineering quality compared
with the same coding agent receiving no additional skill?

## Conditions

Run two isolated conditions:

1. `baseline`: no additional coding skill; and
2. `causeloom`: the frozen Causeloom policy only.

The selected policy is installed project-locally before each fixture's baseline
commit and explicitly invoked where the execution surface supports it.

## Supported execution surfaces

### Codex CLI

Use Codex CLI with ChatGPT authentication for the main repeated experiment,
connected to the official Harbor task containers. Preserve raw Codex and Harbor
artifacts for every run.

### ChatGPT desktop app

Desktop runs may be used for separate product-level validation, but they are not
part of the automated Terminal-Bench comparison.

No direct OpenAI API call is required for either workflow.

## Recommended scale

```text
13 Terminal-Bench 2.0 tasks x 2 conditions x 3 repetitions = 78 runs
```

The preregistered selection and external-harness requirements are in
`evals/RESEARCH_SUITE.md`. Run its oracle, dummy-agent, artifact-isolation, and
Docker preflights before any model run.

The completed GPT-5.6 Luna Max result, chart-ready data, and audit hashes are
published in [`benchmarks/`](benchmarks/). It is a fully matched 78-run
comparison under the a6 execution contract; no historical cells are pooled
into the public result.

## Standard execution profile

Every newly prepared benchmark uses GPT-5.6 Luna with max reasoning, Codex CLI
0.146.0, seed 329, the complete 78-run matrix, thirteen one-task queues, and
eight concurrent workers. The a7 adaptation has no agent timeout. Its global
work-conserving scheduler allows at most two repetitions of one task at once
and at most 20 GB of aggregate declared task memory.

The lock freezes these values before model execution. Changing the model,
reasoning effort, matrix, queue layout, worker cap, scheduler limits, or agent
timeout policy creates a different benchmark contract and requires fresh
model-free preflight evidence.

## Freeze the environment

Keep constant:

- Codex or desktop-app version;
- model and model alias;
- reasoning effort, speed tier, and personality;
- local versus cloud execution;
- repository snapshot and task prompt;
- sandbox, permissions, network access, hooks, and tools;
- context and tool budgets; and
- all common instructions outside the selected policy.

The agent phase must have no general internet egress and no browser, web-search,
MCP, or connector tools. Image pulls and dependency installation happen before
agent work. If Codex requires a local model relay, expose only that endpoint
through a dedicated allowlist and verify that arbitrary outbound requests fail.

Do not impose an agent-phase time limit. Keep verifier, agent-setup, and
environment-build timeouts as infrastructure health checks; they do not cap a
healthy model's working time.

Use a fresh repository and fresh chat for every run. Randomize execution order.
Use an isolated Codex evaluation profile to prevent unrelated global skills and
user configuration from contaminating either condition.

The task instructions and container artifacts are fixed by digest; they are not
generated from a seed. Seed `329` controls run ordering and every grader-side
random source must also be explicitly seeded. Hosted model trajectories may
still vary, so use three repetitions and report that variance.

## Qualification gate

A run is a qualified success only when:

```text
the real goal is achieved
AND public checks pass or are not applicable
AND grader-only checks pass or are not applicable
AND no critical failure occurs
AND the run is valid and not blocked by the environment
```

Correctness and full requirement fidelity qualify a solution. Smaller diffs,
fewer tool calls, lower token usage, and shorter elapsed time are cost
diagnostics and may distinguish only solutions with equivalent outcomes.

## Review

For a full quality comparison, use at least two blinded reviewers. Give them the
starting fixture, original prompt, resulting patch and untracked files, check
logs, final response, and task-specific grading notes. Hide the condition,
policy text, and randomized order. Use `evals/rubric.md`; do not reduce ownership
judgment to lines of code.

## Token accounting

Record input, cached input, cache-write input, output, reasoning, and total
tokens whenever the client exposes them. Keep the raw event or session artifact.
Do not mix per-session totals with cumulative account activity. See
`docs/TOKEN_ACCOUNTING.md`.

## Statistical analysis

Treat the task, not each repetition, as the primary comparison unit:

1. average repetitions within each task and condition;
2. compare conditions task by task;
3. bootstrap paired task-level differences;
4. report 95% confidence intervals; and
5. inspect category-level regressions and critical failures.

Use a lexicographic interpretation: qualified success, critical failures,
blinded quality among qualified runs, task-specific robustness, partial progress,
then cost diagnostics. Do not award a failed run for cheap failure.

## Public tasks and holdouts

Harbor must keep grader tests and oracle solutions outside the agent workspace.
A public benchmark may be present in training data. Strong general-performance
claims should therefore include private holdout tasks following the same schema,
reported separately from public-fixture results.
