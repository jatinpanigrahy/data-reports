# reportgen

Automated financial spend report generator that ingests transaction exports and builds executive single-page PDF dashboards.

## Overview

`reportgen` converts raw departmental transaction exports (CSV) into publication-grade, single-page PDF summaries. It handles real-world export variations including dirty currency formats, accounting negative notations, inconsistent date conventions, and vendor column synonyms.

### Core Capabilities

- **Header Resolution**: Automatically matches common column aliases or accepts explicit YAML column mapping.
- **Data Normalization**: Cleans currency strings, converts mixed date formats, and enforces schema integrity.
- **Analytics Engine**: Computes period-over-period spend delta, top category distributions, and identifies highest-value disbursements.
- **Visuals**: Generates headless Matplotlib bar charts and time trends configured with high-contrast publication styling.
- **Strict 1-Page Layout**: Assembles a calibrated ReportLab Platypus layout guaranteed to fit on a single page.

## Quickstart

### Installation

Install in editable mode with development dependencies:

```bash
pip install -e ".[dev]"
```

### Basic Usage

Generate an executive spend report from a transaction CSV:

```bash
python -m reportgen --input data/sample_expenses.csv --output output/q1_report.pdf
```

Or invoke the installed console script:

```bash
reportgen --input data/sample_expenses.csv --output output/q1_report.pdf
```

### Generating Sample Data

A canonical synthetic dataset with 250 transactions across Q1 2026 is included in `data/sample_expenses.csv`. To regenerate this dataset deterministically:

```bash
python scripts/generate_sample_data.py
```

## Running Tests

Execute unit and integration tests using pytest:

```bash
pytest
```
