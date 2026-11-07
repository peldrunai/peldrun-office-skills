# Excel Formulas in openpyxl

Complete reference for writing the 21 most common Excel formulas with
openpyxl.

## The golden rule

**openpyxl writes formulas as strings. It does NOT calculate them.**

```python
ws.cell(2, 4, "=B2*C2")           # writes the string "=B2*C2"
ws.cell(2, 4).value               # reads back "=B2*C2"  (not 50)
```

Excel or LibreOffice calculates formulas **when the user opens the file**.
Until then, the cell shows `0` in some viewers, or the formula string in
others.

Consequences:

- **Never** assert `ws.cell(...).value == 50` if you wrote a formula.
- **Always** tell the user "values appear when you open the file in Excel".
- If you need a value visible immediately, compute it in Python and
  write the number:

```python
total = qty * price               # compute in Python
ws.cell(2, 4, total)              # write the number, not the formula
```

If the user wants an **editable** formula they can change in Excel, write
the formula string and accept that the value appears on open.

## Formula syntax in openpyxl

Every formula is a **single string** starting with `=`:

```python
ws["A1"] = "=SUM(B2:B10)"
ws.cell(1, 1, "=SUM(B2:B10)")     # equivalent
```

Rules:

- **Locale is English** — commas `,` for argument separators, dots `.`
  for decimals. Never use `;` (European locale) inside a formula.
- **Sheet names** with spaces need single quotes: `'Q1 Data'!A1`.
- **Sheet names** without spaces can be bare: `Sheet2!A1`.
- **Absolute references** use `$`: `$A$1` (both locked), `$A1` (column
  locked), `A$1` (row locked).
- **Ranges**: `A1:B10` (two cells), `A:A` (entire column), `1:1` (entire
  row).
- **Named ranges**: define with `wb.defined_names`, reference by name.

## Math and statistics

### 1. SUM

**Purpose:** Add all numbers in a range.

```python
ws.cell(11, 4, "=SUM(D2:D10)")
```

**Gotcha:** Range must be valid at write time; Excel errors if the range
is empty and `#REF!` if a cell was deleted.

### 2. AVERAGE

**Purpose:** Arithmetic mean of numeric cells. **Skips** text and blank
cells.

```python
ws.cell(11, 4, "=AVERAGE(D2:D10)")
```

**Gotcha:** `#DIV/0!` if all cells in the range are empty or text.

### 3. MIN

```python
ws.cell(11, 4, "=MIN(D2:D10)")
```

### 4. MAX

```python
ws.cell(11, 4, "=MAX(D2:D10)")
```

### 5. COUNT

**Purpose:** Count cells that contain numbers. **Skips** text.

```python
ws.cell(11, 4, "=COUNT(D2:D10)")
```

**Contrast with COUNTA:** `=COUNTA(D2:D10)` counts non-empty cells
(includes text). Use `COUNTA` to count rows, `COUNT` to count numeric
values.

## Conditional aggregation

### 6. SUMIF

**Purpose:** Sum cells that meet a condition.

```python
# Sum column D where column A equals "Widget"
ws.cell(20, 4, '=SUMIF(A2:A10, "Widget", D2:D10)')
```

**Gotcha:** The condition string needs quotes inside the formula. Use
single quotes for the Python string and double quotes inside.

### 7. SUMIFS

**Purpose:** Sum cells that meet **multiple** conditions.

```python
# Sum D where A="Widget" AND B>5
ws.cell(20, 4, '=SUMIFS(D2:D10, A2:A10, "Widget", B2:B10, ">5")')
```

**Argument order:** `SUMIFS(sum_range, criteria_range1, criteria1, ...)`.
The **sum range comes first**, unlike `SUMIF` where it comes third. This
is the #1 source of `SUMIFS` bugs.

### 8. COUNTIF

```python
# Count cells in A that equal "Widget"
ws.cell(20, 2, '=COUNTIF(A2:A10, "Widget")')
```

### 9. COUNTIFS

```python
# Count rows where A="Widget" AND B>5
ws.cell(20, 2, '=COUNTIFS(A2:A10, "Widget", B2:B10, ">5")')
```

### 10. AVERAGEIF

```python
# Average D where A="Widget"
ws.cell(20, 4, '=AVERAGEIF(A2:A10, "Widget", D2:D10)')
```

## Lookup and reference

### 11. VLOOKUP

**Purpose:** Find a value in the first column of a range and return a
value from another column of the same row.

```python
# In sheet "Data", look up A2's value in "Categories" sheet
ws.cell(2, 5, "=VLOOKUP(A2, Categories!$A$2:$B$100, 2, FALSE)")
```

**Argument order:** `VLOOKUP(lookup_value, table_range, column_index,
exact_match)`.

- `column_index` is **1-based** (1 = first column of the table).
- `FALSE` = exact match (recommended). `TRUE` = approximate (requires
  sorted data).
- The **lookup_value must be in the first column** of the table range.
  This is a VLOOKUP limitation — use INDEX/MATCH if you need to look up
  in a different column.

### 12. INDEX / MATCH (VLOOKUP replacement)

**Purpose:** Look up a value in any column and return from any other
column. More flexible than VLOOKUP.

```python
# Find A2 in Categories!B:B, return the corresponding Categories!C:C
ws.cell(2, 5,
    "=INDEX(Categories!$C$2:$C$100, "
    "MATCH(A2, Categories!$B$2:$B$100, 0))")
```

**Advantages over VLOOKUP:**
- Can look up in any column, not just the first.
- Inserting a column does not break the formula (references are
  explicit).

**Argument order:** `INDEX(return_range, MATCH(lookup_value,
lookup_range, 0))`.

### 13. XLOOKUP

**Purpose:** Modern Excel lookup (Excel 365 / Excel 2021+). Handles
lookup-left and errors more gracefully.

```python
ws.cell(2, 5,
    "=XLOOKUP(A2, Categories!$B$2:$B$100, Categories!$C$2:$C$100, "
    '"not found")')
```

**Gotcha:** XLOOKUP does **not** work in Excel 2019 or older, LibreOffice
before 24.8, or Google Sheets (which has its own XLOOKUP with different
defaults). For maximum compatibility, use INDEX/MATCH.

## Logic

### 14. IF

**Purpose:** Return one of two values based on a condition.

```python
# If D2 > 100, write "high"; otherwise "low"
ws.cell(2, 5, '=IF(D2>100, "high", "low")')
```

### 15. IFS

**Purpose:** Multiple conditions (Excel 2019+).

```python
ws.cell(2, 5, '=IFS(D2>100, "high", D2>50, "medium", TRUE, "low")')
```

**Gotcha:** `IFS` returns `#N/A` if no condition matches. The `TRUE`
fallback is the idiomatic way to provide a default.

### 16. IFERROR

**Purpose:** Return a fallback value instead of an error.

```python
ws.cell(2, 5, '=IFERROR(VLOOKUP(A2, Sheet2!A:B, 2, FALSE), "not found")')
```

**Use for:** Wrapping VLOOKUP, division, INDEX/MATCH — anything that
might return `#N/A`, `#DIV/0!`, or `#REF!`.

## Text

### 17. CONCATENATE

**Purpose:** Join text and cell values.

```python
ws.cell(2, 4, '=CONCATENATE(A2, " ", B2)')
# Or the modern operator: =A2 & " " & B2
```

**Recommendation:** Use `&` in new workbooks — shorter, identical
behavior.

### 18. TEXT

**Purpose:** Format a number or date as text with a format string.

```python
# Format a numeric cell as currency text
ws.cell(2, 4, '=TEXT(C2, "$#,##0.00")')
```

**Gotcha:** The result is **text**, not a number. Summing the result
column gives 0 in most formulas.

### 19. LEFT / RIGHT / MID

```python
ws.cell(2, 3, "=LEFT(A2, 3)")     # first 3 chars
ws.cell(2, 4, "=RIGHT(A2, 4)")    # last 4 chars
ws.cell(2, 5, "=MID(A2, 2, 3)")   # 3 chars starting at position 2
```

**Note:** Text functions in Excel operate on **Unicode code points**.
Arabic combining marks count as separate characters. `LEFT("مرحبا", 2)`
returns 2 characters including any combining marks.

### 20. TRIM

**Purpose:** Remove leading/trailing spaces.

```python
ws.cell(2, 4, "=TRIM(A2)")
```

**Important for Arabic:** `TRIM` **does not** normalize Arabic letters
(ة vs ه) or remove tatweel. Use it only for whitespace.

## Date and time

### 21. TODAY / DATE

```python
# Write the current date as a formula (updates on open)
ws.cell(2, 5, "=TODAY()")

# Construct a specific date
ws.cell(2, 6, "=DATE(2026, 11, 8)")

# Extract parts
ws.cell(2, 7, "=YEAR(A2)")
ws.cell(2, 8, "=MONTH(A2)")
ws.cell(2, 9, "=DAY(A2)")
```

**Gotcha:** `=TODAY()` returns a serial number; apply
`number_format = "yyyy-mm-dd"` to display it as a date:

```python
cell = ws.cell(2, 5, "=TODAY()")
cell.number_format = "yyyy-mm-dd"
```

## Cross-sheet references

Reference cells or ranges in other sheets:

```python
# Simple
ws.cell(2, 1, "=Sheet2!A1")

# Sheet name with spaces (needs single quotes)
ws.cell(2, 1, "='Q1 Data'!A1")

# Sheet name with spaces AND absolute range
ws.cell(2, 1, "='Q1 Data'!$A$1:$B$10")

# Sheet name with a hyphen also needs quotes
ws.cell(2, 1, "='North-American Sales'!B2")
```

**Pattern for building sheet references from variables:**

```python
sheet_name = "Q1 Data"
# Escape single quotes in the sheet name
safe_sheet = "'" + sheet_name.replace("'", "''") + "'"
formula = f"=SUM({safe_sheet}!B2:B10)"
ws.cell(1, 1, formula)
```

## Common errors

| Error | Cause | Fix |
|---|---|---|
| `#REF!` | Deleted cell or invalid range | Verify range exists in the sheet |
| `#NAME?` | Formula name misspelled (`=SUMM` instead of `=SUM`) | Check the function name |
| `#VALUE!` | Wrong argument type (text where number expected) | Wrap in `IFERROR` or fix the source cell |
| `#DIV/0!` | Division by zero or empty cell | Wrap in `IFERROR(.../..., 0)` |
| `#N/A` | VLOOKUP/MATCH found no match | Use `IFERROR` to provide a fallback |
| Cell shows formula string instead of result | Missing `=` at start | Add `=` to the string |
| Cell shows `0` after opening in Excel | Excel did not recalculate | File → Options → Formulas → "Automatic" |
| `SUMIFS` returns wrong total | Wrong argument order (sum_range must be first) | `SUMIFS(sum_range, criteria_range1, criteria1, ...)` |
| Arabic text reversed after open | Cell has `Alignment(horizontal="right")` but no `rightToLeft` | Set `ws.sheet_view.rightToLeft = True` on the worksheet |

## When formulas are not enough

For anything that requires **immediate** computed values (a chart that
must render before the user opens Excel, a report the user will print
without editing):

1. Compute the value in Python (`sum()`, `pandas`, `numpy`, or plain
   arithmetic).
2. Write the literal number.
3. Optionally, write the formula in a **comment** or adjacent cell so
   the user can see the logic:

```python
computed_total = sum(qty * price for _, qty, price in rows_data)
ws.cell(11, 4, computed_total)
ws.cell(11, 5).comment = Comment(
    f"Computed from =SUM(D2:D10); expected {computed_total}",
    "PELDRUN"
)
```

This trades editability for determinism — the right choice when the
user says "make a printable report", and the wrong choice when they say
"I need to edit the totals in Excel".

## Verification without Excel

You cannot verify formula *results* without opening the file in Excel.
You **can** verify the formula *strings* were written correctly:

```python
from openpyxl import load_workbook

wb = load_workbook(str(output_path))
ws = wb.active

# Verify the formula string is present
assert ws["D11"].value == "=SUM(D2:D10)", \
    f"Expected =SUM(D2:D10), got {ws['D11'].value!r}"

# Verify it is a formula, not a literal
assert isinstance(ws["D11"].value, str), "Cell is not a string"
assert ws["D11"].value.startswith("="), "Cell is not a formula"

print("Formula strings verified. Values will appear on open.")
```

Do **not** assert on computed values. If the user must see the result,
compute it in Python and write the literal (see "When formulas are not
enough" above).