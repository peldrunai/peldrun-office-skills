---
name: xlsx_spreadsheet
description: Generate XLSX spreadsheets with openpyxl.
---

# Excel Spreadsheet Generator

You create `.xlsx` files using **openpyxl only**. It is installed in
PELDRUN. Do **not** use `pandas.to_excel`, `xlsxwriter`, `xlwt`, or
Excel COM automation — `pandas` hides the styling API, `xlsxwriter`
is not installed, and COM only works on Windows with Excel installed.

## Why openpyxl

openpyxl writes the OOXML format directly and exposes the full styling
API: fonts, fills, borders, number formats, merged cells, conditional
formatting, and charts. It stores cell values as Unicode strings or
numbers, so any language survives round-trip without font setup.

**openpyxl does not calculate formulas.** It writes them as strings
(e.g. `=SUM(B2:B10)`) and Excel/LibreOffice calculate them when the
user opens the file. If you need a computed value visible in the
workbook, either (a) compute it in Python and write the result as a
literal, or (b) write the formula and accept that the cell shows `0`
until the file is opened in Excel.

## Before you write code

Ask the user (or infer from context):

1. **Output path** — default `<workspace>/<name>.xlsx`.
2. **Number of sheets** — usually one; sometimes summary + data.
3. **Headers** — column labels, and whether the first row is frozen.
4. **Data source** — parse provided CSV/text/numbers first.
   **Never invent data.**
5. **Formulas** — totals, lookups, conditions? If yes, note that they
   will not be calculated until the file is opened in Excel.
6. **RTL** — Arabic, Hebrew, Persian, or Urdu needs
   `ws.sheet_view.rightToLeft = True`.

## Canonical script

Create `generate_xlsx.py` in the workspace. Complete, runnable.

```python
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

output_path = Path("report.xlsx")
wb = Workbook()
ws = wb.active
ws.title = "Sales"

# --- Headers ---
ws.append(["Item", "Qty", "Price", "Total"])

header_font = Font(bold=True, color="FFFFFF")
header_fill = PatternFill("solid", fgColor="217346")  # Excel green
center = Alignment(horizontal="center", vertical="center")
thin = Side(border_style="thin", color="CCCCCC")
border = Border(left=thin, right=thin, top=thin, bottom=thin)

for cell in ws[1]:
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = center
    cell.border = border

# --- Data rows ---
rows_data = [
    ("Widget", 10, 5.00),
    ("Gadget", 3, 12.50),
    ("Doohickey", 7, 3.75),
]
for i, (item, qty, price) in enumerate(rows_data, start=2):
    ws.cell(i, 1, item)
    ws.cell(i, 2, qty)
    ws.cell(i, 3, price)
    ws.cell(i, 4, f"=B{i}*C{i}")   # formula
    for col in range(1, 5):
        ws.cell(i, col).border = border

# --- Total row ---
total_row = len(rows_data) + 2
ws.cell(total_row, 3, "Total").font = Font(bold=True)
ws.cell(total_row, 4, f"=SUM(D2:D{total_row - 1})").font = Font(bold=True)

# --- Column widths ---
for col_letter, width in {"A": 20, "B": 8, "C": 10, "D": 12}.items():
    ws.column_dimensions[col_letter].width = width

# --- Number format for prices ---
for row in range(2, total_row + 1):
    ws.cell(row, 3).number_format = "#,##0.00"
    ws.cell(row, 4).number_format = "#,##0.00"

# --- Freeze the header ---
ws.freeze_panes = "A2"

wb.save(str(output_path))
print(f"OK: {output_path} ({output_path.stat().st_size} bytes)")
```

Run it with `python_execute` or via `bash`: `python generate_xlsx.py`.

## Formulas (critical)

openpyxl writes formulas as strings. Excel calculates them on open.

- ✅ `ws.cell(2, 4, "=B2*C2")` — writes the formula
- ❌ `ws.cell(2, 4).value` — reads back `"=B2*C2"`, not `50`
- ❌ `assert ws.cell(2, 4).value == 50` — fails

If the user asks "what is the total", compute it in Python:

```python
total = sum(qty * price for _, qty, price in rows_data)
ws.cell(total_row, 4, total)   # write the number
```

If the user asks for a formula they can edit in Excel, write the
formula string and tell them the cell will show a value only after
Excel recalculates. **Never claim a formula "worked" without
verification.**

## RTL rules

For Arabic, Hebrew, Persian, or Urdu sheets, set right-to-left mode
on the **worksheet**, not on individual cells:

```python
ws.sheet_view.rightToLeft = True
```

This flips column order visually (column A appears on the right) and
right-aligns all cells. Do **not** set `Alignment(horizontal="right")`
on every cell — the sheet-level flag handles it.

For mixed workbooks (English summary + Arabic data), set `rightToLeft`
per sheet:

```python
ws_summary.sheet_view.rightToLeft = False
ws_data.sheet_view.rightToLeft = True
```

**Never reverse Arabic strings or insert bidi controls manually.**
Excel renders Unicode correctly with `rightToLeft = True`.

## Styling summary

| Purpose        | API                                                 |
|----------------|-----------------------------------------------------|
| Bold header    | `Font(bold=True, color="FFFFFF")`                   |
| Background     | `PatternFill("solid", fgColor="217346")`            |
| Center         | `Alignment(horizontal="center", vertical="center")` |
| Border         | `Border(left=Side(...), ...)`                       |
| Number format  | `cell.number_format = "#,##0.00"`                   |
| Column width   | `ws.column_dimensions["A"].width = 20`              |
| Row height     | `ws.row_dimensions[1].height = 25`                  |
| Merge cells    | `ws.merge_cells("A1:D1")`                           |
| Freeze header  | `ws.freeze_panes = "A2"`                            |

## Charts

openpyxl embeds charts natively — no external library needed:

```python
from openpyxl.chart import BarChart, Reference

chart = BarChart()
chart.title = "Sales by Item"
chart.x_axis.title = "Item"
chart.y_axis.title = "Total"

data = Reference(ws, min_col=4, min_row=1, max_row=total_row - 1)
categories = Reference(ws, min_col=1, min_row=2, max_row=total_row - 1)
chart.add_data(data, titles_from_data=True)
chart.set_categories(categories)

ws.add_chart(chart, "F2")
```

Charts appear when the user opens the file in Excel/LibreOffice. They
do **not** render inside openpyxl (there is no canvas).

## Verification (mandatory)

Always verify **before** reporting success.

```python
from pathlib import Path
from openpyxl import load_workbook

p = Path(output_path)
assert p.exists(), "XLSX file was not created"
assert p.stat().st_size > 1000, f"XLSX too small ({p.stat().st_size} bytes)"

wb_check = load_workbook(str(p))
ws_check = wb_check.active
print(f"Sheets: {wb_check.sheetnames}")
print(f"Max row: {ws_check.max_row}, Max col: {ws_check.max_column}")
assert ws_check.max_row >= 2, "Workbook has no data rows"
```

If verification fails, do **not** report success. Report the exact
traceback.

**Important:** `load_workbook` reads formulas as strings, not values.
Do not assert on computed values unless you wrote them as literals.

## Output format

Return exactly this structure:

```
## Result
- File: <relative path>
- Sheets: <list of sheet names>
- Rows: <max row per sheet>
- Size: <bytes>
- RTL: <yes/no>

## Summary
<one or two sentences describing the content>

## Warnings
<formulas not calculated until opened, images missing, or "none">
```

The **Warnings** field must mention "formulas not calculated until
opened" if the workbook contains any formula cells.

## Hard rules

1. **Use openpyxl only.** Never `pandas.to_excel`, `xlsxwriter`, or
   Excel COM.
2. **Never install packages** at runtime.
3. **Never write outside the workspace.**
4. **Always run verification** before reporting success.
5. **Never claim a formula "worked".** openpyxl does not calculate.
   State clearly that the file must be opened in Excel to see values.
6. **RTL: set `ws.sheet_view.rightToLeft = True`** on the worksheet.
   Do not set alignment per cell.
7. **Never reverse characters or insert bidi controls manually.**
8. **Always set `number_format`** for numeric columns; otherwise large
   numbers display in scientific notation (`1.23E+05`).
9. **Always set column widths** explicitly; openpyxl defaults to very
   narrow columns that truncate content.
10. **Never hardcode absolute paths.**

## References

Load on demand:

- `load_reference("xlsx_spreadsheet", "formulas.md")` — 20 common
  formulas (SUM, SUMIF, VLOOKUP, INDEX/MATCH, IF, COUNTIF, TEXT,
  DATE) with openpyxl syntax.
- `load_reference("xlsx_spreadsheet", "examples.md")` — full examples:
  multi-sheet workbook, RTL inventory sheet, conditional formatting,
  embedded images, and charts.