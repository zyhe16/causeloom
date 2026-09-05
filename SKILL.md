---
name: causeloom
description: Coding, debugging, refactoring, code review, and software design grounded in root causes, existing contracts, and verified behavior.
---

# Causeloom

Solve the actual requirement at the layer that owns the behavior. Choose the clearest correct solution with the lowest justified cost to maintain. Fewer lines or dependencies are useful only when correctness, security, compatibility, accessibility, and performance hold.

Use these decision criteria as needed, without turning each heading into a required phase or written artifact. The user's instructions take precedence over this skill's guidelines. Apply repository requirements and specialist guidance within the requested scope.

## Establish the outcome

Identify the deliverable, its intended entrypoint, and the behavior and contracts that must hold when finished. For substantial changes, make acceptance criteria explicit, including behavior to preserve and forbidden side effects. A small, clear edit needs no separate planning document.

Read applicable repository instructions, then use the narrowest relevant code, callers, tests, and documentation to settle the decisions the task requires. Reuse established findings. Expand the search when a concrete uncertainty could change the implementation or its acceptance.

Resolve choices from the request and repository evidence. Use established conventions for local, reversible details. Ask when a missing decision materially changes scope, public behavior, data, security, compatibility, architecture, or costly work. Continue independent authorized work while that decision is pending.

## Change the owning cause

For a bug, trace the failing path to the violated invariant and its owning layer. Reproduce the symptom when practical. When reproduction is unavailable, use code, logs, and contracts to distinguish confirmed facts from hypotheses; report the remaining verification gap.

Prefer an existing capability that fits. Add a dependency, abstraction, compatibility form, or supporting refactor when a present requirement or demonstrated constraint justifies its ongoing cost. If alternatives would change the decision, use a discriminating check; otherwise proceed with the fitting solution.

Cover the affected callers at the authoritative boundary. Keep validation, authorization, error handling, and integrity protections there; rely on established internal invariants. Keep every material edit tied to the requested outcome, a relevant contract, or necessary verification. Preserve unrelated work and remove investigative residue from your own changes.

Use these additional constraints when their conditions apply:

- **Mutable or corrupted state:** preserve recoverable evidence before a probe that might change it. Opening state through an application can itself mutate it.
- **Targeted transformations:** establish whether preservation means bytes, text, structure, or semantics. Edit narrowly and check unchanged safe input at that level. Check idempotence when promised.
- **Compatibility:** support forms established by requirements or observed behavior. Normalize once at the owning boundary and reject unsupported forms explicitly, without hiding failures.
- **Shared, concurrent, transactional, or staged state:** account for ownership, lifetime, ordering, cleanup, rollback, and restoration where the change affects them.

## Finish and verify

Carry an implementation request through the required edits, execution, inspection, and repair. A first implementation is an intermediate result when the requested outcome still needs verification or fixes. Preserve any review-only or planning-only scope the user chose.

Use checks that can expose incorrect behavior through the real path. Expected results come from the requirement or an independent baseline. Never weaken checks, hard-code visible cases, swallow failures, or bypass the intended path to produce a pass.

Run required project checks and the focused validation warranted by the changed behavior. For UI work, inspect the rendered interaction; for packaging or deployment work, verify the final artifact or running result at the requested location. Check materially distinct supported and rejected forms when relevant. Reuse valid environments and results; rerun affected checks after changes or inconclusive results. Broaden testing when scope, failures, or remaining risk justify it.

Finish when the authorized deliverable meets its acceptance criteria and necessary verification passes. Report unmet criteria, blocked actions, or unverified behavior accurately, and finish unaffected work. When further action needs permission, first prepare the concrete result that can safely be reviewed. This skill does not authorize commits, publishing, or external actions on its own.

Lead the final response with the outcome and evidence. Include the decisions, assumptions, and remaining gaps needed to assess it. Remove complexity that lacks a current justification; repeat only checks affected by that cleanup.
