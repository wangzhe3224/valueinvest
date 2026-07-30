"""Trend visualization for the trend module.

Renders a multi-panel PNG -- one subplot per metric (TTM line + latest-point
highlight) -- using a validated, colorblind-aware palette (see the dataviz
skill). matplotlib is imported lazily so the core library never hard-requires
it; call ``pip install valueinvest[plot]`` to enable.

Static PNG target (e.g. for Zhihu paste): no hover layer; identity is carried
by per-panel titles, not a legend (single series per panel).
"""
from typing import List, Optional

from .base import TrendMetric, TrendSeries, TrendSignalResult

# Validated palette (dataviz skill reference instance).
_PLOT_LIGHT = {
    "surface": "#fcfcfb",
    "ink": "#0b0b0b",
    "muted": "#898781",
    "grid": "#e1e0d9",
    "axis": "#c3c2b7",
    "series": "#2a78d6",
}
_PLOT_DARK = {
    "surface": "#1a1a19",
    "ink": "#ffffff",
    "muted": "#898781",
    "grid": "#2c2c2a",
    "axis": "#383835",
    "series": "#3987e5",
}

_LABELS = {
    TrendMetric.REVENUE: "Revenue",
    TrendMetric.GROSS_MARGIN: "Gross Margin",
    TrendMetric.NET_MARGIN: "Net Margin",
    TrendMetric.FCF_YIELD: "FCF Yield",
    TrendMetric.CCC: "Cash Conversion Cycle",
}


def _human(v: float) -> str:
    a = abs(v)
    if a >= 1e12:
        return f"{v / 1e12:.1f}T"
    if a >= 1e9:
        return f"{v / 1e9:.1f}B"
    if a >= 1e6:
        return f"{v / 1e6:.1f}M"
    if a >= 1e3:
        return f"{v / 1e3:.1f}K"
    return f"{v:.0f}"


def _fmt(metric: TrendMetric, val: float) -> str:
    if metric == TrendMetric.REVENUE:
        return _human(val)
    if metric == TrendMetric.CCC:
        return f"{val:.0f} days"
    return f"{val:.1f}%"


def plot_trends(
    series: TrendSeries,
    result: TrendSignalResult,
    output_path: str,
    metrics: Optional[List[TrendMetric]] = None,
    dark: bool = False,
) -> str:
    """Render a multi-panel TTM trend PNG. Returns the output_path.

    Raises ImportError with install guidance if matplotlib is unavailable.
    """
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise ImportError(
            "matplotlib is required for plot_trends. "
            "Install with: pip install valueinvest[plot]"
        ) from e

    pal = _PLOT_DARK if dark else _PLOT_LIGHT

    default_metrics = [
        TrendMetric.REVENUE,
        TrendMetric.GROSS_MARGIN,
        TrendMetric.NET_MARGIN,
        TrendMetric.FCF_YIELD,
    ]
    if result.ccc_applicable:
        default_metrics.append(TrendMetric.CCC)
    plot_metrics = metrics or default_metrics

    n = len(plot_metrics)
    fig, axes = plt.subplots(n, 1, figsize=(10, 2.6 * n), facecolor=pal["surface"])
    if n == 1:
        axes = [axes]

    ttm_recs = series.ttm_records()
    ttm_ends = [r.quarter_end for r in ttm_recs]

    for ax, metric in zip(axes, plot_metrics):
        ax.set_facecolor(pal["surface"])
        vals = series.ttm_values(metric)
        if vals:
            ax.plot(
                ttm_ends,
                vals,
                color=pal["series"],
                linewidth=2,
                marker="o",
                markersize=4,
                zorder=3,
            )
            # latest-point highlight
            ax.scatter(
                [ttm_ends[-1]],
                [vals[-1]],
                color=pal["ink"],
                s=42,
                zorder=4,
                edgecolor=pal["surface"],
                linewidth=1.5,
            )
            latest_str = _fmt(metric, vals[-1])
        else:
            latest_str = "n/a"

        ax.set_title(
            f"{_LABELS[metric]}  —  latest: {latest_str}",
            color=pal["ink"],
            fontsize=11,
            loc="left",
            pad=8,
        )
        ax.tick_params(colors=pal["muted"], labelsize=8)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(pal["axis"])
        ax.grid(True, color=pal["grid"], linewidth=0.6, zorder=0)
        ax.set_axisbelow(True)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        fig.autofmt_xdate(rotation=35, bottom=0.2)

    fig.suptitle(
        f"{series.ticker} — Financial Trends (TTM, {series.n_quarters}q)  "
        f"[{result.rating.value.upper()} {result.composite_score:.0f}]",
        color=pal["ink"],
        fontsize=13,
        x=0.02,
        ha="left",
    )
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(output_path, dpi=140, facecolor=pal["surface"], bbox_inches="tight")
    plt.close(fig)
    return output_path
