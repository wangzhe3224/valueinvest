"""Capital Allocation Engine - composes signals into allocation quality assessment."""

from inspect import signature
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from valueinvest.stock import Stock

from .base import (
    CapitalAllocationResult, AllocationSignal,
    AllocationCategory, AllocationRating,
    _score_to_rating, SignalLevel,
)
from .signals import ALL_SIGNALS

# Default category weights
DEFAULT_CATEGORY_WEIGHTS: Dict[AllocationCategory, float] = {
    AllocationCategory.SHAREHOLDER_RETURN: 0.35,
    AllocationCategory.REINVESTMENT: 0.25,
    AllocationCategory.BALANCE_SHEET: 0.20,
    AllocationCategory.DILUTION: 0.20,
}


class CapitalAllocationEngine:
    """Analyzes management capital allocation quality.

    Composes 12 individual signals across 4 categories into
    a composite score (0-100) and allocation rating.
    """

    def __init__(
        self,
        roic: Optional[float] = None,
        wacc: Optional[float] = None,
        prior_debt_ratio: Optional[float] = None,
        category_weights: Optional[Dict[str, float]] = None,
    ):
        self.roic = roic
        self.wacc = wacc
        self.prior_debt_ratio = prior_debt_ratio
        self.category_weights = category_weights

    def analyze(self, stock: "Stock") -> CapitalAllocationResult:
        """Run all capital allocation signals and produce composite result."""
        signals = self._compute_signals(stock)
        return self._compose_result(stock, signals)

    def _compute_signals(self, stock: "Stock") -> List[AllocationSignal]:
        """Compute all available signals."""
        results = []
        extra_kwargs = {
            "roic": self.roic,
            "wacc": self.wacc,
            "prior_debt_ratio": self.prior_debt_ratio,
        }
        for signal_fn in ALL_SIGNALS:
            try:
                # Only pass kwargs accepted by the signal function
                sig_params = signature(signal_fn).parameters
                kwargs = {k: v for k, v in extra_kwargs.items() if k in sig_params}
                sig = signal_fn(stock, **kwargs)
                results.append(sig)
            except Exception:
                results.append(AllocationSignal(
                    name=signal_fn.__name__,
                    category=AllocationCategory.SHAREHOLDER_RETURN,
                    value=0, score=0,
                    level=SignalLevel.DESTRUCTIVE,
                    description="Error computing signal",
                    is_available=False,
                ))
        return results

    def _compose_result(
        self,
        stock: "Stock",
        signals: List[AllocationSignal],
    ) -> CapitalAllocationResult:
        """Aggregate signals into final CapitalAllocationResult."""
        # Build weights map
        weights = dict(DEFAULT_CATEGORY_WEIGHTS)
        if self.category_weights:
            for cat_str, w in self.category_weights.items():
                weights[AllocationCategory(cat_str)] = w

        # Calculate category sub-scores
        category_scores: Dict[AllocationCategory, list] = {}
        for sig in signals:
            if not sig.is_available:
                continue
            category_scores.setdefault(sig.category, []).append(sig)

        category_results = {}
        for cat in AllocationCategory:
            cat_signals = category_scores.get(cat, [])
            if not cat_signals:
                category_results[cat] = 0.0
                continue
            total_weight = sum(1 for _ in cat_signals)  # Equal weight within category
            cat_score = sum(s.score for s in cat_signals) / total_weight if total_weight > 0 else 0
            category_results[cat] = cat_score

        # Redistribute weights from unavailable categories
        available_weight = sum(weights[c] for c, s in category_results.items() if s > 0)

        # Composite score
        if available_weight > 0:
            composite = 0
            for cat, score in category_results.items():
                if score > 0:
                    normalized_weight = weights[cat] / available_weight
                    composite += score * normalized_weight
        else:
            composite = 0

        composite = max(0, min(100, composite))

        # Key metrics
        shareholder_yield = stock.shareholder_yield() if hasattr(stock, 'shareholder_yield') else 0
        reinvestment_rate = (abs(stock.capex) / stock.revenue * 100) if stock.revenue > 0 else 0
        net_dilution_rate = stock.dilution_rate if hasattr(stock, 'dilution_rate') else 0

        # Build evidence
        strengths = [s.description for s in signals if s.is_available and s.score >= 65]
        concerns = [s.description for s in signals if s.is_available and s.score <= 30]
        warnings = [s.description for s in signals if not s.is_available]

        # Analysis
        analysis = self._build_analysis(stock, composite, category_results, signals)

        return CapitalAllocationResult(
            ticker=stock.ticker,
            overall_score=composite,
            rating=_score_to_rating(composite),
            shareholder_return_score=category_results.get(AllocationCategory.SHAREHOLDER_RETURN, 0),
            reinvestment_score=category_results.get(AllocationCategory.REINVESTMENT, 0),
            balance_sheet_score=category_results.get(AllocationCategory.BALANCE_SHEET, 0),
            dilution_score=category_results.get(AllocationCategory.DILUTION, 0),
            signals=signals,
            shareholder_yield=shareholder_yield,
            reinvestment_rate=reinvestment_rate,
            net_dilution_rate=net_dilution_rate,
            strengths=strengths,
            concerns=concerns,
            warnings=warnings,
            analysis=analysis,
        )

    def _build_analysis(
        self,
        stock: "Stock",
        score: float,
        category_scores: Dict[AllocationCategory, float],
        signals: List[AllocationSignal],
    ) -> List[str]:
        """Build analysis text."""
        lines = []
        rating = _score_to_rating(score)
        lines.append(f"{stock.ticker}: Capital allocation rating = {rating.value.upper()} ({score:.0f}/100)")

        if score >= 60:
            lines.append("Management demonstrates shareholder-friendly capital allocation")
        elif score >= 40:
            lines.append("Capital allocation is adequate with room for improvement")
        else:
            lines.append("Capital allocation raises concerns — potential value destruction")

        # Highlight key metrics
        sy = stock.shareholder_yield() if hasattr(stock, 'shareholder_yield') else 0
        if sy > 3:
            lines.append(f"Strong total shareholder yield of {sy:.1f}%")
        elif sy < 0:
            lines.append(f"Net dilution to shareholders ({sy:.1f}%)")

        return lines
