# Contributing

Contributions are welcome when they improve a demonstrated coding-agent failure mode without weakening correctness, safety, or clarity.

## Before changing the skill

1. Name the observed failure and the task that reproduces it.
2. Explain why existing wording does not already cover it.
3. Prefer a narrow wording change over adding a broad new doctrine.
4. Add or update a frozen evaluation task that can expose both the intended improvement and plausible regressions.
5. Compare the old and new skill under the same model, task, tools, budgets, and repetitions.

## Local checks

Repository tooling requires Python 3.11 or newer and uses only the standard
library.

```bash
make check
```

This validates the skill manifest, runs the repository tests, and builds both
the install-only and full source ZIPs.

## Evaluation evidence

A skill change should report:

- qualified-success rate and critical failures;
- task-level regressions;
- ownership quality among qualified runs;
- token coverage and token use;
- tool calls and elapsed time;
- the model version, skill checksum, task checksum, and execution budget.

Do not claim an improvement from a single run or from lines-of-code reduction alone.

## Pull requests

Keep pull requests focused. Explain the failure mode, the exact policy change, verification performed, and any remaining uncertainty. Do not manually edit generated files without updating their source and regeneration command.


Release maintainers should follow [`docs/RELEASING.md`](docs/RELEASING.md).
