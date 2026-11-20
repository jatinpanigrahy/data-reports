"""Command-line interface for reportgen.

Handles argument parsing, options resolution, log level configuration,
and maps pipeline errors to user-friendly console messages and exit codes.
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence


def build_parser() -> argparse.ArgumentParser:
    """Construct the command-line argument parser with all supported options."""
    parser = argparse.ArgumentParser(
        prog="reportgen",
        description="Generate executive single-page PDF reports from transaction CSV exports.",
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Path to the input transaction CSV file.",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Path where the compiled PDF report should be written.",
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
        help="Currency symbol to display in metrics and tables (default: '$').",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Silence normal output and print only critical error messages.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print verbose execution details and debug tracebacks.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute the CLI application."""
    parser = build_parser()
    args = parser.parse_args(argv)
    # Stub: Phase 6 connects this parser to pipeline.generate_report
    if not args.quiet:
        print(f"reportgen: processing {args.input} -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
