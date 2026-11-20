"""Data ingestion, column mapping, normalization, and validation modules.

Exposes primary entry points for loading, cleaning, mapping, and validating
raw financial disbursement transaction datasets.
"""

from reportgen.data.cleaner import (
    clean_amount_series,
    clean_category_series,
    clean_dataframe,
    clean_dataset,
    clean_date_series,
    clean_department_series,
    clean_text_series,
)
from reportgen.data.loader import (
    load_and_prepare_data,
    load_transaction_csv,
)
from reportgen.data.mapping import (
    CANONICAL_FIELDS,
    DEFAULT_COLUMN_SYNONYMS,
    load_column_mapping,
    load_mapping_file,
    normalize_header,
    resolve_column_mapping,
)
from reportgen.data.validator import (
    REQUIRED_CANONICAL_COLUMNS,
    validate_record_counts,
    validate_records,
    validate_schema,
)

__all__ = [
    "CANONICAL_FIELDS",
    "DEFAULT_COLUMN_SYNONYMS",
    "REQUIRED_CANONICAL_COLUMNS",
    "clean_amount_series",
    "clean_category_series",
    "clean_dataframe",
    "clean_dataset",
    "clean_date_series",
    "clean_department_series",
    "clean_text_series",
    "load_and_prepare_data",
    "load_column_mapping",
    "load_mapping_file",
    "load_transaction_csv",
    "normalize_header",
    "resolve_column_mapping",
    "validate_record_counts",
    "validate_records",
    "validate_schema",
]
