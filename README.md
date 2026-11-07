# PELDRUN Office Skills

Official office-document skills for [PELDRUN](https://peldrun.ai).

Six independent skills covering the most common document formats:

| Skill | Format | Library |
|---|---|---|
| `pdf_document` | PDF | Playwright + Chromium |
| `docx_document` | DOCX | python-docx |
| `xlsx_spreadsheet` | XLSX | openpyxl |
| `pptx_presentation` | PPTX | python-pptx |
| `csv_data` | CSV | pandas |
| `markdown_doc` | Markdown → PDF | markdown-it + Playwright |

Each skill is **instructional only** — it never executes code. The skill
teaches the agent how to write a Python script that produces the document.
The agent then runs that script in its workspace.

## Installation

### From the PELDRUN Skill Catalog

1. Open **Store → Skills → Catalog**.
2. Find the skill you need (e.g. `PDF Document Generator`).
3. Click **Install**.

Only the skill you install is downloaded. The other five remain in the
catalog, uninstalled, until you choose to install them.

### Manual (from a release ZIP)

1. Download the desired ZIP from
   [Releases](https://github.com/peldrunai/peldrun-office-skills/releases).
2. Open **Store → Skills → Install Skill (.zip)**.
3. Pick the ZIP.

## Repository layout

```
peldrun-office-skills/
├── .github/workflows/     # CI (validate on PR, release on tag)
├── docs/                  # Architecture, publishing, testing, contributing
├── scripts/               # validate_skill.py, build_zip.py, update_catalog.py
├── skills/                # One directory per skill
│   ├── pdf_document/
│   ├── docx_document/
│   ├── xlsx_spreadsheet/
│   ├── pptx_presentation/
│   ├── csv_data/
│   └── markdown_doc/
└── catalog.json           # Generated — consumed by PELDRUN
```

## Versioning

Each skill is versioned independently. Tags follow the pattern:

```
<skill_id>-v<major>.<minor>.<patch>
```

Examples:

```
pdf_document-v1.0.0
pdf_document-v1.1.0
csv_data-v1.0.0
```

The `catalog.json` file is regenerated on every tag by CI, and only the
entry for the tagged skill is updated. Other skills keep their existing
version and checksum.

## Releasing a skill

See [`docs/publishing.md`](docs/publishing.md).

## Contributing

See [`docs/contributing.md`](docs/contributing.md).

## License

MIT — see [LICENSE](LICENSE).
