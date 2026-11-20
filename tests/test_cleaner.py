"""Tests for data cleaning, sanitization, and type coercion."""

from __future__ import annotations

import math
import numpy as np
import pandas as pd
import pytest

from reportgen.data.cleaner import (
    clean_amount_series,
    clean_category_series,
    clean_dataframe,
    clean_dataset,
    clean_date_series,
    clean_department_series,
    clean_text_series,
)


def test_clean_amount_series_edge_cases() -> None:
    """Verify amount cleaning parses currency symbols, accounting negatives, and edge cases."""
    inputs = [
        "(125.00)",           # Accounting negative
        "-$450.00",           # Leading negative with currency
        "$-450.00",           # Currency before negative
        "($125.00)",          # Currency inside accounting parentheses
        "$(125.00)",          # Currency before accounting parentheses
        "$14,850.00",         # Currency with thousand commas
        "€1,200.50",          # Euro currency
        "£50.25",             # British pound
        "¥10,000",            # Japanese yen
        "  $ 14,850.00  ",    # Extra whitespace
        42.50,                # Bare float
        100,                  # Bare integer
        "$450.00-",           # Trailing negative sign
        "",                   # Blank string
        "N/A",                # Unparseable text
        None,                 # None value
    ]
    series = pd.Series(inputs)
    result = clean_amount_series(series)

    assert result.dtype == np.float64
    assert math.isclose(result.iloc[0], -125.00)
    assert math.isclose(result.iloc[1], -450.00)
    assert math.isclose(result.iloc[2], -450.00)
    assert math.isclose(result.iloc[3], -125.00)
    assert math.isclose(result.iloc[4], -125.00)
    assert math.isclose(result.iloc[5], 14850.00)
    assert math.isclose(result.iloc[6], 1200.50)
    assert math.isclose(result.iloc[7], 50.25)
    assert math.isclose(result.iloc[8], 10000.00)
    assert math.isclose(result.iloc[9], 14850.00)
    assert math.isclose(result.iloc[10], 42.50)
    assert math.isclose(result.iloc[11], 100.00)
    assert math.isclose(result.iloc[12], -450.00)
    assert pd.isna(result.iloc[13])
    assert pd.isna(result.iloc[14])
    assert pd.isna(result.iloc[15])


def test_clean_date_series_mixed_formats_and_tz_stripping() -> None:
    """Verify date parsing handles mixed formats, timezone offsets, and timezone stripping."""
    inputs = [
        "2026-01-15",
        "02/14/2026",
        "15/03/2026",
        "2026-01-01T12:00:00+02:00",  # UTC 10:00:00
        "2026-01-02T00:00:00Z",
        pd.Timestamp("2026-01-10"),
        "invalid_date",
        None,
    ]
    series = pd.Series(inputs)
    result = clean_date_series(series)

    assert pd.api.types.is_datetime64_any_dtype(result)
    # Ensure timezone is stripped (tz-naive)
    assert getattr(result.dt, "tz", None) is None

    assert result.iloc[0] == pd.Timestamp("2026-01-15 00:00:00")
    assert result.iloc[1] == pd.Timestamp("2026-02-14 00:00:00")
    assert result.iloc[2] == pd.Timestamp("2026-03-15 00:00:00")
    # 12:00 at +02:00 is 10:00 UTC
    assert result.iloc[3] == pd.Timestamp("2026-01-01 10:00:00")
    assert result.iloc[4] == pd.Timestamp("2026-01-02 00:00:00")
    assert result.iloc[5] == pd.Timestamp("2026-01-10 00:00:00")
    assert pd.isna(result.iloc[6])
    assert pd.isna(result.iloc[7])


def test_clean_text_series_and_truncation() -> None:
    """Verify whitespace trimming, empty string fallback, and character limit truncation."""
    series = pd.Series([
        "  Acme Corp  ",
        "Multiple    spaces   between   words",
        "",
        None,
        "A" * 80,  # Long string exceeding 60 characters
    ])
    result = clean_text_series(series, default="Unknown Transaction", max_length=60)

    assert result.iloc[0] == "Acme Corp"
    assert result.iloc[1] == "Multiple spaces between words"
    assert result.iloc[2] == "Unknown Transaction"
    assert result.iloc[3] == "Unknown Transaction"

    truncated = result.iloc[4]
    assert len(truncated) == 60
    assert truncated.endswith("...")
    assert truncated == ("A" * 57) + "..."


def test_clean_category_and_department() -> None:
    """Verify title-casing and default values for category and department series."""
    cats = pd.Series([
        "cloud infrastructure",
        "SOFTWARE & SAAS",
        "  travel & logistics  ",
        "",
        None,
    ])
    cat_result = clean_category_series(cats)
    assert cat_result.iloc[0] == "Cloud Infrastructure"
    assert cat_result.iloc[1] == "Software & SaaS"
    assert cat_result.iloc[2] == "Travel & Logistics"
    assert cat_result.iloc[3] == "Uncategorized"
    assert cat_result.iloc[4] == "Uncategorized"

    depts = pd.Series([
        "engineering",
        "  OPERATIONS  ",
        "",
        None,
    ])
    dept_result = clean_department_series(depts)
    assert dept_result.iloc[0] == "Engineering"
    assert dept_result.iloc[1] == "Operations"
    assert dept_result.iloc[2] == "General"
    assert dept_result.iloc[3] == "General"


def test_clean_dataset_no_mutation_and_row_filtering() -> None:
    """Verify clean_dataset returns a new DataFrame, filters invalid rows, and sorts chronologically."""
    raw_df = pd.DataFrame({
        "date": ["2026-03-01", "invalid_date", "2026-01-15", "2026-02-10"],
        "category": ["cloud infrastructure", "software", "Travel & Logistics", "office supplies"],
        "amount": ["$1,200.00", "$50.00", "bad_amount", "(350.00)"],
        "description": ["AWS Compute", "Figma", "Flight to client", "Paper & pens"],
        "department": ["engineering", "design", "sales", "operations"],
    })
    raw_copy = raw_df.copy()

    cleaned = clean_dataset(raw_df)

    # 1. Verify input is not modified in-place
    pd.testing.assert_frame_equal(raw_df, raw_copy)
    assert cleaned is not raw_df

    # 2. Rows with invalid date (row 1) and invalid amount (row 2) must be dropped
    assert len(cleaned) == 2

    # 3. Output must be sorted chronologically by date ascending
    assert list(cleaned["date"]) == [pd.Timestamp("2026-02-10"), pd.Timestamp("2026-03-01")]

    # 4. Amounts must be floats and accounting notation resolved
    assert math.isclose(cleaned.iloc[0]["amount"], -350.00)
    assert math.isclose(cleaned.iloc[1]["amount"], 1200.00)

    # 5. Index must be reset cleanly
    assert list(cleaned.index) == [0, 1]


def test_clean_dataframe_alias_compatibility() -> None:
    """Verify that clean_dataframe is a drop-in alias for clean_dataset."""
    df = pd.DataFrame({
        "date": ["2026-01-01"],
        "category": ["hardware"],
        "amount": ["100"],
    })
    res1 = clean_dataset(df)
    res2 = clean_dataframe(df)
    pd.testing.assert_frame_equal(res1, res2)
