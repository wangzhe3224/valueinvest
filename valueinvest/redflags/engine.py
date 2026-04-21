"""Accounting Red Flags Engine - composes signals into red flag assessment."""

from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from valueinvest.stock import Stock

from .base import (
    RedFlagResult, RedFlagSignal, RedFlagCategory,
    RiskLevel, RedFlagSeverity, _score_to_risk_level,
)
from .signals import ALL_SIGNALS

DEFAULT_CATEGORY_WEIGHTS: Dict[RedFlagCategory, float] = {
    RedFlagCategory.EARNINGS_QUALITY: 0.30,
    RedFlagCategory.REVENUE_RECOGNITION: 0.25,
    RedFlagCategory.ASSET_WORKING_CAPITAL: 0.25,
    RedFlagCategory.CAPITAL_STRUCTURE: 0.20,
}


class AccountingRedFlagsEngine:
    """Detects accounting manipulation risks from financial signals.

    Composes 11 individual signals across 4 categories into
    a composite red flag score (0-100). Higher score = more red flags.
    """

    def __init__(
        self,
        category_weights: Optional[Dict[str, float]] = None,
    ):
        self.category_weights = category_weights

    def analyze(self, stock: "Stock") -> RedFlagResult:
        signals = self._compute_signals(stock)
        return self._compose_result(stock, signals)

    def _compute_signals(self, stock: "Stock") -> List[RedFlagSignal]:
        results = []
        for signal_fn in ALL_SIGNALS:
            try:
                sig = signal_fn(stock)
                results.append(sig)
            except Exception:
                results.append(RedFlagSignal(
                    name=signal_fn.__name__,
                    category=RedFlagCategory.EARNINGS_QUALITY,
                    value=0, score=0,
                    severity=RedFlagSeverity.NONE,
                    description="Error computing signal",
                    is_available=False,
                ))
        return results

    def _compose_result(
        self,
        stock: "Stock",
        signals: List[RedFlagSignal],
    ) -> RedFlagResult:
        weights = dict(DEFAULT_CATEGORY_WEIGHTS)
        if self.category_weights:
            for cat_str, w in self.category_weights.items():
                weights[RedFlagCategory(cat_str)] = w

        category_scores: Dict[RedFlagCategory, list] = {}
        for sig in signals:
            if not sig.is_available:
                continue
            category_scores.setdefault(sig.category, []).append(sig)

        category_results = {}
        for cat in RedFlagCategory:
            cat_signals = category_scores.get(cat, [])
            if not cat_signals:
                category_results[cat] = 0.0
                continue
            category_results[cat] = sum(s.score for s in cat_signals) / len(cat_signals)

        available_weight = sum(
            weights[c] for c, s in category_results.items() if s > 0
        )

        if available_weight > 0:
            composite = 0
            for cat, score in category_results.items():
                if score > 0:
                    composite += score * (weights[cat] / available_weight)
        else:
            composite = 0

        composite = max(0, min(100, composite))

        triggered_flags = [
            s.description for s in signals
            if s.is_available and s.score >= 50
        ]

        warnings = [
            s.description for s in signals if not s.is_available
        ]

        analysis = self._build_analysis(stock, composite, category_results)

        return RedFlagResult(
            ticker=stock.ticker,
            overall_score=composite,
            risk_level=_score_to_risk_level(composite),
            earnings_quality_score=category_results.get(RedFlagCategory.EARNINGS_QUALITY, 0),
            revenue_recognition_score=category_results.get(RedFlagCategory.REVENUE_RECOGNITION, 0),
            asset_working_capital_score=category_results.get(RedFlagCategory.ASSET_WORKING_CAPITAL, 0),
            capital_structure_score=category_results.get(RedFlagCategory.CAPITAL_STRUCTURE, 0),
            signals=signals,
            triggered_flags=triggered_flags,
            warnings=warnings,
            analysis=analysis,
        )

    def _build_analysis(
        self,
        stock: "Stock",
        score: float,
        category_scores: Dict[RedFlagCategory, float],
    ) -> List[str]:
        lines = []
        risk_level = _score_to_risk_level(score)
        lines.append(
            f"{stock.ticker}: Accounting red flags = "
            f"{risk_level.value.upper()} ({score:.0f}/100)"
        )

        if score >= 60:
            lines.append(
                "Multiple significant accounting red flags detected "
                "-- thorough investigation required"
            )
        elif score >= 40:
            lines.append(
                "Some accounting concerns present -- monitor closely"
            )
        else:
            lines.append(
                "No significant accounting red flags detected"
            )

        available_cats = {c: s for c, s in category_scores.items() if s > 0}
        if available_cats:
            worst_cat = max(available_cats, key=available_cats.get)
            lines.append(
                f"Highest risk area: {worst_cat.value} "
                f"({available_cats[worst_cat]:.0f}/100)"
            )

        return lines
