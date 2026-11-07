# PDF Troubleshooting

Diagnostic guide for the twelve most common failures when generating
PDFs with Playwright + Chromium. Each section follows the same pattern:

1. **Symptom** — what the user or the verification script sees.
2. **Cause** — why it happens.
3. **Diagnose** — how to confirm this is the actual problem.
4. **Fix** — what to do.

Run the verification block from `SKILL.md` **before** assuming any of
these applies. A PDF that fails verification has a real problem; a PDF
that passes may still have cosmetic issues covered below.

---

## 1. Tofu squares (□□□) instead of characters

**Symptom:** The PDF opens, but every non-Latin character is a small
square, a diamond, or a question mark. `pypdf` extraction returns very
few characters or empty text.

**Cause:** Chromium found no font that covers the script. This is most
common for Arabic, Hebrew, CJK, and Devanagari on Linux systems without
the Noto font packages installed, or when a CSS rule overrides the font
stack with a Latin-only font.

**Diagnose:**

```python
from pypdf import PdfReader
reader = PdfReader("report.pdf")
text = reader.pages[0].extract_text() or ""
print(repr(text[:200]))
# Real text   -> '"Monthly Sales Report"'
# Tofu        -> '' or '\n\n\n' or '   '
# Partial     -> '"Monthly" □□□□□□' (some characters missing)
```

**Fix:**

- Verify the HTML has the correct `lang` attribute (e.g. `lang="ar"`,
  `lang="zh-CN"`, `lang="ja"`). A missing or wrong `lang` attribute
  often causes Chromium to pick the wrong fallback font.
- Verify the CSS font-family list includes the Noto family for that
  script. The stack in `SKILL.md` already does.
- On Linux: install `fonts-noto` and `fonts-noto-cjk`. This is an
  operator action, not something the agent can do at runtime.
- On Windows/macOS: the required fonts are already present. If tofu
  still appears, the CSS is overriding the stack — check for a later
  `font-family` rule in the user's HTML.
- **Never** attempt to fix tofu by reversing text or adding bidi control
  characters. That converts a font problem into a layout problem.

---

## 2. Arabic text is reversed or scattered

**Symptom:** The Arabic text reads right-to-left but the words are in
the wrong order, or a Latin word inside an Arabic paragraph breaks the
line mid-word.

**Cause:** This is **not** a shaping problem — it is a bidi layout
problem caused by a missing or incorrect `dir` attribute. Chromium
defaults to `ltr`, which places Arabic characters right-to-left but
keeps the paragraph order left-to-right.

**Diagnose:** Inspect the generated HTML. Confirm:

```html
<html lang="ar" dir="rtl">   <!-- correct -->
<html lang="ar">             <!-- wrong: defaults to ltr -->
<html dir="rtl">             <!-- wrong: no lang, font fallback fails -->
```

**Fix:** Set **both** `lang` and `dir` on `<html>`:

```html
<html lang="ar" dir="rtl">
```

For a mixed document (e.g. English header, Arabic body), set `dir` only
on the container of the RTL section:

```html
<h1>Quarterly Report</h1>
<div lang="ar" dir="rtl">{{ARABIC_BODY}}</div>
```

**Never** apply `unicode-bidi: bidi-override` or `direction: rtl` to
individual spans. Let Chromium compute the bidi runs automatically.

---

## 3. Charts are missing or blank

**Symptom:** The PDF is generated, but the chart area is empty or shows
only the axes without data. Sometimes the chart appears as a white
rectangle on the brand-colored background.

**Cause:** Three possibilities, in order of frequency:

1. `animation: true` (Chart.js default) — Chromium captured the canvas
   before the animation completed, so the data series has not drawn yet.
2. `responsive: true` (Chart.js default) — Playwright has no viewport,
   so the chart sized itself to 0×0 or to the wrong dimensions.
3. Chart.js script failed to load (CDN blocked, local URL wrong).

**Diagnose:** Check the HTML:

- `<script src="...">` — does the URL resolve? Try fetching it with
  `httpx.get(url, timeout=5)`.
- `options: { animation: false, responsive: false }` — both must be set.

**Fix:**

```javascript
options: {
  responsive: false,
  animation: false,
  // ...
}
```

And set explicit `width` / `height` on the `<canvas>`:

```html
<canvas id="chart" width="640" height="320"></canvas>
```

If both the local and CDN URLs fail, remove the chart and add a warning
to the output. Do not block the document on a missing chart.

---

## 4. The PDF file was not created

**Symptom:** `page.pdf()` returns without error, but `Path("report.pdf").exists()`
returns `False`.

**Cause:** The most common cause is a wrong working directory. Playwright
writes relative to the process CWD, not to the script's directory.

**Diagnose:**

```python
import os
from pathlib import Path

print(f"CWD: {os.getcwd()}")
print(f"Absolute output: {Path('report.pdf').resolve()}")
```

**Fix:** Use an absolute path derived from the workspace:

```python
from pathlib import Path

output_path = Path("report.pdf").resolve()
# ...
page.pdf(path=str(output_path), ...)

assert output_path.exists(), f"PDF not created at {output_path}"
```

**Never** use `/tmp/out.pdf` or `C:\...` — they break on the other OS.

---

## 5. The PDF is created but is 0 bytes or too small

**Symptom:** `report.pdf` exists, but `stat().st_size` is 0 or less than
1000 bytes. Opening it shows "cannot open" or "file is damaged".

**Cause:** `page.pdf()` was called before `page.set_content()` finished
loading. The Chromium renderer had nothing to paint.

**Diagnose:** Check the script order:

```python
page.set_content(content, wait_until="networkidle")  # must finish first
page.pdf(path=..., format="A4", print_background=True)
```

If `wait_until="domcontentloaded"` was used, switch to `"networkidle"`
so external resources (Chart.js, images) finish loading.

**Fix:**

- Use `wait_until="networkidle"` (already in `SKILL.md`).
- For a page with no external resources, `wait_until="load"` is faster
  and safe.
- Add the size assertion from `SKILL.md` after generation.

---

## 6. Images appear as broken icons or grey boxes

**Symptom:** The PDF contains a small "broken image" icon or a grey
rectangle where an image should be.

**Cause:** The `<img src="...">` path is wrong, the file does not exist,
or the format is not supported.

**Diagnose:**

```python
from pathlib import Path

image_path = Path("logo.png")
print(f"Exists: {image_path.exists()}")
print(f"Size:   {image_path.stat().st_size if image_path.exists() else 'N/A'}")
print(f"Header: {image_path.read_bytes()[:8].hex() if image_path.exists() else 'N/A'}")
```

Common signatures:

- PNG: `89504e470d0a1a0a`
- JPEG: `ffd8ff`
- GIF: `474946`
- WebP: `52494646...57454250`

If the header does not match the extension, the file is corrupted or has
the wrong extension.

**Fix:**

- Confirm the path is `file:///workspace/<name>` (forward slashes, three
  after `file:`).
- Confirm the file is in the workspace root, not in a subdirectory.
- Confirm the format is PNG, JPEG, SVG, or WebP. GIF only renders the
  first frame. BMP works but is not recommended.

---

## 7. The user provided an HTTP URL instead of a file

**Symptom:** The HTML contains `<img src="https://example.com/logo.png">`.
Sometimes it renders, sometimes it does not, depending on network state
and the remote server's CORS policy.

**Cause:** `file://` and `data:` URIs are deterministic; `http(s)://`
URIs are not. Chromium's behavior depends on the network, TLS, redirects,
and the remote server's response headers.

**Fix:** Download the image to the workspace first, then reference it
with `file://`:

```python
import httpx
from pathlib import Path

def fetch_image(url: str, dest: Path) -> Path:
    if dest.exists():
        return dest
    response = httpx.get(url, timeout=15, follow_redirects=True)
    response.raise_for_status()
    dest.write_bytes(response.content)
    return dest

logo = fetch_image("https://example.com/logo.png", Path("logo.png"))
```

Then in HTML: `<img src="file:///workspace/logo.png">`.

---

## 8. Page numbering is missing

**Symptom:** The PDF has multiple pages, but no "Page X of Y" footer.

**Cause:** CSS `@page` counters (`counter(page)`, `counter(pages)`) are
**not** rendered by Chromium. They require a `@page` margin box
(`@bottom-center { content: counter(page); }`) which Chromium does not
implement.

**Fix:** Use Playwright's built-in header/footer templates:

```python
page.pdf(
    path=str(output_path),
    format="A4",
    print_background=True,
    display_header_footer=True,
    header_template="<div></div>",
    footer_template=(
        '<div style="font-size: 9pt; text-align: center; '
        'width: 100%; color: #888;">'
        'Page <span class="pageNumber"></span> of '
        '<span class="totalPages"></span></div>'
    ),
    margin={"top": "20mm", "bottom": "25mm",
            "left": "20mm", "right": "20mm"},
)
```

The `pageNumber` and `totalPages` classes are populated by Chromium
automatically. Increase `margin.bottom` to leave room for the footer.

---

## 9. `pypdf` is not installed

**Symptom:** Verification fails with `ModuleNotFoundError: No module
named 'pypdf'`.

**Cause:** PELDRUN may ship a minimal Python environment without `pypdf`
when the operator has disabled optional verification dependencies.

**Fix:** Fall back to the size check only — never skip verification
entirely.

```python
from pathlib import Path

p = Path(output_path)
assert p.exists(), "PDF file was not created"
assert p.stat().st_size > 1000, f"PDF too small ({p.stat().st_size} bytes)"
print(f"OK: {p} ({p.stat().st_size} bytes, page count unavailable)")
```

Do not attempt `pip install pypdf` at runtime. If page counts are
essential to the user's request, report that `pypdf` is unavailable and
produce the PDF anyway (the file is still valid).

---

## 10. Playwright browser is not installed

**Symptom:** `Error: BrowserType.launch: Executable doesn't exist at
.../chrome-linux/chrome`.

**Cause:** `playwright install chromium` was not run after installing
the Python package, or the browser was removed by a container rebuild.

**Fix:** This is an operator action — the skill cannot install browsers
at runtime.

```bash
# On the operator's machine, once:
playwright install chromium
```

If the agent detects this error, it should:

1. Report the exact error message.
2. Instruct the user to run the command above in the PELDRUN environment.
3. **Not** attempt to install `chromium` or `playwright` automatically.

---

## 11. The script runs but the agent reports success with a broken PDF

**Symptom:** The agent says "PDF created" but the file does not open, or
opens with missing content.

**Cause:** Verification was skipped, or was run on a different path than
the one actually written.

**Fix:** The verification block in `SKILL.md` is mandatory. Confirm:

1. `output_path` is the same `Path` object used in `page.pdf()` and in
   the `assert` statements.
2. `Path.resolve()` was called consistently.
3. The verification ran **after** `browser.close()`, not before.

```python
# Correct order
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.set_content(content, wait_until="networkidle")
    page.pdf(path=str(output_path), format="A4", print_background=True)
    browser.close()

# Verify AFTER close
assert output_path.exists()
assert output_path.stat().st_size > 1000
```

---

## 12. The PDF works locally but fails in the workspace

**Symptom:** The same script produces a valid PDF on the developer's
laptop but fails when run by the agent in PELDRUN's workspace.

**Cause:** Three differences between local and workspace environments:

1. **Working directory** — the workspace root is different.
2. **Installed packages** — `pypdf`, `playwright`, `httpx` may be present
   locally and missing in the workspace.
3. **Chromium version** — the workspace uses PELDRUN's bundled Chromium,
   which may be older than the developer's.

**Diagnose:**

```python
import sys
from pathlib import Path

print(f"Python: {sys.version}")
print(f"CWD:    {Path.cwd()}")

for pkg in ("playwright", "pypdf", "httpx"):
    try:
        __import__(pkg)
        print(f"  {pkg}: installed")
    except ImportError:
        print(f"  {pkg}: MISSING")
```

**Fix:**

- Always use workspace-relative paths (`Path("report.pdf")`, not
  `Path.home() / "report.pdf"`).
- Check package availability before using optional features (pypdf,
  httpx).
- Test the script in the workspace before reporting success. Do not
  assume local success transfers.

---

## Escalation

If none of the above resolves the issue:

1. Re-run the script with `print_background=True` and
   `wait_until="networkidle"`.
2. Capture the last 20 lines of stdout and stderr.
3. Capture the first 200 characters of the extracted PDF text (if
   `pypdf` is available).
4. Report all three to the user with the exact error message.

Never fabricate a "success" report when the underlying file is missing
or corrupt.