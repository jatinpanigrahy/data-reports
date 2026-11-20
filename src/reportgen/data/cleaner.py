"""Data cleaning, sanitization, and type coercion.

Normalizes dirty currency strings, inconsistent date conventions,
and text fields into canonical pandas data types suitable for downstream analytics.
"""

from __future__ import annotations

import logging
from typing import Final
import pandas as pd


logger = logging.getLogger(__name__)

# Currency tokens stripped during monetary parsing
CURRENCY_SYMBOLS: Final[tuple[str, ...]] = ("$", "€", "£", "¥")


def _parse_amount_value(val: object) -> float:
    """Parse an individual amount value into a standard float.

    Handles accounting parenthesis notation for negatives (e.g., '(125.00)'),
    leading/trailing minus signs, thousand separators, and major currency symbols.
    """
    if val is None or pd.isna(val):
        return float("nan")

    if isinstance(val, (int, float)):
        return float(val)

    raw = str(val).strip()
    if not raw:
        return float("nan")

    is_negative = False
    clean = raw.replace(" ", "")

    # Accounting parentheses notation: (125.00) or ($125.00) or $(125.00)
    if clean.startswith("(") and clean.endswith(")"):
        is_negative = True
        clean = clean[1:-1]
    elif clean.startswith("$(") and clean.endswith(")"):
        is_negative = True
        clean = clean[2:-1]

    # Strip currency symbols and thousand separator commas
    for token in CURRENCY_SYMBOLS + (",",):
        clean = clean.replace(token, "")

    # Leading or trailing minus sign check
    if clean.startswith("-"):
        is_negative = not is_negative
        clean = clean[1:]
    elif clean.endswith("-"):
        is_negative = not is_negative
        clean = clean[:-1]

    try:
        amount = float(clean)
        return -amount if is_negative else amount
    except (ValueError, TypeError):
        return float("nan")


def clean_amount_series(series: pd.Series) -> pd.Series:
    """Parse monetary strings into clean float values.

    Handles currency symbols ($ € £ ¥), thousand separators, and accounting parentheses
    indicating negative values. Unparseable values are coerced to NaN.

    Args:
        series: Series containing dirty monetary strings or numbers.

    Returns:
        Series of dtype float64.
    """
    return series.apply(_parse_amount_value).astype("float64")


def clean_date_series(series: pd.Series) -> pd.Series:
    """Parse date representations into timezone-naive datetime timestamps.

    Converts varied string formats (YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY) into
    timezone-naive UTC timestamps. Unparseable entries are coerced to NaT.

    Args:
        series: Series containing date strings, timestamps, or nulls.

    Returns:
        Series of dtype datetime64[ns] in UTC without timezone localization.
    """
    parsed = pd.to_datetime(series, format="mixed", errors="coerce", utc=True)
    return parsed.dt.tz_localize(None)


def clean_text_series(
    series: pd.Series,
    default: str,
    max_length: int | None = None,
) -> pd.Series:
    """Clean string columns by trimming whitespace and replacing missing values.

    Args:
        series: Source text series.
        default: Fallback string value used when entries are null or blank.
        max_length: Optional character limit. Strings exceeding this limit are truncated
            with an ellipsis ('...') to fit within document layout budgets.

    Returns:
        Series of dtype string.
    """
    def _clean_str(val: object) -> str:
        if val is None or pd.isna(val):
            return default
        s = str(val).strip()
        if not s:
            return default
        # Collapse repeated whitespace
        s = " ".join(s.split())
        if max_length is not None and len(s) > max_length:
            if max_length > 3:
                s = f"{s[:max_length - 3]}..."
            else:
                s = s[:max_length]
        return s

    return series.apply(_clean_str).astype("string")


def clean_category_series(series: pd.Series) -> pd.Series:
    """Normalize expense category names with title casing and standardized acronyms.

    Args:
        series: Series containing raw category names.

    Returns:
        Cleaned, title-cased string Series defaulting to 'Uncategorized'.
    """
    def _clean_cat(val: object) -> str:
        if val is None or pd.isna(val):
            return "Uncategorized"
        s = str(val).strip()
        if not s:
            return "Uncategorized"
        s = " ".join(s.split())
        titled = s.title()
        if titled == "Software & Saas":
            return "Software & SaaS"
        return titled

    return series.apply(_clean_cat).astype("string")


def clean_department_series(series: pd.Series) -> pd.Series:
    """Normalize department names with consistent title casing.

    Args:
        series: Series containing raw department names.

    Returns:
        Cleaned, title-cased string Series defaulting to 'General'.
    """
    def _clean_dept(val: object) -> str:
        if val is None or pd.isna(val):
            return "General"
        s = str(val).strip()
        if not s:
            return "General"
        s = " ".join(s.split())
        return s.title()

    return series.apply(_clean_dept).astype("string")


def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all cleaning transformations and return a sanitized canonical DataFrame.

    Does not modify the input DataFrame in place. Drops any rows where required
    values (date, amount) cannot be parsed or evaluate to NaN.

    Args:
        df: DataFrame containing mapped canonical columns.

    Returns:
        Sanitized DataFrame sorted chronologically by date ascending.
    """
    out = df.copy()

    # Clean amount and date
    if "amount" in out.columns:
        out["amount"] = clean_amount_series(out["amount"])
    if "date" in out.columns:
        out["date"] = clean_date_series(out["date"])

    # Clean strings
    if "category" in out.columns:
        out["category"] = clean_category_series(out["category"])
    else:
        out["category"] = pd.Series(["Uncategorized"] * len(out), dtype="string")

    if "description" in out.columns:
        out["description"] = clean_text_series(
            out["description"],
            default="Unknown Transaction",
            max_length=60,
        )
    else:
        out["description"] = pd.Series(["Unknown Transaction"] * len(out), dtype="string")

    if "department" in out.columns:
        out["department"] = clean_department_series(out["department"])
    else:
        out["department"] = pd.Series(["General"] * len(out), dtype="string")

    # Drop invalid rows where date or amount failed parsing
    initial_count = len(out)
    valid_mask = out["date"].notna() & out["amount"].notna()
    cleaned = out[valid_mask].copy()
    dropped_count = initial_count - len(cleaned)

    if initial_count > 0 and (dropped_count / initial_count) > 0.05:
        logger.warning(
            "Dropped %d of %d rows (%.1f%%) due to unparseable dates or amounts.",
            dropped_count,
            initial_count,
            (dropped_count / initial_count) * 100,
        )

    # Sort chronologically by transaction date
    cleaned = cleaned.sort_values("date", ascending=True).reset_index(drop=True)
    return cleaned


# Backward compatibility alias
clean_dataframe = clean_dataset
