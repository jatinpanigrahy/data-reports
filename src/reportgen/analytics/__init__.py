"""Analytics models and statistical calculation engine.

Exports core immutable data models and analytical computation functions for
financial transaction datasets.
"""

from reportgen.analytics.engine import (
    calculate_analytics,
    compute_analytics,
    format_currency,
)
from reportgen.analytics.models import (
    CategorySummary,
    MetricCard,
    ReportAnalytics,
    TimeSeriesPoint,
    TopExpenseItem,
)

__all__ = [
    "CategorySummary",
    "MetricCard",
    "ReportAnalytics",
    "TimeSeriesPoint",
    "TopExpenseItem",
    "calculate_analytics",
    "compute_analytics",
    "format_currency",
]
