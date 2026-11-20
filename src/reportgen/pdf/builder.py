"""ReportLab document synthesis and strict single-page budget enforcement.

Configures SimpleDocTemplate with calibrated US Letter margins, attaches running
canvas decorators (top brand accent line, bottom confidentiality footer, and metadata),
assembles the Platypus flowable story, and strictly enforces the single-page budget invariant.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import Flowable, Image, SimpleDocTemplate, Spacer

from reportgen.analytics.models import ReportAnalytics
from reportgen.config import (
    PAGE_HEIGHT_PTS,
    PAGE_MARGIN_PTS,
    PAGE_WIDTH_PTS,
    PDFBuildError,
    ReportConfig,
    USABLE_HEIGHT_PTS,
    USABLE_WIDTH_PTS,
)
from reportgen.pdf.components import (
    build_charts_container,
    build_header_banner,
    build_kpi_grid,
    build_section_heading,
    build_top_expenses_table,
)
from reportgen.pdf.styles import (
    COLOR_BORDER,
    COLOR_MUTED,
    COLOR_PRIMARY_NAVY,
    get_report_styles,
)

if TYPE_CHECKING:
    import matplotlib.figure

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Vertical Story Spacers (Budget Allocation in Points)
# -----------------------------------------------------------------------------

# Spacers are calibrated to leave ~200 pt buffer within the 720 pt printable height:
# Header (36 pt) + GAP_HEADER_KPI (10 pt) + KPI (48 pt) + GAP_KPI_SECTION (12 pt)
# + Section1 (14 pt) + GAP_SECTION_CHARTS (6 pt) + Charts (175 pt) + GAP_CHARTS_SECTION (14 pt)
# + Section2 (14 pt) + GAP_SECTION_TABLE (6 pt) + Table (115 pt) = ~450 pt total.
GAP_HEADER_KPI = 10.0
GAP_KPI_SECTION = 12.0
GAP_SECTION_CHARTS = 6.0
GAP_CHARTS_SECTION = 14.0
GAP_SECTION_TABLE = 6.0


# -----------------------------------------------------------------------------
# Canvas Decorators & Two-Pass Numbering
# -----------------------------------------------------------------------------

class NumberedCanvas(canvas.Canvas):
    """Two-pass ReportLab canvas for drawing running headers, footers, and page numbers.

    Accumulates draw operations across all pages during document compilation, then
    renders running headers, footer rules, confidentiality notices, and total page
    counts in a final pass before committing output to disk.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict[str, Any]] = []

    def showPage(self) -> None:
        """Capture the current page state and begin a new canvas page."""
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        """Render running page decorators across all accumulated pages and save."""
        total_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            draw_page_decorations(self, None, total_pages=total_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)


def draw_page_decorations(
    canv: canvas.Canvas,
    doc: Any,
    generated_at: str | None = None,
    total_pages: int = 1,
) -> None:
    """Draw running page decorators directly on the active canvas.

    Draws:
      1. Top Brand Accent Rule: Deep Navy bar along the upper margin boundary.
      2. Bottom Footer Divider: Subtle slate rule above the lower margin boundary.
      3. Confidentiality Notice: Mandatory internal distribution warning and timestamp.
      4. Page Counter: Single-page verification display ('Page 1 of 1').

    Args:
        canv: ReportLab drawing canvas.
        doc: SimpleDocTemplate instance (or None if called from NumberedCanvas).
        generated_at: Optional ISO or formatted generation timestamp string.
        total_pages: Total number of pages in document (defaults to 1).
    """
    canv.saveState()

    # 1. Top Brand Accent Bar (Navy line 4 pt above content frame)
    # y = 792 - 36 + 4 = 760 pt, height = 2.5 pt, spanning full 540 pt printable width
    canv.setFillColor(COLOR_PRIMARY_NAVY)
    accent_y = PAGE_HEIGHT_PTS - PAGE_MARGIN_PTS + 4.0
    canv.rect(
        PAGE_MARGIN_PTS,
        accent_y,
        USABLE_WIDTH_PTS,
        2.5,
        stroke=0,
        fill=1,
    )

    # 2. Bottom Footer Divider Line (0.5 pt rule at y = 30 pt)
    canv.setStrokeColor(COLOR_BORDER)
    canv.setLineWidth(0.5)
    footer_rule_y = PAGE_MARGIN_PTS - 6.0
    canv.line(
        PAGE_MARGIN_PTS,
        footer_rule_y,
        PAGE_WIDTH_PTS - PAGE_MARGIN_PTS,
        footer_rule_y,
    )

    # 3. Confidentiality Notice & Generation Timestamp (Left-aligned)
    canv.setFont("Helvetica", 7.0)
    canv.setFillColor(COLOR_MUTED)
    footer_text_y = PAGE_MARGIN_PTS - 17.0
    timestamp_suffix = f" • GENERATED: {generated_at}" if generated_at else ""
    footer_left_str = f"CONFIDENTIAL — FOR INTERNAL USE ONLY{timestamp_suffix}"
    canv.drawString(PAGE_MARGIN_PTS, footer_text_y, footer_left_str)

    # 4. Page Counter (Right-aligned)
    canv.setFont("Helvetica-Bold", 7.0)
    current_page = getattr(canv, "_pageNumber", 1)
    footer_right_str = f"Page {current_page} of {total_pages}"
    canv.drawRightString(
        PAGE_WIDTH_PTS - PAGE_MARGIN_PTS,
        footer_text_y,
        footer_right_str,
    )

    canv.restoreState()


# -----------------------------------------------------------------------------
# PDF Document Assembly & Page Budget Enforcement
# -----------------------------------------------------------------------------

def build_pdf_report(
    analytics: ReportAnalytics,
    output_path: Path | str,
    category_chart: Image | Any | None = None,
    trend_chart: Image | Any | None = None,
    title: str = "Executive Financial Summary",
    subtitle: str = "Quarterly Expense Analysis & Variance",
) -> Path:
    """Compile the single-page executive PDF report and assert page budget compliance.

    Assembles the document flowable story:
      - Header Banner Table (Title, Subtitle, Date Window)
      - Gap Spacer (10 pt)
      - KPI Summary Cards Grid (4 cards across 540 pt)
      - Gap Spacer (12 pt)
      - Section Heading: 'EXECUTIVE SPEND ANALYSIS'
      - Gap Spacer (6 pt)
      - Dual Charts Table (Category Breakdown & Trend Line)
      - Gap Spacer (14 pt)
      - Section Heading: 'TOP 5 EXPENSE DISBURSEMENTS'
      - Gap Spacer (6 pt)
      - Top Expenses Table (5 rows + header, 540 pt)

    Enforces the strict single-page budget invariant: if the compiled document spills
    onto page 2, the partially generated output is deleted and a ``PDFBuildError``
    is raised immediately.

    Args:
        analytics: Synthesized reporting metrics container.
        output_path: Destination filesystem path for the output PDF.
        category_chart: Category spend bar chart Image flowable or Figure (optional).
        trend_chart: Chronological spend trend line chart Image flowable or Figure (optional).
        title: Document header title.
        subtitle: Document header subtitle.

    Returns:
        Path to the successfully verified single-page PDF document.

    Raises:
        PDFBuildError: If document compilation fails or exceeds the strict 1-page budget.
    """
    dest_path = Path(output_path).resolve()
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    styles = get_report_styles()

    # Generate charts dynamically if not provided by caller
    if category_chart is None or trend_chart is None:
        from reportgen.visuals.charts import render_report_charts
        generated_cat, generated_trend = render_report_charts(analytics=analytics)
        if category_chart is None:
            category_chart = generated_cat
        if trend_chart is None:
            trend_chart = generated_trend

    # Construct Platypus flowable story sequence adhering to calibrated budget
    story: list[Flowable] = [
        # 1. Executive Header Banner
        build_header_banner(
            title=title,
            subtitle=subtitle,
            date_range=analytics.date_range_str,
            styles=styles,
        ),
        Spacer(1, GAP_HEADER_KPI),

        # 2. 4-Card Executive KPI Grid
        build_kpi_grid(analytics=analytics, styles=styles),
        Spacer(1, GAP_KPI_SECTION),

        # 3. Visuals Section Heading
        build_section_heading("EXECUTIVE SPEND ANALYSIS", styles=styles),
        Spacer(1, GAP_SECTION_CHARTS),

        # 4. Dual Charts Row
        build_charts_container(category_chart=category_chart, trend_chart=trend_chart),
        Spacer(1, GAP_CHARTS_SECTION),

        # 5. Disbursements Section Heading
        build_section_heading("TOP 5 EXPENSE DISBURSEMENTS", styles=styles),
        Spacer(1, GAP_SECTION_TABLE),

        # 6. High-Value Expense Ledger Table
        build_top_expenses_table(expenses=analytics.top_expenses, styles=styles),
    ]

    # Initialize document template locked strictly to US Letter portrait
    doc = SimpleDocTemplate(
        str(dest_path),
        pagesize=letter,
        leftMargin=PAGE_MARGIN_PTS,
        rightMargin=PAGE_MARGIN_PTS,
        topMargin=PAGE_MARGIN_PTS,
        bottomMargin=PAGE_MARGIN_PTS,
    )

    def _page_decorator_callback(canv: canvas.Canvas, document: Any) -> None:
        draw_page_decorations(
            canv=canv,
            doc=document,
            generated_at=analytics.generated_at,
            total_pages=1,
        )

    # Build document and catch layout or flowable failures
    try:
        doc.build(
            story,
            onFirstPage=_page_decorator_callback,
            onLaterPages=_page_decorator_callback,
        )
    except Exception as exc:
        if dest_path.exists():
            dest_path.unlink(missing_ok=True)
        raise PDFBuildError(
            f"PDF build failed for '{dest_path}': {exc}"
        ) from exc

    # Strict single-page budget invariant assertion
    if doc.page > 1:
        if dest_path.exists():
            dest_path.unlink(missing_ok=True)
        raise PDFBuildError(
            f"Document exceeded strict 1-page budget (rendered {doc.page} pages). "
            "Review component vertical padding and spacers."
        )

    logger.info("Successfully synthesized 1-page executive PDF report: %s", dest_path)
    return dest_path


def build_report_pdf(
    analytics: ReportAnalytics,
    config: ReportConfig,
    category_chart_fig: matplotlib.figure.Figure | None = None,
    trend_chart_fig: matplotlib.figure.Figure | None = None,
) -> Path:
    """Compile the single-page executive PDF report using a runtime ReportConfig.

    Adapter function bridging runtime configuration models with ``build_pdf_report``.

    Args:
        analytics: Calculated metrics and summaries.
        config: Report generation parameters.
        category_chart_fig: Optional pre-rendered category bar chart figure or flowable.
        trend_chart_fig: Optional pre-rendered trend line chart figure or flowable.

    Returns:
        Path to the generated PDF document.

    Raises:
        PDFBuildError: If compilation fails or layout spills beyond page 1.
    """
    category_chart = category_chart_fig
    trend_chart = trend_chart_fig

    if category_chart is None or trend_chart is None:
        from reportgen.visuals.charts import render_report_charts
        cat_img, trend_img = render_report_charts(
            analytics=analytics,
            currency_symbol=config.currency_symbol,
        )
        if category_chart is None:
            category_chart = cat_img
        if trend_chart is None:
            trend_chart = trend_img

    return build_pdf_report(
        analytics=analytics,
        output_path=config.output_path,
        category_chart=category_chart,
        trend_chart=trend_chart,
        title=config.title or analytics.report_title or "Executive Financial Summary",
        subtitle=config.subtitle or "Quarterly Expense Analysis & Variance",
    )
