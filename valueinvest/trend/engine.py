"""Trend Signal Engine -- composes growth signals into a trend assessment.

Mirrors redflags/engine.py: compute signals -> group by metric -> weighted
composite with available-weight redistribution (so a missing/CCC-inapplicable
metric's weight is reallocated across the rest).
"""
from statistics import mean
from typing import Dict, List, Optional

from .base import (
    METRIC_CATEGORY,
    TrendDirection,
    TrendMetric,
    TrendRating,
    TrendSeries,
    TrendSignal,
    TrendSignalResult,
    score_to_trend_rating,
)
from .signals import METRIC_CONFIG, clamp, is_ccc_applicable

DEFAULT_METRIC_WEIGHTS: Dict[TrendMetric, float] = {
    TrendMetric.REVENUE: 0.30,
    TrendMetric.GROSS_MARGIN: 0.20,
    TrendMetric.NET_MARGIN: 0.20,
    TrendMetric.FCF_YIELD: 0.20,
    TrendMetric.CCC: 0.10,
}


class TrendSignalEngine:
    """Detect growth/trend quality from a quarterly TrendSeries.

    Composes per-metric growth signals into a composite trend score (0-100).
    Higher score = healthier / accelerating trend.
    """

    def __init__(
        self,
        metric_weights: Optional[Dict[TrendMetric, float]] = None,
        sector_hint: str = "",
    ) -> None:
        self.metric_weights = metric_weights or dict(DEFAULT_METRIC_WEIGHTS)
        self.sector_hint = sector_hint

    def analyze(self, series: TrendSeries) -> TrendSignalResult:
        ccc_applicable = is_ccc_applicable(series, self.sector_hint)
        signals = self._compute_signals(series, ccc_applicable)
        return self._compose_result(series, signals, ccc_applicable)

    def _compute_signals(
        self, series: TrendSeries, ccc_applicable: bool
    ) -> List[TrendSignal]:
        out: List[TrendSignal] = []
        for metric, cfg in METRIC_CONFIG.items():
            if cfg.needs_applicability and not ccc_applicable:
                continue
            for fn in cfg.signals:
                try:
                    out.append(fn(series, metric))
                except Exception:
                    out.append(
                        TrendSignal(
                            name=getattr(fn, "__name__", "signal"),
                            metric=metric,
                            category=METRIC_CATEGORY[metric],
                            value=0.0,
                            score=0.0,
                            direction=TrendDirection.INSUFFICIENT_DATA,
                            description="Error computing signal",
                            is_available=False,
                        )
                    )
        return out

    def _compose_result(
        self,
        series: TrendSeries,
        signals: List[TrendSignal],
        ccc_applicable: bool,
    ) -> TrendSignalResult:
        weights = dict(self.metric_weights)

        # per-metric score = mean of its available signals
        metric_scores: Dict[TrendMetric, float] = {}
        for metric in METRIC_CONFIG:
            ms = [s for s in signals if s.metric == metric and s.is_available]
            if ms:
                metric_scores[metric] = mean(s.score for s in ms)

        # weighted composite with available-weight redistribution.
        # weights.get(m, 0.0) so a custom partial metric_weights doesn't KeyError.
        available_weight = sum(weights.get(m, 0.0) for m in metric_scores)
        composite = 0.0
        if available_weight > 0:
            composite = sum(
                s * (weights.get(m, 0.0) / available_weight)
                for m, s in metric_scores.items()
            )
        composite = clamp(composite)
        rating = score_to_trend_rating(composite)

        # category roll-ups
        growth_score = metric_scores.get(TrendMetric.REVENUE, 0.0)
        margin_vals = [
            metric_scores[m]
            for m in (TrendMetric.GROSS_MARGIN, TrendMetric.NET_MARGIN)
            if m in metric_scores
        ]
        margin_score = mean(margin_vals) if margin_vals else 0.0
        cash_flow_score = metric_scores.get(TrendMetric.FCF_YIELD, 0.0)
        efficiency_score = metric_scores.get(TrendMetric.CCC, 0.0)

        strengths = [
            f"{s.metric.value}.{s.name} ({s.score:.0f}): {s.description}"
            for s in signals
            if s.is_available and s.score >= 65
        ]
        weaknesses = [
            f"{s.metric.value}.{s.name} ({s.score:.0f}): {s.description}"
            for s in signals
            if s.is_available and s.score <= 35
        ]
        warnings = [s.description for s in signals if not s.is_available]
        if not ccc_applicable:
            warnings.append(
                "CCC skipped (software/financial business -- inventory negligible)"
            )

        analysis = self._build_analysis(series, composite, metric_scores, ccc_applicable)

        return TrendSignalResult(
            ticker=series.ticker,
            market=series.market,
            composite_score=composite,
            rating=rating,
            growth_score=growth_score,
            margin_score=margin_score,
            cash_flow_score=cash_flow_score,
            efficiency_score=efficiency_score,
            signals=signals,
            strengths=strengths,
            weaknesses=weaknesses,
            warnings=warnings,
            analysis=analysis,
            ccc_applicable=ccc_applicable,
            period_quarters=series.n_quarters,
        )

    @staticmethod
    def _build_analysis(
        series: TrendSeries,
        score: float,
        metric_scores: Dict[TrendMetric, float],
        ccc_applicable: bool,
    ) -> List[str]:
        rating = score_to_trend_rating(score)
        lines: List[str] = [
            f"{series.ticker}: Trend rating = {rating.value.upper()} "
            f"({score:.0f}/100) over {series.n_quarters} quarters"
        ]
        if metric_scores:
            best = max(metric_scores, key=metric_scores.get)
            worst = min(metric_scores, key=metric_scores.get)
            lines.append(
                f"Strongest dimension: {best.value} ({metric_scores[best]:.0f}) | "
                f"Weakest: {worst.value} ({metric_scores[worst]:.0f})"
            )
        if not ccc_applicable:
            lines.append("CCC not applicable for this business (excluded from composite)")
        if series.n_quarters < 8:
            lines.append(
                f"Note: only {series.n_quarters} quarters available -- "
                "growth/acceleration signals are limited"
            )
        return lines


def analyze_trend_signals(
    series: TrendSeries,
    metric_weights: Optional[Dict[TrendMetric, float]] = None,
    sector_hint: str = "",
) -> TrendSignalResult:
    """Convenience wrapper around TrendSignalEngine.analyze."""
    return TrendSignalEngine(
        metric_weights=metric_weights, sector_hint=sector_hint
    ).analyze(series)
