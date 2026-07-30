"""Growth-signal functions for trend analysis.

Each signal fn has signature ``(series, metric) -> TrendSignal``. They are pure
functions; the engine composes them into a TrendSignalResult.

Scoring helpers (clamp, normalize_to_score) are defined locally to keep this
module self-contained and low-coupling, mirroring screener.scorers. Most signals
operate on the **TTM** series (seasonally smoothed); YoY / acceleration /
streak / inflection derive from the TTM series' year-over-year differences.
"""
from statistics import mean, median, stdev
from typing import Callable, List, Optional, Tuple

from .base import (
    METRIC_CATEGORY,
    TrendDirection,
    TrendMetric,
    TrendSignal,
    TrendSignalCategory,
    TrendSeries,
    metric_value,  # noqa: F401  (re-exported for convenience/testing)
    score_to_direction,
)

# A signal function maps (series, metric) -> TrendSignal.
SignalFn = Callable[[TrendSeries, TrendMetric], TrendSignal]


# --------------------------------------------------------------------------- #
# scoring helpers (self-contained; mirror screener.scorers)
# --------------------------------------------------------------------------- #
def clamp(value: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
    return max(min_val, min(max_val, value))


def normalize_to_score(
    value: float, min_val: float, max_val: float, reverse: bool = False
) -> float:
    """Normalize a value to 0-100. min_val -> 0, max_val -> 100 (reversed if reverse)."""
    if max_val == min_val:
        return 50.0
    normalized = (value - min_val) / (max_val - min_val) * 100
    if reverse:
        normalized = 100 - normalized
    return clamp(normalized)


def _higher_better(metric: TrendMetric) -> bool:
    """CCC is the only 'lower is better' metric."""
    return metric != TrendMetric.CCC


def _unavailable(name: str, metric: TrendMetric, reason: str) -> TrendSignal:
    return TrendSignal(
        name=name,
        metric=metric,
        category=METRIC_CATEGORY[metric],
        value=0.0,
        score=0.0,
        direction=TrendDirection.INSUFFICIENT_DATA,
        description=reason,
        is_available=False,
    )


def _make(
    name: str, metric: TrendMetric, value: float, score: float, desc: str
) -> TrendSignal:
    return TrendSignal(
        name=name,
        metric=metric,
        category=METRIC_CATEGORY[metric],
        value=value,
        score=clamp(score),
        direction=score_to_direction(score),
        description=desc,
    )


# --------------------------------------------------------------------------- #
# atomic series transforms (new -- not present elsewhere in the library)
# --------------------------------------------------------------------------- #
def _yoy_series(vals: List[float]) -> List[float]:
    """Year-over-year % change at each point (needs index i and i-4)."""
    out: List[float] = []
    for i in range(len(vals)):
        if i >= 4 and abs(vals[i - 4]) > 1e-9:
            out.append((vals[i] - vals[i - 4]) / abs(vals[i - 4]) * 100)
    return out


def _acceleration_series(yoy: List[float]) -> List[float]:
    """First difference of YoY = second derivative of the underlying value."""
    return [yoy[i] - yoy[i - 1] for i in range(1, len(yoy))]


def _streak(accel: List[float]) -> Tuple[int, int]:
    """Consecutive same-sign accelerations from the latest backwards -> (sign, count)."""
    if not accel or accel[-1] == 0:
        return (0, 0)
    latest_sign = 1 if accel[-1] > 0 else -1
    count = 0
    for v in reversed(accel):
        s = 1 if v > 0 else (-1 if v < 0 else 0)
        if s == latest_sign:
            count += 1
        else:
            break
    return (latest_sign, count)


def _inflection(accel: List[float]) -> Optional[Tuple[int, str]]:
    """Most recent index where acceleration sign flips -> (index, 'trough'|'peak')."""
    for i in range(len(accel) - 1, 0, -1):
        s0 = 1 if accel[i - 1] > 0 else (-1 if accel[i - 1] < 0 else 0)
        s1 = 1 if accel[i] > 0 else (-1 if accel[i] < 0 else 0)
        if s0 != 0 and s1 != 0 and s0 != s1:
            return (i, "trough" if s1 > 0 else "peak")
    return None


def _regression_slope(vals: List[float]) -> float:
    n = len(vals)
    if n < 2:
        return 0.0
    xs = list(range(n))
    mx, my = mean(xs), mean(vals)
    num = sum((xs[i] - mx) * (vals[i] - my) for i in range(n))
    den = sum((xs[i] - mx) ** 2 for i in range(n))
    return num / den if den != 0 else 0.0


def _cv(vals: List[float]) -> Optional[float]:
    """Coefficient of variation = stdev / |mean| (None if undefined)."""
    if len(vals) < 2:
        return None
    m = mean(vals)
    if abs(m) < 1e-9:
        return None
    return stdev(vals) / abs(m)


def _cagr(vals: List[float]) -> float:
    """CAGR over series endpoints; vals are TTM (quarterly cadence -> /4 for years)."""
    if len(vals) < 2:
        return 0.0
    start, end = vals[0], vals[-1]
    if start <= 0 or end <= 0:
        return 0.0
    years = (len(vals) - 1) / 4.0
    if years <= 0:
        return 0.0
    return ((end / start) ** (1 / years) - 1) * 100


def _direction_by_increase_ratio(vals: List[float], higher_better: bool) -> str:
    """'improving'/'stable'/'declining'/'volatile' via up/down consistency."""
    if len(vals) < 3:
        return "stable"
    inc = sum(1 for i in range(1, len(vals)) if vals[i] > vals[i - 1])
    dec = sum(1 for i in range(1, len(vals)) if vals[i] < vals[i - 1])
    total = inc + dec
    if total == 0:
        return "stable"
    good = inc if higher_better else dec
    ratio = good / total
    if ratio >= 0.7:
        return "improving"
    if ratio <= 0.3:
        return "declining"
    if 0.4 <= ratio <= 0.6:
        return "stable"
    return "volatile"


# --------------------------------------------------------------------------- #
# signal functions
# --------------------------------------------------------------------------- #
def ttm_direction_signal(series: TrendSeries, metric: TrendMetric) -> TrendSignal:
    """TTM value up/down consistency (CCC inverted)."""
    ttm = series.ttm_values(metric)
    if len(ttm) < 3:
        return _unavailable("ttm_direction", metric, "need >=3 TTM points")
    hb = _higher_better(metric)
    d = _direction_by_increase_ratio(ttm, hb)
    score = {"improving": 90, "stable": 55, "volatile": 40, "declining": 15}[d]
    return _make("ttm_direction", metric, ttm[-1], score, f"TTM {metric.value}: {d}")


def cagr_signal(series: TrendSeries, metric: TrendMetric) -> TrendSignal:
    """CAGR over TTM endpoints (revenue)."""
    ttm = series.ttm_values(metric)
    if len(ttm) < 5:
        return _unavailable("cagr", metric, "need >=5 TTM points")
    cagr = _cagr(ttm)
    score = normalize_to_score(cagr, -10, 30)
    return _make("cagr", metric, cagr, score, f"CAGR {cagr:.1f}%")


def growth_level_signal(series: TrendSeries, metric: TrendMetric) -> TrendSignal:
    """Median YoY growth level (revenue)."""
    ttm = series.ttm_values(metric)
    yoy = _yoy_series(ttm)
    if len(yoy) < 3:
        return _unavailable("growth_level", metric, "need >=3 YoY points")
    med = median(yoy)
    score = normalize_to_score(med, -10, 40)
    return _make("growth_level", metric, med, score, f"median YoY {med:.1f}%")


def acceleration_signal(series: TrendSeries, metric: TrendMetric) -> TrendSignal:
    """Recent vs early acceleration (2nd derivative) -- half-mean style."""
    ttm = series.ttm_values(metric)
    accel = _acceleration_series(_yoy_series(ttm))
    if len(accel) < 3:
        return _unavailable("acceleration", metric, "need >=3 acceleration points")
    third = max(1, len(accel) // 3)
    delta = mean(accel[-third:]) - mean(accel[:third])
    score = normalize_to_score(delta, -15, 15)
    tag = "accelerating" if delta > 0 else ("decelerating" if delta < 0 else "flat")
    return _make("acceleration", metric, delta, score, f"{metric.value} {tag} (Δacc {delta:.1f})")


def streak_signal(series: TrendSeries, metric: TrendMetric) -> TrendSignal:
    """Consecutive accelerating/decelerating quarters."""
    ttm = series.ttm_values(metric)
    accel = _acceleration_series(_yoy_series(ttm))
    sign, count = _streak(accel)
    if count == 0:
        return _unavailable("streak", metric, "no consistent acceleration streak")
    if sign > 0:
        score = normalize_to_score(count, 1, 4)
        desc = f"{count} consecutive accelerating quarters"
    else:
        score = normalize_to_score(count, 1, 4, reverse=True)
        desc = f"{count} consecutive decelerating quarters"
    return _make("streak", metric, count, score, desc)


def inflection_signal(series: TrendSeries, metric: TrendMetric) -> TrendSignal:
    """Most recent YoY inflection: recent trough up = good, recent peak down = bad."""
    ttm = series.ttm_values(metric)
    accel = _acceleration_series(_yoy_series(ttm))
    inf = _inflection(accel)
    if inf is None:
        return _unavailable("inflection", metric, "no recent inflection")
    idx, kind = inf
    recency = len(accel) - 1 - idx  # quarters since inflection
    if kind == "trough":
        score = normalize_to_score(recency, 4, 0)  # recent -> high
        desc = f"upward inflection {recency}q ago (trough)"
    else:
        score = normalize_to_score(recency, 4, 0, reverse=True)  # recent -> low
        desc = f"downward inflection {recency}q ago (peak)"
    return _make("inflection", metric, recency, score, desc)


def level_vs_history_signal(series: TrendSeries, metric: TrendMetric) -> TrendSignal:
    """Latest TTM vs historical median (CCC inverted)."""
    ttm = series.ttm_values(metric)
    if len(ttm) < 4:
        return _unavailable("level_vs_history", metric, "need >=4 TTM points")
    latest = ttm[-1]
    med = median(ttm[:-1])
    if abs(med) < 1e-9:
        return _unavailable("level_vs_history", metric, "zero/near-zero historical median")
    pct = (latest - med) / abs(med) * 100
    score = normalize_to_score(pct, -20, 20, reverse=not _higher_better(metric))
    return _make("level_vs_history", metric, latest, score, f"latest {pct:+.1f}% vs median")


def stability_signal(series: TrendSeries, metric: TrendMetric) -> TrendSignal:
    """Stability of TTM values (lower coefficient of variation = better)."""
    ttm = series.ttm_values(metric)
    cv = _cv(ttm)
    if cv is None:
        return _unavailable("stability", metric, "insufficient/zero-mean data")
    score = normalize_to_score(cv, 0.4, 0.0)  # cv 0.4 -> 0, cv 0 -> 100
    return _make("stability", metric, cv, score, f"CV {cv:.2f}")


# --------------------------------------------------------------------------- #
# per-metric config
# --------------------------------------------------------------------------- #
class MetricConfig:
    """Which signals apply to a metric, and whether it needs applicability gating."""

    def __init__(self, signals: List[SignalFn], needs_applicability: bool = False):
        self.signals = signals
        self.needs_applicability = needs_applicability


METRIC_CONFIG = {
    TrendMetric.REVENUE: MetricConfig(
        [
            cagr_signal,
            growth_level_signal,
            acceleration_signal,
            streak_signal,
            inflection_signal,
            ttm_direction_signal,
            stability_signal,
        ]
    ),
    TrendMetric.GROSS_MARGIN: MetricConfig(
        [ttm_direction_signal, level_vs_history_signal, acceleration_signal, stability_signal]
    ),
    TrendMetric.NET_MARGIN: MetricConfig(
        [ttm_direction_signal, level_vs_history_signal, acceleration_signal, stability_signal]
    ),
    TrendMetric.FCF_YIELD: MetricConfig(
        [ttm_direction_signal, level_vs_history_signal, stability_signal]
    ),
    TrendMetric.CCC: MetricConfig(
        [ttm_direction_signal, level_vs_history_signal, stability_signal],
        needs_applicability=True,
    ),
}


# --------------------------------------------------------------------------- #
# CCC industry applicability
# --------------------------------------------------------------------------- #
_FINANCIAL_KEYWORDS = (
    "financial",
    "bank",
    "insurance",
    "证券",
    "银行",
    "保险",
)


def is_ccc_applicable(series: TrendSeries, sector_hint: str = "") -> bool:
    """Whether CCC is meaningful for this company.

    Skipped for financials (no inventory working capital) and for
    software/SaaS-like businesses where inventory is negligible relative to
    annualized revenue. Also skipped when inventory/AR/AP are all missing.
    """
    hint = (sector_hint or "").lower()
    if any(k in hint for k in _FINANCIAL_KEYWORDS):
        return False

    recs = series.records
    if not recs:
        return False

    if all(
        r.inventory == 0 and r.accounts_receivable == 0 and r.accounts_payable == 0
        for r in recs
    ):
        return False

    revenues = [r.revenue for r in recs]
    med_rev = median(revenues) if revenues else 0.0
    med_inv = median([r.inventory for r in recs])
    if med_rev > 0 and med_inv / (med_rev * 4) < 0.01:  # < 1% of annualized revenue
        return False

    return True
