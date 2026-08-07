# Design rationale

## Why Causeloom exists

Coding agents often fail in opposite directions. One failure is doing too
little: patching a symptom, trusting a visible test, or stopping before the real
entrypoint works. The other is doing too much: inventing abstractions,
compatibility layers, configuration, dependencies, and verification work that
the task never justified.

Causeloom treats both as failures of causal scope. The agent should understand
which invariant is broken, which layer owns it, which consequences matter, and
what evidence is sufficient to close the work.

```text
Understand -> Bound -> Change -> Verify -> Simplify -> Stop
```

## Core decisions

| Tension | Causeloom rule |
|---|---|
| Ask whenever uncertain vs. choose a default | Resolve from repository evidence first; ask only when the unresolved consequence is material. |
| Native capability vs. custom implementation | Discover existing capabilities first, then choose by actual fit and justified lifecycle ownership. |
| Smallest diff vs. correct architecture | Keep the blast radius surgical, but allow a bounded supporting refactor when the owning layer or safe testability requires it. |
| Fast checks vs. exhaustive verification | Start with the cheapest falsifying check and broaden with behavior, risk, and uncertainty. |
| Tests vs. the real goal | Treat tests as evidence; verify the production path and never redefine the task to satisfy visible checks. |
| Defensive coding vs. duplicated checks | Enforce invariants at authoritative trust boundaries, then rely on established internal guarantees. |
| Robustness vs. speculative compatibility | Add compatibility only for an observed runtime, reproduced mismatch, repository contract, or explicit requirement. |
| Continued exploration vs. delivery | Once acceptance criteria and the strongest proportionate check pass, simplify, verify the final artifact, and stop. |

## Lifecycle ownership

Lifecycle ownership includes custom code, dependencies, configuration, public
interfaces, tests, deployment, operations, security, upgrades, cleanup, and the
future cost of changing the solution.

A dependency can reduce ownership when it is already established and materially
better suited. A short custom implementation can increase ownership when it
recreates a difficult domain. Lines of code are therefore evidence about
surface area, never the objective.

## Influences

Causeloom's preference for direct solutions and resistance to unnecessary
complexity were informed by the MIT-licensed Karpathy Guidelines and Ponytail
projects. Causeloom was independently authored and developed through its own
repository evidence, failure analysis, policy iterations, and controlled
benchmarking.

## Non-goals

Causeloom is not a complete software-engineering handbook and does not replace
domain-specific security, database, frontend, performance, scientific, or
repository guidance. It governs how an agent understands scope, selects a
solution, limits unjustified ownership, verifies the actual outcome, and closes
the task.
