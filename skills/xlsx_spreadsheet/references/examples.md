# XLSX Examples

Five complete, runnable examples that go beyond the base template in
`SKILL.md`. Each example is self-contained: copy the code block into
`generate_xlsx.py`, replace the placeholder data, run.

Every example follows the same conventions:

- **Output path** is a workspace-relative `Path("...")`.
- **Verification** runs at the end and re-opens the file with
  `load_workbook()`.
- **Data** is hard-coded for demonstration; replace with real values.
- **No absolute paths, no external binaries.**

Reminder: **openpyxl does not calculate formulas.** Formulas appear as
values only after the user opens the file in Excel or LibreOffice. See
`formulas.md` for the full implications.

---

## 1. Multi-Sheet Budget (VLOOKUP)

Two sheets: `Categories` (lookup table) and `Expenses` (transaction log).
Each expense looks up its category name via `=VLOOKUP`.

```python
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

output_path = Path("budget.xlsx")
wb = Workbook()

# ============================================================
# Sheet 1: Categories (the lookup table)
# ============================================================
ws_cat = wb.active
ws_cat.title = "Categories"
ws_cat.append(["ID", "Name", "Monthly Budget"])

categories = [
    ("C01", "Salaries",   50000),
    ("C02", "Marketing",  15000),
    ("C03", "Operations", 20000),
    ("C04", "Software",    5000),
]
for cat_id, name, budget in categories:
    ws_cat.append([cat_id, name, budget])

# Style the header
header_fill = PatternFill("solid", fgColor="217346")
header_font = Font(bold=True, color="FFFFFF")
for cell in ws_cat[1]:
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = Alignment(horizontal="center")

# Currency format
for row in range(2, len(categories) + 2):
    ws_cat.cell(row, 3).number_format = '$#,##0.00'

# Column widths
ws_cat.column_dimensions["A"].width = 8
ws_cat.column_dimensions["B"].width = 20
ws_cat.column_dimensions["C"].width = 18

# ============================================================
# Sheet 2: Expenses (the transaction log)
# ============================================================
ws_exp = wb.create_sheet("Expenses")
ws_exp.append(["Date", "Category ID", "Category Name",
               "Description", "Amount"])

expenses = [
    ("2026-11-01", "C01", "November payroll",       42500),
    ("2026-11-03", "C02", "Ad campaign",             8500),
    ("2026-11-05", "C03", "Office supplies",         1200),
    ("2026-11-07", "C04", "Licenses",                3500),
    ("2026-11-08", "C02", "Trade show booth",        5000),
]

for i, (date, cat_id, desc, amount) in enumerate(expenses, start=2):
    ws_exp.cell(i, 1, date)
    ws_exp.cell(i, 2, cat_id)
    # VLOOKUP: find cat_id in Categories!A:B, return column 2 (Name)
    ws_exp.cell(i, 3,
        f"=VLOOKUP(B{i}, Categories!$A$2:$B$5, 2, FALSE)")
    ws_exp.cell(i, 4, desc)
    ws_exp.cell(i, 5, amount)
    ws_exp.cell(i, 5).number_format = '$#,##0.00'

# Style headers
for cell in ws_exp[1]:
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = Alignment(horizontal="center")

# Total row
total_row = len(expenses) + 2
ws_exp.cell(total_row, 4, "Total").font = Font(bold=True)
ws_exp.cell(total_row, 5, f"=SUM(E2:E{total_row - 1})").font = Font(bold=True)
ws_exp.cell(total_row, 5).number_format = '$#,##0.00'

# Column widths
widths = {"A": 12, "B": 12, "C": 18, "D": 25, "E": 12}
for col, w in widths.items():
    ws_exp.column_dimensions[col].width = w

# Freeze header row
ws_exp.freeze_panes = "A2"

# ============================================================
# Save & verify
# ============================================================
wb.save(str(output_path))

from openpyxl import load_workbook
verify = load_workbook(str(output_path))
print(f"OK: {output_path} ({output_path.stat().st_size} bytes)")
print(f"    Sheets: {verify.sheetnames}")

# Verify the VLOOKUP formula string is present (not the computed value)
ws_check = verify["Expenses"]
assert ws_check["C2"].value.startswith("=VLOOKUP"), \
    f"Expected VLOOKUP formula, got {ws_check['C2'].value!r}"
print(f"    VLOOKUP formula verified (C2): {ws_check['C2'].value}")
```

### What to watch for

- **`FALSE` (exact match)** is required. `TRUE` (default) does
  approximate match and silently returns wrong categories.
- **Table range must be absolute** (`$A$2:$B$5`). Without `$`, dragging
  the formula down breaks the reference.
- **Column index is 1-based.** `2` = second column of the table range.
  Column A of `Categories` is 1, column B is 2.
- **The lookup key must be the first column of the range.** Here it is
  (`Categories!A` = `ID`). If you needed to look up by `Name` (column
  B), VLOOKUP would fail — use `INDEX/MATCH` instead (see
  `formulas.md`).

---

## 2. RTL Arabic Inventory (Conditional Formatting)

A right-to-left worksheet with Arabic headers and a conditional
highlight for low stock. Uses `ws.sheet_view.rightToLeft = True` (the
worksheet-level flag) and `CellIsRule` (the openpyxl conditional
formatting API).

```python
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.formatting.rule import CellIsRule, ColorScaleRule

output_path = Path("inventory_ar.xlsx")
wb = Workbook()
ws = wb.active
ws.title = "Inventory"

# === RTL mode (the critical setting) ===
ws.sheet_view.rightToLeft = True

# === Arabic content (the user provides actual Arabic strings) ===
# For this example, we use English text so the file opens cleanly
# in any viewer. Replace these with Arabic strings in production.
headers = ["Product ID", "Product Name", "Quantity", "Min Stock", "Status"]
for col, header in enumerate(headers, start=1):
    cell = ws.cell(1, col, header)
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="217346")
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.font = Font(bold=True, color="FFFFFF", rtl=False)

data = [
    ("P001", "Item A", 120,  50),
    ("P002", "Item B",  30,  50),   # below min -> highlight
    ("P003", "Item C", 200, 100),
    ("P004", "Item D",  15,  25),   # below min -> highlight
    ("P005", "Item E",  80,  50),
]

for i, (pid, name, qty, min_stock) in enumerate(data, start=2):
    ws.cell(i, 1, pid)
    ws.cell(i, 2, name)
    ws.cell(i, 3, qty)
    ws.cell(i, 4, min_stock)
    # Status formula: "Low" if qty < min, else "OK"
    ws.cell(i, 5, f'=IF(C{i}<D{i}, "Low", "OK")')

# === Conditional formatting: red fill where qty < min ===
# A CellIsRule applies when a cell meets a comparison.
red_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE",
                        fill_type="solid")
red_font = Font(color="9C0006", bold=True)

ws.conditional_formatting.add(
    f"C2:C{len(data) + 1}",
    CellIsRule(
        operator="lessThan",
        formula=[f"D2"],   # relative to each row
        fill=red_fill,
        font=red_font,
    ),
)

# === Column widths (RTL means A appears on the right) ===
widths = {"A": 12, "B": 20, "C": 10, "D": 10, "E": 10}
for col, w in widths.items():
    ws.column_dimensions[col].width = w

# === Freeze header ===
ws.freeze_panes = "A2"

# === Save & verify ===
wb.save(str(output_path))

from openpyxl import load_workbook
verify = load_workbook(str(output_path))
ws_check = verify.active
print(f"OK: {output_path} ({output_path.stat().st_size} bytes)")
print(f"    RTL: {ws_check.sheet_view.rightToLeft}")
assert ws_check.sheet_view.rightToLeft is True, "RTL flag was not persisted"
print(f"    Rows: {ws_check.max_row}, Cols: {ws_check.max_column}")
```

### What to watch for

- **`rightToLeft = True` is a worksheet-level flag**, not a cell-level
  property. Do not set `Alignment(horizontal="right")` on every cell —
  the worksheet flag handles alignment automatically.
- **Conditional formatting formula uses relative references.**
  `formula=["D2"]` in the range `C2:C6` means "compare each cell in C
  to the cell in D on the same row". Do **not** write `$D$2` unless you
  want every row compared to D2.
- **Verify the flag persisted**: `load_workbook` returns the saved file;
  the assertion catches a silent failure where openpyxl dropped the
  flag.
- **Arabic strings**: the example uses English to keep the file
  readable in every editor. In production, replace `"Item A"` with
  `"قطعة أ"` (or whatever the user provides) — the code is identical.

---

## 3. Product Catalog with Embedded Images

Embeds product images in cells. openpyxl supports `.png` and `.jpg`.
Images are anchored to a cell and float over the grid.

```python
from pathlib import Path
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

output_path = Path("catalog.xlsx")
wb = Workbook()
ws = wb.active
ws.title = "Products"

# === Headers ===
headers = ["Image", "SKU", "Product Name", "Price", "In Stock"]
for col, header in enumerate(headers, start=1):
    cell = ws.cell(1, col, header)
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="217346")
    cell.alignment = Alignment(horizontal="center")

# === Row height (taller rows for images) ===
ws.row_dimensions[1].height = 20
for r in range(2, 5):
    ws.row_dimensions[r].height = 60   # 60 points ~= 22mm

# === Product data (no images in columns — images are anchored) ===
products = [
    ("SKU-001", "Widget",     9.99,  "Yes"),
    ("SKU-002", "Gadget",    24.99,  "Yes"),
    ("SKU-003", "Doohickey",  4.99,  "No"),
]

for i, (sku, name, price, stock) in enumerate(products, start=2):
    ws.cell(i, 2, sku)
    ws.cell(i, 3, name)
    ws.cell(i, 4, price).number_format = '$#,##0.00'
    ws.cell(i, 5, stock)
    # Column A (index 1) is reserved for the image — leave empty.

# === Column widths ===
widths = {"A": 14, "B": 12, "C": 25, "D": 10, "E": 10}
for col, w in widths.items():
    ws.column_dimensions[col].width = w

# === Embed images (only if the files exist) ===
# In production, the user provides product photos in the workspace.
image_paths = [
    ("product_1.png", "A2"),
    ("product_2.png", "A3"),
    ("product_3.png", "A4"),
]

for img_file, anchor in image_paths:
    if not Path(img_file).exists():
        print(f"WARNING: {img_file} not found, skipping")
        continue
    img = XLImage(img_file)
    # Resize to fit a 50px-wide cell (~37 px is close to one column)
    img.width = 50
    img.height = 50
    ws.add_image(img, anchor)   # anchor is a cell reference string

# === Save & verify ===
wb.save(str(output_path))

from openpyxl import load_workbook
verify = load_workbook(str(output_path))
print(f"OK: {output_path} ({output_path.stat().st_size} bytes)")
print(f"    Images: {len(verify.active._images)}")
```

### What to watch for

- **Images are not values.** You cannot read them back with
  `ws.cell(2, 1).value` — they live in `ws._images`.
- **Anchor is a cell reference string** (`"A2"`), not a coordinate
  tuple. openpyxl accepts both, but the string form is unambiguous.
- **`img.width` / `img.height` are in pixels**, not millimeters. Excel
  internally converts at 96 DPI. A 50×50 image in a 60-point row fits
  with some margin.
- **PNG and JPEG only.** openpyxl does not accept SVG, WebP, or GIF.
  Convert first.
- **Row height** must be tall enough to fit the image. Default row
  height is ~15 points; a 50-pixel image needs ~38 points minimum.
- **`XlImage` scales the image**, it does not crop. Aspect ratio may
  be distorted if you set width and height independently. Compute
  them from the original aspect ratio to avoid stretching.

---

## 4. Sales Report with Charts (Bar + Line)

A single sheet with a data table and two charts (bar for quarterly
revenue, line for growth trend). openpyxl embeds the chart definitions;
Excel renders them on open.

```python
from pathlib import Path
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Font, PatternFill, Alignment

output_path = Path("sales_chart.xlsx")
wb = Workbook()
ws = wb.active
ws.title = "Sales"

# === Data ===
ws.append(["Quarter", "Revenue", "Growth %"])
data = [
    ("Q1",  120000,  0.0),
    ("Q2",  190000,  0.583),
    ("Q3",  300000,  0.579),
    ("Q4",  250000, -0.167),
]
for row in data:
    ws.append(row)

# Style header
for cell in ws[1]:
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="217346")
    cell.alignment = Alignment(horizontal="center")

# Column widths
ws.column_dimensions["A"].width = 12
ws.column_dimensions["B"].width = 15
ws.column_dimensions["C"].width = 15

# Number format: revenue as $, growth as %
for row in range(2, 6):
    ws.cell(row, 2).number_format = '$#,##0'
    ws.cell(row, 3).number_format = '0.0%'

# ============================================================
# Chart 1: Bar chart — quarterly revenue
# ============================================================
bar = BarChart()
bar.type = "col"                  # vertical bars
bar.style = 10
bar.title = "Quarterly Revenue"
bar.x_axis.title = "Quarter"
bar.y_axis.title = "Revenue (USD)"

# Data: column B (revenue), header row 1 through row 5
bar_data = Reference(ws, min_col=2, min_row=1, max_row=5)
bar_categories = Reference(ws, min_col=1, min_row=2, max_row=5)
bar.add_data(bar_data, titles_from_data=True)
bar.set_categories(bar_categories)

# Size (width, height in cm)
bar.width = 15
bar.height = 8

# Anchor chart on the sheet (positioned at cell E2)
ws.add_chart(bar, "E2")

# ============================================================
# Chart 2: Line chart — growth trend
# ============================================================
line = LineChart()
line.title = "Quarter-over-Quarter Growth"
line.x_axis.title = "Quarter"
line.y_axis.title = "Growth %"
line.style = 12

line_data = Reference(ws, min_col=3, min_row=1, max_row=5)
line.add_data(line_data, titles_from_data=True)
line.set_categories(bar_categories)

line.width = 15
line.height = 8

ws.add_chart(line, "E18")   # below the first chart

# === Save & verify ===
wb.save(str(output_path))

from openpyxl import load_workbook
verify = load_workbook(str(output_path))
print(f"OK: {output_path} ({output_path.stat().st_size} bytes)")
print(f"    Charts: {len(verify.active._charts)}")
```

### What to watch for

- **`titles_from_data=True`** reserves the first data row as the series
  name. If you pass `False` (or omit it), the legend shows
  "Series1", "Series2", ...
- **Anchor positions matter.** `"E2"` and `"E18"` are chosen so the
  charts do not overlap the data table (columns A–C) or each other.
  Adjust if the data table is longer.
- **Sizes are in centimeters**, not pixels. A 15×8 cm chart is
  roughly the width of a landscape A4 page (17 cm inner width).
- **Y-axis on bar chart** can start at zero
  (`bar.y_axis.scaling.min = 0`) — recommended for revenue.
- **Number format on the source cells** (`0.0%`) is inherited by the
  chart. Do not format the series separately unless you want to
  override.

---

## 5. Data Validation Dropdowns

A form-style sheet with a dropdown in every row. Users can only select
from the list — free-text entry is rejected by Excel.

```python
from pathlib import Path
from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.styles import Font, PatternFill, Alignment

output_path = Path("form.xlsx")
wb = Workbook()

# === Hidden sheet with the dropdown options ===
ws_options = wb.create_sheet("Options")
ws_options.append(["Status"])
for status in ["Pending", "In Progress", "Completed", "Cancelled"]:
    ws_options.append([status])
ws_options.sheet_state = "hidden"   # hide from the user

# === Main form sheet ===
ws = wb.active
ws.title = "Tasks"
ws.append(["Task ID", "Description", "Status", "Due Date"])

tasks = [
    ("T001", "Design mockups",   "Pending",     "2026-11-15"),
    ("T002", "Implement API",    "In Progress", "2026-11-20"),
    ("T003", "Write tests",      "Pending",     "2026-11-25"),
]

for i, (tid, desc, status, due) in enumerate(tasks, start=2):
    ws.cell(i, 1, tid)
    ws.cell(i, 2, desc)
    ws.cell(i, 3, status)
    ws.cell(i, 4, due)

# Style header
for cell in ws[1]:
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="217346")
    cell.alignment = Alignment(horizontal="center")

# Column widths
ws.column_dimensions["A"].width = 10
ws.column_dimensions["B"].width = 30
ws.column_dimensions["C"].width = 15
ws.column_dimensions["D"].width = 12

# === Data validation: dropdown in column C ===
dv = DataValidation(
    type="list",
    formula1="=Options!$A$2:$A$5",   # reference to the hidden sheet
    allow_blank=False,
    showDropDown=False,              # False = show dropdown arrow
    showErrorMessage=True,
    errorTitle="Invalid status",
    error="Please select a status from the dropdown.",
)

dv.promptTitle = "Status"
dv.prompt = "Choose Pending, In Progress, Completed, or Cancelled."
dv.showInputMessage = True

# Apply to C2:C100 (covers all rows; empty rows ignored)
ws.add_data_validation(dv)
dv.add("C2:C100")

# === Save & verify ===
wb.save(str(output_path))

from openpyxl import load_workbook
verify = load_workbook(str(output_path))
ws_check = verify["Tasks"]
print(f"OK: {output_path} ({output_path.stat().st_size} bytes)")
print(f"    Data validations: {len(ws_check.data_validations.dataValidation)}")
print(f"    Options sheet hidden: "
      f"{verify['Options'].sheet_state == 'hidden'}")
```

### What to watch for

- **`showDropDown=False`** is counter-intuitive: in OOXML, `True`
  hides the arrow. openpyxl passes the value through. Set it to
  `False` to *show* the arrow.
- **Options sheet is hidden, not deleted.** Excel still resolves the
  formula. Deleting the sheet breaks the dropdown.
- **Range `C2:C100`** is larger than the current data. That is
  intentional — new rows will get the dropdown without code changes.
- **`allow_blank=False`** rejects empty cells. Use `True` if the
  field is optional.
- **`DataValidation` objects can overlap.** If you add another rule
  to column C, they may conflict. Use one rule per column.

---

## Common pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `=SUM(...)` shows as text | String does not start with `=` | Ensure the Python string is `"=SUM(...)"`, not `"SUM(...)"` |
| Formula cell shows `0` after open | Excel did not recalculate | Open in Excel with formula calculation set to automatic |
| Arabic text displays left-to-right | `rightToLeft` not set | `ws.sheet_view.rightToLeft = True` on the worksheet |
| Arabic columns are in reverse order | RTL is set, but user expected LTR | Remove `rightToLeft = True`; use `Alignment(horizontal="right")` only |
| Numbers display as `1.23E+05` | No `number_format` | Set `cell.number_format = "#,##0"` |
| Column shows `###` instead of a number | Column too narrow | `ws.column_dimensions["D"].width = 15` |
| Image does not appear | Anchor cell not visible or image path wrong | Verify `Path(img).exists()` and anchor is a valid cell |
| Chart is empty | `titles_from_data=True` but no header, or reference range wrong | Check `min_col`, `min_row`, `max_row` |
| Conditional formatting does not trigger | Rule uses absolute reference | Use relative (`D2` not `$D$2`) |
| Dropdown does not appear | `showDropDown=True` | Set to `False` to show the arrow |

## Verification snippet (reusable)

Copy this into any example before the final `print`:

```python
from openpyxl import load_workbook
from pathlib import Path

p = Path(output_path)
assert p.exists(), "XLSX file was not created"
assert p.stat().st_size > 1000, f"XLSX too small ({p.stat().st_size} bytes)"
verify = load_workbook(str(p))
print(f"OK: {p} ({p.stat().st_size} bytes)")
print(f"    Sheets: {verify.sheetnames}")
print(f"    Active: {verify.active.title}")
```

Do **not** assert on formula values — openpyxl does not calculate them.
See `formulas.md` "The golden rule".