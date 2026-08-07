# Installation

The directory containing `SKILL.md` must be named `causeloom`, matching the
frontmatter `name`.

## Agent Skills CLI (recommended)

```bash
npx skills add zyhe16/causeloom
```

The CLI detects supported agents, finds the repository's `causeloom` skill, and
installs it into the appropriate skills directory.

## Ask your coding agent

Paste this into a coding agent that can access Git and your local skills
directory:

```text
Install Causeloom from https://github.com/zyhe16/causeloom using
`npx skills add zyhe16/causeloom`. Verify that the installed skill is named
`causeloom`, validate its SKILL.md, and do not modify unrelated files.
```

The agent should inspect the CLI result rather than assuming one
platform-specific path.

## Invocation

```text
$causeloom
```

In ChatGPT desktop, type `@` and select **Causeloom**.
