"""Trend visualization for the trend module.

Renders a multi-panel PNG -- one subplot per metric (TTM line + latest-point
highlight), plus a combined YoY-growth panel (revenue / net income / operating
cash flow) -- using a validated, colorblind-aware palette (see the dataviz
skill). matplotlib is imported lazily so the core library never hard-requires
it; call ``pip install valueinvest[plot]`` to enable.

Static PNG target (e.g. for Zhihu paste): no hover layer; identity is carried
by per-panel titles and (for the multi-series growth panel) direct end-of-line
labels, not a legend box.
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

# Categorical trio for the multi-series growth panel (Okabe-Ito derived,
# colorblind-aware; kept in the same value range as the validated base blue).
_GROWTH_COLORS_LIGHT = ("#2a78d6", "#d55e00", "#009e73")
_GROWTH_COLORS_DARK = ("#3987e5", "#ff9d4d", "#2fbf8f")

_GROWTH_PANEL_SPEC = (  # (metric, short label)
    (TrendMetric.REVENUE, "Revenue"),
    (TrendMetric.NET_INCOME, "Net income"),
    (TrendMetric.OPERATING_CASH_FLOW, "Op. cash flow"),
)

# Money metrics get a humanized (B/M) y-axis instead of raw %/days formatting.
_MONEY_METRICS = {TrendMetric.REVENUE, TrendMetric.NET_INCOME, TrendMetric.OPERATING_CASH_FLOW}

# Display clip for YoY growth so one tiny-base outlier (e.g. net income crossing
# zero) cannot flatten the whole panel. Only applied when actually exceeded.
_YOY_CLIP = 200.0

_LABELS = {
    TrendMetric.REVENUE: "Revenue",
    TrendMetric.GROSS_MARGIN: "Gross Margin",
    TrendMetric.NET_MARGIN: "Net Margin",
    TrendMetric.FCF_YIELD: "FCF Yield",
    TrendMetric.CCC: "Cash Conversion Cycle",
    TrendMetric.NET_INCOME: "Net Income",
    TrendMetric.OPERATING_CASH_FLOW: "Operating Cash Flow",
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
    if metric in _MONEY_METRICS:
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
    include_growth: bool = True,
) -> str:
    """Render a multi-panel TTM trend PNG. Returns the output_path.

    Panels: one per metric in ``metrics`` (defaults to revenue, net income,
    operating cash flow, gross/net margin, FCF yield, and CCC when
    applicable), then -- when ``include_growth`` -- a combined YoY panel
    overlaying revenue / net income / operating-cash-flow TTM growth.

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
    growth_colors = _GROWTH_COLORS_DARK if dark else _GROWTH_COLORS_LIGHT

    default_metrics = [
        TrendMetric.REVENUE,
        TrendMetric.NET_INCOME,
        TrendMetric.OPERATING_CASH_FLOW,
        TrendMetric.GROSS_MARGIN,
        TrendMetric.NET_MARGIN,
        TrendMetric.FCF_YIELD,
    ]
    if result.ccc_applicable:
        default_metrics.append(TrendMetric.CCC)
    plot_metrics = metrics or default_metrics

    n_panels = len(plot_metrics) + (1 if include_growth else 0)
    fig, axes = plt.subplots(
        n_panels, 1, figsize=(10, 2.6 * n_panels), facecolor=pal["surface"]
    )
    if n_panels == 1:
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
        if metric in _MONEY_METRICS:
            ax.yaxis.set_major_formatter(
                plt.FuncFormatter(lambda v, _: _human(v))
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

    if include_growth:
        _plot_growth_panel(axes[-1], series, pal, growth_colors, plt)

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


def _plot_growth_panel(ax, series: TrendSeries, pal, colors, plt) -> None:
    """Combined YoY panel: revenue / net income / operating cash flow TTM growth."""
    import matplotlib.dates as mdates

    ax.set_facecolor(pal["surface"])
    ttm_ends = [r.quarter_end for r in series.ttm_records()]
    clipped = False
    plotted_any = False

    for (metric, label), color in zip(_GROWTH_PANEL_SPEC, colors):
        yoy = series.ttm_yoy(metric)
        xs = [d for d, v in zip(ttm_ends, yoy) if v is not None]
        ys_raw = [v for v in yoy if v is not None]
        if not xs:
            continue
        if any(abs(v) > _YOY_CLIP for v in ys_raw):
            clipped = True
        ys = [max(-_YOY_CLIP, min(_YOY_CLIP, v)) for v in ys_raw]
        ax.plot(
            xs,
            ys,
            color=color,
            linewidth=2,
            marker="o",
            markersize=4,
            zorder=3,
        )
        # direct end-of-line label instead of a legend box
        ax.annotate(
            label,
            (xs[-1], ys[-1]),
            xytext=(6, 0),
            textcoords="offset points",
            color=color,
            fontsize=8,
            va="center",
            zorder=5,
        )
        plotted_any = True

    title = "YoY Growth (TTM)  —  Revenue / Net income / Op. cash flow"
    if clipped:
        title += f"  (display clipped to ±{_YOY_CLIP:.0f}%)"
    ax.set_title(
        title + ("" if plotted_any else "  —  n/a"),
        color=pal["ink"],
        fontsize=11,
        loc="left",
        pad=8,
    )
    ax.axhline(0, color=pal["axis"], linewidth=0.8, zorder=1)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.margins(x=0.12)  # room for end-of-line labels
    ax.tick_params(colors=pal["muted"], labelsize=8)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(pal["axis"])
    ax.grid(True, color=pal["grid"], linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

