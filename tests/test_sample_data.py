"""Verification tests for the canonical sample dataset and test fixtures."""

from __future__ import annotations

import math
from pathlib import Path
import pandas as pd
import pytest


def test_sample_csv_exists_and_row_count(sample_csv_path: Path) -> None:
    """Verify that sample_expenses.csv exists and has exactly 251 lines."""
    assert sample_csv_path.is_file()
    with open(sample_csv_path, "r", encoding="utf-8") as f:
        line_count = sum(1 for _ in f)
    assert line_count == 251, f"Expected 251 lines (header + 250 rows), found {line_count}"


def test_raw_sample_df_structure(raw_sample_df: pd.DataFrame) -> None:
    """Verify column names and row count in the raw sample DataFrame."""
    assert len(raw_sample_df) == 250
    expected_cols = ["Date", "Category", "Amount", "Description", "Department"]
    assert list(raw_sample_df.columns) == expected_cols


def test_minimal_cleaned_df_fixture(minimal_cleaned_df: pd.DataFrame) -> None:
    """Verify the minimal cleaned DataFrame fixture."""
    assert len(minimal_cleaned_df) == 5
    assert list(minimal_cleaned_df.columns) == ["date", "category", "amount", "description", "department"]
    assert minimal_cleaned_df["amount"].sum() == 4720.00


def test_sample_dataset_golden_metrics(sample_csv_path: Path) -> None:
    """Verify the sample data parses to exact golden metrics specified in docs."""
    raw_df = pd.read_csv(sample_csv_path)
    assert len(raw_df) == 250

    # Parse amounts matching cleaner logic
    amounts: list[float] = []
    for val in raw_df["Amount"]:
        s = str(val).strip().replace('"', '').replace('$', '').replace(',', '')
        if s.startswith('(') and s.endswith(')'):
            amt = -float(s[1:-1])
        else:
            amt = float(s)
        amounts.append(amt)

    # Parse dates
    dates = pd.to_datetime(raw_df["Date"], format="mixed")
    assert dates.notna().all()

    # Normalize categories
    categories: list[str] = []
    for cat in raw_df["Category"]:
        c = cat.strip().title()
        if c == "Software & Saas":
            c = "Software & SaaS"
        categories.append(c)

    cleaned = pd.DataFrame({
        "date": dates,
        "category": categories,
        "amount": amounts,
        "description": raw_df["Description"],
        "department": raw_df["Department"],
    })

    # Assert golden reference values:
    # 1. Total Rows
    assert len(cleaned) == 250

    # 2. Total Net Spend = $218,435.50
    total_spend = cleaned["amount"].sum()
    assert math.isclose(total_spend, 218435.50, rel_tol=1e-3)

    # 3. Average Transaction = $873.74
    avg_tx = cleaned["amount"].mean()
    assert math.isclose(avg_tx, 873.74, rel_tol=1e-3)

    # 4. Top Category = Cloud Infrastructure with spend = $86,450.00
    by_cat = cleaned.groupby("category")["amount"].sum().sort_values(ascending=False)
    assert by_cat.index[0] == "Cloud Infrastructure"
    top_cat_spend = by_cat.iloc[0]
    assert math.isclose(top_cat_spend, 86450.00, rel_tol=1e-3)

    # 5. Top Category Share = 39.58% (~39.6%)
    top_cat_share = (top_cat_spend / total_spend) * 100
    assert math.isclose(top_cat_share, 39.58, rel_tol=1e-2)

    # 6. MoM Delta = +6.4%
    cleaned["month"] = cleaned["date"].dt.month
    by_month = cleaned.groupby("month")["amount"].sum()
    mom_delta = ((by_month[3] - by_month[2]) / by_month[2]) * 100
    assert math.isclose(mom_delta, 6.4, rel_tol=1e-1)

    # 7. Top 5 Individual Transactions
    top5 = cleaned[cleaned["amount"] > 0].sort_values("amount", ascending=False).head(5)
    top5_records = top5[["description", "amount"]].to_dict(orient="records")
    assert top5_records[0]["description"] == "Amazon Web Services Q1 Compute"
    assert math.isclose(top5_records[0]["amount"], 14850.00)

    assert top5_records[1]["description"] == "Amazon Web Services Hosting"
    assert math.isclose(top5_records[1]["amount"], 14250.00)

    assert top5_records[2]["description"] == "GCP BigQuery Annual Reservation"
    assert math.isclose(top5_records[2]["amount"], 11500.00)

    assert top5_records[3]["description"] == "Cooley LLP Regulatory Filings"
    assert math.isclose(top5_records[3]["amount"], 8200.00)

    assert top5_records[4]["description"] == "Deloitte Systems Integration"
    assert math.isclose(top5_records[4]["amount"], 7500.00)
