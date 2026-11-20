"""Comprehensive test suite for the ReportLab PDF compilation and layout subsystem.

Verifies typography styles, Platypus flowable components, running canvas decorators,
strict single-page budget enforcement, and end-to-end PDF report generation.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import pytest
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table

from reportgen.analytics.engine import calculate_analytics
from reportgen.analytics.models import MetricCard, ReportAnalytics, TopExpenseItem
from reportgen.config import PDFBuildError, ReportConfig
from reportgen.data.loader import load_transaction_csv
from reportgen.pdf.builder import (
    NumberedCanvas,
    build_pdf_report,
    build_report_pdf,
    draw_page_decorations,
)
from reportgen.pdf.components import (
    EXPENSES_TABLE_COL_WIDTHS,
    HEADER_COL_WIDTHS,
    KPI_OUTER_COL_WIDTHS,
    build_charts_container,
    build_header_banner,
    build_kpi_grid,
    build_section_heading,
    build_top_expenses_table,
    create_dual_charts_container,
    create_header_banner,
    create_kpi_cards_row,
    create_top_expenses_table,
)
from reportgen.pdf.styles import (
    COLOR_BORDER,
    COLOR_CARD_BG,
    COLOR_DARK,
    COLOR_GREEN,
    COLOR_MUTED,
    COLOR_PRIMARY_NAVY,
    COLOR_RED,
    COLOR_WHITE,
    get_report_styles,
    get_report_stylesheet,
)
from reportgen.visuals.charts import render_report_charts


# -----------------------------------------------------------------------------
# Fixtures & Verification Helpers
# -----------------------------------------------------------------------------

@pytest.fixture(scope="module")
def sample_analytics(sample_csv_path: Path) -> ReportAnalytics:
    """Compute analytics from the canonical sample dataset."""
    df = load_transaction_csv(sample_csv_path)
    return calculate_analytics(df)


@pytest.fixture
def minimal_analytics(minimal_cleaned_df: pd.DataFrame) -> ReportAnalytics:
    """Compute analytics from the minimal 5-row test dataset."""
    return calculate_analytics(minimal_cleaned_df)


def count_pdf_pages(file_path: Path) -> int:
    """Count physical pages in a compiled PDF file by inspecting binary page objects.

    Standard PDF specification structures define pages as dictionary objects with
    the key-value pair '/Type /Page'. Container catalogs use '/Type /Pages'.

    Args:
        file_path: Absolute or relative path to PDF file.

    Returns:
        Number of discrete pages rendered in the document.
    """
    with open(file_path, "rb") as f:
        content = f.read()
    # Matches /Type /Page followed by whitespace or dictionary delimiter, but not /Pages
    return len(re.findall(rb"/Type\s*/Page\b", content))


# -----------------------------------------------------------------------------
# 1. Typography & Stylesheet Tests
# -----------------------------------------------------------------------------

def test_get_report_styles_and_tokens() -> None:
    """Verify all required style tokens exist, are non-empty, and use standard Helvetica."""
    styles = get_report_styles()
    alt_styles = get_report_stylesheet()

    required_style_names = [
        "HeaderTitle",
        "DocTitle",
        "HeaderSubtitle",
        "DocSubtitle",
        "HeaderDateRange",
        "HeaderMeta",
        "HeaderDateSubtitle",
        "SectionHeading",
        "KpiLabel",
        "KpiValue",
        "KpiDeltaPositive",
        "KpiDeltaNegative",
        "KpiDeltaNeutral",
        "KpiContext",
        "TableHeader",
        "TableHeaderCell",
        "TableHeaderRight",
        "TableHeaderCellRight",
        "TableBodyCell",
        "TableCell",
        "TableAmountCell",
        "TableBodyCellRight",
        "TableDateCell",
        "FooterText",
    ]

    for name in required_style_names:
        assert name in styles, f"Expected '{name}' to be registered in stylesheet."
        assert name in alt_styles, f"Expected '{name}' to be registered in alias stylesheet."
        style = styles[name]
        # Invariant: Type 1 Helvetica fonts exclusively
        assert style.fontName in ("Helvetica", "Helvetica-Bold", "Helvetica-Oblique")
        assert style.fontSize > 0
        assert style.leading > 0


def test_color_tokens_and_contrast() -> None:
    """Verify core brand and semantic color hex codes match specifications."""
    assert COLOR_PRIMARY_NAVY.hexval() == HexColor("#1E3A8A").hexval()
    assert COLOR_DARK.hexval() == HexColor("#0F172A").hexval()
    assert COLOR_MUTED.hexval() == HexColor("#64748B").hexval()
    assert COLOR_GREEN.hexval() == HexColor("#059669").hexval()
    assert COLOR_RED.hexval() == HexColor("#DC2626").hexval()
    assert COLOR_CARD_BG.hexval() == HexColor("#F8FAFC").hexval()
    assert COLOR_BORDER.hexval() == HexColor("#E2E8F0").hexval()
    assert COLOR_WHITE.hexval() == HexColor("#FFFFFF").hexval()


# -----------------------------------------------------------------------------
# 2. Flowable Component Unit Tests
# -----------------------------------------------------------------------------

def test_build_header_banner_geometry() -> None:
    """Verify header banner table dimensions, column widths, and alias compatibility."""
    styles = get_report_styles()
    banner = build_header_banner(
        title="Executive Spend Report",
        subtitle="Internal Audit & Disbursement Ledger",
        date_range="Jan 01, 2026 - Mar 31, 2026",
        styles=styles,
    )
    assert isinstance(banner, Table)
    width, height = banner.wrap(540.0, 720.0)
    assert width == 540.0
    assert 30.0 <= height <= 50.0

    # Test backward-compatibility alias
    alt_banner = create_header_banner(
        title="Executive Spend Report",
        subtitle="Internal Audit",
        date_range_str="Q1 2026",
    )
    assert isinstance(alt_banner, Table)
    alt_w, alt_h = alt_banner.wrap(540.0, 720.0)
    assert alt_w == 540.0


def test_build_kpi_grid_structure_and_variants() -> None:
    """Verify 4-card KPI grid layout, delta indicators, and fallback behavior."""
    styles = get_report_styles()

    cards = [
        MetricCard("Total Spend", "$218,435.50", "+6.4%", "positive", "vs prior period"),
        MetricCard("Transactions", "250", None, "neutral", "Avg: $873.74"),
        MetricCard("Avg Ticket", "$873.74", "-2.1%", "negative", "vs prior period"),
        MetricCard("Top Category", "Engineering", "34.2%", "neutral", "$74,680.00 (34.2%)"),
    ]

    grid = build_kpi_grid(analytics=cards, styles=styles)
    assert isinstance(grid, Table)
    width, height = grid.wrap(540.0, 720.0)
    assert width == 540.0
    assert 40.0 <= height <= 60.0

    # Test alias create_kpi_cards_row
    alt_grid = create_kpi_cards_row(cards)
    assert isinstance(alt_grid, Table)

    # Test fallback with fewer than 4 cards
    sparse_cards = [MetricCard("Spend", "$10,000")]
    sparse_grid = build_kpi_grid(analytics=sparse_cards, styles=styles)
    w, h = sparse_grid.wrap(540.0, 720.0)
    assert w == 540.0


def test_build_section_heading_properties() -> None:
    """Verify section heading paragraph attributes and zero margins."""
    styles = get_report_styles()
    heading = build_section_heading("EXECUTIVE SPEND ANALYSIS", styles=styles)
    assert isinstance(heading, Paragraph)
    assert heading.style.name == "SectionHeading"
    assert heading.style.spaceBefore == 0
    assert heading.style.spaceAfter == 0


def test_build_charts_container_with_images_and_figures() -> None:
    """Verify dual charts table geometry and defensive conversion of Matplotlib Figures."""
    # Test with existing Image flowables
    fig1, ax1 = plt.subplots(figsize=(3.6, 2.4))
    ax1.plot([1, 2, 3], [4, 5, 6])
    fig2, ax2 = plt.subplots(figsize=(3.6, 2.4))
    ax2.bar(["A", "B"], [10, 20])

    # build_charts_container defensively converts Figures to Images
    charts_table = build_charts_container(category_chart=fig1, trend_chart=fig2)
    assert isinstance(charts_table, Table)
    width, height = charts_table.wrap(540.0, 720.0)
    assert width == 540.0
    assert 170.0 <= height <= 185.0

    # Also test create_dual_charts_container alias
    fig3, ax3 = plt.subplots()
    fig4, ax4 = plt.subplots()
    alt_table = create_dual_charts_container(category_chart=fig3, trend_chart=fig4)
    w, h = alt_table.wrap(540.0, 720.0)
    assert w == 540.0


def test_build_top_expenses_table_structure_and_caps() -> None:
    """Verify expense ledger table row limits, column widths, and empty-state fallback."""
    styles = get_report_styles()

    expenses = [
        TopExpenseItem("2026-03-12", f"High Value Expense Item #{i}", "Cloud & SaaS", "Engineering", 10000.0 - i * 500, f"${10000.0 - i * 500:,.2f}")
        for i in range(8)
    ]

    # Must cap to at most 5 records (+ 1 header row = 6 rows)
    ledger = build_top_expenses_table(expenses=expenses, styles=styles)
    assert isinstance(ledger, Table)
    # 6 rows total (1 header + 5 items)
    assert len(ledger._cellvalues) == 6
    width, height = ledger.wrap(540.0, 720.0)
    assert width == 540.0
    assert 100.0 <= height <= 130.0

    # Test alias create_top_expenses_table
    alt_ledger = create_top_expenses_table(expenses=expenses)
    assert len(alt_ledger._cellvalues) == 6

    # Test empty expenses list fallback
    empty_ledger = build_top_expenses_table(expenses=[])
    assert len(empty_ledger._cellvalues) == 2  # 1 header + 1 placeholder row
    w, h = empty_ledger.wrap(540.0, 720.0)
    assert w == 540.0


# -----------------------------------------------------------------------------
# 3. Canvas Decorators & Running Callbacks
# -----------------------------------------------------------------------------

def test_draw_page_decorations_on_canvas(tmp_path: Path) -> None:
    """Verify running canvas callbacks execute without errors."""
    pdf_path = tmp_path / "canvas_decorations.pdf"
    canv = canvas.Canvas(str(pdf_path), pagesize=letter)
    draw_page_decorations(canv, None, generated_at="2026-11-20T19:00:00Z", total_pages=1)
    canv.showPage()
    canv.save()

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 500
    assert count_pdf_pages(pdf_path) == 1


def test_numbered_canvas_two_pass(tmp_path: Path) -> None:
    """Verify NumberedCanvas accumulates and renders pages cleanly."""
    pdf_path = tmp_path / "numbered_canvas.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    styles = get_report_styles()
    doc.build([Paragraph("Numbered Canvas Page Test", styles["Normal"])], canvasmaker=NumberedCanvas)

    assert pdf_path.exists()
    assert count_pdf_pages(pdf_path) == 1


# -----------------------------------------------------------------------------
# 4. End-to-End PDF Generation & Invariants
# -----------------------------------------------------------------------------

def test_build_pdf_report_end_to_end_sample_data(sample_analytics: ReportAnalytics, tmp_path: Path) -> None:
    """Verify complete PDF compilation on canonical sample dataset adheres to all invariants."""
    pdf_path = tmp_path / "sample_report.pdf"
    result_path = build_pdf_report(
        analytics=sample_analytics,
        output_path=pdf_path,
        title="Executive Financial Disbursement Summary",
        subtitle="Quarterly Expense Analysis & Variance",
    )

    assert result_path == pdf_path.resolve()
    assert pdf_path.is_file()
    # Invariant: Size > 10 KB
    file_size = pdf_path.stat().st_size
    assert file_size > 10_000, f"Expected PDF size > 10 KB, got {file_size} bytes."

    # Invariant: Strict 1-Page
    assert count_pdf_pages(pdf_path) == 1, "Expected strictly 1 page in output PDF."


def test_build_report_pdf_adapter_with_config(sample_analytics: ReportAnalytics, tmp_path: Path) -> None:
    """Verify build_report_pdf adapter correctly extracts parameters from ReportConfig."""
    pdf_path = tmp_path / "config_report.pdf"
    config = ReportConfig(
        input_path=Path("dummy.csv"),
        output_path=pdf_path,
        title="Custom Portfolio Report",
        subtitle="Fiscal Year 2026 Q1",
        currency_symbol="$",
    )

    result_path = build_report_pdf(analytics=sample_analytics, config=config)
    assert result_path == pdf_path.resolve()
    assert pdf_path.is_file()
    assert count_pdf_pages(pdf_path) == 1


def test_build_pdf_report_with_minimal_data(minimal_analytics: ReportAnalytics, tmp_path: Path) -> None:
    """Verify report generation succeeds on sparse minimal data without division errors."""
    pdf_path = tmp_path / "minimal_report.pdf"
    result_path = build_pdf_report(analytics=minimal_analytics, output_path=pdf_path)

    assert result_path.is_file()
    assert count_pdf_pages(pdf_path) == 1


def test_build_pdf_report_with_explicit_pre_rendered_charts(
    sample_analytics: ReportAnalytics,
    tmp_path: Path,
) -> None:
    """Verify build_pdf_report accepts pre-rendered Image flowables."""
    cat_img, trend_img = render_report_charts(sample_analytics)
    pdf_path = tmp_path / "pre_rendered_report.pdf"

    result_path = build_pdf_report(
        analytics=sample_analytics,
        output_path=pdf_path,
        category_chart=cat_img,
        trend_chart=trend_img,
    )
    assert result_path.is_file()
    assert count_pdf_pages(pdf_path) == 1


# -----------------------------------------------------------------------------
# 5. Overflow & Error Defense Tests
# -----------------------------------------------------------------------------

def test_page_budget_overflow_defense(sample_analytics: ReportAnalytics, tmp_path: Path) -> None:
    """Verify that attempting to render a document that overflows raises PDFBuildError."""
    pdf_path = tmp_path / "overflow_test.pdf"

    # We simulate an overflow condition by constructing a SimpleDocTemplate with excessive height
    styles = get_report_styles()
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    story = [
        Paragraph("First Page Anchor", styles["HeaderTitle"]),
        Spacer(1, 450),
        Paragraph("Second Page Overflow Content", styles["HeaderTitle"]),
        Spacer(1, 450),
        Paragraph("Third Page Overflow Content", styles["HeaderTitle"]),
    ]

    doc.build(story)
    # The raw document produced 2 or 3 pages
    assert doc.page > 1

    # Now verify that build_pdf_report enforces the 1-page assertion and cleans up disk artifacts
    # We test this by monkeypatching GAP_HEADER_KPI to an excessive value that causes doc.page > 1
    import reportgen.pdf.builder as builder_module
    original_gap = builder_module.GAP_HEADER_KPI
    try:
        # A 400 pt spacer will push content over 1 page without exceeding single-frame height
        builder_module.GAP_HEADER_KPI = 400.0
        with pytest.raises(PDFBuildError, match="exceeded strict 1-page budget"):
            build_pdf_report(analytics=sample_analytics, output_path=pdf_path)

        # Invariant: Partial or multi-page output file must be cleaned up
        assert not pdf_path.exists(), "Overflowing PDF was not cleaned up after error."
    finally:
        builder_module.GAP_HEADER_KPI = original_gap


def test_layout_error_raises_pdf_build_error(sample_analytics: ReportAnalytics, tmp_path: Path) -> None:
    """Verify that unrenderable flowables or layout exceptions raise PDFBuildError."""
    pdf_path = tmp_path / "layout_error.pdf"

    import reportgen.pdf.builder as builder_module
    original_gap = builder_module.GAP_HEADER_KPI
    try:
        # A 1200 pt spacer exceeds the entire printable frame height (720 pt), triggering LayoutError
        builder_module.GAP_HEADER_KPI = 1200.0
        with pytest.raises(PDFBuildError, match="PDF build failed"):
            build_pdf_report(analytics=sample_analytics, output_path=pdf_path)

        assert not pdf_path.exists(), "Partially generated file must be unlinked."
    finally:
        builder_module.GAP_HEADER_KPI = original_gap


def test_long_text_wrapping_defense(sample_analytics: ReportAnalytics, tmp_path: Path) -> None:
    """Verify that extreme text lengths in titles, descriptions, and categories wrap gracefully."""
    long_desc = "Enterprise Multi-Regional High-Availability Distributed Kubernetes Cluster Compute Nodes " * 3
    long_dept = "Global Strategic Infrastructure Engineering Operations"
    long_cat = "Specialized Cloud Computing & Cognitive Microservices"

    extreme_expenses = [
        TopExpenseItem("2026-03-30", long_desc, long_cat, long_dept, 85000.0, "$85,000.00")
        for _ in range(5)
    ]

    custom_analytics = ReportAnalytics(
        total_spend=sample_analytics.total_spend,
        transaction_count=sample_analytics.transaction_count,
        average_transaction=sample_analytics.average_transaction,
        top_category_card=sample_analytics.top_category_card,
        category_breakdown=sample_analytics.category_breakdown,
        spending_trend=sample_analytics.spending_trend,
        top_expenses=extreme_expenses,
        date_range_str="Jan 01, 2026 - Dec 31, 2026",
        generated_at=sample_analytics.generated_at,
        raw_total_spend=sample_analytics.raw_total_spend,
        raw_transaction_count=sample_analytics.raw_transaction_count,
        report_title="Comprehensive Corporate Financial Expenditure Audit & Strategic Capital Allocation Analysis",
    )

    pdf_path = tmp_path / "long_text_report.pdf"
    result_path = build_pdf_report(
        analytics=custom_analytics,
        output_path=pdf_path,
        title=custom_analytics.report_title,
        subtitle="Quarterly Expense Analysis with Extremely Long Nested Paragraph Descriptions",
    )

    assert result_path.is_file()
    assert count_pdf_pages(result_path) == 1, "Long text wrapping caused unexpected multi-page spill!"
