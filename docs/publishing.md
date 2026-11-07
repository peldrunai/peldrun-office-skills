# Publishing

This document explains how to publish a new version of a skill in this
repository: how to choose the version number, how to tag it, what CI
does with the tag, and how to verify the release landed correctly.

For local testing before release, see [testing.md](./testing.md). For
the architectural context, see [architecture.md](./architecture.md).

## 1. When to bump

Each skill is versioned independently. The rules below match semver
and the guidance in [PELDRUN's `creating-skills.md`](https://github.com/peldrunai/peldrun-office-skills/blob/main/docs/architecture.md).

| Change | Bump | Example |
|---|---|---|
| Fix a typo, clarify a sentence, fix a broken link | **Patch** | `1.0.0 → 1.0.1` |
| Add a section, a new example, a new reference file | **Minor** | `1.0.0 → 1.1.0` |
| Change the manifest's `id`, rename the folder, change the execution model | **Major** | `1.0.0 → 2.0.0` |
| Add support for a new language | **Minor** | `1.0.0 → 1.1.0` |
| Fix a bug in the canonical script | **Patch** | `1.0.0 → 1.0.1` |
| Update a package version in a reference (`openpyxl` 3.10 → 3.11) | **Patch** | `1.0.0 → 1.0.1` |

**Never** release two versions of the same skill on the same day unless
the first was broken. `catalog.json` only holds one version per skill;
a newer release replaces the previous one in the catalog.

**Never** edit `manifest.json` in a way that changes what existing users
already downloaded without bumping the version. If a user already
installed `1.0.0` and you fix a bug, bump to `1.0.1` — otherwise the
user has no way to know they have a different build.

## 2. Pre-release checklist

Before bumping the version, verify:

```bash
# 1. The skill passes local validation.
python scripts/validate_skill.py skills/<skill_id>

# 2. All six skills pass (no collateral damage).
python scripts/validate_skill.py --all

# 3. The skill has all required files.
ls skills/<skill_id>/
# Expect: manifest.json, SKILL.md, icon.svg, references/ (if declared)

# 4. The canonical script in SKILL.md runs and produces a valid file.
#    (Run it manually in a test workspace; see testing.md.)
```

If any of the four steps fails, **do not bump**. Fix the issue first.

## 3. The release procedure

### Step 1 — Bump the version

Edit `skills/<skill_id>/manifest.json`:

```json
{
  "version": "1.0.1"
}
```

Also update `release_date` to today's date:

```json
{
  "release_date": "2026-11-20"
}
```

### Step 2 — Update the changelog inside `SKILL.md` (optional)

There is no separate `CHANGELOG.md`. Add a short note at the top of the
`SKILL.md` body if the change is user-facing:

```markdown
> **v1.0.1** — Fixed the `wait_until="networkidle"` typo in the
> canonical script.
```

Skip this for internal-only changes (manifest tweaks, tag fixes).

### Step 3 — Validate locally

```bash
python scripts/validate_skill.py skills/<skill_id>
```

Expect: `Result: PASS` with no warnings. If there is a warning about
`SKILL.md` exceeding 10 KiB, reduce it before releasing (see
"File-size limits" below).

### Step 4 — Build and inspect the ZIP

```bash
python scripts/build_zip.py --only <skill_id>
ls -lh dist/<skill_id>-<version>.zip
```

Verify the size is reasonable (5–25 KB) and the SHA-256 printed matches
the file on disk:

```bash
sha256sum dist/<skill_id>-<version>.zip
```

### Step 5 — Update `catalog.json` locally

```bash
python scripts/update_catalog.py --only <skill_id>
```

Expect: `Total skills in catalog: 6` and a line
`- updated <skill_id> v<version>`. This step **is optional** (CI does it
again), but running it locally catches catalog problems before the tag
is pushed.

### Step 6 — Commit

```bash
git add skills/<skill_id>/manifest.json skills/<skill_id>/SKILL.md
git commit -m "release(<skill_id>): v<version>"
```

If `update_catalog.py` changed `catalog.json`, include it:

```bash
git add catalog.json
git commit --amend --no-edit
```

Push to `main`:

```bash
git push origin main
```

### Step 7 — Tag and push the tag

```bash
git tag <skill_id>-v<version>
git push origin <skill_id>-v<version>
```

The tag **must** follow the format `<skill_id>-v<major>.<minor>.<patch>`.
If it does not match the regex `^[a-z0-9][a-z0-9_]{2,63}-v\d+\.\d+\.\d+(-[a-z0-9.-]+)?$`,
`release.yml` will reject it.

### Step 8 — Watch CI

Open the **Actions** tab on GitHub. The `Release Skill` workflow
runs seven steps:

1. **Parse tag** — extracts `skill_id` and `version`; verifies the
   tag's version matches `manifest.json`.
2. **Validate tagged skill** — runs `validate_skill.py`.
3. **Build deterministic ZIP** — runs `build_zip.py --only`.
4. **Verify ZIP exists** — sanity check.
5. **Update catalog** — runs `update_catalog.py --only`.
6. **Verify catalog entry matches ZIP checksum** — recomputes the
   SHA-256 of the ZIP and compares it to what `catalog.json` recorded.
7. **Create GitHub Release** — uploads the ZIP.

All seven must be green. If any fails, see "When CI fails" below.

### Step 9 — Verify the release

```bash
# 1. The GitHub Release exists.
gh release view <skill_id>-v<version>

# 2. catalog.json on gh-pages has the new version.
curl -s https://<owner>.github.io/peldrun-office-skills/catalog.json \
  | python -c "import json,sys; d=json.load(sys.stdin); \
               e=[x for x in d['skills'] if x['id']=='<skill_id>'][0]; \
               print(e['version'], e['checksum_sha256'])"

# 3. The ZIP downloads and its SHA-256 matches.
curl -sL <download_url_from_catalog> -o /tmp/test.zip
sha256sum /tmp/test.zip
# Compare to the checksum_sha256 printed above.
```

If all three match, the release is live. PELDRUN users will pick it up
on the next catalog refresh (24-hour TTL, or immediately with the
**Refresh** button in the Store UI).

## 4. File-size limits

`scripts/validate_skill.py` enforces:

| File | Warning | Error |
|---|---|---|
| `SKILL.md` | > 10 KiB | > 256 KiB |
| `icon.svg` | > 32 KiB (error) | — |
| Any reference file | > 8 KiB (warning only) | > 512 KiB (error) |
| Any file in the ZIP | — | > 5 MiB |

The **warning** does not fail the build. The **error** does.

If you see a warning, you have two options:

1. **Reduce `SKILL.md`** — trim prose, remove redundancy, move long
   examples into `references/`.
2. **Accept the warning** — if the content is genuinely necessary and
   fits the skill's purpose. Document why in the commit message.

For `pptx_presentation` and `markdown_doc`, the soft limit is raised
because their APIs (PowerPoint XML, Markdown-it options) require more
context than `csv_data`'s.

## 5. When CI fails

### `Tag '<tag>' does not match '<skill_id>-v<semver>'`

The tag format is wrong. Delete and re-tag:

```bash
git tag -d <tag>
git push origin :refs/tags/<tag>
git tag <skill_id>-v<version>
git push origin <skill_id>-v<version>
```

### `Tag version (X) does not match manifest version (Y)`

You forgot to bump `manifest.json` before tagging. Bump it, commit,
then re-tag:

```bash
# edit manifest.json
git add skills/<skill_id>/manifest.json
git commit -m "fix(<skill_id>): bump manifest to v<version>"
git push origin main
git tag -d <tag>
git push origin :refs/tags/<tag>
git tag <skill_id>-v<version>
git push origin <skill_id>-v<version>
```

### `Checksum mismatch for <skill_id>`

The ZIP uploaded to the GitHub Release does not match what
`catalog.json` recorded. This is a defense-in-depth failure — it should
never happen if the release pipeline is intact. Investigate:

1. Did `build_zip.py` fail silently (e.g. disk full)?
2. Was `catalog.json` manually edited between build and deploy?
3. Was the ZIP re-uploaded after the catalog was updated?

Fix by re-running the release:

```bash
gh release delete <tag> --yes
git tag -d <tag>
git push origin :refs/tags/<tag>
git tag <skill_id>-v<version>
git push origin <skill_id>-v<version>
```

### `SKILL.md is N bytes; recommended maximum is 10240 bytes` (warning only)

Not a failure. See "File-size limits" above.

## 6. Rollback

If a release broke something for users, you can roll back by
publishing a **new patch version** with the fix. Do not delete the
old release — PELDRUN users may have installed it and rollback would
strand them.

If the release has a critical bug and no fix is available:

1. **Deprecate the skill** in `manifest.json`:
   ```json
   { "deprecated": true, "deprecation_message": "v1.0.1 has a known bug; use v1.0.0." }
   ```
2. **Publish a patch** restoring the previous behavior.
3. Remove the `deprecated` flag in the following release.

Deleting a tag from GitHub does **not** remove the ZIP from users'
machines. They keep what they installed until they upgrade.

## 7. Publishing all six skills at once

For the **initial v1.0.0 of all six skills**, the procedure is:

```bash
# 1. Ensure all six validate.
python scripts/validate_skill.py --all

# 2. Build all six.
python scripts/build_zip.py --all

# 3. Update the entire catalog.
python scripts/update_catalog.py --all

# 4. Commit the catalog.
git add catalog.json
git commit -m "chore: initial catalog with six skills v1.0.0"
git push origin main

# 5. Push six tags.
git tag pdf_document-v1.0.0
git tag docx_document-v1.0.0
git tag xlsx_spreadsheet-v1.0.0
git tag pptx_presentation-v1.0.0
git tag csv_data-v1.0.0
git tag markdown_doc-v1.0.0
git push origin --tags
```

Each tag triggers its own `release.yml` run. Six runs happen in
parallel (GitHub Actions runs up to 20 concurrent jobs on the free
tier). Total wall time: ~2 minutes.

After all six finish, `catalog.json` on gh-pages has six entries, each
with its own version and SHA-256.

**Do not** tag all six again after that. Subsequent releases should
tag one skill at a time, bumping only that skill's version.

## 8. Post-release verification

After a release goes live, check the catalog and skill from a clean
PELDRUN instance (or a fresh `~/.peldrun/` directory):

1. Open **Store → Skills → Catalog**.
2. Find the skill.
3. Confirm the version badge shows the new version.
4. Click **Install**.
5. Confirm the install succeeds (no checksum mismatch).
6. Open a chat and invoke `/ <skill_id>`.
7. Confirm the skill loads and produces a correct output.

If any step fails, see PELDRUN's `skill-catalog.md` §12 (Troubleshooting).

## 9. See also

- [testing.md](./testing.md) — local test procedure.
- [contributing.md](./contributing.md) — how to add a new skill.
- [architecture.md](./architecture.md) — design context.