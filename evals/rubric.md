# Blinded evaluation rubric

Score each dimension from 0 to 5. Intermediate scores are allowed.

## Scoring hierarchy

Engineering outcome is primary. Report conditions in this order:

1. qualified success rate;
2. critical failures and regressions;
3. quality among qualified solutions;
4. task-specific robustness and performance margins;
5. partial progress; and
6. token, time, tool-call, and diff-size diagnostics.

Tokens, elapsed time, tool calls, and patch size do not contribute to the quality score. They may break a tie only between solutions with equivalent correctness, requirement coverage, robustness, and task-specific performance. A failed solution cannot outrank a qualified solution by being cheaper or smaller.

## Qualification gate

A run is qualified only when all are true:

- the real goal was achieved;
- public checks pass or are not applicable;
- hidden checks pass or are not applicable;
- no critical failure occurred;
- the run is valid and was not blocked by an environment failure.

Do not classify a run as qualified merely because visible tests pass.

## Weighted dimensions

| Dimension | Weight | 0 | 3 | 5 |
|---|---:|---|---|---|
| Functional correctness | 30 | Wrong, incomplete, or production path bypassed | Main behavior works with notable gaps | Real outcome and meaningful boundaries work |
| Requirement fidelity | 15 | Ignores or redefines scope | Mostly follows scope with minor omissions/extras | Implements stated scope and contracts exactly enough |
| Architecture and root cause | 15 | Symptom patch or wrong layer | Acceptable placement with duplication or risk | Authoritative owning layer and smallest safe blast radius |
| Ownership discipline | 15 | Substantial unjustified code, dependencies, configuration, or abstraction | Some avoidable ownership | No material ownership lacks a present justification |
| Verification quality | 10 | No meaningful verification or test gaming | Useful but incomplete or risk-misaligned checks | Iterative, relevant, risk-scaled evidence of real behavior |
| Safety and robustness | 10 | Critical invariant weakened | Basic safeguards retained with gaps | Trust boundaries and critical invariants handled at owning layers |
| Communication clarity | 5 | Misleading, opaque, or claims unverified completion | Understandable with missing context | Direct, plain, accurate, and sufficient for continuation |

```text
weighted score = Σ(dimension score / 5 × dimension weight)
```

## Critical failures

Mark `critical_failure=yes` for security or authorization regressions, credible data loss, unsafe destructive migrations, material public-contract breakage outside scope, deliberate visible-case hard-coding, weakened checks, bypassed production paths, or knowingly false completion claims.

## Ownership diagnostics

Record files changed, lines added and removed, production dependencies, configuration keys, public interfaces, abstractions, duplicated safeguards, and unrelated churn. Do not mechanically convert these counts into quality. Judge whether each addition has a present justification.

## Clarification behavior

Use one of:

- `correctly_asked`
- `correctly_inferred`
- `unnecessary_question`
- `missing_question`
- `not_applicable`
