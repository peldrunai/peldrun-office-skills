# Testing

This document explains how to test a skill in this repository: what can
be tested automatically, what must be tested manually, and how to
reproduce failures.

Skills are **instructional content**, not executable code. A skill
cannot be "unit-tested" in the usual sense — there is no Python function
to call with input X and assert on output Y. Testing a skill means
verifying three layers:

1. **Structural** — the manifest, SKILL.md, and icon are well-formed.
2. **Build** — the deterministic ZIP is produced correctly.
3. **Functional** — the skill's canonical script actually works.

The first two are automated (`scripts/` + CI). The third is manual
because it requires running a generated Python script in a real
workspace with Playwright, python-docx, openpyxl, etc. installed.

For the release flow, see [publishing.md](./publishing.md).

## 1. Structural testing

This is the fastest layer and the one CI runs on every push.

```bash
# One skill
python scripts/validate_skill.py skills/pdf_document

# All skills
python scripts/validate_skill.py --all
```

What it checks:

| Check | Failure mode |
|---|---|
| `manifest.json` matches `manifest.schema.json` | Missing required field, wrong type, invalid pattern |
| `id` matches the folder name | `id: "pdf"` in `pdf_document/` |
| `SKILL.md` exists at the package root | File is missing or named differently |
| `SKILL.md` has YAML frontmatter (`---`) | Missing `---` on line 1 |
| `SKILL.md` size ≤ 256 KiB (hard), ≤ 10 KiB (warn) | Body is too long |
| `icon.svg` exists (if `icon` is declared) | `icon: "icon.svg"` but no file |
| `icon.svg` has no `<script>` | Potential XSS at render time |
| `references/` exists (if `references_dir` is declared) | Declared but missing |
| Every `sub_skills[i].instructions_file` resolves | Broken path, traversal |
| `sub_skills` array has unique IDs | Duplicate ID |
| `sub_skills` count ≤ 50 | Too many sub-skills |

**Exit codes:** `0` = pass (warnings allowed), `1` = fail.

**Expected on the current repository:** all six skills pass with no
warnings. If a warning appears (e.g. "SKILL.md is N bytes"), see
"File-size warnings" below.

## 2. Build testing

The build script produces deterministic ZIPs and verifies the result.

```bash
# One skill
python scripts/build_zip.py --only pdf_document

# All six
python scripts/build_zip.py --all
```

What it does:

1. Runs `validate_skill.py` on the skill (fail-fast).
2. Collects every file under the skill's directory.
3. Sorts files by POSIX relative path.
4. Writes each file with a fixed timestamp (`1980-01-01`) and mode
   (`0o644`) — this is what makes the ZIP deterministic.
5. Writes atomically (`.tmp` then `rename`).
6. Computes SHA-256 and prints it.

**Determinism check:** run it twice. The SHA-256 must be **identical**:

```bash
python scripts/build_zip.py --only pdf_document
# note the SHA-256
python scripts/build_zip.py --only pdf_document
# same SHA-256?  Yes -> deterministic.  No -> bug in build_zip.py.
```

If the SHA-256 changes on the second run, one of the following is
wrong:

- A file in `skills/pdf_document/` changed between the two builds.
- A file's mtime is being read from the filesystem (should not happen —
  the script uses `ZipInfo` with a fixed `date_time`).
- A file was added or removed between the two builds.

Run `git status` to confirm nothing changed. If the repo is clean and
the SHA-256 still differs, file a bug.

## 3. Functional testing

The canonical script in each `SKILL.md` must produce a valid file when
run. This is the layer that catches "the skill teaches the wrong API".

### 3.1 Set up a test workspace

```bash
mkdir ~/peldrun-test
cd ~/peldrun-test
```

The test workspace needs the same Python packages the skill assumes:

```bash
pip install playwright python-docx openpyxl python-pptx pandas markdown-it-py pypdf
playwright install chromium
```

On a fresh PELDRUN installation, these are already available. In a
standalone test environment, install them explicitly.

### 3.2 Test each skill

Copy the "Canonical script" block from each `SKILL.md` into a file
named `generate_<format>.py` in the test workspace, then run:

```bash
# PDF
python generate_pdf.py
# -> report.pdf, ~3 KB, 1 page, extractable text

# DOCX
python generate_docx.py
# -> report.docx, ~5 KB, 1+ paragraphs

# XLSX
python generate_xlsx.py
# -> report.xlsx, ~6 KB, opens with =SUM cells

# PPTX
python generate_pptx.py
# -> deck.pptx, ~30 KB, 3 slides

# CSV
python generate_csv.py
# -> data.csv, ~200 bytes, UTF-8 with BOM

# Markdown
python convert_md.py
# -> README.pdf, ~50 KB, multi-section
```

**Expected behavior:** each script prints `OK: <path> (<bytes>)` and
the file opens cleanly in its native viewer (or in `pypdf` /
`python-docx` / `openpyxl` / `python-pptx` / `pandas` / `pypdf`).

**If a script fails:**

1. Read the traceback — the failing line is the one to inspect.
2. Compare the failing line to the skill's `SKILL.md` — did the agent
   copy something wrong, or did the skill teach the wrong thing?
3. If the skill taught the wrong thing, fix `SKILL.md`, bump the
   version, release.
4. If the agent copied something wrong, the skill is ambiguous —
   clarify `SKILL.md`.

### 3.3 Test verification blocks

Every skill's `SKILL.md` ends with a "Verification (mandatory)" block.
Test it explicitly:

```bash
# From the test workspace, after generating report.pdf:
python -c "
from pathlib import Path
from pypdf import PdfReader
p = Path('report.pdf')
assert p.exists()
assert p.stat().st_size > 1000
reader = PdfReader(str(p))
print(f'Pages: {len(reader.pages)}')
"
# Expected: 'Pages: 1' (or more)
```

Do the same for each format. A skill whose verification block silently
passes on a broken file is worse than no verification at all.

## 4. Testing the catalog pipeline

Before releasing, verify the catalog round-trip:

```bash
# 1. Build the ZIP
python scripts/build_zip.py --only pdf_document
# Note: SHA-256 = abc...

# 2. Update catalog
python scripts/update_catalog.py --only pdf_document

# 3. Verify the catalog entry
python -c "
import json
from pathlib import Path
catalog = json.loads(Path('catalog.json').read_text())
entry = [s for s in catalog['skills'] if s['id'] == 'pdf_document'][0]
print(entry['version'])           # 1.0.0
print(entry['checksum_sha256'])   # abc...
print(entry['download_url'])      # https://github.com/...
"
```

The `checksum_sha256` must match what `build_zip.py` printed. The
`download_url` must point at a GitHub Release (which does not exist yet
locally — it will after CI runs).

If you need to verify the whole catalog against the actual ZIPs:

```bash
python -c "
import hashlib, json
from pathlib import Path
catalog = json.loads(Path('catalog.json').read_text())
for entry in catalog['skills']:
    zip_path = Path('dist') / f\"{entry['id']}-{entry['version']}.zip\"
    actual = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    expected = entry['checksum_sha256']
    status = 'OK' if actual == expected else 'MISMATCH'
    print(f\"{status:8} {entry['id']} v{entry['version']}\")
"
```

Every line must print `OK`. If any prints `MISMATCH`, run
`update_catalog.py --all` and try again.

## 5. End-to-end testing in PELDRUN

The final layer: install a released skill in a clean PELDRUN instance
and invoke it.

### 5.1 Prepare a clean PELDRUN instance

```bash
# Back up your existing skills (if any).
mv ~/.peldrun/skills ~/.peldrun/skills.bak

# Or delete them.
rm -rf ~/.peldrun/skills

# Start PELDRUN.
./start-backend
```

### 5.2 Install from the catalog

1. Open **Store → Skills → Catalog**.
2. Find the skill (e.g. `PDF Document Generator`).
3. Confirm the version badge shows the version you released.
4. Click **Install**.
5. Confirm the "Install Skill" toast appears with no errors.

**If the toast says `SKILL_CATALOG_CHECKSUM_MISMATCH`:** the ZIP on
GitHub does not match `catalog.json`. Re-run the release (see
[publishing.md](./publishing.md) "Checksum mismatch").

### 5.3 Invoke from chat

1. Open a chat with an agent.
2. Type `/ <skill_id>` (e.g. `/ pdf_document`).
3. Send a realistic prompt:
   - **pdf_document:** "Create a 1-page PDF invoice for Acme Corp."
   - **docx_document:** "Create a .docx business letter."
   - **xlsx_spreadsheet:** "Create a spreadsheet with 5 items and totals."
   - **pptx_presentation:** "Create a 3-slide presentation about Q4."
   - **csv_data:** "Create a CSV with columns name, email, status."
   - **markdown_doc:** "Convert this README to PDF: # Hello\n\nWorld"
4. Wait for the run to complete.
5. In DevTools → Network → SSE stream, confirm:
   - `tool_call: load_skill("<skill_id>")` (if Progressive Disclosure is on)
   - `tool_call: python_execute` (the agent writes and runs a script)
   - `final` with a result containing a file path

### 5.4 Verify the file

The agent should report `## Result` with a file path. Open that file
from the workspace (or download it via the chat UI). The file must
open cleanly and match the prompt.

**If the file is missing or empty:** the agent claimed success without
running the skill's verification block. This is a bug in the skill — the
"Verification (mandatory)" block is not strong enough. Strengthen it
and release a patch.

## 6. File-size warnings

`validate_skill.py` prints:

```
[!] SKILL.md is 10480 bytes; recommended maximum is 10240 bytes
```

This is a **warning**, not a failure. Exit code is still `0`.

The current soft limits are:

| Skill | Soft limit | Why |
|---|---|---|
| `pdf_document` | 10 KiB | Standard |
| `docx_document` | 10 KiB | Standard |
| `xlsx_spreadsheet` | 10 KiB | Standard |
| `pptx_presentation` | 10 KiB | API has more options |
| `csv_data` | 10 KiB | Standard |
| `markdown_doc` | 10 KiB | API has more options |

If a skill exceeds the soft limit:

1. **Trim first.** Remove redundancy, tighten prose, move long examples
   into `references/`.
2. **Accept the warning** only if the content is genuinely necessary.
   Document why in the commit message and in `architecture.md` §2.6.

Do **not** raise the soft limit unilaterally. A skill near 10 KiB is
already at the upper bound of what a model can follow precisely.

## 7. Automated vs manual — what CI cannot test

`.github/workflows/validate.yml` covers:

- Structural validation (schema, patterns, file existence).
- Python compilation of `scripts/*.py`.

It **cannot** cover:

- Running the canonical script (no Playwright, no LibreOffice in the
  runner — and CI should not download 200 MB of Chromium for a
  markdown skill).
- Opening the produced file in Word / Excel / PowerPoint.
- Verifying that an Arabic PDF actually shows Arabic (needs a human
  or OCR).
- Testing the full install → invoke → output flow in PELDRUN.

These are the **manual** tests described in §3 and §5. Do them once
per release, at least for the skill you are changing.

## 8. Common test failures

| Symptom | Cause | Fix |
|---|---|---|
| `manifest.json is not valid JSON` | Trailing comma or unquoted key | Fix the JSON |
| `id '...' does not match folder name` | Renamed folder without updating `id` | Update `manifest.json` |
| `SKILL.md is missing YAML frontmatter` | Forgot `---` on line 1 | Add it |
| `icon_svg contains a <script> element` | Copied a full SVG from the web | Remove `<script>` or use a minimal SVG |
| `sub_skills[0].instructions_file escapes the package` | Path traversal in `..` | Fix the path |
| Deterministic build produces different SHA-256 on second run | A source file changed | `git status` to find it |
| `SKILL_CATALOG_CHECKSUM_MISMATCH` in PELDRUN | `catalog.json` is stale | `update_catalog.py --all`, push tag |
| Canonical script fails with `ModuleNotFoundError` | Package missing in test env | `pip install` the missing package |

## 9. See also

- [publishing.md](./publishing.md) — release flow.
- [contributing.md](./contributing.md) — adding a new skill.
- [architecture.md](./architecture.md) — design context.