"""Pipeline orchestration for the report generation lifecycle.

Connects data loading, cleaning, validation, statistical analysis,
visualization rendering, and PDF compilation into a single workflow.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Callable

# Ensure headless matplotlib config cache directory is set before imports
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

from reportgen.analytics.engine import compute_analytics, format_currency
from reportgen.analytics.models import ReportAnalytics
from reportgen.config import (
    DataLoadError,
    DataProcessingError,
    PDFBuildError,
    RenderingError,
    ReportConfig,
    ReportGenError,
    SchemaValidationError,
)
from reportgen.data.loader import load_and_prepare_data
from reportgen.pdf.builder import build_pdf_report
from reportgen.visuals.charts import render_report_charts

logger = logging.getLogger(__name__)


def run_pipeline(
    input_path: Path | str | ReportConfig | None = None,
    output_path: Path | str | None = None,
    mapping_path: Path | str | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    currency: str = "$",
    *,
    config: ReportConfig | None = None,
    progress_callback: Callable[[str], None] | None = None,
    **kwargs: Any,
) -> tuple[Path, ReportAnalytics]:
    """Execute the end-to-end report generation pipeline and return results.

    Coordinates data ingestion, cleaning, schema validation, analytics calculations,
    chart rendering, and single-page PDF compilation.

    Args:
        input_path: Raw CSV file path or a pre-configured ReportConfig instance.
        output_path: Destination path for the generated PDF. Defaults to
            'output/<input_stem>_report.pdf' if not specified.
        mapping_path: Optional path to a YAML column mapping configuration.
        title: Document headline banner text.
        subtitle: Secondary subtitle banner text.
        currency: Currency symbol applied to monetary amounts and chart axes.
        config: Optional ReportConfig dataclass containing runtime options.
        progress_callback: Optional callable receiving progress status messages.

    Returns:
        Tuple of (resolved_output_path, computed_analytics).

    Raises:
        DataLoadError: If input file is missing, empty, or unreadable.
        SchemaValidationError: If required canonical columns cannot be resolved.
        DataProcessingError: If dataset contains no usable rows or invalid types.
        RenderingError: If chart generation fails.
        PDFBuildError: If document compilation fails or exceeds the single-page budget.
    """
    # 1. Resolve configuration arguments
    if isinstance(input_path, ReportConfig):
        cfg = input_path
    elif config is not None:
        cfg = config
    else:
        cfg = None

    if cfg is not None:
        raw_in: Path | str = cfg.input_path
        raw_out: Path | str | None = output_path or cfg.output_path
        raw_map: Path | str | None = mapping_path or cfg.mapping_path
        rep_title: str = title or cfg.title
        rep_subtitle: str = subtitle or cfg.subtitle
        rep_currency: str = currency if currency != "$" else (cfg.currency_symbol or "$")
    else:
        if input_path is None:
            raise DataLoadError("An input CSV path is required to generate a report.")
        raw_in = input_path
        raw_out = output_path
        raw_map = mapping_path
        rep_title = title or "Financial Disbursement Report"
        rep_subtitle = subtitle or "Executive Spend & Variance Summary"
        rep_currency = currency or "$"

    in_file = Path(raw_in)
    if raw_out is not None:
        dest_path = Path(raw_out).resolve()
    else:
        dest_path = (Path("output") / f"{in_file.stem}_report.pdf").resolve()

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    def _notify(msg: str) -> None:
        logger.info(msg)
        if progress_callback is not None:
            progress_callback(msg)

    # 2. Ingestion, mapping, cleaning, and validation
    _notify(f"[INFO] Reading input data from '{in_file}'...")
    df = load_and_prepare_data(file_path=in_file, mapping_path=raw_map)

    date_min = df["date"].min().strftime("%Y-%m-%d")
    date_max = df["date"].max().strftime("%Y-%m-%d")
    _notify(f"[INFO] Resolved {len(df)} transactions spanning {date_min} to {date_max}.")

    # 3. Statistical analytics computation
    analytics = compute_analytics(
        df=df,
        report_title=rep_title,
        currency_symbol=rep_currency,
    )
    spend_str = format_currency(analytics.raw_total_spend, rep_currency)
    delta_str = (
        f"{analytics.pop_delta_percent:+.1f}%"
        if analytics.pop_delta_percent is not None
        else (analytics.total_spend.delta or "N/A")
    )
    _notify(f"[INFO] Calculated executive KPIs (Total Spend: {spend_str}, Period Delta: {delta_str}).")

    # 4. Publication-grade visualization rendering
    _notify("[INFO] Generated category breakdown and time-series trend visuals.")
    category_chart, trend_chart = render_report_charts(
        analytics=analytics,
        currency_symbol=rep_currency,
    )

    # 5. ReportLab Platypus single-page PDF compilation
    final_pdf_path = build_pdf_report(
        analytics=analytics,
        output_path=dest_path,
        category_chart=category_chart,
        trend_chart=trend_chart,
        title=rep_title,
        subtitle=rep_subtitle,
    )
    _notify(f"[INFO] Compiled single-page PDF dashboard to '{final_pdf_path}'.")

    return final_pdf_path, analytics


def generate_report(
    input_path: Path | str | ReportConfig | None = None,
    output_path: Path | str | None = None,
    mapping_path: Path | str | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    currency: str = "$",
    *,
    config: ReportConfig | None = None,
    **kwargs: Any,
) -> Path:
    """Run the complete report generation pipeline and return the generated PDF path.

    Primary public API entry point for programmatic report generation.

    Args:
        input_path: Path to the raw transaction CSV, or a ReportConfig instance.
        output_path: Destination path for the compiled PDF. Defaults to
            'output/<input_stem>_report.pdf' if omitted.
        mapping_path: Optional path to a YAML column alias mapping configuration.
        title: Headline title for the report banner.
        subtitle: Subtitle displayed beneath the headline.
        currency: Monetary symbol applied to values and charts (defaults to '$').
        config: Optional ReportConfig dataclass instance containing runtime options.

    Returns:
        Path to the successfully generated and verified single-page PDF file.

    Raises:
        DataLoadError: If input file is missing, empty, or unreadable.
        SchemaValidationError: If required canonical columns cannot be resolved.
        DataProcessingError: If dataset contains no usable rows or invalid types.
        RenderingError: If chart generation fails.
        PDFBuildError: If document compilation fails or exceeds the single-page budget.
    """
    pdf_path, _ = run_pipeline(
        input_path=input_path,
        output_path=output_path,
        mapping_path=mapping_path,
        title=title,
        subtitle=subtitle,
        currency=currency,
        config=config,
        **kwargs,
    )
    return pdf_path
