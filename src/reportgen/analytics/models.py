"""Domain models for analytics, KPI summaries, and chart data points.

Provides immutable dataclasses representing the calculated metrics
consumed by visualizations and ReportLab PDF document builders.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class MetricCard:
    """Represents a single high-level executive KPI card."""

    title: str
    value: str
    subtitle: str | None = None
    delta_percent: float | None = None
    delta_is_positive_good: bool = False  # For expenses, lower spend is favorable


@dataclass(frozen=True)
class CategorySummary:
    """Aggregated spend details for a single category."""

    name: str
    total_amount: float
    percentage: float
    transaction_count: int


@dataclass(frozen=True)
class TimeSeriesPoint:
    """Single point in the chronological spend trend."""

    label: str
    period_start: date
    amount: float
    transaction_count: int


@dataclass(frozen=True)
class TopExpenseItem:
    """Individual high-value transaction for the executive ledger."""

    date_str: str
    description: str
    category: str
    department: str
    amount: float
    formatted_amount: str


@dataclass(frozen=True)
class ReportAnalytics:
    """Container holding all computed metrics for report generation."""

    date_start: date
    date_end: date
    total_spend: float
    transaction_count: int
    average_transaction: float
    top_category_name: str
    top_category_amount: float
    top_category_percentage: float
    pop_delta_percent: float
    kpis: list[MetricCard]
    categories: list[CategorySummary]
    trend_points: list[TimeSeriesPoint]
    top_expenses: list[TopExpenseItem]
