"""Domain models for analytics calculations, executive KPI cards, and trend points.

Provides frozen dataclasses defining the analytical contract between statistical
computation, chart rendering, and ReportLab PDF document layout.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class MetricCard:
    """Executive KPI card representing a single high-level business metric.

    Attributes:
        label: Metric identifier (e.g., 'Total Spend', 'Transactions').
        value: Formatted display string (e.g., '$218,435.50', '250').
        delta: Period-over-period variance string (e.g., '+6.4%'), or None if uncomputable.
        delta_type: Directional classification ('positive', 'negative', 'neutral') used
            by presentation components for visual indicators (arrows, accent colors).
        subtitle: Secondary contextual text (e.g., 'vs. prior period', 'Avg: $873.74').
    """

    label: str
    value: str
    delta: str | None = None
    delta_type: str = "neutral"
    subtitle: str | None = None

    @property
    def title(self) -> str:
        """Backward-compatibility alias for label."""
        return self.label


@dataclass(frozen=True)
class CategorySummary:
    """Aggregated financial metrics for an individual expense category or composite grouping.

    Attributes:
        name: Normalized category classification (or 'Other' for aggregated tail).
        total_spend: Sum of transaction amounts within this category.
        percentage: Proportion of total net expenditure represented by this category (0.0 to 100.0).
        transaction_count: Frequency of transactions classified under this category.
    """

    name: str
    total_spend: float
    percentage: float
    transaction_count: int

    @property
    def total_amount(self) -> float:
        """Backward-compatibility alias for total_spend."""
        return self.total_spend


@dataclass(frozen=True)
class TimeSeriesPoint:
    """Discrete temporal observation in chronological spend trend series.

    Attributes:
        period_label: Formatted bucket description for axis rendering (e.g., 'Jan 2026', 'W03', 'Nov 15').
        start_date: Calendar commencement date for this temporal interval.
        total_spend: Sum of transaction amounts recorded within this interval.
        transaction_count: Frequency of transactions recorded within this interval.
    """

    period_label: str
    start_date: date
    total_spend: float
    transaction_count: int

    @property
    def label(self) -> str:
        """Backward-compatibility alias for period_label."""
        return self.period_label

    @property
    def period_start(self) -> date:
        """Backward-compatibility alias for start_date."""
        return self.start_date

    @property
    def amount(self) -> float:
        """Backward-compatibility alias for total_spend."""
        return self.total_spend


@dataclass(frozen=True)
class TopExpenseItem:
    """Itemized high-value transaction for executive ledger presentation.

    Attributes:
        date: ISO transaction date string (YYYY-MM-DD).
        description: Merchant, payee, or sanitized transaction note.
        category: Normalized expense classification.
        department: Cost center or organizational division.
        amount: Raw numerical transaction amount.
        formatted_amount: Currency-formatted string (e.g., '$14,850.00').
    """

    date: str
    description: str
    category: str
    department: str
    amount: float
    formatted_amount: str

    @property
    def date_str(self) -> str:
        """Backward-compatibility alias for date."""
        return self.date


@dataclass(frozen=True)
class ReportAnalytics:
    """Root container encapsulating all computed metrics and aggregations for report generation.

    Attributes:
        total_spend: Executive KPI card summarizing gross/net expenditure and PoP delta.
        transaction_count: Executive KPI card summarizing transaction volume and average spend.
        average_transaction: Executive KPI card summarizing mean disbursement amount.
        top_category_card: Executive KPI card highlighting the dominant expense category.
        category_breakdown: Ranked categories (top 5 plus composite 'Other' when >5 exist).
        spending_trend: Chronological spend points aggregated at adaptive time granularity.
        top_expenses: Top 5 individual expense disbursements sorted by amount descending.
        date_range_str: Human-readable reporting window (e.g., 'Jan 04, 2026 - Mar 31, 2026').
        generated_at: ISO or UTC timestamp indicating when calculations were synthesized.
        raw_total_spend: Raw numerical sum of all transaction amounts.
        raw_transaction_count: Total count of processed transaction records.
        report_title: Heading string for report presentation.
        date_start: Earliest transaction date observed in dataset.
        date_end: Latest transaction date observed in dataset.
        pop_delta_percent: Numerical Period-over-Period variance percentage (or None).
    """

    total_spend: MetricCard
    transaction_count: MetricCard
    average_transaction: MetricCard
    top_category_card: MetricCard
    category_breakdown: list[CategorySummary]
    spending_trend: list[TimeSeriesPoint]
    top_expenses: list[TopExpenseItem]
    date_range_str: str
    generated_at: str
    raw_total_spend: float
    raw_transaction_count: int
    report_title: str = "Executive Financial Summary"
    date_start: date | None = None
    date_end: date | None = None
    pop_delta_percent: float | None = None

    @property
    def kpis(self) -> list[MetricCard]:
        """Ordered collection of primary KPI cards for dashboard grid rendering."""
        return [
            self.total_spend,
            self.transaction_count,
            self.average_transaction,
            self.top_category_card,
        ]

    @property
    def categories(self) -> list[CategorySummary]:
        """Backward-compatibility alias for category_breakdown."""
        return self.category_breakdown

    @property
    def trend_points(self) -> list[TimeSeriesPoint]:
        """Backward-compatibility alias for spending_trend."""
        return self.spending_trend

    @property
    def average_transaction_value(self) -> float:
        """Computed mean transaction value as raw float."""
        if self.raw_transaction_count == 0:
            return 0.0
        return self.raw_total_spend / self.raw_transaction_count

    @property
    def top_category_name(self) -> str:
        """Name of the primary spending category, or empty string if empty."""
        if not self.category_breakdown:
            return ""
        return self.category_breakdown[0].name

    @property
    def top_category_amount(self) -> float:
        """Total expenditure in the primary category, or 0.0 if empty."""
        if not self.category_breakdown:
            return 0.0
        return self.category_breakdown[0].total_spend

    @property
    def top_category_percentage(self) -> float:
        """Expenditure proportion of primary category, or 0.0 if empty."""
        if not self.category_breakdown:
            return 0.0
        return self.category_breakdown[0].percentage
