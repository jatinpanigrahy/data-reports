"""Visual theme tokens, color palettes, and Matplotlib rcParams defaults.

Defines a clean, modern aesthetic designed for print and high-DPI displays.
"""

from __future__ import annotations

# Theme color tokens
COLOR_PRIMARY = "#1E3A8A"      # Deep Navy: primary brand, trend line, top category
COLOR_SECONDARY = "#3B82F6"    # Vibrant Blue: secondary bars, fills
COLOR_ACCENT = "#0D9488"       # Teal: highlights, favorable indicators
COLOR_MUTED = "#64748B"        # Slate: labels, ticks, secondary text
COLOR_GRID = "#E2E8F0"         # Light Gray: subtle gridlines
COLOR_CARD_BG = "#F8FAFC"      # Off-white: card backgrounds
COLOR_TEXT_MAIN = "#0F172A"    # Dark Charcoal: primary text and values

# Ordered palette for categorical breakdowns (Top 5 + Other)
CHART_PALETTE: list[str] = [
    "#1E3A8A",  # Rank 1: Deep Navy
    "#2563EB",  # Rank 2: Royal Blue
    "#3B82F6",  # Rank 3: Blue
    "#60A5FA",  # Rank 4: Light Blue
    "#93C5FD",  # Rank 5: Soft Sky
    "#CBD5E1",  # Rank 6: Neutral Slate (Other)
]

# Matplotlib rcParams defaults for headless rendering
CHART_RC_PARAMS: dict[str, object] = {
    "font.sans-serif": ["DejaVu Sans", "Helvetica", "Arial"],
    "font.family": "sans-serif",
    "figure.facecolor": "#FFFFFF",
    "axes.facecolor": "#FFFFFF",
    "axes.edgecolor": "#CBD5E1",
    "axes.linewidth": 0.8,
    "grid.color": "#E2E8F0",
    "grid.linestyle": "--",
    "grid.linewidth": 0.6,
    "grid.alpha": 0.8,
    "xtick.color": "#64748B",
    "ytick.color": "#64748B",
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "text.color": "#0F172A",
}


def apply_chart_theme() -> None:
    """Apply the standard chart theme to Matplotlib rcParams."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(CHART_RC_PARAMS)
