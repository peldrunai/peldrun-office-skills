---
name: markdown_doc
description: Convert Markdown to styled PDF or HTML with RTL support.
---

# Markdown Document Converter

You convert `.md` files to PDF (or HTML) using **markdown-it + Playwright
only**. Both are installed in PELDRUN. Do **not** use `pandoc`,
`mdpdf`, `weasyprint`, or `md-to-pdf` — they either require external
binaries or are not installed.

## Why markdown-it + Playwright

`markdown-it` parses CommonMark and GFM (tables, task lists,
strikethrough) into clean HTML. Playwright renders it to PDF using
Chromium — the same engine as `pdf_document`, so RTL and font fallback
work identically.

Debug by saving the intermediate HTML and opening it in a browser
first: if the PDF looks wrong, the issue is in the HTML/CSS, not in
Playwright.

## Before you write code

Ask the user (or infer from context):

1. **Input** — path to a `.md` file in the workspace, or a Markdown
   string the user provided inline.
2. **Output** — `<name>.pdf` (default) or `<name>.html`.
3. **Language** — English, Arabic, Hebrew, or mixed. RTL is detected
   automatically from the first heading or first paragraph (see "RTL
   auto-detection").
4. **CSS** — use the default typography (see below) or a custom
   `<style>` block / `.css` file.
5. **Features** — code highlighting, table of contents, page numbers,
   footnotes. Any feature not requested is omitted for speed.

**Never invent content.** Convert what the user provided, nothing more.

## Canonical script

Create `convert_md.py` in the workspace. Complete, runnable.

```python
from pathlib import Path
from markdown_it import MarkdownIt
from playwright.sync_api import sync_playwright

input_path = Path("README.md")
output_path = Path("README.pdf")

md = MarkdownIt("commonmark", {"html": True, "linkify": True})
md.enable("table")           # GFM tables
md.enable("strikethrough")   # GFM strikethrough
md.enable("tasklist")        # GFM checkboxes

md_text = input_path.read_text(encoding="utf-8")
html_body = md.render(md_text)

# Detect RTL from the first heading or paragraph with content.
def detect_rtl(text: str) -> bool:
    rtl_ranges = (
        (0x0600, 0x06FF),  # Arabic
        (0x0590, 0x05FF),  # Hebrew
        (0xFB1D, 0xFB4F),  # Hebrew presentation
        (0xFB50, 0xFDFF),  # Arabic presentation A
        (0xFE70, 0xFEFF),  # Arabic presentation B
    )
    for ch in text:
        code = ord(ch)
        for lo, hi in rtl_ranges:
            if lo <= code <= hi:
                return True
    return False

is_rtl = detect_rtl(md_text)
lang = "ar" if is_rtl else "en"
direction = "rtl" if is_rtl else "ltr"

default_css = """
  @page { size: A4; margin: 20mm; }
  body {
    font-family: system-ui, "Noto Sans", "Noto Sans Arabic",
                 "Noto Sans CJK", sans-serif;
    font-size: 11pt; line-height: 1.7; color: #222;
    max-width: 100%; margin: 0 auto;
  }
  h1, h2, h3 { color: #2E4053; margin-top: 1.5em; }
  h1 { font-size: 24pt; border-bottom: 2px solid #6C5CE7;
       padding-bottom: 6px; }
  h2 { font-size: 18pt; border-bottom: 1px solid #ddd;
       padding-bottom: 4px; }
  h3 { font-size: 14pt; }
  p  { margin: 0.6em 0; }
  a  { color: #6C5CE7; text-decoration: none; }
  code {
    background: #f5f5f5; padding: 2px 5px; border-radius: 3px;
    font-family: "Fira Code", "Consolas", "Courier New", monospace;
    font-size: 0.9em;
  }
  pre {
    background: #282c34; color: #abb2bf; padding: 12px 16px;
    border-radius: 6px; overflow-x: auto; line-height: 1.4;
    font-family: "Fira Code", "Consolas", "Courier New", monospace;
    font-size: 0.85em;
  }
  pre code { background: transparent; padding: 0; color: inherit; }
  table {
    width: 100%; border-collapse: collapse; margin: 1em 0;
  }
  th, td { border: 1px solid #ccc; padding: 6px 10px;
           text-align: start; }
  th { background: #2E4053; color: #fff; font-weight: bold; }
  tr:nth-child(even) td { background: #fafafa; }
  blockquote {
    border-inline-start: 4px solid #6C5CE7; margin: 1em 0;
    padding: 0.5em 1em; color: #555; background: #faf8ff;
  }
  hr { border: none; border-top: 1px solid #ddd; margin: 2em 0; }
  ul, ol { padding-inline-start: 1.5em; }
  li { margin: 0.3em 0; }
  img { max-width: 100%; height: auto; }
"""

html = f"""<!DOCTYPE html>
<html lang="{lang}" dir="{direction}">
<head>
<meta charset="utf-8">
<title>{input_path.stem}</title>
<style>{default_css}</style>
</head>
<body>
{html_body}
</body>
</html>
"""

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.set_content(html, wait_until="networkidle")
    page.pdf(
        path=str(output_path),
        format="A4",
        print_background=True,
        margin={"top": "20mm", "bottom": "20mm",
                "left": "20mm", "right": "20mm"},
    )
    browser.close()

print(f"OK: {output_path} ({output_path.stat().st_size} bytes)")
print(f"RTL: {is_rtl} (lang={lang}, dir={direction})")
```

Run it with `python_execute` or via `bash`: `python convert_md.py`.

## GFM features

`markdown-it` in `commonmark` mode supports the base spec. Enable GFM
extensions explicitly:

```python
md = MarkdownIt("commonmark", {"html": True, "linkify": True})
md.enable("table")          # | a | b | tables
md.enable("strikethrough")  # ~~text~~
md.enable("tasklist")       # - [x] done / - [ ] todo
```

**Disabled by default** in `commonmark` mode — you must enable each
one. If a table renders as plain text in the PDF, you forgot
`md.enable("table")`.

## Code highlighting

The default CSS gives code blocks a dark theme (`#282c34` background,
monospace font). It does **not** color individual tokens — that
requires a highlighter library.
```python
try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name
    from pygments.formatters import HtmlFormatter

    def highlight_code(code, lang, attrs):
        try:
            return highlight(code, get_lexer_by_name(lang), HtmlFormatter())
        except Exception:
            return None

    md.options["highlight"] = highlight_code
except ImportError:
    pass   # plain code blocks only
```

If Pygments is unavailable, **do not block the conversion** — plain
code blocks with the dark theme are fine.

## RTL auto-detection

The script scans the Markdown source for Unicode code points in the
RTL ranges and sets `dir="rtl"` + `lang="ar"` (or `he`) automatically.
This handles:

- Arabic (0x0600–0x06FF)
- Hebrew (0x0590–0x05FF)
- Arabic/Hebrew presentation forms

**Limitations:**

- A Markdown file with a single Arabic word in an English document
  triggers global RTL. For mixed documents, set `dir` manually:

  ```python
  direction = "ltr"   # force LTR
  ```

- The detection scans the entire file, not per-block. For paragraph-
  level RTL, wrap the Arabic block in
  `<div dir="rtl">{{ARABIC}}</div>` in the Markdown source (markdown-it
  passes raw HTML through when `"html": True`).

**Never reverse Arabic strings manually.** Chromium handles bidi
reordering when `dir` is set.

## Custom CSS

If the user provides a `.css` file or an inline `<style>` block, append
it **after** `default_css`:

```python
custom_css = ""
if Path("custom.css").exists():
    custom_css = Path("custom.css").read_text(encoding="utf-8")

html = f"""<!DOCTYPE html>
<html lang="{lang}" dir="{direction}">
<head>
<style>{default_css}\n{custom_css}</style>
</head>
<body>{html_body}</body>
</html>
"""
```

CSS cascade: later rules override earlier ones. The user's CSS wins
over the defaults, which is what they expect.

**Do not** replace `default_css` entirely — it provides `@page` sizing
and print margins that Chromium needs. Always append.

## HTML output (when requested)

If the user asks for `.html` instead of `.pdf`, skip Playwright and
write the HTML directly:

```python
if output_path.suffix == ".html":
    output_path.write_text(html, encoding="utf-8")
else:
    # ... Playwright path
```

HTML output is 10–50× faster than PDF (no Chromium launch). Use it
when the user will paste the result into a CMS or email.

## Verification (mandatory)

Always verify **before** reporting success.

```python
from pathlib import Path

p = Path(output_path)
assert p.exists(), f"{p.suffix[1:].upper()} file was not created"
assert p.stat().st_size > 500, f"File too small ({p.stat().st_size} bytes)"

if p.suffix == ".pdf":
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(p))
        print(f"Pages: {len(reader.pages)}")
        text = reader.pages[0].extract_text() or ""
        assert len(text.strip()) > 0, "PDF has no extractable text"
    except ImportError:
        print("pypdf not installed; skipping page count")
```

If verification fails, do **not** report success. Report the exact
traceback.

## Output format

Return exactly this structure:

```
## Result
- File: <relative path>
- Format: <pdf | html>
- Pages: <number or "unknown">
- Size: <bytes>
- RTL: <yes/no (lang)>

## Summary
<one or two sentences describing the content>

## Warnings
<missing Pygments, RTL forced, broken images, or "none">
```

## Hard rules

1. **Use markdown-it + Playwright only.** Never `pandoc`, `mdpdf`,
   `weasyprint`, or `md-to-pdf`.
2. **Never install packages** at runtime. If Pygments is missing, fall
   back to plain code blocks.
3. **Never write outside the workspace.**
4. **Always run verification** before reporting success.
5. **Enable GFM features explicitly:** `md.enable("table")`,
   `md.enable("strikethrough")`, `md.enable("tasklist")`. They are off
   by default in commonmark mode.
6. **Always set `lang` and `dir`** on `<html>`. Auto-detect RTL, but
   allow manual override.
7. **Never reverse or reshape text manually.**
8. **Append custom CSS, never replace `default_css`** — the defaults
   include `@page` sizing that Chromium needs.
9. **Always use `print_background=True`** — otherwise code blocks lose
   their dark background.
10. **Never invent content.** Convert only what the user provided.