# PELDRUN Office Skills

Six independent PELDRUN skills for the most common office-document
formats. Each skill teaches the agent how to write a Python script that
produces the target file — PDF, DOCX, XLSX, PPTX, CSV, or styled
Markdown → PDF/HTML — in **any language**, including Arabic (RTL),
Hebrew, Chinese, Japanese, Korean, and Russian.

[![Validate Skills](https://github.com/peldrunai/peldrun-office-skills/actions/workflows/validate.yml/badge.svg)](https://github.com/peldrunai/peldrun-office-skills/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Skills

| Skill | Format | Library | Languages |
|---|---|---|---|
| [`pdf_document`](skills/pdf_document/) | PDF | Playwright + Chromium | Any (Arabic RTL, CJK, Cyrillic) |
| [`docx_document`](skills/docx_document/) | DOCX | python-docx | Any (per-paragraph RTL) |
| [`xlsx_spreadsheet`](skills/xlsx_spreadsheet/) | XLSX | openpyxl | Any (sheet-level RTL) |
| [`pptx_presentation`](skills/pptx_presentation/) | PPTX | python-pptx | Any (per-paragraph RTL) |
| [`csv_data`](skills/csv_data/) | CSV | pandas | Any (UTF-8 with BOM) |
| [`markdown_doc`](skills/markdown_doc/) | MD → PDF/HTML | markdown-it + Playwright | Any (auto RTL detection) |

Each skill is **instructional only**. It does not execute code. It
contains a markdown document (`SKILL.md`) that the agent reads to learn
how to write a Python script, and a JSON manifest (`manifest.json`)
that tells PELDRUN how to install and display it. The agent writes the
script in its workspace, runs it via `python_execute`, verifies the
output, and reports back.

## Installation

### From the PELDRUN Skill Catalog (recommended)

1. Open **Store → Skills → Catalog** in PELDRUN.
2. Find the skill you need (e.g. **PDF Document Generator**).
3. Click **Install**.

**Only the skill you install is downloaded** (5–20 KB ZIP). The other
five remain visible in the catalog, uninstalled, until you choose to
install them. Installing one skill never touches the others.

### Manual (from a release ZIP)

1. Download the desired ZIP from
   [Releases](https://github.com/peldrunai/peldrun-office-skills/releases).
2. Open **Store → Skills → Install Skill (.zip)**.
3. Pick the ZIP.

Each release is tagged `<skill_id>-v<semver>` and contains exactly one
skill's ZIP.

### From source (for contributors)

```bash
git clone https://github.com/peldrunai/peldrun-office-skills.git
cd peldrun-office-skills

# Validate all six.
python scripts/validate_skill.py --all

# Build the ZIP for one skill.
python scripts/build_zip.py --only pdf_document
# -> dist/pdf_document-1.0.0.zip

# Update the catalog.
python scripts/update_catalog.py --only pdf_document
```

## Usage

Once installed, invoke a skill from the chat composer with `/`:

```
/ pdf_document Create a 1-page invoice for Acme Corp.
```

Or assign it to an agent (ambient instructions on every run):

1. Open **Store → Agents**.
2. Click the ✨ icon on the agent.
3. Select the skill.
4. Save.

Agents load skill bodies via Progressive Disclosure — the catalog is
shown on every run, and the full `SKILL.md` is fetched only when the
model decides it needs it.

## Repository layout

```
peldrun-office-skills/
├── .github/workflows/
│   ├── validate.yml              # CI: validate every push and PR
│   └── release.yml               # CI: build + publish on <skill>-v<ver> tag
├── docs/
│   ├── architecture.md           # Design decisions and structure
│   ├── publishing.md             # How to release a version
│   ├── testing.md                # How to test locally
│   └── contributing.md           # Guide for new contributors
├── scripts/
│   ├── validate_skill.py         # Validate one or all skills
│   ├── build_zip.py              # Build deterministic ZIPs
│   └── update_catalog.py         # Update catalog.json
├── skills/                       # One directory per skill
│   ├── pdf_document/
│   ├── docx_document/
│   ├── xlsx_spreadsheet/
│   ├── pptx_presentation/
│   ├── csv_data/
│   └── markdown_doc/
├── catalog.json                  # Generated index (consumed by PELDRUN)
├── manifest.schema.json          # JSON Schema for all manifests
└── LICENSE                       # MIT
```

## Versioning

Each skill is versioned **independently**. Tags follow the pattern:

```
<skill_id>-v<major>.<minor>.<patch>
```

Examples:

```
pdf_document-v1.0.0
pdf_document-v1.1.0
csv_data-v1.0.0
```

The `catalog.json` file is regenerated on every tag by CI, and **only
the entry for the tagged skill is updated**. Other skills keep their
existing version and checksum. See [docs/publishing.md](docs/publishing.md)
for the release procedure.

## Contributing

We welcome contributions. The best places to start:

- **A bug in an existing skill** — open an issue with `skill:<skill_id>`.
- **A new skill** — read [docs/contributing.md](docs/contributing.md) first,
  then open a discussion before writing code.
- **A documentation improvement** — open a PR directly.

Before opening a PR, run:

```bash
python scripts/validate_skill.py --all
python scripts/build_zip.py --all
```

Both must pass. CI runs the same checks.

## Documentation

- [architecture.md](docs/architecture.md) — what the repository contains
  and why it is structured the way it is.
- [publishing.md](docs/publishing.md) — how to release a version.
- [testing.md](docs/testing.md) — how to test a skill locally.
- [contributing.md](docs/contributing.md) — guide for new contributors.

## License

MIT — see [LICENSE](LICENSE).