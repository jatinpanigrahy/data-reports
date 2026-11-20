"""ReportLab stylesheet definitions and typography tokens.

Configures point sizes, line heights, font families, and color swatches
for consistent document rendering. Uses ReportLab standard Type 1 Helvetica
fonts exclusively to ensure deterministic font metrics across operating systems
without requiring external font file assets.
"""

from __future__ import annotations

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, StyleSheet1, getSampleStyleSheet


# -----------------------------------------------------------------------------
# Color Swatches (Design Tokens)
# -----------------------------------------------------------------------------

# Primary brand colors
COLOR_PRIMARY_NAVY = HexColor("#1E3A8A")   # Blue 900: Header accents, headings, table header
COLOR_DARK = HexColor("#0F172A")           # Slate 900: Document titles and high-emphasis numbers
COLOR_BODY = HexColor("#1E293B")           # Slate 800: Standard body text and table rows
COLOR_MUTED = HexColor("#64748B")          # Slate 500: Subtitles, metadata, and neutral labels

# Semantic indicators (Spend & Variance)
COLOR_GREEN = HexColor("#059669")          # Emerald 600: Favorable variance / spend reduction
COLOR_RED = HexColor("#DC2626")            # Red 600: Unfavorable variance / spend expansion

# Surfaces, borders, and contrasts
COLOR_CARD_BG = HexColor("#F8FAFC")        # Slate 50: Card background and alternating table rows
COLOR_BORDER = HexColor("#E2E8F0")         # Slate 200: Subtle card frames and row dividers
COLOR_WHITE = HexColor("#FFFFFF")          # Pure white: Page canvas and primary table rows


def get_report_styles() -> StyleSheet1:
    """Construct and return the standardized ReportLab stylesheet for the executive report.

    Creates an isolated stylesheet based on ReportLab's ``getSampleStyleSheet()`` and registers
    all typographic hierarchy tokens for headers, KPI summary cards, section titles, and
    tabular ledgers.

    All typography uses core Type 1 Helvetica fonts (``Helvetica``, ``Helvetica-Bold``,
    and ``Helvetica-Oblique``) so that layout metrics remain identical regardless of host
    OS font installations.

    Returns:
        A freshly populated ``StyleSheet1`` instance with document styles.
    """
    styles = getSampleStyleSheet()

    # Document Header & Metadata
    styles.add(
        ParagraphStyle(
            name="HeaderTitle",
            fontName="Helvetica-Bold",
            fontSize=18.0,
            leading=22.0,
            textColor=COLOR_PRIMARY_NAVY,
            alignment=TA_LEFT,
            spaceAfter=2.0,
        )
    )
    # DocTitle alias for compatibility
    styles.add(
        ParagraphStyle(
            name="DocTitle",
            parent=styles["HeaderTitle"],
        )
    )

    styles.add(
        ParagraphStyle(
            name="HeaderSubtitle",
            fontName="Helvetica",
            fontSize=8.5,
            leading=11.5,
            textColor=COLOR_MUTED,
            alignment=TA_LEFT,
        )
    )
    # DocSubtitle alias for compatibility
    styles.add(
        ParagraphStyle(
            name="DocSubtitle",
            parent=styles["HeaderSubtitle"],
        )
    )

    styles.add(
        ParagraphStyle(
            name="HeaderDateRange",
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11.5,
            textColor=COLOR_PRIMARY_NAVY,
            alignment=TA_RIGHT,
        )
    )
    # HeaderMeta alias for compatibility
    styles.add(
        ParagraphStyle(
            name="HeaderMeta",
            parent=styles["HeaderDateRange"],
        )
    )

    styles.add(
        ParagraphStyle(
            name="HeaderDateSubtitle",
            fontName="Helvetica-Bold",
            fontSize=7.0,
            leading=9.0,
            textColor=COLOR_MUTED,
            alignment=TA_RIGHT,
        )
    )

    # Section Headings
    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=13.0,
            textColor=COLOR_PRIMARY_NAVY,
            alignment=TA_LEFT,
            spaceBefore=0.0,
            spaceAfter=0.0,
        )
    )

    # KPI Metric Cards
    styles.add(
        ParagraphStyle(
            name="KpiLabel",
            fontName="Helvetica-Bold",
            fontSize=7.0,
            leading=9.0,
            textColor=COLOR_MUTED,
            alignment=TA_LEFT,
        )
    )

    styles.add(
        ParagraphStyle(
            name="KpiValue",
            fontName="Helvetica-Bold",
            fontSize=13.5,
            leading=16.5,
            textColor=COLOR_DARK,
            alignment=TA_LEFT,
        )
    )

    styles.add(
        ParagraphStyle(
            name="KpiDeltaPositive",
            fontName="Helvetica-Bold",
            fontSize=7.0,
            leading=9.0,
            textColor=COLOR_GREEN,
            alignment=TA_LEFT,
        )
    )

    styles.add(
        ParagraphStyle(
            name="KpiDeltaNegative",
            fontName="Helvetica-Bold",
            fontSize=7.0,
            leading=9.0,
            textColor=COLOR_RED,
            alignment=TA_LEFT,
        )
    )

    styles.add(
        ParagraphStyle(
            name="KpiDeltaNeutral",
            fontName="Helvetica",
            fontSize=7.0,
            leading=9.0,
            textColor=COLOR_MUTED,
            alignment=TA_LEFT,
        )
    )
    # KpiContext alias for compatibility
    styles.add(
        ParagraphStyle(
            name="KpiContext",
            parent=styles["KpiDeltaNeutral"],
        )
    )

    # Tabular Data Styles
    styles.add(
        ParagraphStyle(
            name="TableHeader",
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9.5,
            textColor=COLOR_WHITE,
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableHeaderCell",
            parent=styles["TableHeader"],
        )
    )

    styles.add(
        ParagraphStyle(
            name="TableHeaderRight",
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9.5,
            textColor=COLOR_WHITE,
            alignment=TA_RIGHT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableHeaderCellRight",
            parent=styles["TableHeaderRight"],
        )
    )

    styles.add(
        ParagraphStyle(
            name="TableBodyCell",
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=COLOR_DARK,
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableCell",
            parent=styles["TableBodyCell"],
        )
    )

    styles.add(
        ParagraphStyle(
            name="TableAmountCell",
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9.5,
            textColor=COLOR_DARK,
            alignment=TA_RIGHT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableBodyCellRight",
            parent=styles["TableAmountCell"],
        )
    )

    styles.add(
        ParagraphStyle(
            name="TableDateCell",
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=COLOR_MUTED,
            alignment=TA_LEFT,
        )
    )

    # Page Header / Footer / Canvas Notes
    styles.add(
        ParagraphStyle(
            name="FooterText",
            fontName="Helvetica",
            fontSize=7.0,
            leading=9.0,
            textColor=COLOR_MUTED,
            alignment=TA_LEFT,
        )
    )

    return styles


def get_report_stylesheet() -> StyleSheet1:
    """Alias for ``get_report_styles`` providing backward compatibility."""
    return get_report_styles()
