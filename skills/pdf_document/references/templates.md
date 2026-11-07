# PDF Templates

Ready-to-use HTML templates for the three most common PDF documents:
invoices, reports, and certificates.

**These are HTML snippets, not Python.** Copy the relevant template into
the `content` variable of `generate_pdf.py` (see SKILL.md), replace the
`{{TOKEN}}` placeholders with actual values, and run.

## Conventions used in every template

- **Page size:** A4 (portrait for invoice/report, landscape for certificate)
- **Font stack:** `system-ui, "Noto Sans", "Noto Sans Arabic", ...`
  — matches SKILL.md; do not change it.
- **Print background:** templates assume `print_background=True` in
  `page.pdf()` (Hard rule #9 in SKILL.md).
- **Placeholders:** `{{UPPER_SNAKE_CASE}}` — replace every one.
- **Language:** templates ship with `lang="en" dir="ltr"`. To produce an
  Arabic/Hebrew document, change `<html>` to `lang="ar" dir="rtl"` and
  provide the placeholder values in that language. Do not reverse text
  manually (see SKILL.md "Language rules").

---

## 1. Invoice

Full-page invoice with logo, bill-to/ship-to, line items, totals, and
footer. `text-align: start` and `margin-inline-start` respect `dir`, so
the layout mirrors automatically for RTL languages.

```html
<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8">
<style>
  @page { size: A4; margin: 20mm; }
  body { font-family: system-ui, "Noto Sans", "Noto Sans Arabic",
                     sans-serif; font-size: 11pt; color: #222;
         line-height: 1.5; }
  .header { display: flex; justify-content: space-between;
            align-items: flex-start; border-bottom: 2px solid #E74C3C;
            padding-bottom: 6mm; margin-bottom: 8mm; }
  .header img { width: 40mm; height: auto; }
  .header .doc-title { text-align: end; }
  .header .doc-title h1 { font-size: 24pt; margin: 0; color: #E74C3C; }
  .header .doc-title .meta { font-size: 10pt; color: #666; margin-top: 2mm; }
  .parties { display: flex; justify-content: space-between; margin-bottom: 8mm; }
  .parties .block { width: 45%; }
  .parties h3 { font-size: 11pt; color: #666; margin: 0 0 2mm;
                text-transform: uppercase; letter-spacing: 0.5pt; }
  .parties p { margin: 0; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 6mm; }
  th, td { border: 1px solid #ccc; padding: 3mm; text-align: start; }
  th { background: #2E4053; color: #fff; font-weight: bold; }
  tr:nth-child(even) td { background: #f5f5f5; }
  td.num { text-align: end; font-variant-numeric: tabular-nums; }
  .totals { width: 60%; margin-inline-start: auto; }
  .totals td { padding: 2mm 3mm; border: none; }
  .totals tr.total td { font-weight: bold; font-size: 13pt;
                        border-top: 2px solid #2E4053; }
  .footer { position: fixed; bottom: 10mm; left: 20mm; right: 20mm;
            text-align: center; font-size: 9pt; color: #888;
            border-top: 1px solid #ddd; padding-top: 2mm; }
</style>
</head>
<body>
  <div class="header">
    <img src="file:///workspace/logo.png" alt="Logo">
    <div class="doc-title">
      <h1>INVOICE</h1>
      <div class="meta">
        <div>No. {{INVOICE_NUMBER}}</div>
        <div>Date: {{INVOICE_DATE}}</div>
        <div>Due: {{DUE_DATE}}</div>
      </div>
    </div>
  </div>

  <div class="parties">
    <div class="block">
      <h3>From</h3>
      <p><strong>{{COMPANY_NAME}}</strong></p>
      <p>{{COMPANY_ADDRESS}}</p>
      <p>{{COMPANY_EMAIL}}</p>
    </div>
    <div class="block">
      <h3>Bill To</h3>
      <p><strong>{{CUSTOMER_NAME}}</strong></p>
      <p>{{CUSTOMER_ADDRESS}}</p>
      <p>{{CUSTOMER_EMAIL}}</p>
    </div>
  </div>

  <table>
    <thead>
      <tr>
        <th style="width: 5%;">#</th>
        <th style="width: 45%;">Description</th>
        <th style="width: 10%;">Qty</th>
        <th style="width: 20%;">Unit Price</th>
        <th style="width: 20%;">Total</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>1</td>
        <td>{{ITEM_1_DESC}}</td>
        <td class="num">{{ITEM_1_QTY}}</td>
        <td class="num">{{ITEM_1_PRICE}}</td>
        <td class="num">{{ITEM_1_TOTAL}}</td>
      </tr>
      <tr>
        <td>2</td>
        <td>{{ITEM_2_DESC}}</td>
        <td class="num">{{ITEM_2_QTY}}</td>
        <td class="num">{{ITEM_2_PRICE}}</td>
        <td class="num">{{ITEM_2_TOTAL}}</td>
      </tr>
    </tbody>
  </table>

  <table class="totals">
    <tr><td>Subtotal</td><td class="num">{{SUBTOTAL}}</td></tr>
    <tr><td>Tax ({{TAX_RATE}}%)</td><td class="num">{{TAX_AMOUNT}}</td></tr>
    <tr class="total"><td>Total</td><td class="num">{{TOTAL}}</td></tr>
  </table>

  <div class="footer">
    {{FOOTER_TEXT}} &mdash; Thank you for your business.
  </div>
</body>
</html>
```

### Usage notes

- Add or remove `<tr>` blocks in `<tbody>` to match the number of items.
- For currency, use the user's locale format consistently (`$1,234.56`,
  `1.234,56 SAR`, `EUR 1 234,56`). Never mix formats within one document.
- Round monetary values to 2 decimal places.
- For Arabic/Hebrew: change `<html>` to `lang="ar" dir="rtl"` and set
  `{{COMPANY_NAME}}`, etc. to the translated values.

---

## 2. Business Report

Multi-section report with a cover page, executive summary, a results
table, and a recommendations list. Uses `page-break-after: always` on the
cover to start the body on page 2.

```html
<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8">
<style>
  @page { size: A4; margin: 20mm; }
  body { font-family: system-ui, "Noto Sans", sans-serif;
         font-size: 11pt; color: #222; line-height: 1.6; }
  .cover { height: 250mm; display: flex; flex-direction: column;
           justify-content: center; align-items: center;
           text-align: center; page-break-after: always; }
  .cover h1 { font-size: 32pt; color: #2E4053; margin: 0; }
  .cover .subtitle { font-size: 16pt; color: #666; margin-top: 5mm; }
  .cover .meta { font-size: 11pt; color: #999; margin-top: 30mm;
                 line-height: 2; }
  h2 { font-size: 16pt; color: #2E4053; border-bottom: 2px solid #E74C3C;
       padding-bottom: 2mm; margin-top: 10mm; page-break-after: avoid; }
  p { margin: 2mm 0; }
  table { width: 100%; border-collapse: collapse; margin: 4mm 0; }
  th, td { border: 1px solid #ccc; padding: 2mm 3mm; text-align: start; }
  th { background: #2E4053; color: #fff; }
  tr:nth-child(even) td { background: #f5f5f5; }
  .callout { border-inline-start: 4px solid #E74C3C;
             background: #fef5f4; padding: 3mm 4mm; margin: 4mm 0; }
  .page-break { page-break-before: always; }
</style>
</head>
<body>

<div class="cover">
  <h1>{{REPORT_TITLE}}</h1>
  <div class="subtitle">{{REPORT_SUBTITLE}}</div>
  <div class="meta">
    <div>Prepared for: {{CLIENT_NAME}}</div>
    <div>Date: {{REPORT_DATE}}</div>
    <div>Author: {{AUTHOR_NAME}}</div>
  </div>
</div>

<h2>Executive Summary</h2>
<p>{{SUMMARY_PARAGRAPH}}</p>

<div class="callout">
  <strong>Key finding:</strong> {{KEY_FINDING}}
</div>

<h2>Methodology</h2>
<p>{{METHODOLOGY_PARAGRAPH}}</p>

<h2>Results</h2>
<table>
  <thead>
    <tr><th>Metric</th><th>Value</th><th>Change</th></tr>
  </thead>
  <tbody>
    <tr><td>{{METRIC_1_NAME}}</td><td>{{METRIC_1_VALUE}}</td><td>{{METRIC_1_CHANGE}}</td></tr>
    <tr><td>{{METRIC_2_NAME}}</td><td>{{METRIC_2_VALUE}}</td><td>{{METRIC_2_CHANGE}}</td></tr>
    <tr><td>{{METRIC_3_NAME}}</td><td>{{METRIC_3_VALUE}}</td><td>{{METRIC_3_CHANGE}}</td></tr>
  </tbody>
</table>

<h2>Recommendations</h2>
<ol>
  <li>{{RECOMMENDATION_1}}</li>
  <li>{{RECOMMENDATION_2}}</li>
  <li>{{RECOMMENDATION_3}}</li>
</ol>

</body>
</html>
```

### Usage notes

- Insert `<h2>...</h2>` sections in the body; the page breaks are
  automatic when content overflows.
- Use `<div class="page-break"></div>` to force a page break before a
  specific section.
- For long reports, add a table of contents page after the cover, using
  `page-break-after: always`.

---

## 3. Certificate

Landscape A4 certificate with double border, recipient name, award
description, and two signatures plus a seal. Fixed-height container keeps
the layout centered regardless of text length.

```html
<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8">
<style>
  @page { size: A4 landscape; margin: 15mm; }
  body { font-family: "Georgia", "Times New Roman", serif;
         margin: 0; padding: 0; }
  .cert { border: 8px double #2E4053; padding: 25mm 20mm;
          text-align: center; height: 170mm;
          display: flex; flex-direction: column;
          justify-content: space-between; background: #fefefe; }
  .cert h1 { font-size: 36pt; color: #2E4053; margin: 0;
             letter-spacing: 2pt; }
  .cert .subtitle { font-size: 14pt; color: #666;
                    font-style: italic; margin: 4mm 0; }
  .cert .awarded-to { font-size: 11pt; color: #999;
                      text-transform: uppercase; letter-spacing: 3pt;
                      margin-top: 15mm; }
  .cert .recipient { font-size: 28pt; color: #E74C3C;
                     font-style: italic; margin: 4mm 0;
                     border-bottom: 1px solid #ccc; padding-bottom: 4mm;
                     display: inline-block; min-width: 100mm; }
  .cert .description { font-size: 13pt; color: #444;
                       margin: 10mm auto; max-width: 180mm; }
  .cert .footer { display: flex; justify-content: space-around;
                  margin-top: auto; padding-top: 10mm; }
  .cert .signature { border-top: 1px solid #333; padding-top: 2mm;
                     width: 60mm; font-size: 10pt; color: #666; }
  .cert .seal { width: 30mm; height: 30mm; border-radius: 50%;
                background: #E74C3C; color: #fff;
                display: flex; align-items: center;
                justify-content: center;
                font-size: 10pt; font-weight: bold; }
</style>
</head>
<body>
  <div class="cert">
    <div>
      <h1>CERTIFICATE</h1>
      <div class="subtitle">of Achievement</div>
    </div>

    <div>
      <div class="awarded-to">This certificate is awarded to</div>
      <div class="recipient">{{RECIPIENT_NAME}}</div>
      <div class="description">{{AWARD_DESCRIPTION}}</div>
    </div>

    <div class="footer">
      <div class="signature">
        {{SIGNER_NAME}}<br>{{SIGNER_TITLE}}
      </div>
      <div class="seal">SEAL</div>
      <div class="signature">
        {{ISSUER_NAME}}<br>Date: {{ISSUE_DATE}}
      </div>
    </div>
  </div>
</body>
</html>
```

### Usage notes

- The seal is a red circle with the text "SEAL". Replace with
  `<img src="file:///workspace/seal.png">` for a real seal image.
- For a background image, add
  `<img src="file:///workspace/certificate_bg.png" style="position:fixed; top:0; left:0; width:100%; height:100%; z-index:-1; opacity:0.1;">` before `<div class="cert">`.
- For Arabic certificates: change `<html>` to `lang="ar" dir="rtl"` and
  the border/layout will mirror automatically.

---

## 4. Image patterns

The following snippets show how to embed images correctly. All reference
files with `file:///workspace/<filename>` — never an absolute path, never
an HTTP URL directly (download first, see 4.4).

### 4.1 Logo in header

```html
<div style="text-align: center; margin-bottom: 10mm;">
  <img src="file:///workspace/company_logo.png"
       style="width: 40mm; height: auto;">
</div>
```

`height: auto` preserves the aspect ratio. Never set both `width` and
`height` unless you want to crop or stretch.

### 4.2 Image in a table cell

```html
<table>
  <tr>
    <td>
      <img src="file:///workspace/product_1.jpg"
           style="width: 30mm; height: auto;">
    </td>
    <td>{{PRODUCT_NAME}}</td>
    <td>{{PRODUCT_PRICE}}</td>
  </tr>
</table>
```

Images inside table cells can make rows taller than expected. Test with
one row first, then add the rest.

### 4.3 Full-page background

```html
<style>
  .background {
    position: fixed; top: 0; left: 0;
    width: 100%; height: 100%;
    z-index: -1;
    opacity: 0.15;
  }
</style>
<img src="file:///workspace/background.png" class="background">
```

`position: fixed` repeats the image on every page. `z-index: -1` places
it behind all content. `opacity` keeps text readable — 0.10–0.20 is the
usual range.

### 4.4 Remote image (download first)

Never use an `http://` or `https://` URL in `<img src>` directly. The
network may fail, or the remote server may block headless Chromium.
Download the image to the workspace first:

```python
import httpx
from pathlib import Path

def fetch_image(url: str, dest: Path) -> Path:
    """Download an image to the workspace. Skip if already present."""
    if dest.exists():
        return dest
    response = httpx.get(url, timeout=15, follow_redirects=True)
    response.raise_for_status()
    dest.write_bytes(response.content)
    return dest

logo = fetch_image(
    "https://example.com/logo.png",
    Path("logo.png")
)
# Then in HTML: <img src="file:///workspace/logo.png">
```

### 4.5 Supported formats

| Format | Chromium support | Notes |
|--------|------------------|-------|
| PNG    | Full             | Best for logos, screenshots, transparency |
| JPEG   | Full             | Best for photographs |
| SVG    | Full             | Must have `viewBox`; no external `<use>` |
| WebP   | Full             | Modern format, good compression |
| GIF    | First frame only | Animation not rendered in PDF |
| BMP    | Full             | Legacy format; prefer PNG |

### 4.6 Size recommendations

| Purpose              | Recommended width |
|----------------------|-------------------|
| Logo in header       | 30–50 mm          |
| Product photo        | 30–40 mm          |
| Full-page background | 210 mm (A4 width) |
| Inline icon          | 5–10 mm           |
| Chart (Canvas)       | 170 mm (A4 inner width) |

---

## 5. Chart embedding (Chart.js)

Chart.js renders on a `<canvas>` element. Always set explicit `width` and
`height` attributes AND `options: { responsive: false }` — Playwright's
page has no viewport, so responsive charts produce unpredictable sizes.

```html
<div style="width: 170mm; margin: 6mm auto;">
  <canvas id="revenue_chart" width="640" height="320"></canvas>
</div>

<script src="http://localhost:PORT/static/assets/chart.umd.js"></script>
<script>
new Chart(document.getElementById('revenue_chart'), {
  type: 'bar',
  data: {
    labels: ['Q1', 'Q2', 'Q3', 'Q4'],
    datasets: [{
      label: 'Revenue (thousands)',
      data: [120, 190, 300, 250],
      backgroundColor: '#E74C3C',
      borderColor: '#C0392B',
      borderWidth: 1
    }]
  },
  options: {
    responsive: false,
    animation: false,
    plugins: {
      title: {
        display: true,
        text: 'Quarterly Revenue',
        font: { size: 16 }
      },
      legend: { position: 'bottom' }
    },
    scales: {
      y: { beginAtZero: true, title: { display: true, text: 'USD (k)' } }
    }
  }
});
</script>
```

### Chart types

| Type       | Best for                         |
|------------|----------------------------------|
| `bar`      | Comparing categories over time   |
| `line`     | Trends and continuous data       |
| `pie`      | Proportions (5 slices or fewer)  |
| `doughnut` | Proportions, donut variant       |
| `radar`    | Multi-dimensional comparison     |
| `scatter`  | Correlation between two metrics  |

### Critical settings

- **`animation: false`** — required. With animation on, Chromium may
  print the canvas before the chart finishes drawing, producing a blank
  chart.
- **`responsive: false`** — required. Playwright has no viewport; the
  chart would use the default canvas size or fail to lay out.
- **Explicit `width` / `height`** on `<canvas>` — 640×320 is a good
  default. Scale to 2x the intended display size for crisp rendering.
- **`backgroundColor`** — pick a brand color. `#E74C3C` is the PDF skill
  brand color. For a multi-series chart, use a palette
  (`['#E74C3C', '#3498DB', '#2ECC71', '#F39C12', '#9B59B6']`).

### Fallback if Chart.js is unavailable

If neither the local URL nor the CDN loads, produce the PDF **without**
the chart and add a warning to the output. Do not block the entire
document on chart rendering.

```python
try:
    page.set_content(content, wait_until="networkidle")
except Exception as exc:
    content = content.replace("<script src=", "<!-- skipped: ")
    content = content.replace("</script>", " --></script>")
    page.set_content(content, wait_until="networkidle")
    print(f"WARNING: chart omitted ({exc})")
```

---

## Combining templates

A single PDF can include any combination:

- Page 1: Invoice
- Page 2: Report cover
- Pages 3–N: Report body
- Page N+1: Certificate

Concatenate the HTML strings with `<div style="page-break-before: always;">` between sections:

```python
content = invoice_html + \
          '<div style="page-break-before: always;"></div>' + \
          report_html
```

For very large documents (> 50 pages), consider generating each section
as a separate PDF and merging with `pypdf.PdfWriter`, to avoid keeping
gigabytes of HTML strings in memory.