"""Visualization styling, Matplotlib theme defaults, and chart generation.

Provides publication-grade headless chart rendering routines for executive PDF reports.
"""

from __future__ import annotations

from reportgen.visuals.charts import (
    build_category_bar_chart,
    build_trend_line_chart,
    create_category_bar_chart,
    create_trend_line_chart,
    render_chart_to_flowable,
    render_report_charts,
)
from reportgen.visuals.theme import (
    CATEGORY_PALETTE,
    CHART_PALETTE,
    CHART_RC_PARAMS,
    COLOR_ACCENT,
    COLOR_AMBER,
    COLOR_BORDER,
    COLOR_CARD_BG,
    COLOR_GRID,
    COLOR_MUTED,
    COLOR_PRIMARY,
    COLOR_ROSE,
    COLOR_SECONDARY,
    COLOR_SURFACE,
    COLOR_TEAL,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
    apply_chart_theme,
    chart_theme,
)

__all__ = [
    "CATEGORY_PALETTE",
    "CHART_PALETTE",
    "CHART_RC_PARAMS",
    "COLOR_ACCENT",
    "COLOR_AMBER",
    "COLOR_BORDER",
    "COLOR_CARD_BG",
    "COLOR_GRID",
    "COLOR_MUTED",
    "COLOR_PRIMARY",
    "COLOR_ROSE",
    "COLOR_SECONDARY",
    "COLOR_SURFACE",
    "COLOR_TEAL",
    "COLOR_TEXT_MAIN",
    "COLOR_TEXT_MUTED",
    "apply_chart_theme",
    "build_category_bar_chart",
    "build_trend_line_chart",
    "chart_theme",
    "create_category_bar_chart",
    "create_trend_line_chart",
    "render_chart_to_flowable",
    "render_report_charts",
]
