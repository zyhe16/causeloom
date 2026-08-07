# Installation

The directory containing `SKILL.md` must be named `causeloom`, matching the
frontmatter `name`.

## Recommended: pinned release archive

Pinning the version and verifying the archive checksum is the deterministic
installation path:

```bash
curl -LO https://github.com/zyhe16/causeloom/releases/download/v0.3.0/causeloom-0.3.0.zip
echo "2a7d93bbce926131fe7891c83cc6d95c162c4e66f56a8da713097e417f32e522  causeloom-0.3.0.zip" | sha256sum -c -
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

## Agent Skills CLI

```bash
npx skills add zyhe16/causeloom
```

This follows the selected repository version rather than independently pinning
and verifying the release archive.

## Ask your coding agent

Paste this into a coding agent that can access Git and your local skills
directory:

```text
Install Causeloom v0.3.0 from https://github.com/zyhe16/causeloom.
Prefer the pinned release archive and verify its published SHA-256 checksum.
Use the correct user-level skills directory for this agent, validate the
installed SKILL.md, and do not modify unrelated files.
```

The agent should inspect its supported skill location rather than assuming one
platform-specific path.

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
