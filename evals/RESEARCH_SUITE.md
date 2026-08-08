# Research-backed engineering suite

This is the benchmark design for frontier-model evaluation. It replaces the removed project-authored synthetic fixtures.

No task prompt, test, solution, or container is copied into this repository. Harbor obtains the frozen upstream task artifacts at execution time so that grader tests and oracle solutions stay outside the agent workspace.

## Why Terminal-Bench 2.0

The suite uses thirteen existing tasks from [Terminal-Bench 2.0](https://arxiv.org/abs/2601.11868), not newly invented prompts. The published benchmark provides:

- tasks inspired by real technical workflows;
- a separate containerized environment for every task;
- human-written oracle solutions and outcome-based tests;
- review by three experienced humans plus automated, oracle, dummy-agent, and adversarial checks;
- direct Harbor support for Codex CLI;
- task-level empirical difficulty evidence from 32,155 trials; and
- an Apache-2.0 implementation and task repository.

The official [Harbor instructions](https://www.tbench.ai/docs/run-terminal-bench-2-0) identify Harbor as the Terminal-Bench 2.0 harness. Freeze the dataset as `terminal-bench@2.0`; do not silently substitute `head`, Terminal-Bench 2.1, or Frontier-Bench.

Terminal-Bench 2.0 is public and may be contaminated for newer models. Results therefore measure performance on this frozen public suite, not uncontaminated general coding ability. The final report must disclose that limitation and must not combine these results with the old synthetic run.

## Selection method

The thirteen tasks are listed in `research-suite.csv`. The original ten-task core was selected before the completed rc2 comparison. The three-task coverage expansion is preregistered for the rc3 comparison and must not be retroactively added to the old result.

The three calibration tasks all have the benchmark authors' `medium` label and cover C++ debugging, multi-service deployment, and instrumented source builds without runtime downloads:

1. `custom-memory-heap-crash`
2. `git-multibranch`
3. `sqlite-with-gcov`

The seven extreme tasks come from the difficult half of Figure 11's published task ordering, with five in the bottom twenty-four positions. They were chosen for engineering breadth rather than puzzle novelty:

1. `llm-inference-batching-scheduler`
2. `make-doom-for-mips`
3. `db-wal-recovery`
4. `torch-tensor-parallelism`
5. `make-mips-interpreter`
6. `torch-pipeline-parallelism`
7. `filter-js-from-html`

`db-wal-recovery` and `filter-js-from-html` are author-labeled medium but empirically appear deep in the model-difficulty ordering. This disagreement is useful evidence: the paper reports that models frequently find some human-medium tasks unexpectedly hard. The `extreme` label in this repository refers to the published empirical ordering and the frontier-evaluation purpose, not a rewritten upstream label.

The rc3 coverage tier adds three tasks chosen to test behavior that the systems-heavy core does not isolate:

| Priority | Task | Role | Main rc3 behavior tested |
|---:|---|---|---|
| 1 | `modernize-scientific-stack` | Low-ambiguity efficiency control | Minimum sufficient rigor and early stopping |
| 2 | `kv-store-grpc` | Conventional backend/API feature | Final entrypoint and end-to-end verification |
| 3 | `fix-code-vulnerability` | Existing-repository surgical maintenance | Proportionate rigor at a trust boundary |

These are labeled `coverage`, not `medium` or `extreme`, because their selection purpose is capability coverage rather than the original difficulty-stratification rule. Their upstream author labels and Figure 11 positions remain recorded separately in the manifest.

Tasks that require unavailable source retrieval during the agent phase remain excluded, including `pypi-server` and `build-cython-ext`. `kv-store-grpc` is now feasible under isolation because its exact required packages, `grpcio==1.73.0` and `grpcio-tools==1.73.0`, are installed while the environment image is built. No proto, generated bindings, server implementation, or solution code is preinstalled.

## Network isolation

The agent may not use web search, package registries, source hosting, documentation sites, remote shells, or any other external source of solution help.

Enforce this technically for every trial. The checked-in local runner uses a portable Docker Desktop topology because Harbor 0.20.0's nftables allowlist is unavailable on this Windows host:

- start the task on a public setup/verifier network plus an internal agent network;
- disconnect the task container from the public network for `agent.run()` and verify the transition through Docker inspection;
- keep a fixed-destination relay on the internal network that can reach only `host.docker.internal:10101`, normalizing the Docker authority to loopback for OpenCodex and exposing no proxy protocol or published port;
- upload the digest-pinned Linux Codex binary rather than downloading agent tooling inside the task container;
- disable browser, web-search, MCP, and unrelated connector tools;
- do not expose host credentials, Git credentials, proxy credentials, or API keys inside the task workspace;
- perform image pulls and dependency installation only before the timed agent phase;
- record the effective Harbor network policy and run an egress probe that must fail; and
- invalidate the trial if general outbound access is possible at any point during agent work.

Model-authentication traffic is not task internet access. If Codex CLI must reach the local OpenCodex endpoint, isolate that endpoint on a dedicated allowlisted network and expose no general-purpose proxy or host network. The agent must not be able to turn the model endpoint into a web-fetch service.

Do not merely add a prompt instruction against browsing. A run is valid only when the sandbox enforces it.

## Reproducibility and seeds

Question content is fixed, not generated from a seed. Reproduce it by pinning:

- the `terminal-bench@2.0` dataset release and resolved task artifact digest;
- each Docker image digest rather than a mutable tag;
- the exact instruction and task metadata digests;
- Harbor, Codex CLI, condition, and skill checksums;
- CPU, memory, storage, timeout, network, and verifier settings; and
- the randomized run-order seed, `329`.

Before model runs, audit each selected grader for randomness. Every Python, NumPy, PyTorch, shell, or generated-input random source must be deterministically seeded and recorded; otherwise the task is blocked until an upstream-equivalent, oracle-validated deterministic adaptation exists.

The model itself is not assumed to be bit-for-bit deterministic, especially behind a hosted alias. Record the exact model identifier and service metadata exposed for every run and use three repetitions per task-condition pair to measure run-to-run variance. A seed makes the task and order reproducible; it does not guarantee identical model trajectories.

## What the benchmark measures

The primary question is whether a condition produces better engineering outcomes. Token economy is not part of the quality score.

Report results in this order:

1. qualified task success rate;
2. critical failures and regressions;
3. blinded engineering-quality score among qualified solutions;
4. task-specific robustness or performance margins where the official grader exposes them;
5. partial progress, clearly separated from full resolution; and
6. elapsed time, tool calls, and token usage as cost diagnostics only.

A failed or materially incomplete solution scores zero engineering outcome regardless of how few tokens, edits, or minutes it used. Among qualified solutions, reviewers compare root-cause fit, requirement fidelity, maintainability, safety, regression risk, and whether performance constraints were met without brittle shortcuts. Smaller diffs are better only when they are at least as correct and robust.

Do not compare candidate patches to the oracle by textual similarity. Different implementations can be equally correct. Use the official outcome tests first, then blinded review of the actual patch and verification evidence.

## Experimental protocol

Use the two public conditions in this repository and three repetitions:

```text
13 tasks x 2 conditions x 3 repetitions = 78 model runs
```

Before model runs:

1. verify Docker is running and record Docker, Harbor, Codex CLI, and dataset versions;
2. run the official oracle for every selected task;
3. run the official no-op or dummy agent and confirm it fails;
4. inspect that tests and oracle artifacts are not visible in the agent container;
5. verify the agent-phase egress probe fails and audit all grader randomness;
6. pin the same task resources, no-agent-timeout policy, network policy, model, reasoning effort, and Codex version for every condition; and
7. randomize the 78-run order with seed `329` while keeping three repetitions per task-condition pair.

The current standard uses offline adaptation `a7`, which removes
`[agent].timeout_sec` from every adapted task. Harbor therefore resolves the
agent timeout to `None` and does not stop model work because of elapsed time.
Verifier, agent-setup, and environment-build timeouts remain infrastructure
health checks. The standard model is GPT-5.6 Luna with max reasoning on Codex
CLI 0.146.0.

The completed public GPT-5.6 Luna result remains an a6 historical artifact. It
used four times each upstream agent limit, but all 78 trials finished before
those limits. No historical cells are pooled into that comparison.

`prepare_research_benchmark.py` preserves the seeded run identities and global
execution order in the lock. New locks use a work-conserving global scheduler:
the seed order is the priority, while a later eligible run may fill an idle slot
when the next run is blocked. The frozen limits are thirteen one-task queues,
eight concurrent workers, two concurrent repetitions per task, and 20 GB of
aggregate declared task memory. Every trial still gets a fresh Harbor
environment and Codex home. This avoids the long tail produced by sequential
multi-task queues without allowing unbounded same-task or memory-heavy
concurrency. Any explicit worker-cap override is a different execution
contract and must be reported.

The runner refuses to start until the lock's `MODEL_FREE_READY.json` exists,
preserves Harbor's resolved locks and raw Codex logs, and exports `/app` for
later code review.

Preserve Harbor results, Codex event/session artifacts, container/grader logs, final patches, and final responses. A run blocked by infrastructure is invalid and rerun only under the preregistered retry policy; it is not a model failure.

Do not start the suite until all thirteen oracle checks pass on the actual host.

### Offline host adaptations

The frozen upstream prompts, solutions, and graders are unchanged. Three task environments require infrastructure-only adaptations so the model can work without internet:

- `sqlite-with-gcov` preinstalls the same Fossil/GCC/Jim/Tcl/Make/TZData packages used by the official solution;
- `make-doom-for-mips` preinstalls the official cross-compilation toolchain and replaces a now-dead upstream WAD URL with `/app/doom.wad` extracted from the pinned official `make-mips-interpreter` image (`sha256:082fc882...`, file SHA-256 `1d7d43be...`);
- `kv-store-grpc` preinstalls the two exact pinned grpc packages required by the prompt so the agent can generate the interface and implement and launch the service without package-registry access.

The adaptations contain no solution patch. Before the Luna a6 model run, all
13 official oracles passed, all 13 no-op trials failed, all 13 isolation probes
passed, and the grader-randomness audit found no unseeded source. The public
summary and audit hashes are recorded in `docs/benchmarks/`.

## Sources and exclusions

Primary sources:

- [Terminal-Bench 2.0 paper](https://arxiv.org/abs/2601.11868)
- [Terminal-Bench 2.0 task repository](https://github.com/harbor-framework/terminal-bench-2)
- [Harbor, the official harness](https://github.com/harbor-framework/harbor)
- [Terminal-Bench 2.0 verified leaderboard](https://www.tbench.ai/leaderboard/terminal-bench/2.0?verified=true)

Cross-checks considered during selection:

- [SWE-EVO](https://arxiv.org/abs/2512.18470) is an excellent long-horizon complement, but its 48 tasks are Python-only and use a different repository-evolution scaffold. It should be evaluated as a separate future suite, not mixed into this Terminal-Bench result.
- [SWE-Lancer](https://arxiv.org/abs/2502.12115) uses real paid freelance work and triple-verified end-to-end tests, but the maintained offline setup is Linux-oriented and its task images are very large. It is a valuable external validation suite rather than the first local run on this Windows host.
- SWE-bench Verified was excluded because recent audits found material contamination and test-validity problems. See OpenAI's [benchmark audit](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/) and the independent [PatchDiff study](https://arxiv.org/abs/2503.15223).

This choice favors one reproducible, paper-backed harness over a mixture whose infrastructure differences could be mistaken for policy effects.
