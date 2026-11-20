"""ReportLab Platypus layout engine, typography styles, and PDF synthesis.

Provides publication-grade document construction adhering strictly to an executive
single-page vertical point budget.
"""

from __future__ import annotations

from reportgen.pdf.builder import (
    NumberedCanvas,
    PDFBuildError,
    build_pdf_report,
    build_report_pdf,
    draw_page_decorations,
)
from reportgen.pdf.components import (
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

__all__ = [
    # Styles & Tokens
    "COLOR_BORDER",
    "COLOR_CARD_BG",
    "COLOR_DARK",
    "COLOR_GREEN",
    "COLOR_MUTED",
    "COLOR_PRIMARY_NAVY",
    "COLOR_RED",
    "COLOR_WHITE",
    "get_report_styles",
    "get_report_stylesheet",
    # Flowable Components
    "build_charts_container",
    "build_header_banner",
    "build_kpi_grid",
    "build_section_heading",
    "build_top_expenses_table",
    "create_dual_charts_container",
    "create_header_banner",
    "create_kpi_cards_row",
    "create_top_expenses_table",
    # Builder & Compilation
    "NumberedCanvas",
    "PDFBuildError",
    "build_pdf_report",
    "build_report_pdf",
    "draw_page_decorations",
]
