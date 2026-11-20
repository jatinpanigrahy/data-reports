"""ReportLab document synthesis and strict single-page budget enforcement.

Configures SimpleDocTemplate, attaches running headers and footers,
and verifies the output does not spill past page 1.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from reportgen.analytics.models import ReportAnalytics
from reportgen.config import ReportConfig

if TYPE_CHECKING:
    import matplotlib.figure


class PDFBuildError(Exception):
    """Raised when PDF generation fails or exceeds the single-page budget."""


def build_report_pdf(
    analytics: ReportAnalytics,
    config: ReportConfig,
    category_chart_fig: matplotlib.figure.Figure | None = None,
    trend_chart_fig: matplotlib.figure.Figure | None = None,
) -> Path:
    """Compile the single-page executive PDF report.

    Args:
        analytics: Calculated metrics and summaries.
        config: Report generation parameters.
        category_chart_fig: Optional pre-rendered category bar chart figure.
        trend_chart_fig: Optional pre-rendered trend line chart figure.

    Returns:
        Path to the generated PDF document.

    Raises:
        PDFBuildError: If compilation fails or layout spills beyond page 1.
    """
    raise NotImplementedError("PDF builder will be implemented in Phase 5.")
