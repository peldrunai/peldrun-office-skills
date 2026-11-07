# DOCX Examples

Five complete, runnable examples that go beyond the base template in
`SKILL.md`. Each example is self-contained: copy the code block into
`generate_docx.py`, replace the placeholder data, run.

Every example follows the same conventions:

- **Output path** is a workspace-relative `Path("...")`.
- **Verification** runs at the end and opens the file with `Document()`.
- **Data** is hard-coded for demonstration; replace with real values.
- **No absolute paths, no external binaries.**

---

## 1. RTL Contract (Arabic)

A complete Arabic contract with title, body paragraphs, a signature
block, and correct RTL alignment on every paragraph.

The critical pattern: **every Arabic paragraph needs BOTH
`alignment = RIGHT` AND `run.font.rtl = True`.** Setting only one
produces wrong-margin text or reversed punctuation.

```python
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

output_path = Path("contract_ar.docx")
doc = Document()

# --- Page setup ---
section = doc.sections[0]
section.page_width, section.page_height = Cm(21.0), Cm(29.7)
section.top_margin = section.bottom_margin = Cm(2.5)
section.left_margin = section.right_margin = Cm(2.5)


def add_rtl_paragraph(doc, text, bold=False, size=12):
    """Add a paragraph with correct RTL alignment and run flag."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.bold = bold
    run.font.rtl = True   # <-- critical: RTL run flag
    return p


# --- Title ---
add_rtl_paragraph(doc, "عقد اتفاقية خدمات", bold=True, size=18)

# --- Preamble ---
add_rtl_paragraph(
    doc,
    "تم إبرام هذا العقد في يوم ... بين الطرفين المذكورين أدناه.",
)

# --- Section 1 ---
add_rtl_paragraph(doc, "المادة الأولى: التعريفات", bold=True, size=14)
add_rtl_paragraph(
    doc,
    "يقصد بالمصطلحات الواردة في هذا العقد المعاني المبينة قرين كل منها.",
)

# --- Section 2 ---
add_rtl_paragraph(doc, "المادة الثانية: نطاق العمل", bold=True, size=14)
add_rtl_paragraph(
    doc,
    "يلتزم الطرف الثاني بتقديم الخدمات الموضحة في الملحق (أ).",
)

# --- Signature block ---
doc.add_paragraph()  # spacer
doc.add_paragraph()
add_rtl_paragraph(doc, "توقيع الطرف الأول: ____________________")
add_rtl_paragraph(doc, "توقيع الطرف الثاني: ____________________")
add_rtl_paragraph(doc, "التاريخ: ____ / ____ / 20____")

# --- Save & verify ---
doc.save(str(output_path))

from docx import Document as Doc
verify = Doc(str(output_path))
print(f"OK: {output_path} ({output_path.stat().st_size} bytes)")
print(f"    Paragraphs: {len(verify.paragraphs)}")
```

### What to watch for

- **Numbers inside Arabic text**: if you see `2024/11/08` displayed as
  `08/11/2024` in a Word viewer, this is a bidi rendering choice by
  Word, not a bug in the document. The characters are stored correctly.
  See example 5 for forcing a specific order.
- **Punctuation at line end**: if a period appears at the *start* of the
  line in Arabic, `run.font.rtl = True` is missing.
- **Mixed Arabic + English**: English words inside an Arabic paragraph
  should render LTR automatically. If they appear reversed, `rtl = True`
  is on the wrong run.

---

## 2. Mixed-Language Report

An English title with an Arabic executive summary and English body
sections. Demonstrates per-paragraph RTL — not global RTL.

```python
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

output_path = Path("mixed_report.docx")
doc = Document()


def add_ltr_heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = RGBColor(0x2B, 0x57, 0x9A)  # brand color
    return h


def add_ltr_paragraph(doc, text):
    p = doc.add_paragraph(text)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    return p


def add_rtl_paragraph(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run(text)
    run.font.rtl = True
    return p


# --- English cover ---
title = doc.add_heading("Quarterly Business Review", level=0)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
add_ltr_paragraph(doc, "Prepared for: Acme Corp.")
add_ltr_paragraph(doc, "Date: 2026-11-08")

doc.add_paragraph()

# --- Arabic executive summary ---
add_ltr_heading(doc, "Executive Summary (Arabic)", level=1)
add_rtl_paragraph(
    doc,
    "حقق الفريق نموًا بنسبة 20% في الإيرادات خلال الربع الثالث، "
    "مع انخفاض معدل التسرّب إلى 5%.",
)
add_rtl_paragraph(
    doc,
    "نوصي بالتركيز على الأسواق الجديدة في الربع القادم.",
)

# --- English body ---
add_ltr_heading(doc, "Key Metrics", level=1)
add_ltr_paragraph(doc, "Revenue: $1.2M (up 20%)")
add_ltr_paragraph(doc, "Churn: 5% (down from 10%)")
add_ltr_paragraph(doc, "NPS: 45")

# --- English recommendations ---
add_ltr_heading(doc, "Recommendations", level=1)
for item in [
    "Expand into the EMEA region.",
    "Hire two senior engineers.",
    "Launch the new pricing tier in Q1.",
]:
    doc.add_paragraph(item, style="List Bullet")

doc.save(str(output_path))

from docx import Document as Doc
verify = Doc(str(output_path))
print(f"OK: {output_path} ({output_path.stat().st_size} bytes)")
```

### What to watch for

- **Do not** set `doc.styles["Normal"].paragraph_format.alignment`
  globally. That forces every paragraph in the document to share an
  alignment, which is wrong for mixed-language documents.
- **Do not** set `doc.styles["Normal"].font.rtl = True`. Same reason —
  it applies to runs that don't contain RTL text.
- Set alignment and RTL **per paragraph**, as the helper functions do.

---

## 3. Header / Footer with Page Numbers

Adds a header with the document title and a footer with a "Page X of Y"
pattern. python-docx cannot insert the auto-updating field directly, so
we use a low-level `w:fldSimple` element via `OxmlElement`.

```python
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

output_path = Path("report_paginated.docx")
doc = Document()


def add_page_number_field(paragraph):
    """Insert a 'Page X of Y' field into a paragraph.

    python-docx has no high-level API for fields; the low-level
    OxmlElement approach is the canonical workaround.
    """
    # "Page "
    run = paragraph.add_run("Page ")
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

    # PAGE field
    fld_simple = OxmlElement("w:fldSimple")
    fld_simple.set(qn("w:instr"), "PAGE")
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = "1"  # placeholder; Word updates it on open
    r.append(t)
    fld_simple.append(r)
    paragraph._p.append(fld_simple)

    # " of "
    run_of = paragraph.add_run(" of ")
    run_of.font.size = Pt(9)
    run_of.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

    # NUMPAGES field
    fld_simple2 = OxmlElement("w:fldSimple")
    fld_simple2.set(qn("w:instr"), "NUMPAGES")
    r2 = OxmlElement("w:r")
    t2 = OxmlElement("w:t")
    t2.text = "1"
    r2.append(t2)
    fld_simple2.append(r2)
    paragraph._p.append(fld_simple2)


# --- Header ---
header_p = doc.sections[0].header.paragraphs[0]
header_p.text = "Acme Corp. — Confidential"
header_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
for run in header_p.runs:
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

# --- Footer ---
footer_p = doc.sections[0].footer.paragraphs[0]
footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
add_page_number_field(footer_p)

# --- Content (a few pages worth) ---
doc.add_heading("Section 1", level=1)
doc.add_paragraph("Content for section 1." * 50)

doc.add_page_break()

doc.add_heading("Section 2", level=1)
doc.add_paragraph("Content for section 2." * 50)

doc.add_page_break()

doc.add_heading("Section 3", level=1)
doc.add_paragraph("Content for section 3." * 50)

doc.save(str(output_path))

from docx import Document as Doc
verify = Doc(str(output_path))
print(f"OK: {output_path} ({output_path.stat().st_size} bytes)")
print("Open in Word or LibreOffice to see the page numbers update.")
```

### What to watch for

- **The "1" placeholder is replaced when Word opens the file.** If you
  read the document with python-docx again, you'll see "1" — that's
  expected. The field updates on open.
- **`NUMPAGES` requires Word/LibreOffice to compute.** Some lightweight
  viewers (e.g. Google Docs) handle it differently. For a strictly static
  page count, hard-code the total after generation.
- **Header font**: modify `header_p.runs` — the `.text =` shortcut
  creates a single run with default formatting.

---

## 4. RTL Table (Arabic)

A table with right-aligned Arabic headers and cells, correct column
order (rightmost = first column in the document flow), and bidi runs.

```python
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

output_path = Path("table_ar.docx")
doc = Document()


def rtl_cell(cell, text, bold=False, size=11):
    """Populate a cell with RTL-aligned, RTL-flagged text."""
    cell.text = ""  # clear the default empty paragraph
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.bold = bold
    run.font.rtl = True


# --- Title ---
title = doc.add_paragraph("جدول المبيعات الفصلية")
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
title_run = title.runs[0]
title_run.font.size = Pt(16)
title_run.bold = True
title_run.font.rtl = True

# --- Table ---
table = doc.add_table(rows=1, cols=4)
table.style = "Light Grid Accent 1"
table.alignment = WD_TABLE_ALIGNMENT.CENTER

# Headers (rightmost column is index 0 in RTL flow when the whole
# document is RTL, but python-docx stores columns left-to-right.
# Put the "first" logical column in the rightmost cell for visual RTL.)
headers = ["المنتج", "الكمية", "السعر", "الإجمالي"]
for i, label in enumerate(headers):
    rtl_cell(table.rows[0].cells[i], label, bold=True)

# Data rows
rows_data = [
    ("قطعة أ", "10", "50.00", "500.00"),
    ("قطعة ب", "3", "120.00", "360.00"),
    ("قطعة ج", "5", "75.00", "375.00"),
]
for row_data in rows_data:
    cells = table.add_row().cells
    for i, value in enumerate(row_data):
        rtl_cell(cells[i], value)

# --- Total row ---
total_cells = table.add_row().cells
rtl_cell(total_cells[0], "الإجمالي", bold=True)
rtl_cell(total_cells[1], "", bold=True)
rtl_cell(total_cells[2], "", bold=True)
rtl_cell(total_cells[3], "1,235.00", bold=True)

doc.save(str(output_path))

from docx import Document as Doc
verify = Doc(str(output_path))
print(f"OK: {output_path} ({output_path.stat().st_size} bytes)")
print(f"    Tables: {len(verify.tables)}")
```

### What to watch for

- **Column order**: python-docx stores columns left-to-right
  (`cells[0]` is leftmost). For an Arabic table, you have two choices:
  1. Put the "first" logical column (المنتج) in the **leftmost** cell
     and accept that the table reads left-to-right. This is what many
     Arabic documents do for tabular data.
  2. Set `table._tbl.get_or_add_tblPr()` with `<w:bidiVisual/>` so Word
     flips the column order visually. Advanced — see example 5.
- **Cell alignment**: setting `cell.text = ""` then adding a paragraph
  is required because the default cell paragraph has an empty run that
  would confuse `p.runs[0]` access.

---

## 5. `w:bidi` workaround (numbers and punctuation)

**When to use this:** the user reports that numbers or punctuation
appear in the *wrong position* inside Arabic text even though
`run.font.rtl = True` is set — e.g. `(20%)` renders as `(%20)` or a
trailing period appears at the start of the line.

**Why it happens:** Word applies two independent bidi passes — one at
the paragraph level (`w:bidi`), one at the run level (`w:rtl`).
`run.font.rtl = True` covers the run pass. The paragraph pass needs a
low-level XML flag that python-docx does not expose.

**The workaround:** set `<w:bidi/>` on the paragraph properties via
`OxmlElement`.

```python
from pathlib import Path
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

output_path = Path("rtl_strict.docx")
doc = Document()


def add_strict_rtl_paragraph(doc, text):
    """RTL paragraph with both run-level rtl and paragraph-level bidi."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run(text)
    run.font.rtl = True

    # Paragraph-level bidi flag (the w:bidi element).
    pPr = p._p.get_or_add_pPr()
    bidi = OxmlElement("w:bidi")
    pPr.append(bidi)

    return p


# Arabic text with parentheses and numbers inside:
add_strict_rtl_paragraph(
    doc,
    "بلغت نسبة النمو (20%) خلال الربع الأول من عام 2026.",
)
add_strict_rtl_paragraph(
    doc,
    "سجّل النظام 1,500 طلب جديد، بزيادة 35% عن الفترة السابقة.",
)
add_strict_rtl_paragraph(
    doc,
    "انخفض معدل التسرّب إلى 5% (من 10% في العام الماضي).",
)

doc.save(str(output_path))

from docx import Document as Doc
verify = Doc(str(output_path))
print(f"OK: {output_path} ({output_path.stat().st_size} bytes)")
```

### When you actually need this

- **Try `run.font.rtl = True` first.** In 90% of cases it is enough.
- **Reach for `w:bidi`** only when the user explicitly reports
  punctuation or number-position problems that `rtl=True` did not fix.
- **Do not** apply `w:bidi` to every paragraph unconditionally — it
  makes mixed-language paragraphs (Arabic + English in one paragraph)
  render the English chunk in the wrong order.

### Interaction with example 1

Example 1 (the contract) works correctly with `run.font.rtl` alone
because the contract has no mixed-script numbers inside running text.
Example 5 is for documents that mix Arabic with numerals, currency
symbols, or parenthesized percentages.

---

## Common pitfalls across all examples

| Symptom | Cause | Fix |
|---|---|---|
| Arabic appears left-aligned | `alignment` not set | `p.alignment = WD_ALIGN_PARAGRAPH.RIGHT` |
| Arabic appears right-aligned but punctuation reversed | `run.font.rtl` missing | add `run.font.rtl = True` on every run |
| Numbers reorder inside Arabic text | paragraph-level `w:bidi` missing | see example 5 |
| Header text not visible | header style inherits white font from a theme | set `run.font.color.rgb` explicitly |
| Page numbers stuck at "1" | field not refreshed | open in Word/LibreOffice; or accept static |
| Table columns reversed | RTL expected but python-docx stores LTR | set `table` bidi via `w:bidiVisual`, or reorder manually |
| Image overflows page | no `width` on `add_picture` | `width=Cm(4)` always |

## Verification snippet (reusable)

Copy this into any example before the final `print`:

```python
from docx import Document as Doc
from pathlib import Path

p = Path(output_path)
assert p.exists(), "DOCX file was not created"
assert p.stat().st_size > 1000, f"DOCX too small ({p.stat().st_size} bytes)"
verify = Doc(str(p))
print(f"OK: {p} ({p.stat().st_size} bytes)")
print(f"    Paragraphs: {len(verify.paragraphs)}")
print(f"    Tables:     {len(verify.tables)}")
```