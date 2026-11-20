"""Headless Matplotlib figure generation and ReportLab image conversion.

Renders horizontal category spend bar charts and chronological spend trend lines
into high-DPI in-memory buffers with guaranteed memory cleanup.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from reportgen.analytics.models import CategorySummary, TimeSeriesPoint

if TYPE_CHECKING:
    import matplotlib.figure
    from reportlab.platypus import Image


def create_category_bar_chart(
    categories: list[CategorySummary],
    currency_symbol: str = "$",
) -> matplotlib.figure.Figure:
    """Generate a horizontal bar chart displaying category spend distribution."""
    raise NotImplementedError("Category bar chart will be implemented in Phase 4.")


def create_trend_line_chart(
    points: list[TimeSeriesPoint],
    currency_symbol: str = "$",
) -> matplotlib.figure.Figure:
    """Generate a line chart displaying chronological spend trend with fill."""
    raise NotImplementedError("Trend line chart will be implemented in Phase 4.")


def render_chart_to_flowable(
    fig: matplotlib.figure.Figure,
    width_pts: float = 260.0,
    height_pts: float = 175.0,
) -> Image:
    """Render a Matplotlib figure to a high-DPI ReportLab Image flowable.

    Closes the figure in a finally block to prevent memory leaks.
    """
    raise NotImplementedError("Chart-to-flowable renderer will be implemented in Phase 4.")
