# Contributing

This document is the guide for a new contributor. It assumes you have
never seen the repository before and explains what you need to know to
add a skill, fix a bug, or improve the docs.

For the architectural context, read [architecture.md](./architecture.md)
first. For release mechanics, see [publishing.md](./publishing.md).

## 1. What this repository contains

Six independent PELDRUN skills, one directory each under `skills/`:

```
skills/
├── pdf_document/
├── docx_document/
├── xlsx_spreadsheet/
├── pptx_presentation/
├── csv_data/
└── markdown_doc/
```

Each skill is a self-contained package:

```
skills/<skill_id>/
├── manifest.json        # required
├── SKILL.md             # required
├── icon.svg             # required (declared in manifest)
└── references/          # optional
    └── *.md
```

Skills are **instructional only**. They do not execute code. They
contain a markdown document (`SKILL.md`) that the agent reads to learn
how to write a Python script, and a JSON manifest that tells PELDRUN
how to install, display, and route the skill.

## 2. Prerequisites

- Python 3.12 or later.
- Git.
- A text editor (VS Code, Sublime, or any editor with Markdown support).
- Optional: `pip install jsonschema` for full local validation.
- Optional: `pip install playwright python-docx openpyxl python-pptx pandas markdown-it-py pypdf`
  if you want to run the canonical scripts in `SKILL.md` locally.

You do **not** need PELDRUN installed to contribute a skill. The skill
package is plain JSON + Markdown.

## 3. Quick start — run the existing skills

Before changing anything, confirm the repository is in a working state:

```bash
git clone https://github.com/peldrunai/peldrun-office-skills.git
cd peldrun-office-skills

python scripts/validate_skill.py --all
# Expected: PASSED: all 6 skill(s) validated successfully.

python scripts/build_zip.py --all
# Expected: SUCCESS: 6 skill(s) built in dist

python scripts/update_catalog.py --all
# Expected: Total skills in catalog: 6
```

If any of these fail, stop and ask — the repository is in a broken
state. Do not contribute on top of a broken base.

## 4. Adding a new skill

To add a seventh skill (e.g. `odt_document`):

### Step 1 — Create the directory

```bash
mkdir -p skills/odt_document/references
```

### Step 2 — Write `manifest.json`

Copy an existing manifest and adapt it:

```bash
cp skills/csv_data/manifest.json skills/odt_document/manifest.json
```

Then edit the fields:

- **`id`** — must match the folder name exactly (`odt_document`).
- **`version`** — `1.0.0` for a new skill.
- **`name`** — human-readable (`ODT Document Generator`).
- **`description`** — one line, English only, with search keywords.
- **`brand_color`** — pick a hex color that does not clash with the
  existing six (`#E74C3C`, `#2B579A`, `#217346`, `#D24726`, `#00897B`,
  `#6C5CE7`).
- **`icon`** — `"icon.svg"` (must match the file you create).
- **`tags`** — English only, BM25 keywords.
- **`supported_languages`** — list of ISO 639-1 codes the skill can
  produce.

See `manifest.schema.json` for the full field reference.

### Step 3 — Write `SKILL.md`

Copy an existing skill as a template. The best starting point is
`skills/csv_data/SKILL.md` — it is the shortest and most direct.

A good `SKILL.md` has these sections, in this order:

1. **Frontmatter** (`---\nname: ...\ndescription: ...\n---`)
2. **One-sentence purpose** — "You create X using Y only."
3. **Why `<library>`** — one or two sentences explaining the choice.
4. **Before you write code** — 4–6 questions the agent must ask.
5. **Canonical script** — a complete, runnable Python script.
6. **Critical section** — the single most error-prone aspect
   (encoding, RTL, formulas, or nothing for simple skills).
7. **Verification (mandatory)** — code that fails loudly on bad output.
8. **Output format** — the exact structure the agent returns.
9. **Hard rules** — 8–10 numbered "never do this" statements.

Keep `SKILL.md` under **10 KiB**. If it grows past that, move long
examples or reference tables into `references/`.

### Step 4 — Write `icon.svg`

Minimal SVG, under 1 KiB. The sanitizer rejects `<script>`, `<text>`,
and any `url()` outside the document. Use `<rect>` and `<path>` only.

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <rect x="2" y="2" width="20" height="20" rx="3" fill="#YOUR_COLOR"/>
  <!-- simple shapes -->
</svg>
```

### Step 5 — Optional `references/`

If your skill has content that is only occasionally needed (a formula
cheat-sheet, a set of templates, a troubleshooting guide), put it in
`skills/<id>/references/<name>.md`. Reference files:

- Have no size limit beyond 512 KiB.
- Are loaded on demand via `load_reference(skill_id, path)`.
- Should be referenced from `SKILL.md` in a "References" section.

### Step 6 — Validate and build

```bash
python scripts/validate_skill.py skills/odt_document
python scripts/build_zip.py --only odt_document
python scripts/update_catalog.py --only odt_document
```

All three must succeed.

### Step 7 — Update the README table

Add the new skill to the table at the top of `README.md`.

### Step 8 — Open a pull request

Push your branch and open a PR against `main`. The `Validate Skills`
workflow runs automatically. It must pass. A maintainer reviews the
PR, and once merged, the skill is published with its first tag
(`odt_document-v1.0.0`).

## 5. Editing an existing skill

Bug fixes and small improvements:

1. Edit `SKILL.md` or the appropriate reference file.
2. Run `python scripts/validate_skill.py skills/<id>` — must pass.
3. Run `python scripts/build_zip.py --only <id>` — note the new SHA-256.
4. If the change is **user-visible**, bump the version in
   `manifest.json` (patch for fixes, minor for new sections, major for
   breaking changes). See [publishing.md](./publishing.md) §1.
5. Commit, push, tag. See [publishing.md](./publishing.md) §3.

If the change is **internal only** (fixing a typo in a comment, updating
a link), you may skip the version bump. The release pipeline runs only
on tags, so an unversioned change stays on `main` until the next
versioned release.

## 6. The hard rules (read these)

These apply to **every** skill in this repository. Do not break them
even if a task seems to require it.

1. **No Arabic (or any non-English text) in the final files.** The
   skills are for an international audience and BM25 indexes only
   English. If you need to demonstrate Arabic content, use an English
   placeholder (`{{ARABIC_NAME}}`) and explain in a comment.

2. **No `assets/` directory.** Assets are not accessible at runtime.
   Put reusable HTML/CSS/JSON in `references/`, not in `assets/`.

3. **No `handler.py`, no executable code.** Skills are instructions
   only. The agent writes the Python script; the skill does not.

4. **No hardcoded absolute paths.** Use `<workspace>/...` or workspace-
   relative `Path("...")`. Never `C:\...` or `/tmp/...`.

5. **No external network calls** except the documented Chart.js CDN
   fallback in `pdf_document`. Prefer `file:///workspace/...` for
   images.

6. **Every `SKILL.md` must have a Verification block.** It must fail
   loudly when the output file is missing, empty, or malformed.

7. **Every `manifest.json` must declare `icon: "icon.svg"`.** Without
   it, PELDRUN falls back to a generic icon and the branded card does
   not render.

8. **Tags and descriptions must be English only.** `supported_languages`
   lists what the skill can *produce*, not what its metadata is in.

9. **The canonical script must be complete, not abbreviated.** Small
   models follow a full script; they fail on fragments.

10. **`SKILL.md` must stay under 10 KiB.** Move long content to
    `references/`.

## 7. Local testing

The full local test procedure is in [testing.md](./testing.md). The
short version:

```bash
# 1. Structural
python scripts/validate_skill.py --all

# 2. Build (must be deterministic — run twice, expect same SHA-256)
python scripts/build_zip.py --all

# 3. Functional — copy the canonical script into a test workspace,
#    run it, verify the output file opens.
mkdir /tmp/test && cd /tmp/test
# ... paste the script from SKILL.md ...
python generate_<format>.py
```

If any of these fails, do not open a PR.

## 8. Commit message convention

Use conventional commits:

```
feat(<skill_id>): short description
fix(<skill_id>): short description
docs(<file>): short description
chore: short description
release(<skill_id>): v<major>.<minor>.<patch>
```

Examples:

```
feat(pdf_document): add certificate template to references
fix(docx_document): correct run.font.rtl in RTL helper
docs(architecture): clarify per-skill versioning rationale
release(xlsx_spreadsheet): v1.0.1
```

The `<skill_id>` is the skill's folder name. For changes that span
multiple skills (or the docs/scripts), omit it.

## 9. What reviewers look for

A maintainer reviewing your PR will check:

- Does `validate_skill.py --all` pass?
- Does `build_zip.py --all` produce the same SHA-256 on a second run?
- Does `SKILL.md` follow the nine-section structure?
- Is `SKILL.md` under 10 KiB? If not, why?
- Are the hard rules respected?
- Are tags and descriptions English only?
- Is `icon: "icon.svg"` declared?
- Does the canonical script run and produce a valid file?
- Does the verification block fail loudly on a missing file?
- If the version was bumped, does it match the intended scope
  (patch/minor/major)?

## 10. Where to ask

- **Bugs in a skill:** open an issue with the tag `skill:<skill_id>`.
- **Ideas for a new skill:** open a discussion before writing code.
- **Release problems:** see [publishing.md](./publishing.md) §5
  "When CI fails".
- **Design questions:** see [architecture.md](./architecture.md).

## 11. License

By contributing, you agree to license your contribution under the MIT
License (see [LICENSE](../LICENSE)).