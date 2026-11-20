"""Tests for CSV ingestion, delimiter sniffing, encoding fallbacks, and schema validation."""

from __future__ import annotations

import math
from pathlib import Path
import pandas as pd
import pytest

from reportgen.config import DataLoadError, DataProcessingError, SchemaValidationError
from reportgen.data.loader import load_and_prepare_data, load_transaction_csv


def test_load_canonical_sample_expenses(sample_csv_path: Path) -> None:
    """Verify that the sample dataset loads cleanly and matches canonical metrics."""
    df = load_and_prepare_data(sample_csv_path)

    # 1. Total row count matches expected 250
    assert len(df) == 250

    # 2. Schema columns match canonical names
    expected_cols = ["date", "category", "amount", "description", "department"]
    assert list(df.columns) == expected_cols

    # 3. Data types conform to pipeline contract
    assert pd.api.types.is_datetime64_any_dtype(df["date"])
    assert pd.api.types.is_float_dtype(df["amount"])
    assert pd.api.types.is_string_dtype(df["category"])
    assert pd.api.types.is_string_dtype(df["description"])
    assert pd.api.types.is_string_dtype(df["department"])

    # 4. Total net spend matches golden metric ($218,435.50)
    assert math.isclose(df["amount"].sum(), 218435.50, rel_tol=1e-3)

    # 5. Chronologically sorted ascending
    assert df["date"].is_monotonic_increasing


def test_delimiter_sniffing_semicolon_and_tab(tmp_path: Path) -> None:
    """Verify that delimiter sniffing automatically detects semicolon and tab separators."""
    # Semicolon-delimited file
    semi_file = tmp_path / "semicolon_data.csv"
    semi_file.write_text(
        "Date;Category;Amount;Description;Department\n"
        "2026-01-10;Software & SaaS;120.00;Figma License;Design\n"
        "2026-01-15;Cloud Infrastructure;1500.00;AWS Compute;Engineering\n",
        encoding="utf-8",
    )
    semi_df = load_and_prepare_data(semi_file)
    assert len(semi_df) == 2
    assert math.isclose(semi_df["amount"].sum(), 1620.00)

    # Tab-delimited file (TSV)
    tab_file = tmp_path / "tab_data.tsv"
    tab_file.write_text(
        "Date\tCategory\tAmount\tDescription\tDepartment\n"
        "2026-02-01\tTravel & Logistics\t450.50\tClient Flight\tSales\n"
        "2026-02-05\tOffice Equipment\t85.00\tKeyboard\tOperations\n",
        encoding="utf-8",
    )
    tab_df = load_and_prepare_data(tab_file)
    assert len(tab_df) == 2
    assert math.isclose(tab_df["amount"].sum(), 535.50)


def test_encoding_fallback_latin1_and_utf8_sig(tmp_path: Path) -> None:
    """Verify decoding works for latin-1 and utf-8-sig (with BOM)."""
    # Latin-1 file with accented characters
    latin1_file = tmp_path / "latin1_data.csv"
    latin1_content = (
        "Date,Category,Amount,Description,Department\n"
        "2026-01-20,Services,250.00,Café & Catering Déjeuner,Direction\n"
    )
    latin1_file.write_bytes(latin1_content.encode("latin-1"))

    latin1_df = load_and_prepare_data(latin1_file)
    assert len(latin1_df) == 1
    assert "Café" in latin1_df.iloc[0]["description"]

    # UTF-8 with BOM (utf-8-sig)
    utf8_sig_file = tmp_path / "utf8_sig_data.csv"
    utf8_sig_content = (
        "Date,Category,Amount,Description,Department\n"
        "2026-03-01,Hardware,99.99,Monitor stand,Engineering\n"
    )
    utf8_sig_file.write_bytes(utf8_sig_content.encode("utf-8-sig"))

    utf8_sig_df = load_and_prepare_data(utf8_sig_file)
    assert len(utf8_sig_df) == 1
    assert math.isclose(utf8_sig_df.iloc[0]["amount"], 99.99)


def test_missing_required_columns_raises_schema_validation_error(tmp_path: Path) -> None:
    """Verify that missing required canonical columns raise SchemaValidationError with helpful remediation."""
    bad_csv = tmp_path / "missing_columns.csv"
    bad_csv.write_text(
        "transaction_code,vendor_name,memo\n"
        "TX101,Acme Corp,Office supplies\n",
        encoding="utf-8",
    )

    with pytest.raises(SchemaValidationError) as exc_info:
        load_and_prepare_data(bad_csv)

    err_msg = str(exc_info.value)
    # Check that missing columns are listed
    assert "date" in err_msg
    assert "category" in err_msg
    assert "amount" in err_msg
    # Check that available columns are listed
    assert "transaction_code" in err_msg
    assert "vendor_name" in err_msg
    # Check that remediation instructions and YAML example are provided
    assert "column_mapping:" in err_msg
    assert "--mapping" in err_msg


def test_custom_yaml_mapping_file_overrides(tmp_path: Path) -> None:
    """Verify that an explicit YAML mapping file resolves arbitrary non-standard column headers."""
    csv_file = tmp_path / "custom_headers.csv"
    csv_file.write_text(
        "tx_time,spend_type,line_cost,vendor_name,cost_center_code\n"
        "2026-01-12,Hosting,500.00,CloudFlare,Infra\n"
        "2026-01-15,Subscriptions,35.00,GitHub,Engineering\n",
        encoding="utf-8",
    )

    mapping_file = tmp_path / "custom_mapping.yaml"
    mapping_file.write_text(
        "column_mapping:\n"
        "  tx_time: date\n"
        "  spend_type: category\n"
        "  line_cost: amount\n"
        "  vendor_name: description\n"
        "  cost_center_code: department\n",
        encoding="utf-8",
    )

    df = load_and_prepare_data(csv_file, mapping_path=mapping_file)
    assert len(df) == 2
    assert list(df.columns) == ["date", "category", "amount", "description", "department"]
    assert math.isclose(df["amount"].sum(), 535.00)
    assert df.iloc[0]["description"] == "CloudFlare"
    assert df.iloc[0]["department"] == "Infra"


def test_empty_csv_raises_data_load_error(tmp_path: Path) -> None:
    """Verify that an entirely empty (0-byte) CSV file raises DataLoadError."""
    empty_file = tmp_path / "empty.csv"
    empty_file.write_text("", encoding="utf-8")

    with pytest.raises(DataLoadError) as exc_info:
        load_and_prepare_data(empty_file)

    assert "empty" in str(exc_info.value).lower()


def test_all_invalid_rows_raises_data_processing_error(tmp_path: Path) -> None:
    """Verify that a CSV where all rows have unparseable values raises DataProcessingError."""
    invalid_data_file = tmp_path / "all_invalid.csv"
    invalid_data_file.write_text(
        "Date,Category,Amount\n"
        "not_a_date,Software,invalid_cost\n"
        "bad_date,Hardware,not_a_number\n",
        encoding="utf-8",
    )

    with pytest.raises(DataProcessingError) as exc_info:
        load_and_prepare_data(invalid_data_file)

    assert "No valid transaction records found" in str(exc_info.value)


def test_header_only_csv_raises_data_processing_error(tmp_path: Path) -> None:
    """Verify that a CSV with headers but no rows raises DataProcessingError."""
    header_only_file = tmp_path / "header_only.csv"
    header_only_file.write_text(
        "Date,Category,Amount,Description,Department\n",
        encoding="utf-8",
    )

    with pytest.raises(DataProcessingError) as exc_info:
        load_and_prepare_data(header_only_file)

    assert "No valid transaction records found" in str(exc_info.value)


def test_missing_files_raise_data_load_error(tmp_path: Path) -> None:
    """Verify that non-existent data or mapping files raise DataLoadError."""
    non_existent_csv = tmp_path / "does_not_exist.csv"
    with pytest.raises(DataLoadError) as exc_info:
        load_and_prepare_data(non_existent_csv)
    assert "not found" in str(exc_info.value).lower()

    # Valid CSV, but non-existent mapping file
    valid_csv = tmp_path / "valid.csv"
    valid_csv.write_text("Date,Category,Amount\n2026-01-01,Test,10.0\n", encoding="utf-8")
    non_existent_mapping = tmp_path / "no_mapping.yaml"

    with pytest.raises(DataLoadError) as exc_info:
        load_and_prepare_data(valid_csv, mapping_path=non_existent_mapping)
    assert "not found" in str(exc_info.value).lower()


def test_load_transaction_csv_alias(sample_csv_path: Path) -> None:
    """Verify that load_transaction_csv works identically to load_and_prepare_data."""
    df1 = load_and_prepare_data(sample_csv_path)
    df2 = load_transaction_csv(sample_csv_path)
    pd.testing.assert_frame_equal(df1, df2)


def test_delimiter_sniffing_pipe(tmp_path: Path) -> None:
    """Verify that pipe-delimited CSVs are correctly sniffed and parsed."""
    pipe_file = tmp_path / "pipe_data.csv"
    pipe_file.write_text(
        "Date|Category|Amount\n"
        "2026-03-10|Hosting|75.00\n",
        encoding="utf-8",
    )
    df = load_and_prepare_data(pipe_file)
    assert len(df) == 1
    assert math.isclose(df.iloc[0]["amount"], 75.00)
    assert df.iloc[0]["description"] == "Unknown Transaction"
    assert df.iloc[0]["department"] == "General"


def test_custom_mapping_inverted_and_invalid_yaml(tmp_path: Path) -> None:
    """Verify inverted custom mapping syntax and error handling on invalid YAML files."""
    csv_file = tmp_path / "inverted.csv"
    csv_file.write_text("tx_col,cat_col,cost_col\n2026-01-01,Dev,50.0\n", encoding="utf-8")

    # Inverted mapping: canonical_name: source_column
    inverted_yaml = tmp_path / "inverted.yaml"
    inverted_yaml.write_text(
        "column_mapping:\n"
        "  date: tx_col\n"
        "  category: cat_col\n"
        "  amount: cost_col\n",
        encoding="utf-8",
    )
    df = load_and_prepare_data(csv_file, mapping_path=inverted_yaml)
    assert len(df) == 1
    assert list(df.columns) == ["date", "category", "amount", "description", "department"]

    # Malformed YAML
    broken_yaml = tmp_path / "broken.yaml"
    broken_yaml.write_text("column_mapping: [unclosed list", encoding="utf-8")
    with pytest.raises(DataLoadError) as exc_info:
        load_and_prepare_data(csv_file, mapping_path=broken_yaml)
    assert "YAML" in str(exc_info.value) or "parse" in str(exc_info.value)


def test_validator_functions_directly() -> None:
    """Verify validator functions raise appropriate exceptions under faulty inputs."""
    from reportgen.data.validator import validate_record_counts, validate_records, validate_schema

    # 1. Missing canonical column
    df_missing = pd.DataFrame({"date": [pd.Timestamp("2026-01-01")], "amount": [10.0]})
    with pytest.raises(SchemaValidationError):
        validate_schema(df_missing)

    # 2. Non-numeric amount
    df_bad_amount = pd.DataFrame({
        "date": [pd.Timestamp("2026-01-01")],
        "category": ["Dev"],
        "amount": ["not_numeric"],
    })
    with pytest.raises(DataProcessingError) as exc_info:
        validate_records(df_bad_amount)
    assert "numeric" in str(exc_info.value)

    # 3. Non-datetime date
    df_bad_date = pd.DataFrame({
        "date": ["not_a_timestamp"],
        "category": ["Dev"],
        "amount": [100.0],
    })
    with pytest.raises(DataProcessingError) as exc_info:
        validate_records(df_bad_date)
    assert "datetime64" in str(exc_info.value)

    # 4. Record count threshold
    df_valid = pd.DataFrame({
        "date": [pd.Timestamp("2026-01-01")],
        "category": ["Dev"],
        "amount": [100.0],
    })
    with pytest.raises(DataProcessingError) as exc_info:
        validate_record_counts(df_valid, min_records=5)
    assert "minimum of 5 is required" in str(exc_info.value)
