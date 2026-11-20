"""File ingestion and CSV parsing.

Handles file loading, character encoding detection, delimiter sniffing,
and coordinates initial column mapping.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd


class DataLoadError(Exception):
    """Raised when an input file cannot be found, read, or decoded."""


def load_transaction_csv(file_path: Path, mapping_path: Path | None = None) -> pd.DataFrame:
    """Read a CSV file and return a DataFrame mapped to the canonical schema.

    Args:
        file_path: Path to the raw CSV file.
        mapping_path: Optional path to a YAML column mapping file.

    Returns:
        DataFrame with columns renamed to canonical schema names.

    Raises:
        DataLoadError: If file cannot be found or read.
    """
    raise NotImplementedError("Transaction loader will be implemented in Phase 2.")
