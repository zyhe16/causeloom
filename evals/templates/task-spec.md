# Task authoring template

## Real outcome

State the actual behavior that must work, independently of the visible tests.

## Starting repository

Record the immutable commit or archive checksum and dependency lockfile.

## Prompt

Use the exact text shown to every condition.

## Public checks

Checks the agent may inspect and run. They should provide useful feedback without fully specifying the hidden solution.

## Grader checks

Test meaningful generalization, sibling paths, contracts, and failure modes. Do not reward textual similarity to a reference implementation.

## Targeted failure mode

Name the policy behavior being tested and explain which tempting solution is wrong.

## Acceptable solution families

List multiple correct architectural approaches when applicable.

## Critical failures

Specify security, data, compatibility, or specification-gaming outcomes that disqualify a run.

## Initial check state

Record expected public and hidden exit codes before any change, including cases where visible checks already pass.
