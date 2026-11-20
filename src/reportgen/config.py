"""Configuration structures, geometry definitions, and layout constants.

Holds page dimensions, color tokens, and runtime report settings.
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


@dataclass(frozen=True)
class ReportConfig:
    """Runtime configuration for report generation."""

    input_path: Path
    output_path: Path
    title: str = "Financial Disbursement Report"
    subtitle: str = "Executive Spend & Variance Summary"
    mapping_path: Path | None = None
    currency_symbol: str = "$"
    verbose: bool = False
    quiet: bool = False
