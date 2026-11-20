"""End-to-end integration tests for the reportgen orchestration pipeline.

Verifies complete execution through ingestion, statistical analysis,
visualization generation, and PDF compilation under varied configurations and failure modes.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch
import pytest

from reportgen import (
    DataLoadError,
    DataProcessingError,
    PDFBuildError,
    ReportConfig,
    SchemaValidationError,
    generate_report,
)
from reportgen.analytics.models import ReportAnalytics
from reportgen.pipeline import run_pipeline
from tests.test_pdf_builder import count_pdf_pages


def test_generate_report_sample_data(tmp_path: Path) -> None:
    """Verify that generating a report from canonical sample data succeeds and produces a 1-page PDF."""
    input_path = Path("data/sample_expenses.csv")
    output_path = tmp_path / "test_executive_report.pdf"

    result_path = generate_report(
        input_path=input_path,
        output_path=output_path,
    )

    assert result_path == output_path.resolve()
    assert output_path.is_file()
    assert output_path.stat().st_size > 10_000, "Expected PDF file size > 10 KB."
    assert count_pdf_pages(output_path) == 1, "Expected strictly 1 page in generated executive report."


def test_generate_report_with_custom_titles_and_currency(tmp_path: Path) -> None:
    """Verify that custom headline, subtitle, and currency symbol propagate through the pipeline."""
    input_path = Path("data/sample_expenses.csv")
    output_path = tmp_path / "custom_report.pdf"

    result_path = generate_report(
        input_path=input_path,
        output_path=output_path,
        title="European Division Expenditures",
        subtitle="FY26 Q1 Cross-Border Disbursements",
        currency="€",
    )

    assert result_path.is_file()
    assert count_pdf_pages(result_path) == 1


def test_generate_report_default_output_resolution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that omitting output_path defaults to output/<stem>_report.pdf."""
    monkeypatch.chdir(tmp_path)

    # Create a small valid CSV
    csv_file = tmp_path / "quarterly_spend.csv"
    csv_file.write_text(
        "date,category,amount,description,department\n"
        "2026-01-15,Software,150.00,Subscription,Engineering\n"
        "2026-01-20,Hardware,450.00,Monitor,Engineering\n"
        "2026-02-10,Travel,320.00,Train,Sales\n",
        encoding="utf-8",
    )

    result_path = generate_report(input_path=csv_file)
    expected_path = (tmp_path / "output" / "quarterly_spend_report.pdf").resolve()

    assert result_path == expected_path
    assert expected_path.is_file()
    assert count_pdf_pages(expected_path) == 1


def test_generate_report_with_report_config(tmp_path: Path) -> None:
    """Verify that passing a ReportConfig dataclass executes the full pipeline cleanly."""
    input_path = Path("data/sample_expenses.csv")
    output_path = tmp_path / "config_run.pdf"

    config = ReportConfig(
        input_path=input_path,
        output_path=output_path,
        title="Automated Pipeline Validation",
        subtitle="Verification Run",
        currency_symbol="$",
    )

    result_path = generate_report(config=config)
    assert result_path == output_path.resolve()
    assert output_path.is_file()
    assert count_pdf_pages(output_path) == 1


def test_run_pipeline_progress_callback_and_analytics(tmp_path: Path) -> None:
    """Verify that run_pipeline invokes the progress callback and returns the computed analytics."""
    input_path = Path("data/sample_expenses.csv")
    output_path = tmp_path / "callback_run.pdf"
    progress_messages: list[str] = []

    result_path, analytics = run_pipeline(
        input_path=input_path,
        output_path=output_path,
        progress_callback=progress_messages.append,
    )

    assert result_path.is_file()
    assert isinstance(analytics, ReportAnalytics)
    assert analytics.raw_transaction_count == 250
    assert analytics.raw_total_spend == pytest.approx(218_435.50, abs=0.1)

    # Check progress messages emitted
    assert any("[INFO] Reading input data" in msg for msg in progress_messages)
    assert any("[INFO] Resolved 250 transactions" in msg for msg in progress_messages)
    assert any("[INFO] Calculated executive KPIs" in msg for msg in progress_messages)
    assert any("[INFO] Generated category breakdown" in msg for msg in progress_messages)
    assert any("[INFO] Compiled single-page PDF" in msg for msg in progress_messages)


def test_generate_report_with_custom_mapping(tmp_path: Path) -> None:
    """Verify pipeline execution with arbitrary column names using a YAML mapping configuration."""
    csv_file = tmp_path / "vendor_export.csv"
    csv_file.write_text(
        "trans_date,classification,gross_spend,vendor_name,team\n"
        "2026-01-10,Cloud Services,1250.00,AWS Hosting,Infrastructure\n"
        "2026-01-15,Software,340.00,GitHub Enterprise,Engineering\n"
        "2026-02-01,Travel,620.00,Delta Airlines,Executive\n"
        "2026-02-14,Meals,85.50,Dinner Meeting,Sales\n"
        "2026-03-01,Hardware,2100.00,Apple Store,Design\n",
        encoding="utf-8",
    )

    mapping_file = tmp_path / "mapping.yaml"
    mapping_file.write_text(
        "column_mapping:\n"
        "  trans_date: date\n"
        "  classification: category\n"
        "  gross_spend: amount\n"
        "  vendor_name: description\n"
        "  team: department\n",
        encoding="utf-8",
    )

    output_path = tmp_path / "mapped_report.pdf"
    result_path = generate_report(
        input_path=csv_file,
        output_path=output_path,
        mapping_path=mapping_file,
    )

    assert result_path.is_file()
    assert count_pdf_pages(result_path) == 1


def test_pipeline_missing_input_file_raises_data_load_error(tmp_path: Path) -> None:
    """Verify that a non-existent CSV file raises DataLoadError with exit code 10."""
    missing_path = tmp_path / "does_not_exist.csv"

    with pytest.raises(DataLoadError) as exc_info:
        generate_report(input_path=missing_path)

    assert exc_info.value.exit_code == 10
    assert "not found" in str(exc_info.value)


def test_pipeline_missing_canonical_columns_raises_schema_validation_error(tmp_path: Path) -> None:
    """Verify that input lacking required canonical fields raises SchemaValidationError with exit code 11."""
    bad_csv = tmp_path / "unmapped.csv"
    bad_csv.write_text(
        "order_id,user_name,score\n"
        "1,Alice,95\n"
        "2,Bob,88\n",
        encoding="utf-8",
    )

    with pytest.raises(SchemaValidationError) as exc_info:
        generate_report(input_path=bad_csv)

    assert exc_info.value.exit_code == 11
    assert "Unable to resolve required canonical columns" in str(exc_info.value)


def test_pipeline_empty_csv_raises_data_processing_or_load_error(tmp_path: Path) -> None:
    """Verify that an empty or zero-row dataset raises DataProcessingError (exit code 12)."""
    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text("date,category,amount\n", encoding="utf-8")

    with pytest.raises(DataProcessingError) as exc_info:
        generate_report(input_path=empty_csv)

    assert exc_info.value.exit_code == 12


def test_pipeline_pdf_build_error_propagation(tmp_path: Path) -> None:
    """Verify that PDF compilation errors raise PDFBuildError with exit code 13."""
    input_path = Path("data/sample_expenses.csv")
    output_path = tmp_path / "fail_report.pdf"

    with patch("reportgen.pipeline.build_pdf_report", side_effect=PDFBuildError("Page budget overflow")):
        with pytest.raises(PDFBuildError) as exc_info:
            generate_report(input_path=input_path, output_path=output_path)

        assert exc_info.value.exit_code == 13
