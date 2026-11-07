---
name: csv_data
description: Generate and transform CSV files with pandas.
---

# CSV Data Handler

You create and manipulate `.csv` files using **pandas only**. It is
installed in PELDRUN. Do **not** use Python's built-in `csv` module for
anything beyond trivial 2-column files — pandas handles encodings,
quoting, delimiters, and type inference correctly.

## Why pandas

`pandas.read_csv` detects encoding, delimiter, and quoting automatically
in most cases, and exposes a DataFrame API for filtering, aggregation,
joins, and pivots. `to_csv` writes UTF-8 with BOM by default in this
skill, so Excel opens Arabic, Hebrew, CJK, and Cyrillic files correctly
without a manual "Data → From Text" import.

## Before you write code

Ask the user (or infer from context):

1. **Output path** — default `<workspace>/<name>.csv`.
2. **Encoding** — if the user opens the file in Excel on Windows, use
   `utf-8-sig` (UTF-8 with BOM). Otherwise `utf-8`.
3. **Delimiter** — comma by default; `\t` for TSV, `;` for some
   European locales.
4. **Data source** — parse provided text/numbers first.
   **Never invent data.**
5. **Operation** — create, filter, merge, or transform.

## Canonical script

Create `generate_csv.py` in the workspace. This is a complete, runnable
script — do not abbreviate.

```python
import pandas as pd
from pathlib import Path

output_path = Path("data.csv")

data = {
    "item": ["Widget", "Gadget", "Doohickey"],
    "quantity": [10, 3, 7],
    "price": [5.00, 12.50, 3.75],
}
df = pd.DataFrame(data)
df["total"] = df["quantity"] * df["price"]

# UTF-8 with BOM: Excel opens Arabic/CJK/Cyrillic correctly.
df.to_csv(output_path, index=False, encoding="utf-8-sig")

print(f"OK: {output_path} ({output_path.stat().st_size} bytes)")
print(f"Rows: {len(df)}, Columns: {list(df.columns)}")
```

Run it with `python_execute` or via `bash`: `python generate_csv.py`.

## Encoding (critical)

The **only** encoding mistake that matters: Excel on Windows reads
UTF-8 without BOM as Latin-1, so Arabic, Chinese, and Cyrillic appear
as mojibake (`Ø£Ù‡Ù„Ø§` instead of `أهلاً`).

| Target                          | `encoding=`    |
|---------------------------------|----------------|
| Excel (Windows, macOS)          | `utf-8-sig`    |
| Linux tools (grep, awk, pandas) | `utf-8`        |
| Legacy Windows Arabic (cp1256)  | `cp1256`       |
| Legacy Western European         | `latin-1`      |

**Rule:** `utf-8-sig` is the safe default when the user will open the
file in Excel. It writes a 3-byte BOM at the start; most modern tools
ignore it silently.

**Reading:** `pd.read_csv` auto-detects UTF-8, UTF-8-BOM, UTF-16, and
latin-1. If it fails, pass `encoding="utf-8"` explicitly. For mixed or
unknown encodings, use `encoding_errors="replace"` to avoid crashes at
the cost of losing unmappable characters.

## Reading files

```python
# Auto-detect encoding and delimiter (works for most CSVs)
df = pd.read_csv("input.csv")

# Explicit encoding and delimiter
df = pd.read_csv("input.csv", encoding="utf-8-sig", sep=",")

# Tab-separated
df = pd.read_csv("input.tsv", sep="\t")

# Semicolon-separated (some European exports)
df = pd.read_csv("input.csv", sep=";")

# Large file: read in chunks
for chunk in pd.read_csv("huge.csv", chunksize=100_000):
    process(chunk)
```

**Note:** `pd.read_csv` treats the first row as headers by default.
Pass `header=None` if the file has no header row.

## Common operations

```python
# Filter rows
active = df[df["status"] == "active"]

# Select columns
subset = df[["name", "email"]]

# Sort
sorted_df = df.sort_values("total", ascending=False)

# Aggregate
totals = df.groupby("category")["amount"].sum()

# Add a computed column
df["total"] = df["quantity"] * df["price"]

# Merge (SQL-style join)
merged = pd.merge(orders, customers, on="customer_id", how="left")

# Pivot
pivot = df.pivot_table(
    index="category", columns="month", values="amount", aggfunc="sum"
)
```

## Delimiters and quoting

For data containing commas inside fields (e.g. addresses), pandas
quotes automatically:

```python
df.to_csv(output_path, index=False, encoding="utf-8-sig", quoting=1)
```

`quoting=1` (QUOTE_ALL) quotes every field. `quoting=2` (QUOTE_MINIMAL,
the default) quotes only fields containing the delimiter, quote, or
newline.

## Verification (mandatory)

Always verify **before** reporting success.

```python
import pandas as pd
from pathlib import Path

p = Path(output_path)
assert p.exists(), "CSV file was not created"
assert p.stat().st_size > 10, f"CSV too small ({p.stat().st_size} bytes)"

verify = pd.read_csv(p, encoding="utf-8-sig")
print(f"Rows: {len(verify)}")
print(f"Columns: {list(verify.columns)}")
assert len(verify) >= 1, "CSV has no data rows"
```

If verification fails, do **not** report success. Report the exact
traceback.

## Output format

Return exactly this structure:

```
## Result
- File: <relative path>
- Rows: <number>
- Columns: <list>
- Encoding: <utf-8-sig | utf-8 | ...>
- Size: <bytes>

## Summary
<one or two sentences describing the content>

## Warnings
<large file (> 100 MB), mixed types in a column, or "none">
```

## Hard rules

1. **Use pandas only.** Never Python's `csv` module for anything beyond
   trivial 2-column files.
2. **Never install packages** at runtime.
3. **Never write outside the workspace.**
4. **Always run verification** before reporting success.
5. **Use `encoding="utf-8-sig"`** by default when the user will open
   the file in Excel. Arabic, Chinese, and Cyrillic display correctly
   only with the BOM.
6. **Never invent data.** If the user did not provide values, ask.
7. **Never hardcode absolute paths.**
8. **Prefer `pd.read_csv` auto-detection** over manual encoding
   guessing. Pass `encoding=` only if auto-detection fails.
9. **For files > 100 MB, use `chunksize`** in `read_csv`. Reading the
   whole file into memory may crash the workspace.
10. **Always pass `index=False` to `to_csv`** — otherwise pandas writes
    an unnamed index column that confuses every downstream tool.