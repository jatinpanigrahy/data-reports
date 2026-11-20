"""Platypus flowable component builders for report layout.

Builds executive header banners, KPI metric card grids, chart containers,
and top expense disbursement tables.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from reportgen.analytics.models import MetricCard, TopExpenseItem

if TYPE_CHECKING:
    from reportlab.platypus import Flowable, Image, Table


def create_header_banner(
    title: str,
    subtitle: str,
    date_range_str: str,
) -> Table:
    """Build the document header banner with title, subtitle, and date window."""
    raise NotImplementedError("Header banner builder will be implemented in Phase 5.")


def create_kpi_cards_row(
    cards: list[MetricCard],
) -> Table:
    """Build the horizontal row of executive KPI metric cards."""
    raise NotImplementedError("KPI cards row builder will be implemented in Phase 5.")


def create_dual_charts_container(
    category_chart: Image,
    trend_chart: Image,
) -> Table:
    """Build side-by-side table container housing category and trend charts."""
    raise NotImplementedError("Charts container builder will be implemented in Phase 5.")


def create_top_expenses_table(
    expenses: list[TopExpenseItem],
) -> Table:
    """Build the high-value transaction disbursement ledger table."""
    raise NotImplementedError("Top expenses table builder will be implemented in Phase 5.")
