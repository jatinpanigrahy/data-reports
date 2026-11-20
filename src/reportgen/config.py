"""Configuration structures, geometry definitions, layout constants, and domain exceptions.

Holds page dimensions, color tokens, runtime report settings, and the domain
exception taxonomy used throughout the report generation lifecycle.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


# US Letter dimensions in PostScript points (72 points per inch)
PAGE_WIDTH_PTS = 612.0   # 8.5 inches
PAGE_HEIGHT_PTS = 792.0  # 11.0 inches
PAGE_MARGIN_PTS = 36.0   # 0.5 inch margins

# Printable canvas geometry
USABLE_WIDTH_PTS = PAGE_WIDTH_PTS - (2 * PAGE_MARGIN_PTS)    # 540.0 pt
USABLE_HEIGHT_PTS = PAGE_HEIGHT_PTS - (2 * PAGE_MARGIN_PTS)  # 720.0 pt


# -----------------------------------------------------------------------------
# Domain Exception Taxonomy
# -----------------------------------------------------------------------------

class ReportGenError(Exception):
    """Base domain exception for reportgen pipeline failures.

    All domain-specific errors inherit from this class to allow callers to catch
    any internal failure cleanly without masking standard system exceptions.
    """

    exit_code: int = 1


class DataLoadError(ReportGenError):
    """Raised when an input file or mapping configuration cannot be found, read, or decoded.

    Maps to CLI exit code 10.
    """

    exit_code: int = 10


class SchemaValidationError(ReportGenError):
    """Raised when required canonical fields cannot be resolved after mapping.

    Maps to CLI exit code 11.

    Args:
        message_or_missing: Either a humanized error string or a list of missing canonical columns.
        available_columns: Column headers discovered in the source dataset for diagnostic feedback.
        source_name: Path or descriptor of the source dataset.
    """

    exit_code: int = 11

    def __init__(
        self,
        message_or_missing: str | list[str],
        available_columns: list[str] | None = None,
        source_name: str | None = None,
    ) -> None:
        if isinstance(message_or_missing, list):
            self.missing_columns = message_or_missing
            self.available_columns = available_columns or []
            self.source_name = source_name or "input dataset"
            msg = self._build_diagnostic_message()
            super().__init__(msg)
        else:
            self.missing_columns = []
            self.available_columns = available_columns or []
            self.source_name = source_name or "input dataset"
            super().__init__(message_or_missing)

    def _build_diagnostic_message(self) -> str:
        missing_fmt = ", ".join(f"'{col}'" for col in self.missing_columns)
        available_fmt = (
            ", ".join(f"'{col}'" for col in self.available_columns)
            if self.available_columns
            else "None detected"
        )
        sample_mappings = "\n".join(
            f"    <your_{col}_column>: {col}" for col in self.missing_columns
        )
        return (
            f"Unable to resolve required canonical columns in {self.source_name}: {missing_fmt}.\n"
            f"Detected columns in input: {available_fmt}.\n\n"
            f"To resolve this, specify a custom YAML column mapping via --mapping. Example format:\n"
            f"  column_mapping:\n"
            f"{sample_mappings}"
        )


class DataProcessingError(ReportGenError):
    """Raised when data values cannot be coerced or the dataset contains no usable rows.

    Maps to CLI exit code 12.
    """

    exit_code: int = 12


class RenderingError(ReportGenError):
    """Raised when Matplotlib encounters an unrecoverable failure during visual rendering.

    Maps to CLI exit code 13.
    """

    exit_code: int = 13


class PDFBuildError(ReportGenError):
    """Raised when ReportLab fails to compile the document or breaches the single-page budget.

    Maps to CLI exit code 13.
    """

    exit_code: int = 13


# -----------------------------------------------------------------------------
# Runtime Configuration Model
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class ReportConfig:
    """Runtime configuration parameters for report generation."""

    input_path: Path
    output_path: Path
    title: str = "Financial Disbursement Report"
    subtitle: str = "Executive Spend & Variance Summary"
    mapping_path: Path | None = None
    currency_symbol: str = "$"
    verbose: bool = False
    quiet: bool = False
