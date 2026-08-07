# Frozen public evaluation condition

The public benchmark uses two conditions:

| Condition | Injected policy | Bundled snapshot |
|---|---|---|
| `baseline` | No extra coding policy beyond common instructions | Not applicable |
| `causeloom` | Causeloom only | `causeloom/POLICY.md` |

`causeloom/POLICY.md` is copied from the canonical root `SKILL.md` by
`python evals/scripts/snapshot_condition.py`. Its SHA-256 is recorded in
[`CHECKSUMS.sha256`](CHECKSUMS.sha256). Changing the snapshot creates a different
experiment and requires a new result dataset.

The snapshot is intentionally named `POLICY.md`, not `SKILL.md`, so cloning the
source repository into a skills directory cannot register a second skill.
