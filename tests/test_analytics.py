"""Unit and regression tests for statistical analytics engine and data models.

Validates golden metrics on the canonical sample dataset, Period-over-Period (PoP)
variance calculations, adaptive temporal trend bucketing, categorical aggregations,
and defensive mathematical edge cases.
"""

from __future__ import annotations

import math
from pathlib import Path
import pandas as pd
import pytest

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
from reportgen.config import DataProcessingError
from reportgen.data.loader import load_transaction_csv


# -----------------------------------------------------------------------------
# Golden Reference Metric Verification
# -----------------------------------------------------------------------------

def test_sample_expenses_golden_metrics(sample_csv_path: Path) -> None:
    """Verify calculated metrics on data/sample_expenses.csv strictly match canonical specs."""
    df = load_transaction_csv(sample_csv_path)
    analytics = compute_analytics(df, report_title="Q1 2026 Executive Financial Report")

    # 1. Total Net Spend = $218,435.50
    assert math.isclose(analytics.raw_total_spend, 218435.50, rel_tol=1e-3)
    assert analytics.total_spend.value == "$218,435.50"
    assert analytics.total_spend.label == "Total Spend"

    # 2. Transaction Count = 250
    assert analytics.raw_transaction_count == 250
    assert analytics.transaction_count.value == "250"
    assert analytics.transaction_count.label == "Transactions"

    # 3. Average Transaction = $873.74
    assert math.isclose(analytics.average_transaction_value, 873.742, rel_tol=1e-3)
    assert analytics.average_transaction.value == "$873.74"

    # 4. Top Category = Cloud Infrastructure ($86,450.00, ~39.6%)
    assert analytics.top_category_name == "Cloud Infrastructure"
    assert analytics.top_category_card.value == "Cloud Infrastructure"
    assert math.isclose(analytics.top_category_amount, 86450.00, rel_tol=1e-3)
    assert math.isclose(analytics.top_category_percentage, 39.58, rel_tol=1e-2)
    assert analytics.top_category_card.delta == "39.6%"

    # 5. Period-over-Period (PoP) Delta = +6.4%
    assert analytics.pop_delta_percent is not None
    assert math.isclose(analytics.pop_delta_percent, 6.4, rel_tol=1e-1)
    assert analytics.total_spend.delta == "+6.4%"
    assert analytics.total_spend.delta_type == "positive"

    # 6. Top 5 Ledger items matching canonical ranks
    assert len(analytics.top_expenses) == 5

    rank1 = analytics.top_expenses[0]
    assert rank1.date == "2026-03-12"
    assert rank1.description == "Amazon Web Services Q1 Compute"
    assert rank1.category == "Cloud Infrastructure"
    assert rank1.department == "Engineering"
    assert math.isclose(rank1.amount, 14850.00)
    assert rank1.formatted_amount == "$14,850.00"

    rank2 = analytics.top_expenses[1]
    assert rank2.date == "2026-01-04"
    assert rank2.description == "Amazon Web Services Hosting"
    assert rank2.category == "Cloud Infrastructure"
    assert rank2.department == "Engineering"
    assert math.isclose(rank2.amount, 14250.00)
    assert rank2.formatted_amount == "$14,250.00"

    rank3 = analytics.top_expenses[2]
    assert rank3.date == "2026-02-18"
    assert rank3.description == "GCP BigQuery Annual Reservation"
    assert rank3.category == "Cloud Infrastructure"
    assert rank3.department == "Engineering"
    assert math.isclose(rank3.amount, 11500.00)
    assert rank3.formatted_amount == "$11,500.00"

    rank4 = analytics.top_expenses[3]
    assert rank4.date == "2026-02-28"
    assert rank4.description == "Cooley LLP Regulatory Filings"
    assert rank4.category == "Professional Services"
    assert rank4.department == "Legal"
    assert math.isclose(rank4.amount, 8200.00)
    assert rank4.formatted_amount == "$8,200.00"

    rank5 = analytics.top_expenses[4]
    assert rank5.date == "2026-03-24"
    assert rank5.description == "Deloitte Systems Integration"
    assert rank5.category == "Professional Services"
    assert rank5.department == "Operations"
    assert math.isclose(rank5.amount, 7500.00)
    assert rank5.formatted_amount == "$7,500.00"

    # 7. Metadata and date window
    assert analytics.date_range_str == "Jan 04, 2026 - Mar 31, 2026"
    assert analytics.report_title == "Q1 2026 Executive Financial Report"
    assert len(analytics.category_breakdown) == 5  # Exactly 5 categories in sample data, no "Other"

    # 8. Backward-compatible function calculate_analytics produces identical result
    compat_analytics = calculate_analytics(df, report_title="Q1 2026 Executive Financial Report")
    assert compat_analytics.raw_total_spend == analytics.raw_total_spend
    assert compat_analytics.total_spend.value == analytics.total_spend.value


# -----------------------------------------------------------------------------
# Edge Case Handling
# -----------------------------------------------------------------------------

def test_empty_dataframe_raises_data_processing_error() -> None:
    """Ensure passing an empty DataFrame raises DataProcessingError."""
    with pytest.raises(DataProcessingError, match="Cannot compute analytics on an empty dataset"):
        compute_analytics(pd.DataFrame())

    empty_canonical = pd.DataFrame(columns=["date", "category", "amount", "description", "department"])
    with pytest.raises(DataProcessingError, match="Cannot compute analytics on an empty dataset"):
        compute_analytics(empty_canonical)


def test_single_transaction_dataset() -> None:
    """Test analytics computations on a minimal dataset with exactly 1 record."""
    single_df = pd.DataFrame([
        {
            "date": pd.Timestamp("2026-02-15"),
            "category": "Software & SaaS",
            "amount": 250.00,
            "description": "Slack Pro Tier",
            "department": "Operations",
        }
    ])

    analytics = compute_analytics(single_df)

    assert analytics.raw_transaction_count == 1
    assert analytics.raw_total_spend == 250.00
    assert analytics.total_spend.value == "$250.00"
    assert analytics.average_transaction.value == "$250.00"
    assert analytics.date_range_str == "Feb 15, 2026"

    # Single record cannot produce a period variance
    assert analytics.total_spend.delta is None
    assert analytics.total_spend.delta_type == "neutral"
    assert analytics.pop_delta_percent is None

    # Category breakdown has 1 entry representing 100%
    assert len(analytics.category_breakdown) == 1
    assert analytics.category_breakdown[0].name == "Software & SaaS"
    assert analytics.category_breakdown[0].percentage == 100.0

    # Trend has 1 daily point
    assert len(analytics.spending_trend) == 1
    assert analytics.spending_trend[0].total_spend == 250.00
    assert analytics.spending_trend[0].transaction_count == 1

    # Top expenses ledger contains the single item
    assert len(analytics.top_expenses) == 1
    assert analytics.top_expenses[0].formatted_amount == "$250.00"


def test_negative_refund_amounts_reduce_net_spend() -> None:
    """Verify that credit/refund rows (negative amounts) correctly reduce total net spend."""
    df = pd.DataFrame([
        {
            "date": pd.Timestamp("2026-01-10"),
            "category": "Cloud Infrastructure",
            "amount": 1000.00,
            "description": "AWS Compute",
            "department": "Engineering",
        },
        {
            "date": pd.Timestamp("2026-01-15"),
            "category": "Software & SaaS",
            "amount": 500.00,
            "description": "Subscription",
            "department": "Engineering",
        },
        {
            "date": pd.Timestamp("2026-01-20"),
            "category": "Cloud Infrastructure",
            "amount": -200.00,
            "description": "Vendor Credit Refund",
            "department": "Engineering",
        },
    ])

    analytics = compute_analytics(df)

    # Net spend = 1000 + 500 - 200 = 1300.00
    assert math.isclose(analytics.raw_total_spend, 1300.00)
    assert analytics.total_spend.value == "$1,300.00"
    assert analytics.raw_transaction_count == 3
    # Average = 1300 / 3 = 433.333...
    assert math.isclose(analytics.average_transaction_value, 433.333, rel_tol=1e-2)

    # Top expenses ledger should prioritize the positive disbursements
    descriptions = [e.description for e in analytics.top_expenses]
    assert "AWS Compute" in descriptions
    assert "Subscription" in descriptions


# -----------------------------------------------------------------------------
# Categorical Aggregation Tests
# -----------------------------------------------------------------------------

def test_category_breakdown_exactly_five_vs_more_than_five() -> None:
    """Verify that 5 or fewer categories produce no 'Other' bucket, while 6+ categories do."""
    # Exactly 5 categories
    df_five = pd.DataFrame([
        {"date": pd.Timestamp("2026-01-01"), "category": f"Cat_{i}", "amount": float(100 * (10 - i)), "description": f"Tx_{i}", "department": "General"}
        for i in range(1, 6)
    ])
    analytics_five = compute_analytics(df_five)
    cat_names_five = [c.name for c in analytics_five.category_breakdown]
    assert len(analytics_five.category_breakdown) == 5
    assert "Other" not in cat_names_five
    assert math.isclose(sum(c.percentage for c in analytics_five.category_breakdown), 100.0, rel_tol=1e-3)

    # 7 categories -> top 5 + "Other" = 6 total
    df_seven = pd.DataFrame([
        {"date": pd.Timestamp("2026-01-01"), "category": f"Cat_{i}", "amount": float(100 * (10 - i)), "description": f"Tx_{i}", "department": "General"}
        for i in range(1, 8)
    ])
    analytics_seven = compute_analytics(df_seven)
    assert len(analytics_seven.category_breakdown) == 6
    assert analytics_seven.category_breakdown[-1].name == "Other"

    # Other should contain Cat_6 ($400) + Cat_7 ($300) = $700, 2 transactions
    other_cat = analytics_seven.category_breakdown[-1]
    assert math.isclose(other_cat.total_spend, 700.00)
    assert other_cat.transaction_count == 2

    # All percentages sum to 100%
    assert math.isclose(sum(c.percentage for c in analytics_seven.category_breakdown), 100.0, rel_tol=1e-3)


# -----------------------------------------------------------------------------
# Adaptive Time-Grain Trend Tests
# -----------------------------------------------------------------------------

def test_adaptive_time_grain_daily_weekly_monthly() -> None:
    """Verify time grain adapts to daily (<=14d), weekly (15-90d), and monthly (>90d)."""
    # 1. Daily: span = 10 days
    dates_daily = pd.date_range("2026-01-01", "2026-01-11", freq="D")
    df_daily = pd.DataFrame({
        "date": dates_daily,
        "category": "Cloud Infrastructure",
        "amount": 100.0,
        "description": "Daily Compute",
        "department": "Engineering",
    })
    analytics_daily = compute_analytics(df_daily)
    # Span is 10 days <= 14 -> daily bucketing (11 daily points)
    assert len(analytics_daily.spending_trend) == 11
    assert analytics_daily.spending_trend[0].period_label == "Jan 01"

    # 2. Weekly: span = 45 days (between 15 and 90 days)
    dates_weekly = pd.date_range("2026-01-01", "2026-02-15", freq="3D")
    df_weekly = pd.DataFrame({
        "date": dates_weekly,
        "category": "Software & SaaS",
        "amount": 200.0,
        "description": "Periodic License",
        "department": "Engineering",
    })
    analytics_weekly = compute_analytics(df_weekly)
    # Weekly points anchored on W-MON
    assert len(analytics_weekly.spending_trend) > 1
    # Check that intervals span 7 days
    point0 = analytics_weekly.spending_trend[0]
    assert point0.start_date is not None

    # 3. Monthly: span = 120 days (> 90 days)
    dates_monthly = pd.date_range("2026-01-01", "2026-05-01", freq="15D")
    df_monthly = pd.DataFrame({
        "date": dates_monthly,
        "category": "Professional Services",
        "amount": 500.0,
        "description": "Monthly Retainer",
        "department": "Operations",
    })
    analytics_monthly = compute_analytics(df_monthly)
    # Jan, Feb, Mar, Apr, May = 5 monthly points
    assert len(analytics_monthly.spending_trend) == 5
    assert analytics_monthly.spending_trend[0].period_label == "Jan 2026"
    assert analytics_monthly.spending_trend[-1].period_label == "May 2026"


# -----------------------------------------------------------------------------
# Period-over-Period (PoP) Variance Edge Cases
# -----------------------------------------------------------------------------

def test_period_over_period_short_span_half_split() -> None:
    """Test PoP variance on short span (<= 60 days) splitting into earlier vs later halves."""
    # Earlier half (Jan 01-15): spend = $200. Later half (Jan 16-30): spend = $300.
    # Growth = (300 - 200) / 200 * 100 = +50.0%
    df_growth = pd.DataFrame([
        {"date": pd.Timestamp("2026-01-05"), "category": "General", "amount": 200.0, "description": "T1", "department": "General"},
        {"date": pd.Timestamp("2026-01-25"), "category": "General", "amount": 300.0, "description": "T2", "department": "General"},
    ])
    analytics_growth = compute_analytics(df_growth)
    assert analytics_growth.total_spend.delta == "+50.0%"
    assert analytics_growth.total_spend.delta_type == "positive"
    assert analytics_growth.pop_delta_percent == 50.0

    # Earlier half spend = $400. Later half spend = $300.
    # Variance = (300 - 400) / 400 * 100 = -25.0%
    df_drop = pd.DataFrame([
        {"date": pd.Timestamp("2026-01-05"), "category": "General", "amount": 400.0, "description": "T1", "department": "General"},
        {"date": pd.Timestamp("2026-01-25"), "category": "General", "amount": 300.0, "description": "T2", "department": "General"},
    ])
    analytics_drop = compute_analytics(df_drop)
    assert analytics_drop.total_spend.delta == "-25.0%"
    assert analytics_drop.total_spend.delta_type == "negative"
    assert analytics_drop.pop_delta_percent == -25.0


def test_period_over_period_prior_period_zero_or_negative_spend() -> None:
    """Ensure that prior period spend <= 0 safely returns None with neutral delta type."""
    # Prior period spend = 0 (or negative)
    df_zero_prior = pd.DataFrame([
        {"date": pd.Timestamp("2026-01-05"), "category": "General", "amount": 0.0, "description": "Zero Spend", "department": "General"},
        {"date": pd.Timestamp("2026-01-25"), "category": "General", "amount": 500.0, "description": "Spend", "department": "General"},
    ])
    analytics = compute_analytics(df_zero_prior)
    assert analytics.total_spend.delta is None
    assert analytics.total_spend.delta_type == "neutral"
    assert analytics.pop_delta_percent is None


# -----------------------------------------------------------------------------
# Formatting and Model Contract Tests
# -----------------------------------------------------------------------------

def test_format_currency_helper() -> None:
    """Verify format_currency handles positive, negative, zero, and currency symbol overrides."""
    assert format_currency(218435.50) == "$218,435.50"
    assert format_currency(-450.00) == "-$450.00"
    assert format_currency(0.0) == "$0.00"
    assert format_currency(1234567.89, symbol="€") == "€1,234,567.89"
    assert format_currency(-125.50, symbol="£") == "-£125.50"


def test_model_properties_and_backward_compatibility(minimal_cleaned_df: pd.DataFrame) -> None:
    """Verify convenience properties and aliases on all frozen dataclasses."""
    analytics = compute_analytics(minimal_cleaned_df)

    # ReportAnalytics properties
    assert len(analytics.kpis) == 4
    assert analytics.categories == analytics.category_breakdown
    assert analytics.trend_points == analytics.spending_trend
    assert analytics.top_category_name == analytics.category_breakdown[0].name
    assert analytics.top_category_amount == analytics.category_breakdown[0].total_spend
    assert analytics.top_category_percentage == analytics.category_breakdown[0].percentage

    # MetricCard alias
    assert analytics.total_spend.title == analytics.total_spend.label

    # CategorySummary alias
    cat = analytics.category_breakdown[0]
    assert cat.total_amount == cat.total_spend

    # TimeSeriesPoint aliases
    pt = analytics.spending_trend[0]
    assert pt.label == pt.period_label
    assert pt.period_start == pt.start_date
    assert pt.amount == pt.total_spend

    # TopExpenseItem alias
    item = analytics.top_expenses[0]
    assert item.date_str == item.date
