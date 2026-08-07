# Causeloom

**From root cause to verified closure.**

[![CI](https://github.com/zyhe16/causeloom/actions/workflows/ci.yml/badge.svg)](https://github.com/zyhe16/causeloom/actions/workflows/ci.yml)
[![MIT License](https://img.shields.io/badge/license-MIT-356ae6.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.3.0-172033.svg)](VERSION)

Causeloom is an instruction-only engineering skill for coding agents. It guides
an agent to understand the real requirement, locate the owning cause, choose the
smallest sufficient intervention, verify the intended entrypoint, simplify the
finished diff, and stop when the evidence is strong enough.

It is not a mandate to write the fewest lines. It is a discipline for avoiding
both under-engineering and unjustified ownership.

```text
Understand -> Bound -> Change -> Verify -> Simplify -> Stop
```

## Philosophy

Causeloom is built around six ideas:

1. **Correctness is the gate.** Small, fast, or elegant work is not valuable if
   it misses the actual requirement.
2. **Ambiguity is resolved by consequence.** Ask only when a choice materially
   changes behavior, safety, compatibility, architecture, irreversible state,
   or substantial effort.
3. **Changes belong at the owning layer.** Fix violated invariants where they
   are authoritative instead of scattering symptom guards.
4. **Rigor should be proportionate.** Start with the cheapest check capable of
   falsifying the current approach; broaden only when risk or evidence requires
   it.
5. **Every addition creates lifecycle ownership.** Dependencies, abstractions,
   compatibility branches, configuration, and hooks need a present reason.
6. **Closure is part of quality.** Verify the final entrypoint, reserve time for
   delivery, remove abandoned machinery, and stop after sufficient evidence.

The complete policy is in [`SKILL.md`](SKILL.md). Design rationale is documented
in [`docs/DESIGN.md`](docs/DESIGN.md).

## Install

Ask a coding agent to install it:

```text
Install the Causeloom skill from https://github.com/zyhe16/causeloom.
Use the correct user-level skills directory for this agent, validate the
installed SKILL.md, and do not modify unrelated files.
```

Or use the Agent Skills CLI:

```bash
npx skills add zyhe16/causeloom
```

Or install the release archive:

```bash
mkdir -p ~/.agents/skills
unzip causeloom-0.3.0.zip -d ~/.agents/skills
```

Project-local installation uses the same directory contract:

```text
<repository>/.agents/skills/causeloom/SKILL.md
```

Invoke it explicitly with `$causeloom`. In ChatGPT desktop, type `@` and select
**Causeloom**. See [`docs/INSTALLATION.md`](docs/INSTALLATION.md) for other
supported layouts.

## Benchmark

Causeloom was evaluated with GPT-5.6 Sol at high reasoning through Codex CLI
0.146.0 on a frozen thirteen-task Terminal-Bench 2.0 suite. Each condition has
39 task attempts: 13 tasks with three repetitions. Tasks ran in isolated Harbor
containers with agent internet access blocked. Official verifier reward is the
correctness measure; tokens and elapsed time are diagnostics.

### What the suite covers

| Class | Tasks | What they exercise |
|---|---:|---|
| Medium integration/build/debugging | 3 | Release-only C++ debugging, Git/deployment integration, offline source instrumentation |
| Extreme systems workflows | 7 | Scheduling optimization, cross-compilation and emulation, database recovery, distributed ML runtimes, HTML/XSS transformation |
| Targeted coverage | 3 | Low-ambiguity modernization, conventional backend/API delivery, surgical security maintenance |

Seven of thirteen tasks are in the preregistered `extreme` tier, so the suite is
weighted toward technically complex, multi-step systems work. It is not a
direct proxy for repository size; large existing repositories remain a useful
future validation target.

### Results

![Causeloom and the no-skill baseline across 39 task attempts](docs/assets/benchmark-full.svg)

| Condition | Reward 1 | Exception-free reward 1 | Timeouts | Mean tokens / attempted run | Mean tokens / successful run | Sources |
|---|---:|---:|---:|---:|---:|---:|
| No-skill baseline | 20/39 (51.3%) | 19/39 | 4 | 420,488 | 397,829 | 27 a5 + 12 a3 |
| Causeloom | **27/39 (69.2%)** | **25/39** | 4 | 523,594 | 539,583 | 39 a5 |

The benchmark was completed in two phases to avoid spending tokens on
unnecessary reruns. The second phase reran cells that had timed out previously
and added three coverage tasks; twelve completed baseline cells were reused from
the first phase. Both phases used the same task selection, model family, three
repetitions, and run-order seed. The twelve reused cells had the earlier timeout
contract, however, and a shared seed does not make hosted model trajectories
deterministic. The 39-run view is therefore descriptive evidence, not a fully
matched causal estimate.

The mean-token columns come from preserved raw records. "Attempted run" is the
mean across all 39 attempts; "successful run" is the mean among attempts with
official reward 1.

Task-level inspection found that Causeloom's gains on the contemporaneously
rerun slice came from two `extreme` systems tasks: cross-compiling Doom for MIPS
and pipeline-parallel runtime work. That supports a strength on complex
multi-step problems, but the sample is too small to claim a general large-scale
repository advantage.

### Code-quality review

The preserved final-code review was performed by **Codex with GPT-5.6 Sol**. It
inspected 15 pre-rc.3 Causeloom artifacts across five code-bearing tasks,
combining verifier output with direct review of structure, maintainability, and
failure behavior. It was an engineering review, not a blinded numeric score.

One concrete example is the row-parallel tensor implementation. The no-skill
attempt assumed every caller supplied the full input and always scattered it:

```python
if input.size(-1) != self.in_features:
    raise ValueError(...)
local_input = _ScatterToTensorParallelRegion.apply(input)
```

The passing Causeloom implementation preserved the actual boundary: callers
could provide either the full tensor or the already-local shard used by the
grader.

```python
if input.shape[-1] == self.in_features:
    input = input.narrow(-1, rank * shard_size, shard_size)
elif input.shape[-1] != self.in_features_per_rank:
    raise ValueError(...)
```

That Causeloom artifact was the only implementation in the 12-attempt task to
pass all world-size, bias, forward, and gradient checks. The same review found
the opposite failure pattern on HTML sanitization: Causeloom built three
446-493-line custom parsers, but all scored 0/3 because they still missed an
attack case and changed legitimate HTML. In other words, added structure helped
when it represented real distributed-state ownership, and hurt when it became
an expanding substitute for a preservation-first design.

The review's bottom line was **strong peak decomposition and auditability, but
uneven simplicity and closure**. The rc.3 policy added explicit stopping,
preservation-first checks, compatibility evidence, and final-artifact closure in
response. The rc.3 artifacts have not received a second blinded quality score,
so this conclusion remains separate from the verifier results above.

### Strengths and tradeoffs

| Strengths | Tradeoffs |
|---|---|
| 27 official successes versus 20 for the no-skill baseline in the full 39-attempt view | About 25% more mean tokens per attempt and 36% more among successful runs |
| 25 exception-free successes versus 19 | The same four timeout-flagged attempts |
| Gains appeared on two difficult cross-build/distributed-runtime tasks | No measured advantage on the three new coverage tasks |
| Review evidence of strong state ownership and auditable decomposition | Review evidence of overbuilding and speculative compatibility on some tasks |
| Explicit root-cause, ownership, verification, simplification, and stopping discipline | The two-phase full view is descriptive rather than a fully matched causal estimate |

The chart-ready data, generator, audit hashes, task selection, validity limits,
and reproduction notes are under [`docs/benchmarks`](docs/benchmarks/) and
[`evals`](evals/). The public repository compares only Causeloom with no extra
skill. Other policies may be useful as private calibration standards, but their
named results and policy copies are intentionally not published here.

## Motivation

Causeloom is strongly motivated by two thoughtful projects that champion direct,
simple solutions:

- [Karpathy Guidelines](https://github.com/multica-ai/andrej-karpathy-skills)
- [Ponytail](https://github.com/DietrichGebert/ponytail)

Causeloom builds on that motivation with explicit rules for consequence-based
ambiguity, lifecycle ownership, preservation, authoritative boundary placement,
risk-scaled verification, simplification, and verified closure.

## Develop and package

```bash
make check
make package
make package-repo
```

On Windows without GNU Make, run the corresponding Python commands from the
[`Makefile`](Makefile).

The repository intentionally excludes `work/`, `results/`,
`evals/private-conditions/`, local environments, logs, caches, and generated
release archives. Those paths can contain large raw benchmark sessions,
private calibration policies, or host-specific state and do not belong in
source history.

## Repository map

```text
SKILL.md                 canonical installable policy
agents/openai.yaml       ChatGPT/Codex UI metadata
docs/                    design, installation, release, and benchmark evidence
evals/                   public baseline evaluation and reproducible tooling
scripts/                 validation and deterministic packaging
tests/                   repository and evaluation-tooling checks
```

## License

Causeloom is released under the [MIT License](LICENSE).
