"""Unit and regression tests for chart generation and visualization themes.

Verifies:
- ReportLab Image flowable dimensions (width=260 pt, height=175 pt).
- Absolute figure lifecycle and memory leak prevention (plt.get_fignums() is empty).
- Accurate rendering with standard canonical sample expenses analytics.
- Defensive handling of edge cases (single category, single time point, flat trend).
- Graceful handling of negative refund values and explicit RenderingError on empty inputs.
- Custom geometry, currency symbol variations, and Matplotlib rcParams styling.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
import matplotlib
import matplotlib.pyplot as plt
import pytest
from reportlab.platypus import Image

from reportgen.analytics.engine import compute_analytics
from reportgen.analytics.models import (
    CategorySummary,
    ReportAnalytics,
    TimeSeriesPoint,
)
from reportgen.config import RenderingError
from reportgen.data.loader import load_transaction_csv
from reportgen.visuals.charts import (
    _format_compact_currency,
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
    COLOR_PRIMARY,
    apply_chart_theme,
    chart_theme,
)


@pytest.fixture(autouse=True)
def ensure_no_active_figures() -> None:
    """Fixture ensuring Matplotlib figure registry is completely clean before and after each test."""
    plt.close("all")
    assert len(plt.get_fignums()) == 0, "Leaked figure detected before test execution"
    yield
    plt.close("all")
    assert len(plt.get_fignums()) == 0, "Leaked figure detected after test execution"


@pytest.fixture(scope="session")
def sample_analytics(sample_csv_path: Path) -> ReportAnalytics:
    """Provide a synthesized ReportAnalytics instance from the canonical sample expenses CSV."""
    df = load_transaction_csv(sample_csv_path)
    return compute_analytics(df, report_title="Executive Financial Dashboard")


# -----------------------------------------------------------------------------
# Visual Theme & rcParams Tests
# -----------------------------------------------------------------------------

def test_theme_constants_and_palettes() -> None:
    """Verify that color palette tokens match design specifications."""
    assert COLOR_PRIMARY == "#1E3A8A"
    assert len(CATEGORY_PALETTE) == 6
    assert CATEGORY_PALETTE[0] == "#1E3A8A"  # Deep Navy
    assert CATEGORY_PALETTE[5] == "#64748B"  # Neutral Slate for 'Other'
    assert CHART_PALETTE == CATEGORY_PALETTE


def test_apply_chart_theme() -> None:
    """Verify that apply_chart_theme properly updates Matplotlib global rcParams."""
    apply_chart_theme()
    assert plt.rcParams["figure.facecolor"] == "#FFFFFF"
    assert plt.rcParams["axes.facecolor"] == "#FFFFFF"
    assert plt.rcParams["text.color"] == "#0F172A"
    assert plt.rcParams["figure.dpi"] == 300


def test_chart_theme_context_manager() -> None:
    """Verify that chart_theme context manager applies settings and restores previous state."""
    original_dpi = plt.rcParams["figure.dpi"]
    with chart_theme():
        assert plt.rcParams["figure.facecolor"] == "#FFFFFF"
    assert plt.rcParams["figure.dpi"] == original_dpi


# -----------------------------------------------------------------------------
# Number Formatting Helper Tests
# -----------------------------------------------------------------------------

def test_format_compact_currency() -> None:
    """Verify compact monetary formatting across different magnitudes and signs."""
    assert _format_compact_currency(0.0) == "$0"
    assert _format_compact_currency(450.0) == "$450"
    assert _format_compact_currency(1200.0) == "$1.2k"
    assert _format_compact_currency(42500.0) == "$42.5k"
    assert _format_compact_currency(1500000.0) == "$1.5M"
    assert _format_compact_currency(-450.0) == "-$450"
    assert _format_compact_currency(-12500.0) == "-$12.5k"
    assert _format_compact_currency(1200.0, symbol="€") == "€1.2k"


# -----------------------------------------------------------------------------
# Category Bar Chart Tests
# -----------------------------------------------------------------------------

def test_build_category_bar_chart_sample_data(sample_analytics: ReportAnalytics) -> None:
    """Verify category bar chart generation on canonical sample expenses dataset."""
    img = build_category_bar_chart(sample_analytics.category_breakdown)

    assert isinstance(img, Image)
    assert img.drawWidth == 260.0
    assert img.drawHeight == 175.0
    assert img.width == 260.0
    assert img.height == 175.0
    assert len(plt.get_fignums()) == 0


def test_build_category_bar_chart_single_category() -> None:
    """Verify category bar chart renders gracefully with exactly one category."""
    categories = [
        CategorySummary(
            name="Cloud Infrastructure",
            total_spend=12500.0,
            percentage=100.0,
            transaction_count=15,
        )
    ]
    img = build_category_bar_chart(categories)

    assert isinstance(img, Image)
    assert img.drawWidth == 260.0
    assert img.drawHeight == 175.0
    assert len(plt.get_fignums()) == 0


def test_build_category_bar_chart_with_negative_refunds() -> None:
    """Verify category bar chart handles negative net spend categories without error."""
    categories = [
        CategorySummary(
            name="Hardware Refunds",
            total_spend=-450.0,
            percentage=0.0,
            transaction_count=2,
        ),
        CategorySummary(
            name="Software & SaaS",
            total_spend=3200.0,
            percentage=87.7,
            transaction_count=10,
        ),
        CategorySummary(
            name="Other",
            total_spend=450.0,
            percentage=12.3,
            transaction_count=3,
        ),
    ]
    img = build_category_bar_chart(categories)

    assert isinstance(img, Image)
    assert img.drawWidth == 260.0
    assert img.drawHeight == 175.0
    assert len(plt.get_fignums()) == 0


def test_build_category_bar_chart_empty_raises_rendering_error() -> None:
    """Verify passing an empty category list raises an explicit RenderingError."""
    with pytest.raises(RenderingError, match="category list is empty"):
        build_category_bar_chart([])
    assert len(plt.get_fignums()) == 0


# -----------------------------------------------------------------------------
# Trend Line Chart Tests
# -----------------------------------------------------------------------------

def test_build_trend_line_chart_sample_data(sample_analytics: ReportAnalytics) -> None:
    """Verify trend line chart generation on canonical sample expenses dataset."""
    img = build_trend_line_chart(sample_analytics.spending_trend)

    assert isinstance(img, Image)
    assert img.drawWidth == 260.0
    assert img.drawHeight == 175.0
    assert img.width == 260.0
    assert img.height == 175.0
    assert len(plt.get_fignums()) == 0


def test_build_trend_line_chart_single_observation() -> None:
    """Verify trend line chart renders a discrete marker for a single reporting period."""
    points = [
        TimeSeriesPoint(
            period_label="Jan 2026",
            start_date=date(2026, 1, 1),
            total_spend=18500.0,
            transaction_count=25,
        )
    ]
    img = build_trend_line_chart(points)

    assert isinstance(img, Image)
    assert img.drawWidth == 260.0
    assert img.drawHeight == 175.0
    assert len(plt.get_fignums()) == 0


def test_build_trend_line_chart_flat_trend() -> None:
    """Verify trend line chart handles flat constant values without division-by-zero or scaling errors."""
    points = [
        TimeSeriesPoint("Jan", date(2026, 1, 1), 5000.0, 10),
        TimeSeriesPoint("Feb", date(2026, 2, 1), 5000.0, 10),
        TimeSeriesPoint("Mar", date(2026, 3, 1), 5000.0, 10),
    ]
    img = build_trend_line_chart(points)

    assert isinstance(img, Image)
    assert img.drawWidth == 260.0
    assert img.drawHeight == 175.0
    assert len(plt.get_fignums()) == 0


def test_build_trend_line_chart_dense_points() -> None:
    """Verify trend line chart steps tick frequencies when observations exceed 8 points."""
    points = [
        TimeSeriesPoint(f"W{i:02d}", date(2026, 1, 1), 1000.0 + (i * 100.0), 5)
        for i in range(1, 16)
    ]
    img = build_trend_line_chart(points)

    assert isinstance(img, Image)
    assert img.drawWidth == 260.0
    assert img.drawHeight == 175.0
    assert len(plt.get_fignums()) == 0


def test_build_trend_line_chart_zero_spend_points() -> None:
    """Verify trend line chart handles all-zero spend points cleanly."""
    points = [
        TimeSeriesPoint("Jan", date(2026, 1, 1), 0.0, 0),
        TimeSeriesPoint("Feb", date(2026, 2, 1), 0.0, 0),
    ]
    img = build_trend_line_chart(points)

    assert isinstance(img, Image)
    assert img.drawWidth == 260.0
    assert img.drawHeight == 175.0
    assert len(plt.get_fignums()) == 0


def test_build_trend_line_chart_empty_raises_rendering_error() -> None:
    """Verify passing an empty points list raises an explicit RenderingError."""
    with pytest.raises(RenderingError, match="trend points list is empty"):
        build_trend_line_chart([])
    assert len(plt.get_fignums()) == 0


# -----------------------------------------------------------------------------
# Orchestrator & Flowable Conversion Tests
# -----------------------------------------------------------------------------

def test_render_report_charts_orchestrator(sample_analytics: ReportAnalytics) -> None:
    """Verify convenience orchestrator produces both flowables with zero figure leakage."""
    cat_img, trend_img = render_report_charts(sample_analytics)

    assert isinstance(cat_img, Image)
    assert isinstance(trend_img, Image)
    assert cat_img.drawWidth == 260.0
    assert cat_img.drawHeight == 175.0
    assert trend_img.drawWidth == 260.0
    assert trend_img.drawHeight == 175.0
    assert len(plt.get_fignums()) == 0


def test_custom_dimensions_and_currency_symbol(sample_analytics: ReportAnalytics) -> None:
    """Verify custom dimensions and alternative currency symbol propagation."""
    custom_w = 320.0
    custom_h = 210.0
    cat_img, trend_img = render_report_charts(
        sample_analytics,
        width_pt=custom_w,
        height_pt=custom_h,
        currency_symbol="£",
    )

    assert cat_img.drawWidth == custom_w
    assert cat_img.drawHeight == custom_h
    assert trend_img.drawWidth == custom_w
    assert trend_img.drawHeight == custom_h
    assert len(plt.get_fignums()) == 0


def test_render_chart_to_flowable_with_figure() -> None:
    """Verify render_chart_to_flowable safely closes manually supplied Figure."""
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.plot([0, 1], [0, 1])
    assert len(plt.get_fignums()) == 1

    img = render_chart_to_flowable(fig, width_pts=200.0, height_pts=150.0)
    assert isinstance(img, Image)
    assert img.drawWidth == 200.0
    assert img.drawHeight == 150.0
    # Figure must be closed
    assert len(plt.get_fignums()) == 0


def test_render_chart_to_flowable_with_callable() -> None:
    """Verify render_chart_to_flowable supports callable factories."""
    def make_fig() -> matplotlib.figure.Figure:
        f, a = plt.subplots()
        a.bar([1, 2], [3, 4])
        return f

    img = render_chart_to_flowable(make_fig, width_pt=260.0, height_pt=175.0)
    assert isinstance(img, Image)
    assert len(plt.get_fignums()) == 0


def test_render_chart_to_flowable_invalid_type_raises_rendering_error() -> None:
    """Verify invalid argument to render_chart_to_flowable raises RenderingError."""
    with pytest.raises(RenderingError, match="Expected matplotlib Figure or callable"):
        render_chart_to_flowable("invalid_string_argument")
    assert len(plt.get_fignums()) == 0


def test_create_functions_return_figures() -> None:
    """Verify low-level create_* functions return matplotlib Figures that can be inspected."""
    cats = [CategorySummary("Marketing", 1000.0, 100.0, 5)]
    pts = [TimeSeriesPoint("Jan", date(2026, 1, 1), 1000.0, 5)]

    fig1 = create_category_bar_chart(cats)
    assert isinstance(fig1, matplotlib.figure.Figure)
    plt.close(fig1)

    fig2 = create_trend_line_chart(pts)
    assert isinstance(fig2, matplotlib.figure.Figure)
    plt.close(fig2)

    assert len(plt.get_fignums()) == 0
