# Installation

The directory containing `SKILL.md` must be named `causeloom`, matching the
frontmatter `name`.

## Ask your coding agent

Paste this into a coding agent that can access Git and your local skills
directory:

```text
Install the Causeloom skill from https://github.com/zyhe16/causeloom.
Use the correct user-level skills directory for this agent, validate the
installed SKILL.md, and do not modify unrelated files.
```

The agent should inspect its supported skill location rather than assuming one
platform-specific path.

## Agent Skills CLI

```bash
npx skills add zyhe16/causeloom
```

## Release archive

```bash
mkdir -p ~/.agents/skills
unzip causeloom-0.3.0.zip -d ~/.agents/skills
```

The resulting layout is:

```text
~/.agents/skills/
`-- causeloom/
    |-- SKILL.md
    |-- agents/openai.yaml
    |-- LICENSE
    `-- VERSION
```

For a project-local installation, extract to `.agents/skills` instead.

## Source checkout

```bash
git clone https://github.com/zyhe16/causeloom.git
cd causeloom
python scripts/validate_skill.py .
```

## Invocation

```text
$causeloom
```

In ChatGPT desktop, type `@` and select **Causeloom**.
