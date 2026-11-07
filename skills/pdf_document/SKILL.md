---
name: pdf_document
description: Generate multilingual PDFs with Playwright + Chromium.
---

# PDF Document Generator

You create PDF files using **Playwright + Chromium only**. Both are
installed in PELDRUN. Do **not** import `reportlab`, `weasyprint`,
`fpdf`, `fpdf2`, or `pdfkit` — they either do not support non-Latin
scripts without manual font setup, or are not installed.

## Why Playwright

Chromium handles letter shaping (Arabic, Persian, Urdu), bidi reordering
(RTL), and font fallback (CJK, Cyrillic) for you. No font registration
or bidi helper needed. Write plain HTML with the correct `lang` and
`dir` attributes and Chromium does the rest.

## Before you write code

Ask the user (or infer from context) before starting:

1. **Output path** — default `<workspace>/<name>.pdf`. Never hardcode
   `/tmp/out.pdf` or any absolute path outside the workspace.
2. **Language(s)** — one or mixed (an English invoice with Arabic
   customer names is common).
3. **Structure** — title, sections, tables, images, page breaks.
4. **Orientation** — portrait (default) or landscape (wide tables).
5. **Data source** — if the user provided CSV/text/numbers, parse that
   first. **Never invent data.** If a value is missing, ask.

## Canonical script

Create `generate_pdf.py` in the workspace. This is a complete, runnable
script — do not abbreviate it.

```python
from pathlib import Path
from playwright.sync_api import sync_playwright

output_path = Path("report.pdf")

content = """
<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8">
<style>
  @page { size: A4; margin: 20mm; }
  body {
    font-family: system-ui, "Noto Sans", "Noto Sans Arabic",
                 "Noto Sans CJK", "Noto Sans Hebrew", sans-serif;
    font-size: 12pt; line-height: 1.6; color: #222;
  }
  h1 { font-size: 22pt; margin-bottom: 8mm;
       border-bottom: 2px solid #E74C3C; padding-bottom: 4mm; }
  h2 { font-size: 15pt; margin-top: 8mm; margin-bottom: 3mm; }
  table { width: 100%; border-collapse: collapse; margin-top: 6mm; }
  th, td { border: 1px solid #bbb; padding: 6px 10px; text-align: start; }
  th { background: #2E4053; color: #fff; font-weight: bold; }
  tr:nth-child(even) td { background: #f5f5f5; }
</style>
</head>
<body>
  <h1>{{TITLE}}</h1>
  <p>{{INTRO_PARAGRAPH}}</p>
  <table>
    <thead>
      <tr><th>Item</th><th>Quantity</th><th>Unit Price</th><th>Total</th></tr>
    </thead>
    <tbody>
      <tr><td>{{ITEM_1}}</td><td>{{QTY_1}}</td><td>{{PRICE_1}}</td><td>{{TOTAL_1}}</td></tr>
      <tr><td>{{ITEM_2}}</td><td>{{QTY_2}}</td><td>{{PRICE_2}}</td><td>{{TOTAL_2}}</td></tr>
    </tbody>
  </table>
</body>
</html>
"""

# Replace placeholders before rendering. The values may be in any
# language; the <html lang> and <html dir> attributes drive the layout.
# For an Arabic document, set lang="ar" dir="rtl" on <html> and provide
# the Arabic strings as replacement values.
replacements = {
    "{{TITLE}}": "Monthly Sales Report",
    "{{INTRO_PARAGRAPH}}": "Sales for Q4 2026.",
    "{{ITEM_1}}": "Widget",   "{{QTY_1}}": "10",
    "{{PRICE_1}}": "5.00",    "{{TOTAL_1}}": "50.00",
    "{{ITEM_2}}": "Gadget",   "{{QTY_2}}": "3",
    "{{PRICE_2}}": "12.50",   "{{TOTAL_2}}": "37.50",
}
for token, value in replacements.items():
    content = content.replace(token, value)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.set_content(content, wait_until="networkidle")
    page.pdf(
        path=str(output_path),
        format="A4",
        print_background=True,
        margin={"top": "20mm", "bottom": "20mm",
                "left": "20mm", "right": "20mm"},
    )
    browser.close()

print(f"OK: {output_path} ({output_path.stat().st_size} bytes)")
```

Run it with `python_execute` or via `bash`: `python generate_pdf.py`.

## Language rules

Set `lang` and `dir` on `<html>` **before** generating. Do not rely on
CSS or JavaScript to set them.

| Language family               | HTML attribute                                    |
|-------------------------------|---------------------------------------------------|
| Arabic, Hebrew, Persian, Urdu | `<html lang="ar" dir="rtl">` (or `he`/`fa`/`ur`) |
| English, Russian, European    | `<html lang="en" dir="ltr">`                      |
| Chinese                       | `<html lang="zh-CN">` or `zh-TW`                  |
| Japanese, Korean              | `<html lang="ja">` or `ko`                        |

**Never reverse Arabic strings manually.** **Never** apply a shaping
helper. **Never** insert Unicode bidi controls. Chromium does it
correctly when `dir` is set; manual reversal breaks on numbers and
mixed-script text.

For a **mixed** document, set `lang`/`dir` on the non-default section
only:

```html
<div lang="ar" dir="rtl">{{ARABIC_BLOCK}}</div>
```

## Images

Reference images with `file://` URLs relative to the workspace:

```html
<img src="file:///workspace/logo.png" style="width:40mm">
```

Verify the path exists before generating:

```python
if not Path("logo.png").exists():
    raise FileNotFoundError("logo.png not found in workspace")
```

If an image is missing, ask the user. Do **not** produce a PDF with
broken placeholders.

## Charts (Chart.js)

PELDRUN serves Chart.js at
`http://localhost:PORT/static/assets/chart.umd.js`. Use that URL first:

```html
<canvas id="chart" width="600" height="300"></canvas>
<script src="http://localhost:PORT/static/assets/chart.umd.js"></script>
<script>
new Chart(document.getElementById('chart'), {
  type: 'bar',
  data: { labels: ['Q1','Q2','Q3','Q4'],
          datasets: [{ label: 'Revenue', data: [120,190,300,250] }] },
  options: { responsive: false }
});
</script>
```

If unavailable, fall back to
`https://cdn.jsdelivr.net/npm/chart.js@4/chart.umd.js`. If both fail,
produce the PDF **without** the chart and warn the user.

## Verification (mandatory)

Always verify **before** reporting success. A claimed PDF that does not
exist is worse than a failed generation — the user believes they have a
file and does not.

```python
from pathlib import Path
from pypdf import PdfReader

p = Path(output_path)
assert p.exists(), "PDF file was not created"
assert p.stat().st_size > 1000, f"PDF too small ({p.stat().st_size} bytes)"

reader = PdfReader(str(p))
print(f"Pages: {len(reader.pages)}")
if reader.pages:
    text = reader.pages[0].extract_text() or ""
    print(f"First page chars: {len(text.strip())}")
    assert len(text.strip()) > 0, "PDF has no extractable text (possible font failure)"
```

If `pypdf` is not installed, skip the page-count check but **keep** the
size check. Never skip both.

If verification fails, do **not** report success. Report the exact
traceback.

## Output format

Return exactly this structure:

```
## Result
- File: <relative path>
- Pages: <number or "unknown">
- Size: <bytes>
- Languages: <list>

## Summary
<one or two sentences describing the content>

## Warnings
<missing fonts, broken images, omitted charts, or "none">
```

## Hard rules

1. **Use Playwright + Chromium only.** Never `reportlab`, `weasyprint`,
   `fpdf`, `fpdf2`, or `pdfkit`.
2. **Never install fonts or packages** at runtime. If a font is missing,
   report it and suggest a Noto Sans variant.
3. **Never write outside the workspace.** All output paths must be
   relative to `<workspace>`.
4. **Always run verification** before reporting success. **Never claim
   success without a file on disk that passed verification.**
5. **Never reverse or reshape text manually.**
6. **Always set `lang` and `dir` on `<html>`.** Missing `dir` on an
   Arabic document produces a left-aligned, misordered PDF.
7. **Never invent data.** If the user did not provide values, ask.
8. **Never hardcode absolute paths** like `/tmp/out.pdf`.
9. **Always use `print_background=True`** on `page.pdf()` — otherwise
   table headers and brand colors are lost.

## References

Load on demand:

- `load_reference("pdf_document", "templates.md")` — invoice, report,
  and certificate HTML templates.
- `load_reference("pdf_document", "troubleshooting.md")` — tofu squares,
  missing fonts, image paths, and page numbering.