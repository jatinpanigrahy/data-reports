"""Shared test fixtures for the reportgen test suite.

Provides canonical in-memory DataFrames, paths to sample datasets,
and common test configurations.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest


@pytest.fixture(scope="session")
def sample_csv_path() -> Path:
    """Return the absolute path to the canonical sample expenses CSV file."""
    path = Path(__file__).resolve().parent.parent / "data" / "sample_expenses.csv"
    assert path.is_file(), f"Sample expenses CSV not found at {path}"
    return path


@pytest.fixture(scope="session")
def raw_sample_df(sample_csv_path: Path) -> pd.DataFrame:
    """Load the raw canonical sample CSV into a pandas DataFrame."""
    return pd.read_csv(sample_csv_path)


@pytest.fixture
def minimal_cleaned_df() -> pd.DataFrame:
    """Provide a 5-row canonical DataFrame for fast isolated tests."""
    return pd.DataFrame([
        {
            "date": pd.Timestamp("2026-01-10"),
            "category": "Software & SaaS",
            "amount": 120.00,
            "description": "Figma Subscription",
            "department": "Design",
        },
        {
            "date": pd.Timestamp("2026-01-15"),
            "category": "Cloud Infrastructure",
            "amount": 1500.00,
            "description": "AWS Compute",
            "department": "Engineering",
        },
        {
            "date": pd.Timestamp("2026-02-05"),
            "category": "Software & SaaS",
            "amount": 250.00,
            "description": "Slack Pro Tier",
            "department": "Operations",
        },
        {
            "date": pd.Timestamp("2026-02-20"),
            "category": "Travel & Logistics",
            "amount": 650.00,
            "description": "Client Onsite Flight",
            "department": "Sales",
        },
        {
            "date": pd.Timestamp("2026-03-01"),
            "category": "Cloud Infrastructure",
            "amount": 2200.00,
            "description": "AWS Reserved Instances",
            "department": "Engineering",
        },
    ])
