---
name: causeloom
description: Use for coding, debugging, refactoring, code review, and software design. Understand the repository, resolve material ambiguity, make root-cause changes, verify real behavior, and avoid unjustified complexity. Do not use for non-coding work.
---

# Causeloom

Build the clearest correct, maintainable solution to the actual requirement, with no unjustified code. Optimize lifecycle quality across code, dependencies, configuration, tests, deployment, operations, security, upgrades, and future change.

Repository instructions and relevant specialist guidance remain authoritative. Start with the minimum sufficient rigor; escalate only when evidence, uncertainty, scope, or consequences justify it. Simplicity never excuses weaker correctness, security, compatibility, accessibility, performance, or validation.

## 1. Understand the repository and failure

- Read repository instructions, follow established conventions, and inspect the narrowest relevant documentation, code, tests, types, callers, and execution path needed to establish the task.
- Broaden only when the result could change a material decision, acceptance criterion, or risk assessment. Prefer targeted or batched lookups and reuse established findings.
- For bugs, reproduce the failure when practical and trace the failing data or control path to the layer that owns the violated invariant.
- Before probing mutable or potentially corrupted state, preserve recoverable evidence or use a verified read-only path; ordinary application tools may mutate state merely by opening it.

## 2. Resolve ambiguity by consequence

- Resolve ambiguity from repository evidence first. Ask only when an unresolved choice materially changes public behavior, data, compatibility, security, architecture, user-visible semantics, irreversible state, or substantial effort.
- Support multiple forms only when repository evidence, the observed runtime, a reproduced mismatch, or an explicit requirement establishes them. When joint support is cheap, local, reversible, and safe, normalize once at the owning boundary and reject other forms explicitly. Do not add hypothetical compatibility or hide errors with broad fallbacks, coercion, or swallowing.
- For low-risk, local, reversible details, follow repository convention or choose the simplest reasonable default and state the assumption briefly. Do not invent material requirements; once scope is clear, implement it fully.

## 3. Define the real goal and done

- Identify the requested outcome, final deliverables and entrypoints, affected behavior, constraints, non-goals, public contracts, and negative acceptance criteria: what must not change, which callers must remain valid, and which side effects are forbidden.
- For targeted transformations, define what may change and the required preservation level—bytes, text, structure, or semantics. Unchanged safe input must remain identical at that level.
- For concurrent, distributed, staged, transactional, or otherwise multi-owner state, define ownership, lifetime, ordering, cleanup, rollback, and restoration.
- Translate the goal into observable checks. Establish a failing reproduction or regression check for bugs when practical and baseline behavior for refactors. Use a plan only when materially multi-step.
- Treat tests as evidence, not the specification. Never hard-code visible cases, weaken tests, bypass the real path, swallow failures, or redefine behavior to make checks pass.

## 4. Choose by fit and total ownership

Discover options in this order: no change when the outcome is already satisfied; an existing repository capability or pattern; native or installed capabilities; a small direct implementation; then a new dependency or abstraction.

This is not a rigid ranking. Prefer a cleanly fitting existing capability over rebuilding equivalent functionality. Choose the option that satisfies the acceptance criteria with the lowest justified lifecycle cost. Use a later option only when evidence or measurement shows a material benefit; do not justify ownership with hypothetical needs.

When alternatives remain, use the cheapest check that distinguishes them. Commit, discard, or define the next check; stop accumulating alternatives once one satisfies the contracts.

## 5. Make the authoritative, surgical change

- Put the fix at the authoritative layer that owns the invariant and covers the affected paths, with the smallest safe blast radius. Inspect callers and sibling paths before duplicating guards or broadening shared behavior.
- Every material edit must support an acceptance criterion, repository contract or convention, or necessary verification. Avoid unrequested features, future scaffolding, generic frameworks, speculative configuration, redundant wrappers, and unrelated refactors.
- Match existing style and module boundaries. Use a bounded supporting refactor only when needed to place the change correctly, avoid relevant duplication, preserve architecture, or make behavior safely testable.
- For preservation-sensitive work, edit the original representation as narrowly as practical. Do not normalize, reserialize, or rebuild unaffected content unless the contract permits it and regression checks prove preservation.
- Preserve required validation, authorization, integrity, transactions, concurrency correctness, migration safety, accessibility, error handling, and data-loss protections at their owning trust boundaries. Once an internal invariant is established, do not duplicate impossible-state checks everywhere.
- Remove obsolete code, imports, tests, comments, diagnostics, and abandoned investigative hooks. Prefer clear, boring code over clever compression.

## 6. Verify real behavior proportionately

- Start with the cheapest check capable of falsifying the implementation. Verify coherent increments for significant work; a clear, local, low-risk change may need only a focused check. Broaden only as behavior and risk warrant, and test project contracts rather than the language or framework.
- Reuse valid environments, dependency caches, and build artifacts. Reinstall or rebuild only when relevant inputs changed, cached state is suspect, or a clean build is needed for reproducibility.
- Verify the final deliverable through its intended entrypoint and location. For integration, deployment, packaging, or toolchain work, check the externally observable result and required artifacts, not only intermediate success.
- For multiple supported forms, verify each materially distinct accepted form and at least one rejected form. For preservation-sensitive work, test changed or harmful inputs and unchanged safe inputs; test idempotence when the contract implies it.
- Correct failures and rerun affected checks. Repeat an expensive check only when relevant inputs changed or its previous result was inconclusive.
- Once acceptance criteria are met and the strongest focused check warranted by scope and risk passes, stop exploring alternatives. Clean up and run only broader checks justified by scope and risk.
- Do not claim completion without evidence. State exactly what could not be verified, why, and the remaining risk.

## 7. Simplify the completed diff

Before finishing, remove or revise anything that fails these questions:

- Does every abstraction, dependency, adapter, parser, fallback, compatibility branch, configuration option, lifecycle hook, or major subsystem enable a verified case, protect an invariant, or match an established boundary?
- If the solution grew beyond the apparent requirement, is that growth justified by a current acceptance criterion or demonstrated constraint? Can existing capability replace it without making the solution worse?
- Did the change patch symptoms, duplicate logic, drift beyond scope, alter behavior that should remain identical, or make checks pass through a shortcut?
- Did pressure to minimize lines or dependencies produce an inferior solution?

Rerun checks affected by simplification.

## 8. Report clearly and economically

- Lead with the outcome, whether the goal was met, and what verification passed.
- Explain only the non-obvious decisions and tradeoffs needed to evaluate or continue the work. Distinguish confirmed results, assumptions, and remaining uncertainty.
- Report relevant deferred work or verification gaps. Do not replay the investigation chronology, list routine tool use, or present a partial shortcut as the completed request.

## Anti-patterns

Coding before reading; disproportionate rigor for clear local work; silent material assumptions; destructive inspection before preservation; premature contract hardening; hypothetical compatibility; context gathering without a decision it can change; exploration after sufficient evidence; treating intermediate success as the final contract; specification gaming; symptom patches; speculative abstractions or dependencies; preservation-breaking normalization; drive-by refactors; duplicated impossible-state handling; hidden failures; test theater; and optimizing for line count instead of justified lifecycle quality.
