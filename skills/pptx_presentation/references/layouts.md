# PowerPoint Layouts

Complete reference for python-pptx slide layouts, placeholder indices,
and the six most common slide patterns.

## The 9 built-in layouts

Every `.pptx` created by `Presentation()` has 9 layouts. The **indices
are stable** across themes, but the **placeholder indices vary** —
always inspect before assuming.

| Idx | Typical name                | Placeholders (indices vary)              |
|-----|-----------------------------|------------------------------------------|
| 0   | Title Slide                 | 0=title, 1=subtitle                     |
| 1   | Title and Content           | 0=title, 1=content (bullets)            |
| 2   | Section Header              | 0=title, 1=text                         |
| 3   | Two Content                 | 0=title, 1=left, 2=right                |
| 4   | Comparison                  | 0=title, 1=left hdr, 2=left body, 3=right hdr, 4=right body |
| 5   | Title Only                  | 0=title (no body — good for charts)     |
| 6   | Blank                       | none                                     |
| 7   | Content with Caption        | 0=title, 1=caption, 2=content           |
| 8   | Picture with Caption        | 0=title, 1=picture, 2=caption           |

## How to inspect a layout

Before populating placeholders, print their indices and types:

```python
from pptx import Presentation

prs = Presentation()
for idx, layout in enumerate(prs.slide_layouts):
    print(f"Layout {idx}: {layout.name}")
    for ph in layout.placeholders:
        print(f"  ph idx={ph.placeholder_format.idx} "
              f"type={ph.placeholder_format.type} "
              f"name={ph.name!r}")
```

Run this once for a given theme to learn its exact placeholder indices.

## Pattern 1: Title slide (layout 0)

The simplest pattern. Fills the title and subtitle placeholders.

```python
from pptx import Presentation
from pathlib import Path

output_path = Path("deck.pptx")
prs = Presentation()

slide = prs.slides.add_slide(prs.slide_layouts[0])
slide.shapes.title.text = "Q4 2026 Results"
slide.placeholders[1].text = "Acme Corp. — Board Meeting"
slide.placeholders[1].text_frame.paragraphs[0].alignment = 1  # center

prs.save(str(output_path))
```

**Gotchas:**

- `slide.shapes.title` is a shortcut for `slide.placeholders[0]`.
- `slide.placeholders[1]` (subtitle) exists only on layout 0 and 2.
- Some themes invert indices (title = 1, subtitle = 0). Always verify
  with `inspect_theme()`.

## Pattern 2: Bullet list (layout 1)

Populate the content placeholder with bullets. The first paragraph is
the placeholder's default — subsequent paragraphs need `add_paragraph()`.

```python
from pptx import Presentation
from pptx.util import Pt

slide = prs.slides.add_slide(prs.slide_layouts[1])
slide.shapes.title.text = "Highlights"

body = slide.placeholders[1].text_frame
body.text = "Revenue up 20%"
for bullet in ["Churn down 5%", "NPS at 45", "New market: EMEA"]:
    p = body.add_paragraph()
    p.text = bullet
    p.font.size = Pt(20)
    p.level = 0   # top-level bullet
```

**Gotchas:**

- `body.text = "..."` **overwrites** the placeholder's initial text.
  Use `body.paragraphs[0].text = ...` to modify in place.
- `p.level` 0 = top-level, 1 = sub-bullet, 2 = sub-sub. Use 0 unless
  the user explicitly asks for hierarchy.

## Pattern 3: Two-column (layout 3)

Two content areas side-by-side. Use for before/after, pros/cons,
feature comparison.

```python
slide = prs.slides.add_slide(prs.slide_layouts[3])
slide.shapes.title.text = "Before vs After"

left = slide.placeholders[1].text_frame
left.text = "Before"
left.paragraphs[0].font.bold = True
for item in ["Manual process", "6-hour cycle", "40% error rate"]:
    left.add_paragraph().text = f"• {item}"

right = slide.placeholders[2].text_frame
right.text = "After"
right.paragraphs[0].font.bold = True
for item in ["Automated", "30-minute cycle", "2% error rate"]:
    right.add_paragraph().text = f"• {item}"
```

**Gotchas:**

- Layout 3 has **3 placeholders**: 0=title, 1=left, 2=right.
- If both columns are long, the text overflows. Keep each under ~5
  bullets.
- Consider adding a vertical divider with a thin rectangle if the
  columns are visually unclear.

## Pattern 4: Comparison (layout 4)

Comparison has **5 placeholders**: title, two headers, two bodies. The
headers are visually distinct (colored band).

```python
slide = prs.slides.add_slide(prs.slide_layouts[4])
slide.shapes.title.text = "Plan Comparison"

slide.placeholders[1].text = "Free Plan"
slide.placeholders[3].text = "Pro Plan"

free_body = slide.placeholders[2].text_frame
free_body.text = "5 projects"
for item in ["1 GB storage", "Email support"]:
    free_body.add_paragraph().text = item

pro_body = slide.placeholders[4].text_frame
pro_body.text = "Unlimited projects"
for item in ["100 GB storage", "Priority support", "Custom domain"]:
    pro_body.add_paragraph().text = item
```

## Pattern 5: Chart slide (layout 5)

Layout 5 has **only the title**. Use it when the main content is a
chart or table — both are added as shapes, not as placeholder content.

```python
from pptx.chart.data import ChartData
from pptx.enum.chart import XL_CHART_TYPE
from pptx.util import Inches

slide = prs.slides.add_slide(prs.slide_layouts[5])
slide.shapes.title.text = "Revenue by Quarter"

data = ChartData()
data.categories = ["Q1", "Q2", "Q3", "Q4"]
data.add_series("2026", (120, 190, 300, 250))

slide.shapes.add_chart(
    XL_CHART_TYPE.COLUMN_CLUSTERED,
    Inches(1), Inches(1.5), Inches(8), Inches(4.5),
    data,
)
```

**Why layout 5 and not layout 1?**

- Layout 1 has a content placeholder that shows "Click to add text"
  if you don't populate it.
- Layout 5 has no content placeholder — the chart fills the empty area.
- No empty placeholder to remove.

## Pattern 6: Image slide (layout 8)

Layout 8 (Picture with Caption) has a picture placeholder. Use
`placeholder.insert_picture()` to fill it.

```python
from pathlib import Path

if not Path("hero.png").exists():
    raise FileNotFoundError("hero.png not found")

slide = prs.slides.add_slide(prs.slide_layouts[8])
slide.shapes.title.text = "Product Launch"
slide.placeholders[1].insert_picture("hero.png")
slide.placeholders[2].text = "Acme Widget, available Q1 2027"
```

**Gotchas:**

- `insert_picture()` preserves the placeholder's aspect ratio — it
  crops or letterboxes the image to fit.
- If the image is very wide or tall, the crop may hide content. Check
  the result visually.
- For a non-cropping image, use `add_picture()` on layout 5 (title
  only) and size it explicitly.

## Removing empty placeholders

If a slide has an empty placeholder (e.g. you only need the title,
not the subtitle), remove it. Otherwise PowerPoint shows "Click to
add text" when the user opens the file.

```python
from pptx import Presentation

def remove_empty_placeholders(slide):
    """Remove placeholder shapes whose text frames are empty."""
    for shape in list(slide.shapes):
        if not shape.is_placeholder:
            continue
        if shape.has_text_frame and not shape.text_frame.text.strip():
            shape.element.getparent().remove(shape.element)


# Usage
slide = prs.slides.add_slide(prs.slide_layouts[0])
slide.shapes.title.text = "Minimal Deck"
# No subtitle filled — remove the empty placeholder
remove_empty_placeholders(slide)
```

**Why this matters:**

- Empty placeholders render as "Click to add subtitle" in PowerPoint.
- Users interpret this as a broken deck.
- The fix is one function; call it on every slide before saving.

## Applying RTL to a slide

Arabic, Hebrew, Persian, or Urdu text needs **both** `alignment=RIGHT`
and `pPr.set("rtl", "1")` on every paragraph. The helper below walks
the entire slide:

```python
from pptx.enum.text import PP_ALIGN

def apply_rtl_to_slide(slide):
    """Set RTL on every paragraph in every shape on the slide."""
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        for p in shape.text_frame.paragraphs:
            p.alignment = PP_ALIGN.RIGHT
            p._p.get_or_add_pPr().set("rtl", "1")


# Usage
slide = prs.slides.add_slide(prs.slide_layouts[1])
slide.shapes.title.text = "التقرير السنوي"      # e.g. "Annual Report"
body = slide.placeholders[1].text_frame
body.text = "ارتفاع الإيرادات بنسبة 20%"        # e.g. "Revenue up 20%"
body.add_paragraph().text = "انخفاض معدل التسرّب"  # e.g. "Churn down"
apply_rtl_to_slide(slide)
```

**Gotchas:**

- The helper assumes **all** text on the slide is RTL. For mixed
  slides (English title, Arabic body), apply RTL selectively:

  ```python
  # English title — leave LTR
  slide.shapes.title.text = "Annual Report"

  # Arabic body — apply RTL
  body = slide.placeholders[1].text_frame
  for p in body.paragraphs:
      p.alignment = PP_ALIGN.RIGHT
      p._p.get_or_add_pPr().set("rtl", "1")
  ```

- For tables, walk `cell.text_frame.paragraphs` the same way.
- For charts, the axis labels and legend are not paragraphs — they
  are controlled by `chart.font.rtl`. Set
  `chart.font.rtl = True` for RTL charts.

## Speaker notes

Add presenter notes to any slide:

```python
slide.notes_slide.notes_text_frame.text = (
    "Mention that Q4 revenue grew 20% year-over-year. "
    "Close with the EMEA expansion timeline."
)
```

Notes appear in PowerPoint's Presenter View, not on the slide itself.
They are preserved across saves and round-trips.

## Common pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| "Click to add text" shows in deck | Empty placeholder not removed | `remove_empty_placeholders(slide)` |
| Bullet points on the left in RTL | `alignment` set, `rtl="1"` missing | Add `pPr.set("rtl", "1")` |
| Arabic text reversed | `bidi` controls inserted manually | Remove them; use `rtl="1"` |
| Chart empty in PowerPoint | `ChartData` missing series | `chart_data.add_series(...)` |
| Image overflows slide | No `width`/`height` on `add_picture` | `width=Inches(6)` or `height=Inches(4)` |
| Image cropped unexpectedly | `insert_picture()` crops to fit | Use `add_picture()` on layout 5 instead |
| Title missing after save | Used `slide.shapes.add_textbox` instead of `slide.shapes.title` | Access the title placeholder, not a new textbox |
| Text runs off the slide | Font too large for placeholder | Reduce `p.font.size = Pt(16)` or move to a new slide |
| RTL chart labels still LTR | `chart.font.rtl` not set | `chart.font.rtl = True` |

## Verification snippet (reusable)

Copy this into any example before the final `print`:

```python
from pptx import Presentation
from pathlib import Path

p = Path(output_path)
assert p.exists(), "PPTX was not created"
assert p.stat().st_size > 1000, f"PPTX too small ({p.stat().st_size} bytes)"

verify = Presentation(str(p))
assert len(verify.slides) >= 1, "Deck has no slides"
print(f"OK: {p} ({p.stat().st_size} bytes)")
print(f"    Slides: {len(verify.slides)}")
for i, slide in enumerate(verify.slides, start=1):
    title = slide.shapes.title.text if slide.shapes.title else "(no title)"
    print(f"    Slide {i}: {title!r}")
```