# Repository instructions

- `SKILL.md` is the canonical policy. Do not edit the frozen evaluation copy directly; run `python evals/scripts/snapshot_condition.py` after changing the canonical skill.
- Keep the frontmatter name, installed skill directory, release-package prefix,
  and project-local condition directory equal to `causeloom`. The recommended
  public repository name is also `causeloom`; a developer's existing local
  checkout directory may differ.
- Treat correctness and requirement fidelity as qualification gates. Never reward a smaller but incorrect patch.
- Keep Codex CLI and ChatGPT desktop evaluation paths free of direct API calls. The CLI benchmark should default to isolated ChatGPT authentication.
- Token details such as cached input, cache-write input, and reasoning tokens are informational parts of normalized input/output usage. Never double-count them.
- Preserve raw Codex event or session artifacts whenever token usage is imported.
- Use only the Python standard library in repository tooling unless a measured requirement justifies a dependency.
- Run `make check` before submitting changes.
- Synthetic example results must remain clearly labeled and must never be presented as empirical evidence.
