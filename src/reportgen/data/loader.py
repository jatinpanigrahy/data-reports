"""File ingestion, encoding detection, and CSV parsing.

Handles file loading, character encoding fallback, delimiter sniffing,
and coordinates column alias mapping, cleaning, and validation.
"""

from __future__ import annotations

import csv
from pathlib import Path
import pandas as pd

from reportgen.config import DataLoadError
from reportgen.data.cleaner import clean_dataset
from reportgen.data.mapping import load_column_mapping, resolve_column_mapping
from reportgen.data.validator import validate_records, validate_schema


def _detect_encoding_and_delimiter(path: Path) -> tuple[str, str]:
    """Detect file encoding and CSV delimiter defensively.

    Tries standard encodings in order: utf-8, utf-8-sig, latin-1.
    Uses csv.Sniffer with heuristic fallback for standard delimiters (comma, semicolon, tab, pipe).

    Args:
        path: Path to the target CSV file.

    Returns:
        Tuple of (encoding_name, delimiter_character).

    Raises:
        DataLoadError: If file cannot be read or decoded in any supported encoding.
    """
    encodings = ("utf-8", "utf-8-sig", "latin-1")
    chosen_encoding: str | None = None
    sample = ""

    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                sample = f.read(8192)
            chosen_encoding = enc
            break
        except (UnicodeDecodeError, OSError):
            continue

    if chosen_encoding is None:
        raise DataLoadError(
            f"Unable to decode '{path}' using supported encodings (utf-8, utf-8-sig, latin-1). "
            f"Ensure the file is saved as standard UTF-8 or Latin-1 text."
        )

    if not sample.strip():
        return chosen_encoding, ","

    delimiter = ","
    try:
        sample_lines = "\n".join(sample.splitlines()[:10])
        if sample_lines:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample_lines, delimiters=",\t;|")
            if dialect.delimiter in (",", "\t", ";", "|"):
                delimiter = dialect.delimiter
    except Exception:
        # Fallback: evaluate delimiter counts in the first non-empty line
        first_line = ""
        for line in sample.splitlines():
            if line.strip():
                first_line = line
                break
        counts = {
            ",": first_line.count(","),
            ";": first_line.count(";"),
            "\t": first_line.count("\t"),
            "|": first_line.count("|"),
        }
        best_delim, count = max(counts.items(), key=lambda item: item[1])
        if count > 0:
            delimiter = best_delim

    return chosen_encoding, delimiter


def load_and_prepare_data(
    file_path: Path | str,
    mapping_path: Path | str | None = None,
) -> pd.DataFrame:
    """Load, map, sanitize, and validate an input transaction CSV.

    Performs complete ingestion workflow:
    1. Validates file existence and readability.
    2. Detects character encoding with fallbacks (utf-8, utf-8-sig, latin-1).
    3. Sniffs delimiter (comma, semicolon, tab).
    4. Resolves column aliases using custom YAML mapping and built-in synonyms.
    5. Validates presence of required canonical columns (date, category, amount).
    6. Sanitizes currency, datetime, and text fields.
    7. Validates records integrity (non-empty, correct data types).

    Args:
        file_path: Path to the input CSV file.
        mapping_path: Optional path to a YAML column mapping configuration.

    Returns:
        Cleaned, validated pandas DataFrame conforming to canonical reporting schema.

    Raises:
        DataLoadError: If file is missing, empty, or unreadable.
        SchemaValidationError: If required canonical columns cannot be resolved.
        DataProcessingError: If dataset has no valid records or invalid data types after cleaning.
    """
    path = Path(file_path)
    if not path.is_file():
        raise DataLoadError(
            f"Input transaction file not found at '{path}'. "
            f"Please verify that the file exists and is accessible."
        )

    encoding, delimiter = _detect_encoding_and_delimiter(path)

    try:
        raw_df = pd.read_csv(path, encoding=encoding, sep=delimiter)
    except pd.errors.EmptyDataError:
        raise DataLoadError(
            f"Input CSV file '{path}' is empty or contains no readable columns."
        )
    except Exception as exc:
        raise DataLoadError(
            f"Failed to read input CSV file '{path}': {exc}."
        ) from exc

    if raw_df.empty and len(raw_df.columns) == 0:
        raise DataLoadError(
            f"Input CSV file '{path}' contains no columns or data."
        )

    # Resolve column mappings
    custom_mapping = load_column_mapping(mapping_path) if mapping_path else None
    col_mapping = resolve_column_mapping(list(raw_df.columns), custom_mapping=custom_mapping)

    mapped_df = raw_df.rename(columns=col_mapping)

    # Validate that canonical required columns are resolved
    validate_schema(mapped_df, source_name=str(path))

    # Clean and coerce data types
    cleaned_df = clean_dataset(mapped_df)

    # Validate resulting records integrity
    validate_records(cleaned_df)

    return cleaned_df


# Backward compatibility alias
load_transaction_csv = load_and_prepare_data
