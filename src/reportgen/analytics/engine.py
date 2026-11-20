"""Statistical analytics engine for financial transaction datasets.

Performs deterministic mathematical aggregations, Period-over-Period (PoP)
variance calculations, categorical distribution breakdowns, and adaptive
time-series bucketing with zero presentation dependencies.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pandas as pd

from reportgen.analytics.models import (
    CategorySummary,
    MetricCard,
    ReportAnalytics,
    TimeSeriesPoint,
    TopExpenseItem,
)
from reportgen.config import DataProcessingError


def format_currency(amount: float, symbol: str = "$") -> str:
    """Format a numerical amount as a standard currency string with thousand separators.

    Handles negative values explicitly by placing the minus sign before the currency
    symbol (e.g. -$450.00 rather than $-450.00) to adhere to standard financial notation.

    Args:
        amount: Raw numerical currency value.
        symbol: Currency symbol prefix (defaults to '$').

    Returns:
        Formatted monetary string with two decimal places.
    """
    if amount < 0:
        return f"-{symbol}{abs(amount):,.2f}"
    return f"{symbol}{amount:,.2f}"


def _compute_period_delta(
    df: pd.DataFrame,
    span_days: int,
) -> tuple[float | None, str | None, str]:
    """Calculate Period-over-Period (PoP) spend variance and trend classification.

    Applies adaptive temporal partitioning based on total dataset duration:
    - Span > 60 days: Partitions data into calendar months, comparing the latest
      complete or current month against the immediately preceding calendar month.
    - Span <= 60 days: Splits the chronological date span into two equal temporal
      windows [t_min, t_mid) and [t_mid, t_max] to compute variance between the
      earlier baseline and later activity.

    Mathematical Invariants:
    - If prior period spend is zero or negative, percentage growth is mathematically
      undefined; in this scenario, delta is set to None and delta_type is 'neutral'.
    - If the dataset has only a single period or single timestamp, variance cannot be
      established; returns (None, None, 'neutral').

    Args:
        df: Cleaned transaction DataFrame sorted chronologically by date.
        span_days: Calendar duration in days between min and max transaction dates.

    Returns:
        Tuple of (numeric_delta_percent, formatted_delta_string, delta_type).
        delta_type is 'positive' for increases (>0), 'negative' for decreases (<0),
        and 'neutral' for zero variance or uncomputable baselines.
    """
    if span_days > 60:
        # Group by calendar month to establish month-over-month progression
        monthly_spend = (
            df.groupby(df["date"].dt.to_period("M"), observed=False)["amount"]
            .sum()
            .sort_index()
        )
        if len(monthly_spend) < 2:
            return None, None, "neutral"

        current_spend = float(monthly_spend.iloc[-1])
        prior_spend = float(monthly_spend.iloc[-2])
    else:
        # Short span: partition into two equal temporal halves [t_min, t_mid) and [t_mid, t_max]
        t_min = df["date"].min()
        t_max = df["date"].max()
        if t_min == t_max:
            return None, None, "neutral"

        half_duration = (t_max - t_min) / 2
        t_mid = t_min + half_duration

        prior_spend = float(df[df["date"] < t_mid]["amount"].sum())
        current_spend = float(df[df["date"] >= t_mid]["amount"].sum())

    # Protect against division by zero or nonsensical percentages on negative baselines
    if prior_spend <= 0:
        return None, None, "neutral"

    delta = ((current_spend - prior_spend) / prior_spend) * 100.0

    if delta > 0:
        delta_str = f"+{delta:.1f}%"
        delta_type = "positive"
    elif delta < 0:
        delta_str = f"{delta:.1f}%"
        delta_type = "negative"
    else:
        delta_str = "0.0%"
        delta_type = "neutral"

    return delta, delta_str, delta_type


def _compute_category_summaries(
    df: pd.DataFrame,
    total_net_spend: float,
    top_n: int = 5,
) -> list[CategorySummary]:
    """Aggregate expenditure by category, retaining top N and grouping remainder into 'Other'.

    Mathematical Invariants:
    - Categories are sorted strictly descending by net spend.
    - If total unique categories exceed top_n, rows after top_n are summed into a composite
      'Other' entry. If unique categories <= top_n, no 'Other' bucket is introduced.
    - Category percentage shares are normalized against total_net_spend (sum to ~100%).

    Args:
        df: Cleaned transaction DataFrame.
        total_net_spend: Precomputed net expenditure across all records.
        top_n: Maximum individual categories to retain before bundling remainder.

    Returns:
        List of CategorySummary items sorted by total_spend descending.
    """
    grouped = (
        df.groupby("category", observed=False)["amount"]
        .agg(["sum", "count"])
        .sort_values("sum", ascending=False)
    )

    summaries: list[CategorySummary] = []
    category_count = len(grouped)

    # Process top individual categories
    primary_slice = grouped.iloc[:top_n]
    for cat_name, row in primary_slice.iterrows():
        spend = float(row["sum"])
        count = int(row["count"])
        pct = (spend / total_net_spend * 100.0) if total_net_spend > 0 else 0.0
        summaries.append(
            CategorySummary(
                name=str(cat_name),
                total_spend=spend,
                percentage=pct,
                transaction_count=count,
            )
        )

    # Aggregate tail into 'Other' if more than top_n categories exist
    if category_count > top_n:
        tail_slice = grouped.iloc[top_n:]
        other_spend = float(tail_slice["sum"].sum())
        other_count = int(tail_slice["count"].sum())
        other_pct = (other_spend / total_net_spend * 100.0) if total_net_spend > 0 else 0.0
        summaries.append(
            CategorySummary(
                name="Other",
                total_spend=other_spend,
                percentage=other_pct,
                transaction_count=other_count,
            )
        )

    return summaries


def _compute_spending_trend(
    df: pd.DataFrame,
    span_days: int,
) -> list[TimeSeriesPoint]:
    """Generate adaptive chronological trend points for time-series visualization.

    Adaptive bucketing rules:
    - Span > 90 days: Aggregated by calendar month ('ME').
    - Span 15 to 90 days: Aggregated by weekly intervals anchored to Mondays ('W-MON').
    - Span <= 14 days: Aggregated by calendar day ('D').

    Ensures continuous intervals between min and max transaction dates so downstream
    line charts render unbroken chronological sequences.

    Args:
        df: Cleaned transaction DataFrame sorted chronologically by date.
        span_days: Calendar duration in days between min and max transaction dates.

    Returns:
        List of TimeSeriesPoint items in chronological order.
    """
    if span_days > 90:
        # Use ME (MonthEnd) if supported by pandas runtime, else fall back to M
        freq = "ME"
        try:
            pd.date_range("2026-01-01", periods=1, freq="ME")
        except ValueError:
            freq = "M"
    elif span_days >= 15:
        freq = "W-MON"
    else:
        freq = "D"

    indexed = df.set_index("date").sort_index()
    resampled = (
        indexed.resample(freq)["amount"]
        .agg(total_spend="sum", transaction_count="count")
        .reset_index()
    )

    points: list[TimeSeriesPoint] = []
    for _, row in resampled.iterrows():
        dt = row["date"]
        spend = float(row["total_spend"])
        count = int(row["transaction_count"])

        if freq in ("ME", "M"):
            # Month start date and month-year label
            start_d = dt.replace(day=1).date()
            label = dt.strftime("%b %Y")
        elif freq == "W-MON":
            # Monday-anchored 7-day period start using native date arithmetic
            start_d = dt.date() - timedelta(days=6)
            label = dt.strftime("%b %d")
        else:
            # Daily interval
            start_d = dt.date()
            label = dt.strftime("%b %d")

        points.append(
            TimeSeriesPoint(
                period_label=label,
                start_date=start_d,
                total_spend=spend,
                transaction_count=count,
            )
        )

    return points


def _compute_top_expenses(
    df: pd.DataFrame,
    currency_symbol: str = "$",
    limit: int = 5,
) -> list[TopExpenseItem]:
    """Extract and format the highest-value individual transaction disbursements.

    Prioritizes gross expenditure transactions (amount > 0) to highlight major cost
    drivers on executive dashboards. In datasets containing exclusively credit or refund
    items, gracefully falls back to absolute rank without raising errors.

    Args:
        df: Cleaned transaction DataFrame.
        currency_symbol: Currency symbol for formatting monetary displays.
        limit: Maximum number of expense entries to extract.

    Returns:
        List of TopExpenseItem items sorted by amount descending.
    """
    positive_txs = df[df["amount"] > 0]
    target_df = positive_txs if not positive_txs.empty else df

    top_rows = target_df.sort_values("amount", ascending=False).head(limit)

    items: list[TopExpenseItem] = []
    for _, row in top_rows.iterrows():
        amt = float(row["amount"])
        date_val = row["date"]
        date_str = date_val.strftime("%Y-%m-%d") if hasattr(date_val, "strftime") else str(date_val)

        items.append(
            TopExpenseItem(
                date=date_str,
                description=str(row.get("description", "Unknown Transaction")),
                category=str(row.get("category", "Uncategorized")),
                department=str(row.get("department", "General")),
                amount=amt,
                formatted_amount=format_currency(amt, currency_symbol),
            )
        )

    return items


def compute_analytics(
    df: pd.DataFrame,
    report_title: str = "Executive Financial Summary",
    currency_symbol: str = "$",
    generated_at: str | None = None,
) -> ReportAnalytics:
    """Compute all executive KPIs, breakdowns, and trend points from cleaned transactions.

    Executes core statistical procedures:
    1. Net spend and transaction volume aggregation.
    2. Adaptive Period-over-Period (PoP) variance computation.
    3. Categorical distribution analysis with Top-5 + 'Other' bundling.
    4. Adaptive temporal trend bucketing based on dataset span.
    5. Highest-value disbursement ledger extraction.

    Args:
        df: Cleaned transaction DataFrame conforming to canonical schema.
        report_title: Header title for executive reporting presentation.
        currency_symbol: Currency symbol for monetary string formatting.
        generated_at: Optional override timestamp; defaults to current UTC time.

    Returns:
        Immutable ReportAnalytics container housing calculated metrics and cards.

    Raises:
        DataProcessingError: If the input DataFrame is empty or contains zero valid rows.
    """
    if df.empty or len(df) == 0:
        raise DataProcessingError("Cannot compute analytics on an empty dataset.")

    # Core volume and net monetary expenditure
    raw_total_spend = float(df["amount"].sum())
    raw_transaction_count = len(df)
    avg_transaction_val = (
        raw_total_spend / raw_transaction_count if raw_transaction_count > 0 else 0.0
    )

    # Date range and duration analysis
    min_date = df["date"].min()
    max_date = df["date"].max()
    span_days = (max_date.date() - min_date.date()).days

    if min_date.date() == max_date.date():
        date_range_str = min_date.strftime("%b %d, %Y")
    else:
        date_range_str = f"{min_date.strftime('%b %d, %Y')} - {max_date.strftime('%b %d, %Y')}"

    if generated_at is None:
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Period-over-Period variance
    pop_delta_percent, pop_delta_str, pop_delta_type = _compute_period_delta(df, span_days)

    # Categorical breakdown (Top 5 + 'Other')
    category_breakdown = _compute_category_summaries(df, raw_total_spend, top_n=5)

    # Identify primary spending category
    if category_breakdown:
        top_cat = category_breakdown[0]
        top_cat_card = MetricCard(
            label="Top Category",
            value=top_cat.name,
            delta=f"{top_cat.percentage:.1f}%",
            delta_type="neutral",
            subtitle=f"{format_currency(top_cat.total_spend, currency_symbol)} ({top_cat.percentage:.1f}%)",
        )
    else:
        top_cat_card = MetricCard(
            label="Top Category",
            value="None",
            delta=None,
            delta_type="neutral",
            subtitle=None,
        )

    # Assemble executive KPI cards
    total_spend_card = MetricCard(
        label="Total Spend",
        value=format_currency(raw_total_spend, currency_symbol),
        delta=pop_delta_str,
        delta_type=pop_delta_type,
        subtitle="vs. prior period" if pop_delta_str is not None else "Net expenditure",
    )

    transaction_count_card = MetricCard(
        label="Transactions",
        value=f"{raw_transaction_count:,}",
        delta=None,
        delta_type="neutral",
        subtitle=f"Avg: {format_currency(avg_transaction_val, currency_symbol)}",
    )

    average_transaction_card = MetricCard(
        label="Avg Transaction",
        value=format_currency(avg_transaction_val, currency_symbol),
        delta=None,
        delta_type="neutral",
        subtitle="Per transaction mean",
    )

    # Adaptive trend points and high-value expense ledger
    spending_trend = _compute_spending_trend(df, span_days)
    top_expenses = _compute_top_expenses(df, currency_symbol=currency_symbol, limit=5)

    return ReportAnalytics(
        total_spend=total_spend_card,
        transaction_count=transaction_count_card,
        average_transaction=average_transaction_card,
        top_category_card=top_cat_card,
        category_breakdown=category_breakdown,
        spending_trend=spending_trend,
        top_expenses=top_expenses,
        date_range_str=date_range_str,
        generated_at=generated_at,
        raw_total_spend=raw_total_spend,
        raw_transaction_count=raw_transaction_count,
        report_title=report_title,
        date_start=min_date.date(),
        date_end=max_date.date(),
        pop_delta_percent=pop_delta_percent,
    )


def calculate_analytics(
    df: pd.DataFrame,
    currency_symbol: str = "$",
    report_title: str = "Executive Financial Summary",
) -> ReportAnalytics:
    """Backward-compatible entry point calling compute_analytics.

    Args:
        df: Cleaned transaction DataFrame conforming to canonical schema.
        currency_symbol: Currency symbol for formatting monetary displays.
        report_title: Header title for executive reporting presentation.

    Returns:
        ReportAnalytics instance containing KPIs, breakdowns, and trend data.
    """
    return compute_analytics(
        df,
        report_title=report_title,
        currency_symbol=currency_symbol,
    )
