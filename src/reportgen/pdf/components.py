"""Platypus flowable component builders for executive PDF report layout.

Constructs modular, publication-grade layout components adhering strictly to the
calibrated vertical point budget:
  - Document Header & Metadata Banner (width = 540 pt)
  - 4-Card Executive KPI Summary Grid (width = 540 pt)
  - Section Headings with calibrated vertical leading
  - Dual Visual Charts Container (width = 540 pt, 260 pt + 20 pt gap + 260 pt)
  - Top 5 High-Value Expense Ledger Table (width = 540 pt)

All text cells inside tables are encapsulated within ReportLab ``Paragraph``
flowables with explicit column widths to guarantee deterministic line wrapping
and eliminate horizontal overflow.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Sequence

from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import Flowable, Image, Paragraph, Table, TableStyle

from reportgen.analytics.models import MetricCard, ReportAnalytics, TopExpenseItem
from reportgen.pdf.styles import (
    COLOR_BORDER,
    COLOR_CARD_BG,
    COLOR_PRIMARY_NAVY,
    COLOR_WHITE,
    get_report_styles,
)

if TYPE_CHECKING:
    from reportlab.lib.styles import StyleSheet1


# -----------------------------------------------------------------------------
# Component Geometry Constants (in PostScript points, 72 pt = 1 inch)
# -----------------------------------------------------------------------------

# Printable canvas width matching US Letter portrait with 36 pt (0.5 in) margins
CANVAS_PRINTABLE_WIDTH_PTS = 540.0

# Header banner 2-column partition (360 pt title/subtitle + 180 pt date metadata = 540 pt)
HEADER_COL_WIDTHS = [360.0, 180.0]

# KPI 4-card row configuration:
# 4 outer slots of 135 pt each (total 540 pt). Each card is rendered as an inner
# framed box of 129 pt width, producing an optical 6 pt horizontal spacing between cards.
KPI_OUTER_COL_WIDTHS = [135.0, 135.0, 135.0, 135.0]
KPI_CARD_INNER_WIDTH = 129.0

# Dual charts row: 260 pt category chart + 20 pt gutter + 260 pt trend chart = 540 pt
CHARTS_COL_WIDTHS = [260.0, 20.0, 260.0]

# High-value ledger table: 5 columns totaling exactly 540 pt
# Date (70 pt) + Description (170 pt) + Category (130 pt) + Department (90 pt) + Amount (80 pt) = 540 pt
EXPENSES_TABLE_COL_WIDTHS = [70.0, 170.0, 130.0, 90.0, 80.0]


# -----------------------------------------------------------------------------
# Component Builders
# -----------------------------------------------------------------------------

def build_header_banner(
    title: str,
    subtitle: str,
    date_range: str,
    styles: StyleSheet1 | None = None,
) -> Table:
    """Build the executive report header banner spanning the full printable canvas width.

    Constructs a borderless two-column table where the left column houses the primary
    report title and descriptive subtitle, and the right column houses the reporting
    period metadata right-aligned.

    Args:
        title: Primary document heading (e.g., 'Financial Disbursement Report').
        subtitle: Secondary descriptive text (e.g., 'Executive Spend & Variance Summary').
        date_range: Formatted temporal coverage string (e.g., 'Jan 04, 2026 - Mar 31, 2026').
        styles: ReportLab stylesheet. Defaults to ``get_report_styles()``.

    Returns:
        ReportLab Table flowable with width 540 pt and height ~44 pt.
    """
    if styles is None:
        styles = get_report_styles()

    left_flowables = [
        Paragraph(title, styles["HeaderTitle"]),
        Paragraph(subtitle, styles["HeaderSubtitle"]),
    ]

    right_flowables = [
        Paragraph("REPORTING PERIOD", styles["HeaderDateSubtitle"]),
        Paragraph(date_range, styles["HeaderDateRange"]),
    ]

    banner_table = Table([[left_flowables, right_flowables]], colWidths=HEADER_COL_WIDTHS)
    banner_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0.0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0.0),
                ("TOPPADDING", (0, 0), (-1, -1), 0.0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0.0),
            ]
        )
    )
    return banner_table


def create_header_banner(
    title: str,
    subtitle: str,
    date_range_str: str,
    styles: StyleSheet1 | None = None,
) -> Table:
    """Backward-compatibility alias for ``build_header_banner``."""
    return build_header_banner(
        title=title,
        subtitle=subtitle,
        date_range=date_range_str,
        styles=styles,
    )


def build_kpi_grid(
    analytics: ReportAnalytics | Sequence[MetricCard],
    styles: StyleSheet1 | None = None,
) -> Table:
    """Build the 4-card executive KPI summary row spanning 540 pt.

    Each metric card displays a 3-tier visual hierarchy:
      1. Uppercase metric label (e.g., 'TOTAL SPEND') in muted typography.
      2. High-contrast primary metric value (e.g., '$218,435.50').
      3. Period-over-period delta or contextual caption (e.g., '+6.4% vs. prior period'),
         color-coded based on delta type (green for favorable, red for unfavorable).

    Cards are encapsulated within individual framed tables with light surface backgrounds
    (`#F8FAFC`) and subtle borders (`#E2E8F0`), maintaining clean separation across
    the horizontal axis.

    Args:
        analytics: Either a ``ReportAnalytics`` instance or an explicit sequence of ``MetricCard`` objects.
        styles: ReportLab stylesheet. Defaults to ``get_report_styles()``.

    Returns:
        ReportLab Table flowable with width 540 pt and height ~48-52 pt.
    """
    if styles is None:
        styles = get_report_styles()

    if isinstance(analytics, ReportAnalytics):
        cards = analytics.kpis
    else:
        cards = list(analytics)

    # Pad with fallback empty cards if fewer than 4 are provided
    card_tables: list[Table] = []
    for i in range(4):
        if i < len(cards):
            card = cards[i]
            label_text = card.label.upper()
            value_text = card.value

            # Determine contextual indicator styling and copy
            if card.delta is not None:
                if card.delta_type == "positive":
                    delta_style = styles["KpiDeltaPositive"]
                elif card.delta_type == "negative":
                    delta_style = styles["KpiDeltaNegative"]
                else:
                    delta_style = styles["KpiDeltaNeutral"]

                # If subtitle already repeats the delta percentage, avoid redundant prefixing
                if card.subtitle and card.delta in card.subtitle:
                    context_text = card.subtitle
                elif card.subtitle:
                    context_text = f"{card.delta} {card.subtitle}"
                else:
                    context_text = card.delta
            elif card.subtitle:
                delta_style = styles["KpiDeltaNeutral"]
                context_text = card.subtitle
            else:
                delta_style = styles["KpiDeltaNeutral"]
                context_text = "&nbsp;"
        else:
            label_text = "—"
            value_text = "—"
            delta_style = styles["KpiDeltaNeutral"]
            context_text = "&nbsp;"

        inner_content = [
            Paragraph(label_text, styles["KpiLabel"]),
            Paragraph(value_text, styles["KpiValue"]),
            Paragraph(context_text, delta_style),
        ]

        # Inner card table with boundary stroke and subtle background fill
        card_box = Table([[inner_content]], colWidths=[KPI_CARD_INNER_WIDTH])
        card_box.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), COLOR_CARD_BG),
                    ("BOX", (0, 0), (-1, -1), 0.75, COLOR_BORDER),
                    ("TOPPADDING", (0, 0), (-1, -1), 5.0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5.0),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7.0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7.0),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        card_tables.append(card_box)

    outer_grid = Table([card_tables], colWidths=KPI_OUTER_COL_WIDTHS)
    outer_grid.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0.0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0.0),
                ("TOPPADDING", (0, 0), (-1, -1), 0.0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0.0),
            ]
        )
    )
    return outer_grid


def create_kpi_cards_row(
    cards: list[MetricCard] | ReportAnalytics,
    styles: StyleSheet1 | None = None,
) -> Table:
    """Backward-compatibility alias for ``build_kpi_grid``."""
    return build_kpi_grid(analytics=cards, styles=styles)


def build_section_heading(
    title: str,
    styles: StyleSheet1 | None = None,
) -> Paragraph:
    """Build a standardized section heading Paragraph flowable.

    Provides crisp, high-contrast visual signposting with strictly zero before/after
    spacing so that vertical layout budgets remain completely controlled by explicit
    ``Spacer`` flowables in the story assembly.

    Args:
        title: Section title text (e.g., 'EXECUTIVE SPEND ANALYSIS').
        styles: ReportLab stylesheet. Defaults to ``get_report_styles()``.

    Returns:
        ReportLab Paragraph flowable.
    """
    if styles is None:
        styles = get_report_styles()

    return Paragraph(title, styles["SectionHeading"])


def build_charts_container(
    category_chart: Image | Any,
    trend_chart: Image | Any,
) -> Table:
    """Build the side-by-side dual chart container table spanning 540 pt.

    Arranges the spend by category bar chart and chronological spend trend line chart
    in a 2-column layout with a 20 pt center gutter:
      - Column 0: Category chart flowable (width = 260 pt, height = 175 pt)
      - Column 1: Spacing gutter (width = 20 pt)
      - Column 2: Spend trend chart flowable (width = 260 pt, height = 175 pt)

    Defensively converts any incoming Matplotlib ``Figure`` objects into ReportLab
    ``Image`` flowables if they have not yet been rasterized.

    Args:
        category_chart: Category spend bar chart Image flowable or Figure.
        trend_chart: Chronological spend trend line chart Image flowable or Figure.

    Returns:
        ReportLab Table flowable with width 540 pt and height ~175 pt.
    """
    # Defensively convert Matplotlib Figures if passed directly
    if not isinstance(category_chart, Image):
        from reportgen.visuals.charts import render_chart_to_flowable
        category_chart = render_chart_to_flowable(category_chart, width_pts=260.0, height_pts=175.0)

    if not isinstance(trend_chart, Image):
        from reportgen.visuals.charts import render_chart_to_flowable
        trend_chart = render_chart_to_flowable(trend_chart, width_pts=260.0, height_pts=175.0)

    row_data = [[category_chart, "", trend_chart]]
    charts_table = Table(row_data, colWidths=CHARTS_COL_WIDTHS)
    charts_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, 0), "LEFT"),
                ("ALIGN", (2, 0), (2, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0.0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0.0),
                ("TOPPADDING", (0, 0), (-1, -1), 0.0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0.0),
            ]
        )
    )
    return charts_table


def create_dual_charts_container(
    category_chart: Image | Any,
    trend_chart: Image | Any,
) -> Table:
    """Backward-compatibility alias for ``build_charts_container``."""
    return build_charts_container(category_chart=category_chart, trend_chart=trend_chart)


def _clip_text(text: str, max_chars: int) -> str:
    """Defensively clamp string length with ellipsis to protect vertical page budgets."""
    cleaned = text.strip()
    if len(cleaned) > max_chars:
        return cleaned[: max_chars - 3].rstrip() + "..."
    return cleaned


def build_top_expenses_table(
    expenses: Sequence[TopExpenseItem],
    styles: StyleSheet1 | None = None,
) -> Table:
    """Build the high-value transaction disbursement ledger table spanning 540 pt.

    Presents the top 5 largest transaction disbursements sorted by numerical amount
    descending. Adheres to calibrated column widths:
      - Date: 70 pt (left-aligned)
      - Description: 170 pt (left-aligned, auto-wrapping Paragraph)
      - Category: 130 pt (left-aligned)
      - Department: 90 pt (left-aligned)
      - Amount: 80 pt (right-aligned, bold)
      - Total Width: 540 pt

    Features a deep navy header row (`#1E3A8A`) with white text, alternating row fills
    (`#FFFFFF` and `#F8FAFC`), and subtle horizontal row dividers (`#E2E8F0`). Text
    lengths are defensively bounded to prevent unbounded vertical row expansion.

    Args:
        expenses: Sequence of ``TopExpenseItem`` records (capped at the top 5).
        styles: ReportLab stylesheet. Defaults to ``get_report_styles()``.

    Returns:
        ReportLab Table flowable with width 540 pt and height ~110-140 pt.
    """
    if styles is None:
        styles = get_report_styles()

    header_cells = [
        Paragraph("DATE", styles["TableHeaderCell"]),
        Paragraph("DESCRIPTION", styles["TableHeaderCell"]),
        Paragraph("CATEGORY", styles["TableHeaderCell"]),
        Paragraph("DEPARTMENT", styles["TableHeaderCell"]),
        Paragraph("AMOUNT", styles["TableHeaderCellRight"]),
    ]

    table_data: list[list[Paragraph]] = [header_cells]

    # Limit to top 5 disbursements
    top_items = list(expenses)[:5]

    if not top_items:
        # Fallback placeholder row when no expense records exist
        empty_row = [
            Paragraph("—", styles["TableDateCell"]),
            Paragraph("No transaction records recorded for this period.", styles["TableBodyCell"]),
            Paragraph("—", styles["TableBodyCell"]),
            Paragraph("—", styles["TableBodyCell"]),
            Paragraph("—", styles["TableAmountCell"]),
        ]
        table_data.append(empty_row)
    else:
        for item in top_items:
            # Protect vertical line budgets: max ~2 lines per description/category/dept
            desc_text = _clip_text(str(item.description), max_chars=80)
            cat_text = _clip_text(str(item.category), max_chars=40)
            dept_text = _clip_text(str(item.department), max_chars=30)
            row_cells = [
                Paragraph(str(item.date), styles["TableDateCell"]),
                Paragraph(desc_text, styles["TableBodyCell"]),
                Paragraph(cat_text, styles["TableBodyCell"]),
                Paragraph(dept_text, styles["TableBodyCell"]),
                Paragraph(str(item.formatted_amount), styles["TableAmountCell"]),
            ]
            table_data.append(row_cells)

    ledger_table = Table(table_data, colWidths=EXPENSES_TABLE_COL_WIDTHS)
    ledger_table.setStyle(
        TableStyle(
            [
                # Header row styling
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY_NAVY),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-2, -1), "LEFT"),
                ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
                # Alternating row background fills
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLOR_WHITE, COLOR_CARD_BG]),
                # Horizontal row divider lines
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                # Internal cell padding
                ("TOPPADDING", (0, 0), (-1, -1), 4.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6.0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6.0),
            ]
        )
    )
    return ledger_table


def create_top_expenses_table(
    expenses: list[TopExpenseItem],
    styles: StyleSheet1 | None = None,
) -> Table:
    """Backward-compatibility alias for ``build_top_expenses_table``."""
    return build_top_expenses_table(expenses=expenses, styles=styles)
