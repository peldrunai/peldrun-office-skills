# Architecture

This document describes the design of the PELDRUN Office Skills
repository: what it contains, why it is structured the way it is, and
how the pieces fit together.

For **how to release** a new version, see [publishing.md](./publishing.md).
For **how to test** locally, see [testing.md](./testing.md). For **how to
contribute**, see [contributing.md](./contributing.md).

## 1. What this repository is

A single Git repository containing six independent PELDRUN skills:

| Skill               | Format | Underlying tool          |
|---------------------|--------|--------------------------|
| `pdf_document`      | PDF    | Playwright + Chromium    |
| `docx_document`     | DOCX   | python-docx              |
| `xlsx_spreadsheet`  | XLSX   | openpyxl                 |
| `pptx_presentation` | PPTX   | python-pptx              |
| `csv_data`          | CSV    | pandas                   |
| `markdown_doc`      | MD → PDF/HTML | markdown-it + Playwright |

Each skill is a self-contained instruction package. It is **not**
executable code. Its purpose is to teach the agent how to write a
Python script that produces the target format, and how to verify the
result before reporting success.

### Skills are instructional only

A PELDRUN skill cannot execute code, cannot access the network, cannot
write to the filesystem beyond its own package. It is a markdown
document (`SKILL.md`) with a JSON manifest (`manifest.json`). The agent
reads it, writes a Python script in the workspace, runs that script via
`python_execute`, verifies the output, and reports back.

This is why every skill in this repository includes:

- A **Canonical script** block that the agent copies verbatim.
- A **Verification (mandatory)** block that fails loudly if the output
  file is missing, empty, or malformed.
- A **Hard rules** section listing what not to do (wrong libraries,
  absolute paths, fake data).

## 2. Architectural decisions

### 2.1 Monorepo, not six repositories

All six skills live in a single repository. This gives:

- **One CI pipeline** that builds ZIPs for any skill.
- **One `catalog.json`** that lists all six.
- **Shared tooling** (`scripts/`), documentation (`docs/`), and
  conventions (`.github/workflows/`).

Six separate repositories would duplicate CI, tooling, and docs with no
corresponding benefit — each skill is only 5–20 KB of text.

### 2.2 Per-skill versioning (tags)

Each skill is versioned **independently**. Tags follow the pattern:

```
<skill_id>-v<major>.<minor>.<patch>
```

Examples:

```
pdf_document-v1.0.0
pdf_document-v1.1.0
docx_document-v1.0.0
csv_data-v1.0.0
```

The alternative — a single `v1.0.0` tag for all six — creates version
drift: bumping `pdf_document` to `v1.0.1` would force `csv_data` to
`v1.0.1` even though its code is unchanged. Per-skill tags avoid this.

The cost is one extra step in `release.yml` (parse the tag, extract
`skill_id` and `version`). The benefit is that `catalog.json` remains
accurate: each entry's `version` matches its ZIP's actual content.

### 2.3 Deterministic ZIPs

`scripts/build_zip.py` produces **byte-identical** ZIPs for the same
input. It does this by:

- Sorting files by POSIX relative path.
- Fixing modification time to `1980-01-01T00:00:00`.
- Fixing file mode to `0o644`.
- Fixing compression level to `9`.

This matters because `catalog.json` records the SHA-256 of each ZIP. If
the ZIP were non-deterministic, every rebuild would change the
checksum even when no source file changed — invalidating the catalog
entry.

### 2.4 No embedded fonts

Skills do **not** bundle fonts. Playwright/Chromium uses the system's
installed fonts automatically. This is the only approach that works
across Windows, macOS, and Linux without shipping 18 MB of Noto fonts
in every ZIP.

`pdf_document` handles the "missing font" case by asserting that the
extracted PDF text is non-empty (which catches tofu). If a font is
missing, the agent reports it to the user.

### 2.5 No runtime coupling to GitHub

The `catalog.json` file is fetched from GitHub Pages by PELDRUN with a
24-hour TTL. The download URL points at a GitHub Release asset. But
**nothing in PELDRUN calls GitHub at runtime** beyond those two
fetches. If GitHub is down, PELDRUN uses its cached catalog and cached
skills. See PELDRUN's `skill-catalog.md` §4 for details.

### 2.6 Progressive Disclosure is the runtime model

Every skill is designed for **Progressive Disclosure** — the model sees
a compact catalog, loads only the skill body it needs. This is why:

- `SKILL.md` targets **8 KiB** (recently raised to 10 KiB for
  `pptx_presentation` and `markdown_doc`, whose APIs require more
  context).
- Longer content is moved to `references/` and loaded on demand via
  `load_reference`.
- The catalog descriptions and tags are written in English only, because
  BM25 indexes them with an ASCII-only tokenizer.

See PELDRUN's `progressive-disclosure.md` for the full model.

### 2.7 No router skills

None of the six skills uses the router pattern (parent + sub-skills).
Each skill is a single self-contained document. Reasons:

- The skills cover **distinct formats** — `pdf_document` and
  `csv_data` do not share content, so there is no parent to dispatch
  from.
- Router overhead (parent body + two `load_sub_skill` round trips)
  would exceed any savings for skills this size.

The router pattern is documented in PELDRUN's `router-pattern.md`. It
is suitable for deep skills that cover multiple concerns (e.g. a
`code_review` skill with security / correctness / maintainability
sub-skills). None of the six Office skills fit that profile.

### 2.8 Playwright for PDF (not reportlab)

Both `pdf_document` and `markdown_doc` use Playwright + Chromium
because Chromium handles:

- Arabic, Hebrew, Persian, Urdu shaping and bidi reordering.
- CJK, Cyrillic, Devanagari font fallback.
- CSS layout (tables, columns, page breaks).
- Chart.js rendering (for `pdf_document`).

`reportlab` would require manual font registration, manual Arabic
reshaping with `arabic-reshaper`, and manual bidi with `python-bidi`.
None of this is needed with Playwright.

### 2.9 English-only metadata

`manifest.tags` and `manifest.description` are **English only**. BM25
tokenizes with `[a-z0-9_]+` and strips everything else — Arabic tags
would silently be removed from the index, making the skill
undiscoverable. The `supported_languages` field records what languages
the skill can *produce*, not what languages its metadata is in.

### 2.10 CI builds, humans review

`.github/workflows/validate.yml` runs on every push and PR. It
validates every skill against `manifest.schema.json` and runs
`validate_skill.py`. It **does not** build ZIPs or publish.

`.github/workflows/release.yml` runs only on `<skill_id>-v<semver>`
tags. It:

1. Validates the tagged skill.
2. Builds the ZIP.
3. Updates **one entry** in `catalog.json`.
4. Creates a GitHub Release.
5. Deploys `catalog.json` to GitHub Pages.

This separation ensures a broken skill cannot reach `main`, and a
release can only be created by an explicit `git tag` + `git push`.

## 3. Repository layout

```
peldrun-office-skills/
├── .github/workflows/
│   ├── validate.yml              # CI: validate every push and PR
│   └── release.yml               # CI: build + publish on <skill>-v<ver> tag
├── docs/                         # This documentation
├── scripts/
│   ├── validate_skill.py         # Validate one or all skills
│   ├── build_zip.py              # Build deterministic ZIPs
│   └── update_catalog.py         # Update catalog.json (--only or --all)
├── skills/
│   ├── pdf_document/
│   │   ├── manifest.json
│   │   ├── SKILL.md
│   │   ├── icon.svg
│   │   └── references/
│   │       ├── templates.md
│   │       └── troubleshooting.md
│   ├── docx_document/            # manifest + SKILL + icon + references/examples.md
│   ├── xlsx_spreadsheet/         # manifest + SKILL + icon + references/{formulas,examples}.md
│   ├── pptx_presentation/        # manifest + SKILL + icon + references/layouts.md
│   ├── csv_data/                 # manifest + SKILL + icon (no references)
│   └── markdown_doc/             # manifest + SKILL + icon (no references)
├── dist/                         # Built ZIPs (gitignored)
├── catalog.json                  # Generated by update_catalog.py
├── manifest.schema.json          # The skill manifest JSON Schema
├── README.md
├── LICENSE
└── .gitignore
```

Each `skills/<id>/` directory is a **self-contained skill package**. It
can be zipped and installed with no other file in the repository
needed.

## 4. The catalog

`catalog.json` is the machine-readable index consumed by PELDRUN. Its
shape:

```json
{
  "schema_version": 1,
  "updated_at": "2026-11-08T12:00:00Z",
  "skills": [
    {
      "id": "pdf_document",
      "name": "PDF Document Generator",
      "version": "1.0.0",
      "description": "Generate PDF reports, invoices...",
      "download_url": "https://github.com/peldrunai/peldrun-office-skills/releases/download/pdf_document-v1.0.0/pdf_document-1.0.0.zip",
      "checksum_sha256": "a1b2c3...",
      "tags": ["pdf", "document", "report"],
      "has_sub_skills": false,
      "sub_skills_count": 0,
      "trust": "community",
      "license": "MIT",
      "release_date": "2026-11-08"
    }
  ]
}
```

Key invariants:

- **One entry per installed skill.** No duplicates.
- **`checksum_sha256` matches the ZIP in the GitHub Release.** The
  `release.yml` "Verify catalog entry matches ZIP checksum" step
  enforces this.
- **`version` matches `manifest.json`'s `version`.** The
  `release.yml` "Parse tag" step rejects any mismatch.
- **`download_url` is HTTPS.** The `update_catalog.py` always
  constructs it from `https://github.com/...`.

The backend **recomputes** `installable` and `installability_reason`
from these fields. They must never appear in `catalog.json` — the
validator would reject the file.

## 5. Security model

Three attack surfaces, all mitigated:

| Threat | Mitigation |
|---|---|
| Malicious `manifest.json` (bad field, wrong pattern) | JSON Schema validated by `validate_skill.py` locally and by the backend at install time |
| Malicious `SKILL.md` (prompt injection) | `--- BEGIN SKILL ---` delimiters; instructions only, no execution |
| Path traversal in `references/` or sub-skill paths | Backend containment check (`resolve().relative_to(package_dir)`); local validator rejects `..` |
| Malicious `icon.svg` (`<script>`, external URLs) | Sanitized at install time and at render time |
| Tampered ZIP (supply-chain) | SHA-256 in `catalog.json`; `release.yml` verifies before publishing |
| Oversized content (memory exhaustion) | `max_instructions_bytes` (256 KiB) per body, 512 KiB per reference, 5 MiB per file in the ZIP |

The skills themselves have **no execution capability**. The worst a
malicious skill can do is give the model bad advice — which the model
may or may not follow. The install-time checks (schema, containment,
sanitizer) prevent the model from being tricked into reading files
outside the package.

## 6. Testing and release flow

**Local validation:**

```bash
python scripts/validate_skill.py skills/pdf_document
python scripts/validate_skill.py --all
```

**Local build:**

```bash
python scripts/build_zip.py --only pdf_document
python scripts/build_zip.py --all
```

**Local catalog update:**

```bash
python scripts/update_catalog.py --only pdf_document
python scripts/update_catalog.py --all
```

**Release:**

```bash
# 1. Bump manifest.version in the skill you are updating.
# 2. Commit and push to main.
# 3. Tag and push the tag:
git tag pdf_document-v1.1.0
git push origin pdf_document-v1.1.0
# 4. CI does the rest (see release.yml).
```

## 7. Relationship to PELDRUN core

This repository is a **content publisher**. It does not contain code
that runs inside PELDRUN. It contains markdown + JSON that PELDRUN
fetches and interprets.

PELDRUN core (separate repository) handles:

- Fetching `catalog.json` (HTTPS, 24-hour TTL).
- Downloading ZIPs (HTTPS, 60-second timeout, 10 MB cap).
- Verifying SHA-256.
- Calling `SkillManager.install_skill` — the same code path as manual
  ZIP upload.
- Loading `SKILL.md` into the system prompt (or exposing it via
  `load_skill` tools).
- Sanitizing SVG at both install time and render time.

This repository has **no knowledge** of any of the above. It only
produces artifacts that satisfy the contracts documented in PELDRUN's
own documentation (`skill-catalog.md`, `progressive-disclosure.md`,
`creating-skills.md`, `router-pattern.md`).

## 8. Open questions

- **Font coverage:** some Linux distributions ship without Noto CJK.
  `pdf_document` reports this via the "Warnings" output field. A future
  version could ship a minimal Noto subset, at the cost of ~2 MB per
  ZIP. Deferred until there is user demand.
- **Router pattern:** none of the six skills uses it. A future
  `office_documents` router that dispatches to all six would reduce the
  catalog size by 5 entries, but would add a `load_sub_skill` round
  trip. Not adopted.
- **Multiple versions per skill:** `catalog.json` currently holds one
  version per skill. If a skill's old version needs to stay available
  (e.g. for backward compatibility), a `versions[]` array per entry
  would be needed. Not currently implemented.

## 9. See also

- [publishing.md](./publishing.md) — how to release a version.
- [testing.md](./testing.md) — how to test locally.
- [contributing.md](./contributing.md) — how to add a skill.
- PELDRUN's own `skill-catalog.md`, `progressive-disclosure.md`,
  `creating-skills.md`, `router-pattern.md`.