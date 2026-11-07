---
name: pptx_presentation
description: Generate PPTX presentations with python-pptx.
---

# PowerPoint Presentation Generator

You create `.pptx` decks using **python-pptx only**. It is installed in
PELDRUN. Do **not** shell out to PowerPoint COM, LibreOffice Impress
headless, `python-pptx-template`, or `markdown-pptx` — they require
external binaries or are not installed.

## Why python-pptx

`python-pptx` writes OOXML DrawingML directly and exposes the built-in
slide layouts (`slide_layouts[0..8]`) from every PowerPoint theme. Pick
a layout, populate the placeholders, and PowerPoint handles the rest.
RTL needs two settings per paragraph: right alignment and a low-level
`pPr` attribute (see "RTL rules").

## Before you write code

Ask the user (or infer from context):

1. **Output path** — default `<workspace>/<name>.pptx`.
2. **Slide count** — typically 5–15 for a deck.
3. **Flow** — title, agenda, sections, conclusion.
4. **Layout per slide** — title, title+content, image, blank.
5. **Language** — Arabic/Hebrew/Persian/Urdu needs RTL per paragraph.
6. **Data source** — parse provided data first. **Never invent data.**

## Slide layouts

Every presentation has 9 layout templates. The indices are stable
across themes:

| Index | Layout name (typical)       | Use for                                  |
|-------|-----------------------------|------------------------------------------|
| 0     | Title Slide                 | Cover with title + subtitle              |
| 1     | Title and Content           | Bullet list (most common)                |
| 2     | Section Header              | Section divider                          |
| 3     | Two Content                 | Side-by-side content                     |
| 4     | Comparison                  | Left + right with headers                |
| 5     | Title Only                  | Title + custom content (chart, table)    |
| 6     | Blank                       | Full custom (rarely needed)              |
| 7     | Content with Caption        | Image with caption below                 |
| 8     | Picture with Caption        | Full image + caption                     |

**Rules of thumb:**

- **Slide 1:** layout 0 (title slide)
- **Content slides:** layout 1 (title + bullet list)
- **Chart/table slides:** layout 5 (title only) — then add the chart
  or table manually
- **Image slides:** layout 8 (picture with caption)
- **Avoid layout 6 (blank)** unless you position every shape by hand

## Canonical script

Create `generate_pptx.py` in the workspace. Complete, runnable.

```python
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

output_path = Path("deck.pptx")
prs = Presentation()

# --- Slide 1: Title ---
slide = prs.slides.add_slide(prs.slide_layouts[0])
slide.shapes.title.text = "Q4 Results"
slide.placeholders[1].text = "PELDRUN Inc. — November 2026"

# --- Slide 2: Bullet list ---
slide = prs.slides.add_slide(prs.slide_layouts[1])
slide.shapes.title.text = "Highlights"

body = slide.placeholders[1].text_frame
body.text = "Revenue up 20%"              # first bullet
for text in ["Churn down 5%", "NPS at 45", "New market: EMEA"]:
    p = body.add_paragraph()
    p.text = text
    p.font.size = Pt(20)

# --- Slide 3: Chart (layout 5 — title only) ---
from pptx.chart.data import ChartData
from pptx.enum.chart import XL_CHART_TYPE

slide = prs.slides.add_slide(prs.slide_layouts[5])
slide.shapes.title.text = "Revenue by Quarter"

chart_data = ChartData()
chart_data.categories = ["Q1", "Q2", "Q3", "Q4"]
chart_data.add_series("Revenue", (120, 190, 300, 250))

x, y, cx, cy = Inches(1), Inches(1.5), Inches(8), Inches(4.5)
chart = slide.shapes.add_chart(
    XL_CHART_TYPE.COLUMN_CLUSTERED,
    x, y, cx, cy, chart_data
).chart
chart.has_title = True
chart.chart_title.text_frame.text = "Quarterly Revenue (USD thousands)"

prs.save(str(output_path))
print(f"OK: {output_path} ({output_path.stat().st_size} bytes)")
```

Run it with `python_execute` or via `bash`: `python generate_pptx.py`.

## RTL rules (critical)

For Arabic, Hebrew, Persian, or Urdu, every paragraph needs **two**
settings:

```python
from pptx.enum.text import PP_ALIGN

p = text_frame.add_paragraph()   # or text_frame.paragraphs[0]
p.text = rtl_text
p.alignment = PP_ALIGN.RIGHT     # right-align the paragraph

# Low-level XML: set rtl="1" on the paragraph properties.
pPr = p._p.get_or_add_pPr()
pPr.set("rtl", "1")
```

- `alignment = PP_ALIGN.RIGHT` sets `algn="r"`.
- `pPr.set("rtl", "1")` flips bullet position, numbering, and mixed runs.
- **Only `alignment`**: bullets stay left, English words misordered.
- **Only `rtl="1"`**: right-aligned but bullets may still be off.

**Never reverse Arabic characters, insert bidi controls, or manually
reorder punctuation.** PowerPoint applies bidi layout when `rtl="1"`.

For **mixed slides** (English title, Arabic body), apply RTL
per-paragraph, not per-text-frame:

```python
title_p = slide.shapes.title.text_frame.paragraphs[0]
# leave title LTR

for line in arabic_lines:
    p = body.add_paragraph()
    p.text = line
    p.alignment = PP_ALIGN.RIGHT
    p._p.get_or_add_pPr().set("rtl", "1")
```

## Tables

```python
rows, cols = 4, 3
left, top, width, height = Inches(1), Inches(2), Inches(8), Inches(3)
table_shape = slide.shapes.add_table(rows, cols, left, top, width, height)
table = table_shape.table

# Headers
for i, label in enumerate(["Item", "Qty", "Total"]):
    table.cell(0, i).text = label

# Data
data = [("Widget", "10", "$50"), ("Gadget", "3", "$37.50")]
for r, (item, qty, total) in enumerate(data, start=1):
    table.cell(r, 0).text = item
    table.cell(r, 1).text = qty
    table.cell(r, 2).text = total
```

For **RTL tables**, set `rtl="1"` on each cell's paragraph:

```python
for row in table.rows:
    for cell in row.cells:
        for p in cell.text_frame.paragraphs:
            p.alignment = PP_ALIGN.RIGHT
            p._p.get_or_add_pPr().set("rtl", "1")
```

## Images

```python
from pptx.util import Inches
from pathlib import Path

if not Path("logo.png").exists():
    raise FileNotFoundError("logo.png not found in workspace")

slide.shapes.add_picture(
    "logo.png",
    left=Inches(1), top=Inches(1),
    width=Inches(3)   # height auto-scales to preserve aspect ratio
)
```

- Supported formats: PNG, JPEG, GIF (first frame), BMP, TIFF.
- **SVG is not supported.** Convert to PNG first.
- Always pass `width` **or** `height` (not both, unless you want to
  stretch). Omitting both uses native size, which often overflows.

## Charts

python-pptx has native chart support. The chart is a real PowerPoint
chart — editable when the user opens the deck.

```python
from pptx.chart.data import ChartData
from pptx.enum.chart import XL_CHART_TYPE
from pptx.util import Inches

chart_data = ChartData()
chart_data.categories = ["Q1", "Q2", "Q3", "Q4"]
chart_data.add_series("2025", (120, 190, 300, 250))
chart_data.add_series("2026", (150, 220, 340, 280))

chart = slide.shapes.add_chart(
    XL_CHART_TYPE.COLUMN_CLUSTERED,
    Inches(1), Inches(1.5), Inches(8), Inches(4.5),
    chart_data,
).chart
```

Available types: `COLUMN_CLUSTERED`, `COLUMN_STACKED`, `BAR_CLUSTERED`,
`LINE`, `LINE_MARKERS`, `PIE`, `DOUGHNUT`, `AREA`, `SCATTER`.

Charts render **immediately** in PowerPoint — no "wait for Excel"
delay. python-pptx embeds the data, so PowerPoint displays it on open.

## Speaker notes

Add speaker notes below each slide:

```python
slide.notes_slide.notes_text_frame.text = (
    "Mention that Q4 revenue grew 20% year-over-year."
)
```

Notes are visible in PowerPoint's Presenter View, not on the slide.
Use them for the script the presenter should say.

## Verification (mandatory)

Always verify **before** reporting success.

```python
from pathlib import Path
from pptx import Presentation

p = Path(output_path)
assert p.exists(), "PPTX file was not created"
assert p.stat().st_size > 1000, f"PPTX too small ({p.stat().st_size} bytes)"

verify = Presentation(str(p))
print(f"Slides: {len(verify.slides)}")
assert len(verify.slides) >= 1, "Presentation has no slides"

for i, slide in enumerate(verify.slides, start=1):
    title_shape = slide.shapes.title
    title = title_shape.text if title_shape else "(no title)"
    print(f"  Slide {i}: {title!r}")
```

If verification fails, do **not** report success. Report the exact
traceback.

Re-opening catches malformed OOXML from a crashed save.

## Output format

Return exactly this structure:

```
## Result
- File: <relative path>
- Slides: <number>
- Size: <bytes>
- Layouts used: <list of layout indices>
- RTL: <yes/no>

## Summary
<one or two sentences describing the deck>

## Warnings
<missing images, empty placeholders, or "none">
```

## Hard rules

1. **Use python-pptx only.** Never PowerPoint COM, LibreOffice, or
   `markdown-pptx`.
2. **Never install packages** at runtime.
3. **Never write outside the workspace.**
4. **Always run verification** before reporting success. Re-open the
   file with `Presentation()`.
5. **RTL: set BOTH `alignment = PP_ALIGN.RIGHT` AND
   `pPr.set("rtl", "1")`** on every Arabic/Hebrew/Persian/Urdu
   paragraph. One without the other produces wrong bullet position or
   reversed punctuation.
6. **Never reverse characters or insert bidi controls manually.**
7. **Use built-in layouts** (`slide_layouts[0..8]`) rather than blank
   slides with manual shapes, unless the user explicitly asks for a
   custom design.
8. **Never leave placeholders empty.** If a slide has an empty
   placeholder, either populate it or remove the shape.
9. **Always pass `width` (or `height`) to `add_picture`.** Without it,
   images overflow the slide.
10. **Never claim success without a file on disk that opened
    successfully.**

## References

Load on demand:

- `load_reference("pptx_presentation", "layouts.md")` — all 9 layouts
  with placeholder indices, plus 5 ready-to-use slide patterns (title,
  bullet, image, chart, two-column comparison).