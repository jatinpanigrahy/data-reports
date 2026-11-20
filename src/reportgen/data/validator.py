"""Schema validation and dataset integrity checks.

Validates that loaded datasets contain required canonical fields and
have sufficient non-null records to produce a meaningful report.
"""

from __future__ import annotations

from typing import Final
import pandas as pd

from reportgen.config import DataProcessingError, SchemaValidationError


# Required canonical fields without which downstream reporting cannot proceed
REQUIRED_CANONICAL_COLUMNS: Final[tuple[str, ...]] = ("date", "category", "amount")


def validate_schema(df: pd.DataFrame, source_name: str | None = None) -> None:
    """Ensure the DataFrame contains all required canonical fields.

    Checks for the presence of 'date', 'category', and 'amount'. If any are missing,
    raises a SchemaValidationError with diagnostic guidance and an example YAML mapping.

    Args:
        df: DataFrame after column mapping and renaming.
        source_name: Optional file path or dataset label for diagnostic output.

    Raises:
        SchemaValidationError: If required canonical columns are missing.
    """
    missing = [col for col in REQUIRED_CANONICAL_COLUMNS if col not in df.columns]
    if missing:
        raise SchemaValidationError(
            message_or_missing=missing,
            available_columns=list(df.columns),
            source_name=source_name,
        )


def validate_records(df: pd.DataFrame) -> None:
    """Verify that the cleaned dataset contains valid records with canonical types.

    Ensures that the DataFrame is not empty and that the 'amount' and 'date' columns
    contain numeric and datetime data types, respectively.

    Args:
        df: Cleaned canonical DataFrame.

    Raises:
        DataProcessingError: If the dataset is empty or columns have incorrect data types.
    """
    if df.empty or len(df) == 0:
        raise DataProcessingError("No valid transaction records found in dataset.")

    if "amount" in df.columns and not pd.api.types.is_numeric_dtype(df["amount"]):
        raise DataProcessingError(
            f"Expected numeric values in 'amount' column, received dtype '{df['amount'].dtype}'."
        )

    if "date" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["date"]):
        raise DataProcessingError(
            f"Expected datetime64 timestamps in 'date' column, received dtype '{df['date'].dtype}'."
        )


def validate_record_counts(df: pd.DataFrame, min_records: int = 1) -> None:
    """Ensure the DataFrame contains at least min_records valid transactions.

    Args:
        df: Cleaned DataFrame.
        min_records: Minimum required row count.

    Raises:
        DataProcessingError: If the record count is below the minimum threshold.
    """
    validate_records(df)
    if len(df) < min_records:
        raise DataProcessingError(
            f"Dataset contains {len(df)} record(s), but a minimum of {min_records} is required to generate a report."
        )
