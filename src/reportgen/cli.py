"""Command-line interface for reportgen.

Handles argument parsing, options resolution, log level configuration,
and maps pipeline errors to user-friendly console messages and exit codes.
"""

from __future__ import annotations

import os

# Ensure headless matplotlib config cache directory is set before imports
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import argparse
from pathlib import Path
import sys
import time
from typing import Sequence

from reportgen import __version__
from reportgen.analytics.engine import format_currency
from reportgen.config import ReportGenError
from reportgen.pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    """Construct the command-line argument parser with all supported options.

    Configures flags for input/output paths, executive titles, custom column
    mappings, monetary symbols, verbose tracing, quiet mode, and document viewing.
    """
    parser = argparse.ArgumentParser(
        prog="reportgen",
        description="Generate executive single-page PDF reports from transaction CSV exports.",
    )
    parser.add_argument(
        "input_pos",
        nargs="?",
        default=None,
        metavar="INPUT",
        help="Path to input transaction CSV file (can also be passed via -i/--input).",
    )
    parser.add_argument(
        "-i", "--input",
        dest="input_opt",
        default=None,
        help="Path to input transaction CSV file.",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Path where the compiled PDF report should be written (defaults to output/<stem>_report.pdf).",
    )
    parser.add_argument(
        "-t", "--title",
        default="Financial Disbursement Report",
        help="Headline title for the report banner.",
    )
    parser.add_argument(
        "-s", "--subtitle",
        default="Executive Spend & Variance Summary",
        help="Subtitle displayed beneath the main headline.",
    )
    parser.add_argument(
        "-m", "--mapping",
        default=None,
        help="Optional path to a YAML column mapping configuration file.",
    )
    parser.add_argument(
        "-c", "--currency",
        default="$",
        help="Currency symbol applied to metrics and charts (default: '$').",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Attempt to open the generated PDF with the default platform viewer.",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Silence standard console output; emit only error messages.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print verbose execution details and debug tracebacks on failure.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"reportgen {__version__}",
        help="Display package version and exit.",
    )
    return parser


def _open_file(path: Path) -> None:
    """Attempt to open the generated PDF file using the default system viewer.

    Launches the external viewer asynchronously so the CLI process is not blocked.
    Fails silently if the operating system viewer cannot be invoked.
    """
    try:
        import platform
        import subprocess

        sys_name = platform.system().lower()
        if sys_name == "darwin":
            subprocess.Popen(["open", str(path)])
        elif sys_name == "windows":
            import os
            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        # Non-critical: launching external viewer should never break report generation
        pass


def main(argv: Sequence[str] | None = None) -> int:
    """Execute the CLI application and return standard UNIX exit codes.

    Exit codes:
      0: Successful execution; PDF written to target destination.
      1: Unhandled runtime error.
      2: Command-line syntax or invalid flag arguments.
      10: Input file missing, unreadable, or invalid CSV encoding (DataLoadError).
      11: Schema validation failed; required columns missing (SchemaValidationError).
      12: Data empty or zero valid transaction records (DataProcessingError).
      13: Document rendering or layout budget failed (PDFBuildError / RenderingError).
    """
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        input_path = args.input_opt or args.input_pos
        if not input_path:
            parser.error("an input transaction CSV file is required (pass via -i/--input or positional argument)")

        start_time = time.perf_counter()
        progress_fn = None if args.quiet else print

        pdf_path, analytics = run_pipeline(
            input_path=input_path,
            output_path=args.output,
            mapping_path=args.mapping,
            title=args.title,
            subtitle=args.subtitle,
            currency=args.currency,
            progress_callback=progress_fn,
        )

        duration = time.perf_counter() - start_time
        if not args.quiet:
            total_spend_str = format_currency(analytics.raw_total_spend, args.currency)
            print(
                f"[SUCCESS] Report generated: {pdf_path} "
                f"({analytics.raw_transaction_count} transactions, "
                f"{analytics.date_range_str}, "
                f"Net Spend: {total_spend_str}) "
                f"in {duration:.2f}s."
            )

        if args.open:
            _open_file(pdf_path)

        return 0

    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 0
    except ReportGenError as err:
        if args.verbose:
            import traceback
            traceback.print_exc(file=sys.stderr)
        else:
            sys.stderr.write(f"[ERROR] {err}\n")
        return getattr(err, "exit_code", 1)
    except KeyboardInterrupt:
        sys.stderr.write("\n[INFO] Operation interrupted by user.\n")
        return 130
    except Exception as err:
        if args.verbose:
            import traceback
            traceback.print_exc(file=sys.stderr)
        else:
            sys.stderr.write(f"[ERROR] Unexpected runtime failure: {err}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
