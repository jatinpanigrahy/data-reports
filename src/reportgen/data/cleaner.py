"""Data cleaning, sanitization, and type coercion.

Normalizes dirty currency strings, inconsistent date conventions,
and text fields into canonical pandas data types.
"""

from __future__ import annotations

import pandas as pd


def clean_amount_series(series: pd.Series) -> pd.Series:
    """Parse monetary strings into clean float values.

    Handles currency symbols, thousand separators, and accounting parentheses
    indicating negative values.
    """
    raise NotImplementedError("Amount cleaner will be implemented in Phase 2.")


def clean_date_series(series: pd.Series) -> pd.Series:
    """Parse date representations into timezone-naive datetime timestamps."""
    raise NotImplementedError("Date cleaner will be implemented in Phase 2.")


def clean_text_series(series: pd.Series, default: str, max_length: int | None = None) -> pd.Series:
    """Clean string columns by trimming whitespace and replacing missing values."""
    raise NotImplementedError("Text cleaner will be implemented in Phase 2.")


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all cleaning transformations to a normalized DataFrame."""
    raise NotImplementedError("DataFrame cleaner will be implemented in Phase 2.")
