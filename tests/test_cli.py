"""Integration and behavior tests for the reportgen CLI interface.

Tests argument parsing, exit codes (0, 1, 2, 10, 11, 12, 13), humanized error messages,
traceback suppression, flag combinations, and subprocess invocation.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
import pytest

from reportgen import __version__
from reportgen.cli import build_parser, main
from reportgen.config import PDFBuildError, RenderingError
from tests.test_pdf_builder import count_pdf_pages


# -----------------------------------------------------------------------------
# 1. Successful Executions (Exit Code 0)
# -----------------------------------------------------------------------------

def test_cli_success_positional_input(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Verify CLI completes successfully with positional input argument and exit code 0."""
    pdf_path = tmp_path / "positional_report.pdf"
    exit_code = main(["data/sample_expenses.csv", "-o", str(pdf_path)])

    assert exit_code == 0
    assert pdf_path.is_file()
    assert count_pdf_pages(pdf_path) == 1

    captured = capsys.readouterr()
    assert "[INFO] Reading input data" in captured.out
    assert "[SUCCESS] Report generated:" in captured.out
    assert "250 transactions" in captured.out
    assert "$218,435.50" in captured.out


def test_cli_success_flag_input(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Verify CLI completes successfully with -i/--input flag argument."""
    pdf_path = tmp_path / "flag_report.pdf"
    exit_code = main(["-i", "data/sample_expenses.csv", "-o", str(pdf_path)])

    assert exit_code == 0
    assert pdf_path.is_file()
    assert count_pdf_pages(pdf_path) == 1

    captured = capsys.readouterr()
    assert "[SUCCESS]" in captured.out


def test_cli_quiet_mode_suppresses_stdout(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Verify that -q/--quiet silences all progress and success logs from stdout."""
    pdf_path = tmp_path / "quiet_report.pdf"
    exit_code = main(["-i", "data/sample_expenses.csv", "-o", str(pdf_path), "-q"])

    assert exit_code == 0
    assert pdf_path.is_file()

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_cli_custom_mapping_and_options(tmp_path: Path) -> None:
    """Verify CLI handles custom column mapping YAML, titles, and currency symbol."""
    csv_file = tmp_path / "custom_data.csv"
    csv_file.write_text(
        "tx_date,line_item,cost,vendor,division\n"
        "2026-01-15,Software,150.00,GitHub,Tech\n"
        "2026-01-20,Hardware,450.00,Dell,Tech\n"
        "2026-02-10,Travel,320.00,British Airways,Sales\n",
        encoding="utf-8",
    )

    mapping_file = tmp_path / "custom_mapping.yaml"
    mapping_file.write_text(
        "column_mapping:\n"
        "  tx_date: date\n"
        "  line_item: category\n"
        "  cost: amount\n"
        "  vendor: description\n"
        "  division: department\n",
        encoding="utf-8",
    )

    pdf_path = tmp_path / "custom_mapped_out.pdf"
    exit_code = main([
        str(csv_file),
        "-m", str(mapping_file),
        "-o", str(pdf_path),
        "-t", "UK Division Disbursements",
        "-s", "Q1 Infrastructure",
        "-c", "£",
    ])

    assert exit_code == 0
    assert pdf_path.is_file()
    assert count_pdf_pages(pdf_path) == 1


def test_cli_open_flag_launches_viewer(tmp_path: Path) -> None:
    """Verify --open calls the platform launcher without crashing."""
    pdf_path = tmp_path / "open_test.pdf"
    with patch("reportgen.cli._open_file") as mock_open:
        exit_code = main(["data/sample_expenses.csv", "-o", str(pdf_path), "--open"])
        assert exit_code == 0
        mock_open.assert_called_once()


# -----------------------------------------------------------------------------
# 2. CLI Argument & Syntax Errors (Exit Code 2)
# -----------------------------------------------------------------------------

def test_cli_missing_input_argument_returns_code_2(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify missing required input returns UNIX exit code 2."""
    exit_code = main([])
    assert exit_code == 2

    captured = capsys.readouterr()
    assert "error:" in captured.err.lower()
    assert "input" in captured.err.lower()


def test_cli_unrecognized_argument_returns_code_2(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify unrecognized CLI flag returns UNIX exit code 2."""
    exit_code = main(["--unrecognized-nonexistent-flag"])
    assert exit_code == 2

    captured = capsys.readouterr()
    assert "error:" in captured.err.lower()


# -----------------------------------------------------------------------------
# 3. Domain Exception Exit Codes & Diagnostics (Exit Codes 10, 11, 12, 13)
# -----------------------------------------------------------------------------

def test_cli_data_load_error_returns_code_10(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Verify missing input file triggers DataLoadError and exit code 10."""
    missing_file = tmp_path / "nonexistent.csv"
    exit_code = main([str(missing_file)])

    assert exit_code == 10
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err
    assert "not found" in captured.err
    # Traceback must be suppressed by default
    assert "Traceback (most recent call last)" not in captured.err


def test_cli_schema_validation_error_returns_code_11(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Verify missing canonical columns trigger SchemaValidationError with guide and exit code 11."""
    bad_csv = tmp_path / "invalid_schema.csv"
    bad_csv.write_text("item_id,title,value\n1,Widget,50\n", encoding="utf-8")

    exit_code = main([str(bad_csv)])

    assert exit_code == 11
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err
    assert "Unable to resolve required canonical columns" in captured.err
    assert "column_mapping:" in captured.err
    assert "Traceback (most recent call last)" not in captured.err


def test_cli_data_processing_error_returns_code_12(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Verify empty dataset with valid headers triggers DataProcessingError and exit code 12."""
    empty_csv = tmp_path / "empty_valid_headers.csv"
    empty_csv.write_text("date,category,amount\n", encoding="utf-8")

    exit_code = main([str(empty_csv)])

    assert exit_code == 12
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err
    assert "Traceback (most recent call last)" not in captured.err


def test_cli_pdf_build_error_returns_code_13(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Verify PDF build failure triggers PDFBuildError and exit code 13."""
    pdf_path = tmp_path / "failed_budget.pdf"

    with patch("reportgen.pipeline.build_pdf_report", side_effect=PDFBuildError("Document exceeded strict 1-page budget.")):
        exit_code = main(["data/sample_expenses.csv", "-o", str(pdf_path)])

    assert exit_code == 13
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err
    assert "Document exceeded strict 1-page budget." in captured.err
    assert "Traceback (most recent call last)" not in captured.err


def test_cli_rendering_error_returns_code_13(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Verify visualization failure triggers RenderingError and exit code 13."""
    pdf_path = tmp_path / "failed_render.pdf"

    with patch("reportgen.pipeline.render_report_charts", side_effect=RenderingError("Chart figure failed to render.")):
        exit_code = main(["data/sample_expenses.csv", "-o", str(pdf_path)])

    assert exit_code == 13
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err
    assert "Chart figure failed to render." in captured.err


# -----------------------------------------------------------------------------
# 4. General Runtime Error & Traceback Flag (Exit Code 1)
# -----------------------------------------------------------------------------

def test_cli_unexpected_error_returns_code_1(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify unexpected non-domain exceptions return exit code 1 with clean message."""
    with patch("reportgen.cli.run_pipeline", side_effect=RuntimeError("Unexpected hardware I/O glitch")):
        exit_code = main(["data/sample_expenses.csv"])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "[ERROR] Unexpected runtime failure: Unexpected hardware I/O glitch" in captured.err
    assert "Traceback (most recent call last)" not in captured.err


def test_cli_verbose_flag_displays_full_traceback(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify passing -v/--verbose prints full Python traceback on error."""
    with patch("reportgen.cli.run_pipeline", side_effect=RuntimeError("Debuggable explosion")):
        exit_code = main(["data/sample_expenses.csv", "-v"])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Traceback (most recent call last)" in captured.err
    assert "Debuggable explosion" in captured.err


def test_cli_keyboard_interrupt_returns_code_130(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify user interruption via SIGINT/Ctrl+C returns exit code 130 gracefully."""
    with patch("reportgen.cli.run_pipeline", side_effect=KeyboardInterrupt):
        exit_code = main(["data/sample_expenses.csv"])

    assert exit_code == 130
    captured = capsys.readouterr()
    assert "Operation interrupted by user" in captured.err


# -----------------------------------------------------------------------------
# 5. Metadata Flags (--version, --help) & Subprocess Invocations
# -----------------------------------------------------------------------------

def test_cli_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify --version prints reportgen 0.1.0 and returns 0."""
    exit_code = main(["--version"])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert f"reportgen {__version__}" in captured.out


def test_cli_help_flag(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify --help prints usage manual and returns 0."""
    exit_code = main(["--help"])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "usage: reportgen" in captured.out
    assert "--output" in captured.out
    assert "--currency" in captured.out


def test_subprocess_execution(tmp_path: Path) -> None:
    """Verify end-to-end execution of `python -m reportgen` via real subprocess."""
    pdf_path = tmp_path / "subprocess_report.pdf"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "reportgen",
            "data/sample_expenses.csv",
            "-o",
            str(pdf_path),
        ],
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, f"CLI subprocess failed: {proc.stderr}"
    assert "[SUCCESS] Report generated:" in proc.stdout
    assert pdf_path.is_file()
    assert count_pdf_pages(pdf_path) == 1
