"""Headless Matplotlib figure generation and ReportLab image conversion.

Renders horizontal category spend bar charts and chronological spend trend lines
into high-DPI in-memory buffers with guaranteed memory cleanup. Adheres to modern
publication standards: high data-to-ink ratio, subdued architectural gridlines,
direct data labeling, and strict headless execution.
"""

from __future__ import annotations

import io
import math
import os
from typing import Any

# Ensure headless execution and writable configuration cache directory before importing pyplot.
# Setting MPLCONFIGDIR prevents filesystem permission errors on isolated headless systems.
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from reportlab.platypus import Image

from reportgen.analytics.models import (
    CategorySummary,
    ReportAnalytics,
    TimeSeriesPoint,
)
from reportgen.config import RenderingError, ReportGenError
from reportgen.visuals.theme import (
    CATEGORY_PALETTE,
    COLOR_BORDER,
    COLOR_CARD_BG,
    COLOR_GRID,
    COLOR_PRIMARY,
    COLOR_SURFACE,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
    apply_chart_theme,
)


def _format_compact_currency(amount: float, symbol: str = "$") -> str:
    """Format numerical currency values cleanly for chart labels and axis ticks.

    Converts large figures into standard compact notation (e.g. $42.5k, $1.2M),
    while preserving negative sign placement (-$15.0k) and formatting smaller values
    with comma grouping ($840).

    Args:
        amount: Numerical monetary value.
        symbol: Currency prefix symbol (defaults to '$').

    Returns:
        Compact formatted string suitable for high-density chart axes and callouts.
    """
    prefix = "-" if amount < 0 else ""
    abs_amt = abs(amount)

    if abs_amt >= 1_000_000:
        val_str = f"{abs_amt / 1_000_000:.1f}M"
    elif abs_amt >= 1_000:
        val_str = f"{abs_amt / 1_000:.1f}k"
    elif abs_amt == 0:
        val_str = "0"
    elif abs_amt < 10:
        val_str = f"{abs_amt:.2f}"
    else:
        val_str = f"{abs_amt:,.0f}"

    return f"{prefix}{symbol}{val_str}"


def create_category_bar_chart(
    categories: list[CategorySummary],
    currency_symbol: str = "$",
    width_pt: float = 260.0,
    height_pt: float = 175.0,
) -> matplotlib.figure.Figure:
    """Generate a horizontal bar chart displaying category spend distribution.

    Orders categories so the largest expenditure appears at the top of the chart,
    applies accessible palette tokens, annotates bar tips directly with monetary
    and percentage callouts, and strips unnecessary spines to maximize the
    data-to-ink ratio.

    Coordinate Geometry:
        - Matplotlib horizontal bar charts place y=0 at the bottom and y=N-1 at
          the top. Categories are sorted ascending by total spend (with any composite
          'Other' bucket anchored at the bottom) so the dominant category rests at y=max.
        - X-axis limit is expanded with ~30% headroom beyond the maximum value to
          prevent bar-tip text annotations from clipping against the axes boundary.

    Args:
        categories: Ranked category summary metrics to display.
        currency_symbol: Currency symbol prefix for annotations.
        width_pt: Target layout width in ReportLab points (defaults to 260.0).
        height_pt: Target layout height in ReportLab points (defaults to 175.0).

    Returns:
        Matplotlib Figure instance configured headlessly.

    Raises:
        RenderingError: If categories list is empty.
    """
    if not categories:
        raise RenderingError("Cannot render category bar chart: category list is empty.")

    apply_chart_theme()

    # Convert PostScript layout points (72 pt/in) to Matplotlib canvas inches
    figsize = (width_pt / 72.0, height_pt / 72.0)
    fig, ax = plt.subplots(figsize=figsize, dpi=300)

    try:
        # Visual Hierarchy & Ordering:
        # Anchor composite 'Other' category at the bottom (y=0) if present,
        # then sort remaining categories ascending so the largest appears at the top.
        other_cats = [c for c in categories if c.name.strip().lower() == "other"]
        main_cats = [c for c in categories if c.name.strip().lower() != "other"]
        main_sorted = sorted(main_cats, key=lambda c: c.total_spend)
        display_cats = other_cats + main_sorted

        num_categories = len(display_cats)
        y_positions = list(range(num_categories))
        amounts = [c.total_spend for c in display_cats]

        # Assign semantic palette colors:
        # Top-ranked category (at top of chart) receives Deep Navy (Rank 1).
        # Subsequent categories descend through the accessible palette.
        # Composite 'Other' receives Neutral Slate.
        bar_colors = []
        for i, cat in enumerate(display_cats):
            if cat.name.strip().lower() == "other":
                bar_colors.append(CATEGORY_PALETTE[5])  # Neutral Slate
            else:
                # Rank 0 is top category (index num_categories - 1)
                rank = (num_categories - 1) - i
                bar_colors.append(CATEGORY_PALETTE[rank % len(CATEGORY_PALETTE)])

        # Bar proportion: calibrate height based on category count to balance white space
        bar_height = 0.65 if num_categories > 3 else 0.45
        bars = ax.barh(
            y_positions,
            amounts,
            height=bar_height,
            color=bar_colors,
            edgecolor="none",
            zorder=3,
        )

        # Coordinate Geometry: determine dynamic X-axis bounds and annotation headroom
        max_val = max(amounts) if amounts else 0.0
        min_val = min(amounts) if amounts else 0.0

        if max_val > 0:
            right_bound = max_val * 1.32
            headroom = max_val
        else:
            right_bound = 100.0
            headroom = 100.0

        if min_val < 0:
            left_bound = min_val * 1.32
            # Add subtle vertical baseline at zero for negative refund balances
            ax.axvline(0, color=COLOR_GRID, linewidth=0.8, linestyle="-", zorder=2)
        else:
            left_bound = 0.0

        ax.set_xlim(left=left_bound, right=right_bound)

        # Direct Data Labels: annotate each bar tip with compact currency and percentage
        for i, (cat, bar) in enumerate(zip(display_cats, bars)):
            spend = cat.total_spend
            pct = cat.percentage
            formatted_val = _format_compact_currency(spend, currency_symbol)

            if pct is not None and pct > 0:
                label_text = f"{formatted_val} ({pct:.0f}%)"
            else:
                label_text = formatted_val

            # Offset text slightly past bar boundary
            offset = headroom * 0.02
            if spend >= 0:
                x_pos = spend + offset
                ha = "left"
            else:
                x_pos = spend - offset
                ha = "right"

            ax.text(
                x_pos,
                i,
                label_text,
                va="center",
                ha=ha,
                fontsize=7.0,
                color="#334155",
                fontweight="medium",
                zorder=4,
            )

        # Y-Axis Typography & Spacing: left-aligned category labels
        ax.set_yticks(y_positions)
        ax.set_yticklabels(
            [c.name for c in display_cats],
            fontsize=7.5,
            color=COLOR_TEXT_MAIN,
        )
        ax.tick_params(axis="y", length=0, pad=4)

        # X-Axis Tick Formatting: compact currency ticks
        ax.xaxis.set_major_formatter(
            ticker.FuncFormatter(lambda x, pos: _format_compact_currency(x, currency_symbol))
        )
        ax.tick_params(axis="x", labelsize=7.0, colors=COLOR_TEXT_MUTED, length=2)

        # Spine Cleansing: remove non-essential borders to emphasize data
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.spines["bottom"].set_color(COLOR_BORDER)
        ax.spines["bottom"].set_linewidth(0.8)

        # Gridlines: subtle vertical rules for scale estimation
        ax.xaxis.grid(True, linestyle="--", linewidth=0.5, color=COLOR_GRID, alpha=0.8, zorder=1)
        ax.yaxis.grid(False)
        ax.set_axisbelow(True)

        # Section Heading
        ax.set_title(
            "Spend by Category",
            loc="left",
            fontsize=9.0,
            fontweight="bold",
            color=COLOR_TEXT_MAIN,
            pad=6,
        )

        return fig

    except Exception:
        # Lifecycle Management: close figure on unexpected error during construction
        plt.close(fig)
        raise


def create_trend_line_chart(
    points: list[TimeSeriesPoint],
    currency_symbol: str = "$",
    width_pt: float = 260.0,
    height_pt: float = 175.0,
) -> matplotlib.figure.Figure:
    """Generate a line chart displaying chronological spend trend with fill and callouts.

    Plots a solid Deep Navy line with circular markers, a 10% opacity area fill
    under the curve, a zero-anchored Y-axis to prevent misleading visual shifts,
    and a peak spend callout badge.

    Coordinate Geometry:
        - Baseline Invariant: Y-axis strictly starts at zero (`ylim(bottom=0)`).
          Truncating the baseline visually exaggerates modest percentage fluctuations.
        - Headroom: Y-axis upper limit includes ~25% headroom to accommodate the
          peak annotation callout box without clipping against the top spine.
        - Single-Point Handling: Gracefully renders a standalone marker with an
          explanatory annotation when the dataset spans only one interval.

    Args:
        points: Chronological time-series points to display.
        currency_symbol: Currency symbol prefix for annotations.
        width_pt: Target layout width in ReportLab points (defaults to 260.0).
        height_pt: Target layout height in ReportLab points (defaults to 175.0).

    Returns:
        Matplotlib Figure instance configured headlessly.

    Raises:
        RenderingError: If points list is empty.
    """
    if not points:
        raise RenderingError("Cannot render trend line chart: trend points list is empty.")

    apply_chart_theme()

    # Convert PostScript layout points (72 pt/in) to Matplotlib canvas inches
    figsize = (width_pt / 72.0, height_pt / 72.0)
    fig, ax = plt.subplots(figsize=figsize, dpi=300)

    try:
        x_coords = list(range(len(points)))
        y_values = [p.total_spend for p in points]
        labels = [p.period_label for p in points]

        max_val = max(y_values) if y_values else 0.0

        # Edge Case: Single reporting period / single observation
        if len(points) == 1:
            val = y_values[0]
            ax.plot(
                [0],
                [val],
                marker="o",
                markersize=5.5,
                color=COLOR_PRIMARY,
                markerfacecolor=COLOR_SURFACE,
                markeredgecolor=COLOR_PRIMARY,
                markeredgewidth=1.8,
                zorder=4,
            )
            # Standalone point callout
            amt_str = _format_compact_currency(val, currency_symbol)
            ax.annotate(
                f"{amt_str}\n(Single Reporting Period)",
                xy=(0, val),
                xytext=(0, 10),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=7.0,
                fontweight="bold",
                color=COLOR_PRIMARY,
                bbox=dict(
                    boxstyle="round,pad=0.25",
                    facecolor=COLOR_CARD_BG,
                    edgecolor="#93C5FD",
                    linewidth=0.7,
                ),
                zorder=5,
            )
            ax.set_xticks([0])
            ax.set_xticklabels([labels[0]], fontsize=7.0, color=COLOR_TEXT_MUTED)
            ax.set_xlim(-0.5, 0.5)
            top_bound = max(100.0, val * 1.35) if val > 0 else 100.0
            ax.set_ylim(bottom=0, top=top_bound)

        else:
            # Continuous Line & Marker Geometry
            ax.plot(
                x_coords,
                y_values,
                color=COLOR_PRIMARY,
                linewidth=1.8,
                marker="o",
                markersize=4.5,
                markerfacecolor=COLOR_SURFACE,
                markeredgecolor=COLOR_PRIMARY,
                markeredgewidth=1.5,
                zorder=4,
            )

            # Area Fill: 10% opacity semi-transparent fill under curve
            ax.fill_between(
                x_coords,
                y_values,
                color=COLOR_PRIMARY,
                alpha=0.10,
                zorder=2,
            )

            # Baseline Invariant: Y-axis strictly starts at zero
            top_bound = max(100.0, max_val * 1.25) if max_val > 0 else 100.0
            ax.set_ylim(bottom=0, top=top_bound)
            ax.set_xlim(-0.35, len(points) - 0.65)

            # Peak Spend Callout: highlight the highest spend observation
            if max_val > 0:
                peak_idx = max(range(len(y_values)), key=lambda i: y_values[i])
                peak_val = y_values[peak_idx]
                peak_label = f"Peak: {_format_compact_currency(peak_val, currency_symbol)}"

                # Adjust horizontal alignment near plot edges to prevent callout clipping
                if peak_idx == 0:
                    ha = "left"
                    xytext = (5, 8)
                elif peak_idx == len(points) - 1:
                    ha = "right"
                    xytext = (-5, 8)
                else:
                    ha = "center"
                    xytext = (0, 8)

                ax.annotate(
                    peak_label,
                    xy=(peak_idx, peak_val),
                    xytext=xytext,
                    textcoords="offset points",
                    ha=ha,
                    va="bottom",
                    fontsize=7.0,
                    fontweight="bold",
                    color=COLOR_PRIMARY,
                    bbox=dict(
                        boxstyle="round,pad=0.25",
                        facecolor=COLOR_CARD_BG,
                        edgecolor="#93C5FD",
                        linewidth=0.7,
                    ),
                    zorder=5,
                )

            # X-Axis Tick Label Density: step frequency if points > 8 to prevent overlap
            if len(points) <= 8:
                ax.set_xticks(x_coords)
                ax.set_xticklabels(labels, fontsize=7.0, color=COLOR_TEXT_MUTED)
            else:
                step = math.ceil(len(points) / 8)
                tick_indices = list(range(0, len(points), step))
                if (len(points) - 1) not in tick_indices:
                    if (len(points) - 1) - tick_indices[-1] > step // 2:
                        tick_indices.append(len(points) - 1)
                    else:
                        tick_indices[-1] = len(points) - 1
                ax.set_xticks(tick_indices)
                ax.set_xticklabels(
                    [labels[i] for i in tick_indices],
                    fontsize=7.0,
                    color=COLOR_TEXT_MUTED,
                )

        # Y-Axis Formatting: currency tick labels
        ax.yaxis.set_major_formatter(
            ticker.FuncFormatter(lambda y, pos: _format_compact_currency(y, currency_symbol))
        )
        ax.tick_params(axis="y", labelsize=7.0, colors=COLOR_TEXT_MUTED, length=2)
        ax.tick_params(axis="x", length=2, colors=COLOR_TEXT_MUTED)

        # Spine Cleansing: remove top and right spines, retain subtle bottom and left axes
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(COLOR_BORDER)
        ax.spines["bottom"].set_color(COLOR_BORDER)
        ax.spines["left"].set_linewidth(0.8)
        ax.spines["bottom"].set_linewidth(0.8)

        # Gridlines: subtle horizontal alignment lines
        ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color=COLOR_GRID, alpha=0.8, zorder=1)
        ax.xaxis.grid(False)
        ax.set_axisbelow(True)

        # Section Heading
        ax.set_title(
            "Spend Trend Over Time",
            loc="left",
            fontsize=9.0,
            fontweight="bold",
            color=COLOR_TEXT_MAIN,
            pad=6,
        )

        return fig

    except Exception:
        # Lifecycle Management: close figure on unexpected error during construction
        plt.close(fig)
        raise


def render_chart_to_flowable(
    fig_or_func: matplotlib.figure.Figure | Any,
    *args: Any,
    width_pts: float = 260.0,
    height_pts: float = 175.0,
    width_pt: float | None = None,
    height_pt: float | None = None,
    **kwargs: Any,
) -> Image:
    """Render a Matplotlib figure or plotting function to a high-DPI ReportLab Image flowable.

    Renders the figure to an in-memory 300 DPI PNG buffer without writing temporary
    files to disk, wraps the buffer in a ReportLab Image flowable with exact point
    dimensions, and guarantees memory cleanup by closing the figure in a finally block.

    Args:
        fig_or_func: Either an instantiated matplotlib.figure.Figure or a callable
            that accepts arguments and returns a Figure.
        *args: Positional arguments forwarded to fig_or_func if callable.
        width_pts: Target layout width in ReportLab points (defaults to 260.0).
        height_pts: Target layout height in ReportLab points (defaults to 175.0).
        width_pt: Optional alias for width_pts.
        height_pt: Optional alias for height_pts.
        **kwargs: Keyword arguments forwarded to fig_or_func if callable.

    Returns:
        ReportLab Image flowable wrapping the rendered in-memory PNG buffer.

    Raises:
        RenderingError: If rendering or buffer conversion encounters an unrecoverable failure.
    """
    effective_width = width_pt if width_pt is not None else width_pts
    effective_height = height_pt if height_pt is not None else height_pts

    if isinstance(fig_or_func, matplotlib.figure.Figure):
        fig = fig_or_func
    elif callable(fig_or_func):
        fig = fig_or_func(*args, **kwargs)
    else:
        raise RenderingError(
            f"Expected matplotlib Figure or callable returning Figure, got {type(fig_or_func).__name__}"
        )

    img_buffer = io.BytesIO()
    try:
        # In-Memory Invariant: Render directly to buffer at 300 DPI (no disk writes)
        fig.savefig(
            img_buffer,
            format="png",
            dpi=300,
            bbox_inches="tight",
            pad_inches=0.04,
            facecolor=fig.get_facecolor(),
            edgecolor="none",
        )
        img_buffer.seek(0)
        img = Image(img_buffer, width=effective_width, height=effective_height)
        # Expose direct width/height attributes alongside ReportLab's drawWidth/drawHeight
        img.width = effective_width
        img.height = effective_height
        return img

    except Exception as exc:
        if isinstance(exc, ReportGenError):
            raise
        raise RenderingError(f"Failed to rasterize Matplotlib figure into Image flowable: {exc}") from exc

    finally:
        # Memory Lifecycle Invariant: Always close the figure to release font
        # rasterizers, canvas arrays, and Pyplot registry entries immediately.
        plt.close(fig)


def build_category_bar_chart(
    categories: list[CategorySummary],
    width_pt: float = 260.0,
    height_pt: float = 175.0,
    currency_symbol: str = "$",
) -> Image:
    """Build a publication-ready horizontal category spend bar chart as an Image flowable.

    Orchestrates figure construction, theme styling, bar geometry layout, and
    in-memory rasterization with deterministic lifecycle management.

    Args:
        categories: Ranked category summary metrics to display.
        width_pt: Target layout width in ReportLab points (defaults to 260.0).
        height_pt: Target layout height in ReportLab points (defaults to 175.0).
        currency_symbol: Monetary prefix symbol for value callouts.

    Returns:
        ReportLab Image flowable ready for insertion into Platypus story or table.

    Raises:
        RenderingError: If the category list is empty or rendering fails.
    """
    fig = create_category_bar_chart(
        categories=categories,
        currency_symbol=currency_symbol,
        width_pt=width_pt,
        height_pt=height_pt,
    )
    return render_chart_to_flowable(fig, width_pts=width_pt, height_pts=height_pt)


def build_trend_line_chart(
    trend_points: list[TimeSeriesPoint],
    width_pt: float = 260.0,
    height_pt: float = 175.0,
    currency_symbol: str = "$",
) -> Image:
    """Build a publication-ready chronological spend trend line chart as an Image flowable.

    Orchestrates figure construction, theme styling, marker/area plotting, and
    in-memory rasterization with deterministic lifecycle management.

    Args:
        trend_points: Chronological time-series points to display.
        width_pt: Target layout width in ReportLab points (defaults to 260.0).
        height_pt: Target layout height in ReportLab points (defaults to 175.0).
        currency_symbol: Monetary prefix symbol for value callouts.

    Returns:
        ReportLab Image flowable ready for insertion into Platypus story or table.

    Raises:
        RenderingError: If the trend points list is empty or rendering fails.
    """
    fig = create_trend_line_chart(
        points=trend_points,
        currency_symbol=currency_symbol,
        width_pt=width_pt,
        height_pt=height_pt,
    )
    return render_chart_to_flowable(fig, width_pts=width_pt, height_pts=height_pt)


def render_report_charts(
    analytics: ReportAnalytics,
    width_pt: float = 260.0,
    height_pt: float = 175.0,
    currency_symbol: str = "$",
) -> tuple[Image, Image]:
    """Render both category distribution and temporal spend trend charts.

    Convenience orchestrator that builds the two complementary dashboard charts
    from a computed ReportAnalytics instance, returning ReportLab Image flowables
    calibrated to standard executive dashboard dimensions.

    Args:
        analytics: Synthesized reporting metrics container.
        width_pt: Target layout width in ReportLab points (defaults to 260.0).
        height_pt: Target layout height in ReportLab points (defaults to 175.0).
        currency_symbol: Monetary prefix symbol for value callouts.

    Returns:
        Tuple of (category_bar_image, trend_line_image).
    """
    category_chart = build_category_bar_chart(
        categories=analytics.category_breakdown,
        width_pt=width_pt,
        height_pt=height_pt,
        currency_symbol=currency_symbol,
    )
    trend_chart = build_trend_line_chart(
        trend_points=analytics.spending_trend,
        width_pt=width_pt,
        height_pt=height_pt,
        currency_symbol=currency_symbol,
    )
    return (category_chart, trend_chart)
