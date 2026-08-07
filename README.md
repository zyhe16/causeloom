<h1 align="center">Causeloom</h1>

<p align="center"><strong>From root cause to verified closure.</strong></p>

<p align="center">
  <a href="https://github.com/zyhe16/causeloom/actions/workflows/ci.yml"><img src="https://github.com/zyhe16/causeloom/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/version-0.3.0-172033.svg" alt="Version 0.3.0">
  <img src="https://img.shields.io/badge/license-MIT-356ae6.svg" alt="MIT License">
</p>

Causeloom is a set of instructions for coding agents. It helps an agent
understand what you asked for, fix the real cause, test the result people will
actually use, and avoid unnecessary code.

**In a 39-attempt benchmark, Causeloom completed 27 attempts versus 20 for the
same agent without the skill.**

```text
Understand -> Bound -> Change -> Verify -> Simplify -> Stop
```

## Why use it?

Coding agents often do too little or too much. They may make a small patch that
does not solve the real problem, or build a large solution for something
simple. Causeloom guides the agent toward work that is correct, focused, and
properly tested.

| Without Causeloom | With Causeloom |
|---|---|
| Guesses and starts coding | Checks important assumptions first |
| Fixes only what looks broken | Finds and fixes the real cause |
| Adds features for imagined future needs | Adds only what the task needs |
| Stops when the code builds | Tests the result people will actually use |
| Leaves temporary or unused code | Cleans up before finishing |

Causeloom does not mean “write the fewest lines.” The solution must first be
correct and safe. Then it should be made as simple as possible.

## Install

### Agent Skills CLI (recommended)

```bash
npx skills add zyhe16/causeloom
```

> [!NOTE]
> **Codex-only, non-interactive install:** if the agent selector glitches, use
> `npx skills add zyhe16/causeloom --agent codex -y`.

### Ask your coding agent

Alternatively, ask an agent to install it for you:

```text
Install Causeloom from https://github.com/zyhe16/causeloom using
`npx skills add zyhe16/causeloom`. Select the correct coding tool, verify that
the installed skill is named `causeloom`, validate its SKILL.md, and do not
modify unrelated files.
```

Invoke the installed skill with `$causeloom`; in ChatGPT desktop, type `@` and
select **Causeloom**. More details are in
[`docs/INSTALLATION.md`](docs/INSTALLATION.md).

## Results

All 13 benchmark problems come from
[Terminal-Bench 2.0](https://www.tbench.ai/benchmarks/terminal-bench-2), with
three attempts per problem for both Causeloom and the baseline.

![Official reward across all 39 attempts](docs/assets/benchmark-full.svg)

| Setup | Passed runs | Passes without exceptions | Timeouts | Average tokens per run |
|---|---:|---:|---:|---:|
| No-skill baseline | 20/39 (51.3%) | 19/39 | 4 | 420,488 |
| **Causeloom** | **27/39 (69.2%)** | **25/39** | 4 | 523,594 |

> [!IMPORTANT]
> We split the benchmark into two batches to avoid spending tokens on runs that
> had already finished. For every earlier baseline problem where at least one of
> its three runs reached the shorter time limit, we reran all three runs with the
> longer limit. We reused only 12 earlier baseline runs whose three-run groups
> finished within the shorter limit. Those 12 were not selected by score: 8
> passed the automated tests and 4 failed. Reuse depended only on timeout status.
> The combined result is **descriptive evidence, not a fully matched causal estimate**.
> See [Method, briefly](#method-briefly).

That is a **17.9 percentage-point** increase in the raw pass rate and six more
passes without exceptions. Causeloom used about **24.5% more tokens per run**.
This is consistent with the extra work the skill asks for: reading the relevant
code, checking assumptions, testing the program people will run, and cleaning
up before finishing. Token use is a cost, not a quality score, and this
benchmark cannot tell us exactly which step caused the increase.

### Where the difference appeared

![Tasks with official Causeloom successes and zero baseline successes](docs/assets/benchmark-causeloom-only-wins.svg)

On these four harder technical problems, Causeloom produced **6 passes in 12
runs; the baseline produced 0**.

> [!WARNING]
> One Doom run passed every automated check but also reached the time limit. It
> counts as a pass, but not as a pass without exceptions.

### Method, briefly

- GPT-5.6 Sol, high reasoning, Codex CLI 0.146.0
- Terminal-Bench 2.0, 13 problems, 3 runs each, isolated Harbor containers
- 3 medium integration/build tasks, 7 extreme systems workflows, 3 targeted
  coverage tasks
- No internet access during tasks; automated test results decide whether a run
  passes

The second batch added three problems and doubled the agent time limits. For
each earlier baseline problem affected by a timeout, all three runs were
repeated under the longer limit. Both batches used the same model family,
number of runs per problem, and ordering seed. However, a shared seed does not
make hosted model trajectories deterministic. Technical details, file hashes,
and instructions for repeating the benchmark are in
[`docs/benchmarks`](docs/benchmarks/) and [`evals`](evals/).

## Code-quality review

> [!NOTE]
> This review happened after the benchmark and was not blind. It did not give
> the code a numeric score. The automated benchmark results above remain the
> main score.

**Codex with GPT-5.6 Sol** reviewed the saved final code and automated test
results. The examples below are shortened excerpts from real benchmark
submissions.

### 1. Accept both valid input shapes

The baseline accepted only the full tensor. The test gave it the smaller piece
already assigned to that worker, so it rejected a valid input:

```python
if input.size(-1) != self.in_features:
    raise ValueError(...)
local_input = _ScatterLastDimension.apply(input, self.world_size, self.rank)
```

Causeloom accepted both valid input shapes. It split the tensor only when it
received the full one:

```python
if input.size(-1) == self.in_features_per_rank:
    local_input = input
elif input.size(-1) == self.in_features:
    start = self.rank * self.in_features_per_rank
    local_input = input.narrow(-1, start, self.in_features_per_rank)
else:
    raise ValueError(...)
```

Result: Causeloom passed every tensor-parallel test, including output and
gradient checks. The baseline failed the row-parallel test.

### 2. Keep messages and gradients in the right order

The baseline processed the backward steps in reverse order:

```python
for microbatch_index in range(microbatch_count - 1, -1, -1):
    ...
```

Causeloom kept them in the order expected by the messages sent between workers:

```python
for microbatch_index in range(num_microbatches):
    ...
```

Result: Causeloom passed the two-worker comparison. The baseline produced the
wrong gradient for one layer.

### 3. Test the program people will actually run

The baseline built a program file, but running it never produced the requested
image:

```make
CROSS ?= mips-linux-gnu-
CC := $(CROSS)gcc
LDFLAGS := -EL -m elf32ltsmip -T mips_vm.ld
# ... my_stdlib.c
```

Causeloom used compiler and linker settings that matched the supplied virtual
machine:

```make
CC := clang
CFLAGS := --target=mipsel-unknown-linux-gnu --sysroot=/usr/mips-linux-gnu ...
$(LD) -m elf32ltsmip -static -T mips.ld -o $@ $(OBJECTS)
# ... vm_libc.c
```

Result: `node vm.js` produced the image and passed all three checks: the program
ran, the image existed, and it matched the reference. This is the timeout-marked
run described above.

The lesson from these examples is not “write more code.” It is: accept the
right inputs, keep steps in the right order, and test the finished program. The
review also found a weakness. On an HTML cleaning task, Causeloom built large
custom parsers that still changed safe HTML and missed a harmful case.

## Strengths and tradeoffs

| Works well for | Limits |
|---|---|
| Code where several parts share data or state | Extra reading and testing can use more tokens |
| Builds that involve several tools or steps | It can still build too much for some tasks |
| Inputs that can arrive in more than one valid form | It had the same number of timed-out runs in this benchmark |
| Work that must be easy to inspect and review | The evidence comes from one model and 13 problems |

## How it works

The policy asks the agent to:

1. Turn the request into clear checks for success.
2. Find the real cause before changing code.
3. Make the smallest change that fully solves the problem.
4. Check valid inputs and make sure existing behavior still works.
5. Test the final program, not only one step along the way.
6. Remove extra code and stop when there is enough proof that it works.

Read the complete policy in [`SKILL.md`](SKILL.md) and its rationale in
[`docs/DESIGN.md`](docs/DESIGN.md).

## Motivation

Causeloom is strongly motivated by two projects that encourage direct, simple
solutions:

- [Karpathy Guidelines](https://github.com/multica-ai/andrej-karpathy-skills)
- [Ponytail](https://github.com/DietrichGebert/ponytail)

It adds a stronger focus on asking useful questions, putting fixes in the right
place, keeping existing behavior safe, testing according to risk, cleaning up,
and finishing with proof that the result works.

## Develop

```bash
make check
make package
make package-repo
```

The repository contains the skill, repeatable packaging tools, benchmark tools,
and the data used in the charts. Large raw benchmark files, private comparison
rules, caches, logs, and generated archives are not stored in Git.

## License

[MIT](LICENSE)
