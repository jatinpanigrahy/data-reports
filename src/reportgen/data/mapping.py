"""Column alias resolution and mapping configuration.

Maps varied CSV column headers from diverse accounting systems to the canonical
schema expected by the downstream analytics and visualization pipeline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping


DEFAULT_COLUMN_SYNONYMS: dict[str, list[str]] = {
    "date": [
        "date", "transaction_date", "trans_date", "tx_date",
        "timestamp", "posted_date", "invoice_date", "expense_date",
    ],
    "category": [
        "category", "expense_category", "type", "spend_category",
        "classification", "account", "gl_category",
    ],
    "amount": [
        "amount", "cost", "spend", "total", "price",
        "value", "transaction_amount", "net_amount", "charge",
    ],
    "description": [
        "description", "merchant", "vendor", "name",
        "details", "memo", "payee", "line_item",
    ],
    "department": [
        "department", "dept", "cost_center", "business_unit",
        "team", "division", "group",
    ],
}


def load_mapping_file(mapping_path: Path) -> dict[str, str]:
    """Load user-defined column overrides from a YAML mapping configuration."""
    raise NotImplementedError("Mapping file loader will be implemented in Phase 2.")


def resolve_column_mapping(
    columns: list[str],
    custom_mapping: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Resolve raw CSV header names to canonical schema columns.

    Args:
        columns: List of raw header names found in the input CSV.
        custom_mapping: Optional explicit mapping of source headers to canonical names.

    Returns:
        Dictionary mapping raw column names to canonical schema keys.
    """
    raise NotImplementedError("Column mapping resolution will be implemented in Phase 2.")
