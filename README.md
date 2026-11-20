# reportgen

`reportgen` is a command-line tool and Python library that converts tabular transaction CSVs into single-page executive PDF financial reports.

It ingests raw transaction exports, resolves column header aliases, cleans monetary strings and timestamps, computes summary KPIs and period-over-period variance, renders categorical and temporal charts, and compiles a single-page PDF dashboard.

---

## Prerequisites and Installation

Requires Python 3.10 or later.

```bash
# Clone the repository
git clone https://github.com/jatinpanigrahy/data-reports.git
cd data-reports

# Install in editable mode
pip install -e .

# Or install with development dependencies for testing
pip install -e ".[dev]"
```

---

## Quickstart

### 1. Generate Sample Data

A deterministic 250-row synthetic dataset spanning Q1 2026 is included at `data/sample_expenses.csv`. To regenerate this dataset:

```bash
python scripts/generate_sample_data.py
```

### 2. Generate a PDF Report

Run `reportgen` against the sample dataset:

```bash
python -m reportgen data/sample_expenses.csv -o output/executive_report.pdf
```

Output:

```text
[INFO] Reading input data from 'data/sample_expenses.csv'...
[INFO] Resolved 250 transactions spanning 2026-01-04 to 2026-03-31.
[INFO] Calculated executive KPIs (Total Spend: $218,435.50, Period Delta: +6.4%).
[INFO] Generated category breakdown and time-series trend visuals.
[INFO] Compiled single-page PDF dashboard to 'output/executive_report.pdf'.
[SUCCESS] Report generated: output/executive_report.pdf (250 transactions, Jan 04, 2026 - Mar 31, 2026, Net Spend: $218,435.50) in 0.13s.
```

If installed via pip, the console script `reportgen` is also available:

```bash
reportgen data/sample_expenses.csv -o output/executive_report.pdf
```

---

## CLI Reference

```text
reportgen [-h] [-i INPUT] [-o OUTPUT] [-t TITLE] [-s SUBTITLE]
          [-m MAPPING] [-c CURRENCY] [--open] [-q] [-v] [--version]
          [INPUT]
```

### Options

| Flag | Short | Default | Description |
| :--- | :--- | :--- | :--- |
| `INPUT` / `--input` | `-i` | None (Required) | Path to raw transaction CSV file. Can be passed positionally or with `-i`. |
| `--output` | `-o` | `output/<stem>_report.pdf` | Destination path for the compiled PDF. Parent folders are created automatically. |
| `--title` | `-t` | `Financial Disbursement Report` | Headline title rendered in the report banner. |
| `--subtitle` | `-s` | `Executive Spend & Variance Summary` | Contextual subheader rendered beneath the title. |
| `--mapping` | `-m` | None | Path to YAML file defining custom CSV column aliases. |
| `--currency` | `-c` | `$` | Currency symbol applied to KPI cards, table amounts, and chart value labels. |
| `--open` | | `False` | Attempt to launch the generated PDF in the system default viewer. |
| `--quiet` | `-q` | `False` | Silence standard console output; emit only error diagnostics. |
| `--verbose` | `-v` | `False` | Print full Python tracebacks on error for debugging. |
| `--version` | | — | Print `reportgen 0.1.0` and exit. |
| `--help` | `-h` | — | Display argument documentation and exit. |

---

## Column Mapping Configuration

`reportgen` requires three canonical columns to construct a report:

| Canonical Column | Type | Description | Built-in Synonyms |
| :--- | :--- | :--- | :--- |
| `date` | Date / Datetime | Transaction posting date | `date`, `transaction_date`, `trans_date`, `tx_date`, `timestamp` |
| `category` | String | Expense classification | `category`, `expense_category`, `type`, `classification` |
| `amount` | Numeric | Net transaction amount | `amount`, `cost`, `spend`, `total`, `price`, `gross_amount` |
| `description` | String (Optional) | Merchant or memo (defaults to `General Expense`) | `description`, `merchant`, `vendor`, `payee`, `memo`, `details` |
| `department` | String (Optional) | Division or cost center (defaults to `Operations`) | `department`, `dept`, `cost_center`, `team`, `division` |

If your CSV uses non-standard column names that do not match built-in synonyms, create a YAML mapping file:

```yaml
# config/custom_mapping.yaml
column_mapping:
  trans_time: date
  line_item: category
  gross_cost: amount
  vendor_name: description
  cost_center: department
```

Pass the mapping file via `--mapping`:

```bash
reportgen data/vendor_export.csv --mapping config/custom_mapping.yaml -o output/vendor_report.pdf
```

---

## Programmatic Python API

You can call the report generator directly from Python code:

```python
from pathlib import Path
from reportgen import generate_report, ReportConfig

# Minimal programmatic invocation
pdf_path: Path = generate_report(
    input_path="data/sample_expenses.csv",
    output_path="output/executive_report.pdf",
    title="Q1 Technology Disbursements",
    currency="$",
)

# Advanced invocation using ReportConfig
config = ReportConfig(
    input_path=Path("data/sample_expenses.csv"),
    output_path=Path("output/q1_summary.pdf"),
    title="Quarterly Board Summary",
    subtitle="Consolidated Operating Expenses",
    currency_symbol="$",
)
pdf_path = generate_report(config=config)
```

---

## Architecture and Design Constraints

`reportgen` is built around specific operational constraints:

- **Strict single-page budget**: Reports are formatted for US Letter in portrait mode (612 pt x 792 pt) with 36 pt margins, leaving exactly 540 pt x 720 pt of usable canvas space. All table cells wrap in Platypus Paragraphs to prevent horizontal clipping. The PDF builder explicitly asserts `doc.page == 1`; if content spills onto page 2, the partial PDF is deleted from disk and a `PDFBuildError` is raised.
- **Offline Type 1 typography**: Document styling uses standard Helvetica fonts (`Helvetica`, `Helvetica-Bold`, `Helvetica-Oblique`). No network font downloads or operating system font installations are required.
- **Zero temporary chart files**: Visualizations are rendered via Matplotlib's non-interactive `Agg` backend into in-memory `io.BytesIO` PNG byte buffers (300 DPI) and converted into ReportLab `Image` flowables. Every figure is closed inside a `finally` block (`plt.close(fig)`) to eliminate memory leaks during batch runs.
- **Defensive currency parsing**: The cleaner parses negative amounts formatted as accounting parentheses (`(120.00)`), currency-prefixed strings (`-$45.50`, `$1,250.00`), and raw floats. Refunds correctly offset net spend.

---

## Exit Codes and Error Diagnostics

`reportgen` follows standard UNIX exit code conventions:

| Exit Code | Error Category | Root Cause and Remediation |
| :--- | :--- | :--- |
| `0` | Success | Pipeline succeeded; single-page PDF written to destination. |
| `1` | Unexpected Error | Unhandled internal exception. Rerun with `--verbose` for debug details. |
| `2` | Argument Error | Invalid flag, missing required input CSV, or unparseable argument. |
| `10` | `DataLoadError` | Input file not found, unreadable, or invalid CSV encoding. Verify the file path and file permissions. |
| `11` | `SchemaValidationError` | Required canonical columns (`date`, `category`, `amount`) missing. Pass a YAML mapping via `--mapping`. |
| `12` | `DataProcessingError` | Empty CSV, zero valid rows after sanitization, or unparseable timestamps. |
| `13` | `PDFBuildError` / `RenderingError` | ReportLab layout exceeded 1 page, or Matplotlib failed to rasterize a figure. |

By default, Python tracebacks are suppressed on failure, printing a clean diagnostic message to `stderr`. Pass `-v` or `--verbose` to view full tracebacks.

---

## Running the Test Suite

Run the full pytest suite:

```bash
pytest -v
```
