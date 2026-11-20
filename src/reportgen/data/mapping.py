"""Column alias resolution and mapping configuration.

Maps varied CSV column headers from diverse accounting systems to the canonical
schema expected by the downstream analytics and visualization pipeline.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Mapping
import yaml

from reportgen.config import DataLoadError


# Canonical schema fields recognized by reportgen
CANONICAL_FIELDS: tuple[str, ...] = (
    "date",
    "category",
    "amount",
    "description",
    "department",
)

# Built-in synonyms for automatic header detection.
# Ordered by matching priority: exact canonical names come first.
DEFAULT_COLUMN_SYNONYMS: dict[str, list[str]] = {
    "date": [
        "date",
        "transaction_date",
        "tx_date",
        "trans_date",
        "timestamp",
        "posted_date",
        "invoice_date",
        "expense_date",
    ],
    "category": [
        "category",
        "expense_category",
        "expense_type",
        "type",
        "cost_center",
        "bucket",
        "spend_category",
        "classification",
        "account",
        "gl_category",
    ],
    "amount": [
        "amount",
        "cost",
        "total",
        "spend",
        "net_amount",
        "price",
        "value",
        "transaction_amount",
        "charge",
    ],
    "description": [
        "description",
        "desc",
        "memo",
        "notes",
        "vendor",
        "merchant",
        "details",
        "name",
        "payee",
        "line_item",
    ],
    "department": [
        "department",
        "dept",
        "team",
        "business_unit",
        "division",
        "group",
    ],
}


def normalize_header(header: str) -> str:
    """Normalize a column header string for case- and separator-insensitive matching.

    Strips whitespace, converts to lowercase, and replaces spaces and hyphens
    with underscores. Surrounding quotes are also stripped.

    Args:
        header: Raw column header string from CSV or user configuration.

    Returns:
        Cleaned, snake_cased header string.
    """
    cleaned = header.strip().strip("'\"").lower()
    return re.sub(r"[\s\-]+", "_", cleaned)


def load_column_mapping(mapping_path: Path | str | None) -> dict[str, str]:
    """Load user-defined column overrides from a YAML mapping configuration file.

    Expects either a root-level dictionary of source-to-canonical column names,
    or a nested structure under a 'column_mapping' key:

    ```yaml
    column_mapping:
      tx_time: date
      spend_type: category
      gross_amount: amount
    ```

    Args:
        mapping_path: Path to the YAML file, or None if no custom mapping is provided.

    Returns:
        Dictionary mapping raw column names to canonical schema keys.

    Raises:
        DataLoadError: If the mapping file cannot be found, read, or contains invalid YAML.
    """
    if mapping_path is None:
        return {}

    path = Path(mapping_path)
    if not path.is_file():
        raise DataLoadError(
            f"Column mapping configuration file not found at '{path}'. "
            f"Verify the file path exists and is readable."
        )

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise DataLoadError(
            f"Failed to parse column mapping YAML file '{path}': {exc}. "
            f"Ensure the file contains valid YAML syntax."
        ) from exc
    except OSError as exc:
        raise DataLoadError(
            f"Could not read mapping file '{path}': {exc}."
        ) from exc

    if raw_data is None:
        return {}

    if not isinstance(raw_data, dict):
        raise DataLoadError(
            f"Invalid column mapping configuration in '{path}'. "
            f"Expected a dictionary or a 'column_mapping' key, received {type(raw_data).__name__}."
        )

    # Extract mapping from root or 'column_mapping' block
    mapping_dict = raw_data.get("column_mapping", raw_data)
    if not isinstance(mapping_dict, dict):
        raise DataLoadError(
            f"Invalid 'column_mapping' section in '{path}'. "
            f"Expected a dictionary of column pairs, received {type(mapping_dict).__name__}."
        )

    return {str(source): str(target) for source, target in mapping_dict.items()}


# Backward compatibility alias
load_mapping_file = load_column_mapping


def resolve_column_mapping(
    columns: list[str],
    custom_mapping: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Resolve raw CSV header names to canonical schema columns.

    Matches raw headers against custom overrides first, then falls back to built-in
    synonyms in priority order. Guarantees that each canonical field is assigned
    to at most one source column.

    Args:
        columns: List of raw header names found in the input CSV.
        custom_mapping: Optional user-defined mapping of source headers to canonical names.

    Returns:
        Dictionary mapping raw column names present in the input to their canonical target names.
    """
    result: dict[str, str] = {}
    assigned_canonical: set[str] = set()
    assigned_sources: set[str] = set()

    # Phase 1: Apply custom mapping overrides
    if custom_mapping:
        for src_col in columns:
            norm_src = normalize_header(src_col)
            for custom_k, custom_v in custom_mapping.items():
                norm_k = normalize_header(str(custom_k))
                norm_v = normalize_header(str(custom_v))

                # Case A: user wrote {source_column: canonical_column}
                if norm_src == norm_k and norm_v in CANONICAL_FIELDS:
                    if norm_v not in assigned_canonical and src_col not in assigned_sources:
                        result[src_col] = norm_v
                        assigned_canonical.add(norm_v)
                        assigned_sources.add(src_col)
                        break

                # Case B: user wrote {canonical_column: source_column}
                elif norm_src == norm_v and norm_k in CANONICAL_FIELDS:
                    if norm_k not in assigned_canonical and src_col not in assigned_sources:
                        result[src_col] = norm_k
                        assigned_canonical.add(norm_k)
                        assigned_sources.add(src_col)
                        break

    # Phase 2: Resolve remaining canonical columns via built-in synonyms
    for canonical in CANONICAL_FIELDS:
        if canonical in assigned_canonical:
            continue

        synonyms = DEFAULT_COLUMN_SYNONYMS.get(canonical, [])
        match_found = False

        for synonym in synonyms:
            norm_syn = normalize_header(synonym)
            for src_col in columns:
                if src_col in assigned_sources:
                    continue

                if normalize_header(src_col) == norm_syn:
                    result[src_col] = canonical
                    assigned_canonical.add(canonical)
                    assigned_sources.add(src_col)
                    match_found = True
                    break

            if match_found:
                break

    return result
