"""Visual theme tokens, color palettes, and Matplotlib rcParams styling defaults.

Establishes a publication-grade aesthetic designed for high-DPI rasterization and
deterministic PDF document integration: high data-to-ink ratio, subdued architectural
gridlines, accessible categorical colors, and legible sans-serif typography.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Generator

# Ensure headless execution and writable configuration cache directory before importing pyplot.
# On headless CI runners or containerized environments without a home directory, Matplotlib
# requires a writable configuration path to initialize font tables and glyph caches.
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

# Suppress non-critical font substitution warnings from polluting console streams
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# -----------------------------------------------------------------------------
# Color Palette Tokens
# -----------------------------------------------------------------------------

# Primary brand and trendline token: Deep Navy provides strong visual authority
# and anchors the primary data series across executive dashboards.
COLOR_PRIMARY = "#1E3A8A"

# Secondary / Accent token: Slate Blue offers balanced contrast for supporting
# fills, secondary category bars, and trendline areas.
COLOR_ACCENT = "#3B82F6"
COLOR_SECONDARY = "#3B82F6"

# Semantic accent tokens for highlights, favorable trends, and warnings
COLOR_TEAL = "#0D9488"
COLOR_AMBER = "#F59E0B"
COLOR_ROSE = "#E11D48"

# Structural surface and gridline tokens: subtle grays ensure that alignment
# guides provide visual orientation without competing with data ink.
COLOR_SURFACE = "#FFFFFF"
COLOR_CARD_BG = "#F8FAFC"
COLOR_GRID = "#E2E8F0"
COLOR_BORDER = "#CBD5E1"

# Typographic tokens: high-contrast charcoal for titles and primary metrics,
# muted slate for axis ticks, labels, and secondary metadata.
COLOR_TEXT_MAIN = "#0F172A"
COLOR_TEXT_MUTED = "#64748B"
COLOR_MUTED = "#64748B"

# 6-color accessible categorical palette (Rank 1 through 5 + Rank 6 for 'Other')
# Selected for high contrast, perceptual distinction, and colorblind accessibility.
CATEGORY_PALETTE: list[str] = [
    "#1E3A8A",  # Rank 1: Deep Navy (Dominant spend category)
    "#3B82F6",  # Rank 2: Slate Blue
    "#0D9488",  # Rank 3: Teal
    "#F59E0B",  # Rank 4: Amber
    "#E11D48",  # Rank 5: Rose
    "#64748B",  # Rank 6: Neutral Slate (Composite 'Other' bucket)
]

# Backward-compatible alias for CATEGORY_PALETTE
CHART_PALETTE: list[str] = CATEGORY_PALETTE


# -----------------------------------------------------------------------------
# Matplotlib rcParams Styling Configuration
# -----------------------------------------------------------------------------

CHART_RC_PARAMS: dict[str, object] = {
    # Typography: prefer clean system sans-serif typefaces available across platforms
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Helvetica", "Arial"],
    "text.color": COLOR_TEXT_MAIN,

    # Canvas & Surface Geometry: crisp white background to blend seamlessly into PDF pages
    "figure.facecolor": COLOR_SURFACE,
    "figure.edgecolor": "none",
    "axes.facecolor": COLOR_SURFACE,
    "axes.edgecolor": COLOR_BORDER,
    "axes.linewidth": 0.8,

    # Gridlines: subdued dashed rules to assist value estimation without visual clutter
    "grid.color": COLOR_GRID,
    "grid.linestyle": "--",
    "grid.linewidth": 0.6,
    "grid.alpha": 0.8,

    # Axis ticks & labels: subdued slate text with clean spacing
    "xtick.color": COLOR_TEXT_MUTED,
    "ytick.color": COLOR_TEXT_MUTED,
    "xtick.labelsize": 8.0,
    "ytick.labelsize": 8.0,
    "axes.labelcolor": COLOR_TEXT_MUTED,
    "axes.labelsize": 8.5,
    "axes.titlesize": 10.0,
    "axes.titleweight": "bold",
    "axes.titlecolor": COLOR_TEXT_MAIN,

    # Savings & rendering defaults: high DPI rasterization for publication print quality
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.04,
}


def apply_chart_theme() -> None:
    """Apply the publication-grade chart theme to global Matplotlib rcParams.

    Registers font preferences, background colors, gridline aesthetics, and tick
    styling globally for all subsequently instantiated figures.
    """
    plt.rcParams.update(CHART_RC_PARAMS)


@contextmanager
def chart_theme() -> Generator[None, None, None]:
    """Context manager applying the chart theme temporarily to a rendering block.

    Yields control within an active `matplotlib.rc_context` block and restores
    prior rcParams upon exit to avoid unintended global state side-effects.

    Example:
        >>> with chart_theme():
        ...     fig, ax = plt.subplots(...)
        ...     # render themed chart elements
    """
    with plt.rc_context(CHART_RC_PARAMS):
        yield
