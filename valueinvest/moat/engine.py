"""Moat Analysis Engine - composes signals into moat assessment."""

import inspect
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from valueinvest.stock import Stock

from .base import (
    MoatResult, MoatSignal, MoatSignalCategory, SignalStrength,
    MoatType, _score_to_moat_type,
)
from .signals import ALL_SIGNALS

# Default category weights
DEFAULT_CATEGORY_WEIGHTS: Dict[MoatSignalCategory, float] = {
    MoatSignalCategory.PROFITABILITY: 0.30,
    MoatSignalCategory.EFFICIENCY: 0.20,
    MoatSignalCategory.GROWTH: 0.20,
    MoatSignalCategory.MARKET_POSITION: 0.15,
    MoatSignalCategory.FINANCIAL_FORTRESS: 0.15,
}


class MoatAnalysisEngine:
    """Analyzes economic moat strength from financial signals.

    Composes 11 individual signals across 5 categories into
    a composite moat score (0-100) and moat type classification.
    """

    def __init__(
        self,
        invested_capital: Optional[float] = None,
        roic: Optional[float] = None,
        wacc: Optional[float] = None,
        revenue_cagr_5y: Optional[float] = None,
        earnings_cagr_5y: Optional[float] = None,
        prior_gross_margin: Optional[float] = None,
        category_weights: Optional[Dict[str, float]] = None,
    ):
        self.roic = roic
        self.wacc = wacc
        self.invested_capital = invested_capital
        self.revenue_cagr_5y = revenue_cagr_5y
        self.earnings_cagr_5y = earnings_cagr_5y
        self.prior_gross_margin = prior_gross_margin
        self.category_weights = category_weights  # Dict[str, float] for JSON compatibility

    def analyze(self, stock: "Stock") -> MoatResult:
        """Run all moat signals and produce composite result."""
        signals = self._compute_signals(stock)
        return self._compose_result(stock.ticker, signals)

    def _compute_signals(self, stock: "Stock") -> List[MoatSignal]:
        """Compute all available signals."""
        # Pre-build optional kwargs that some signals accept
        optional_kwargs = {
            "roic": self.roic,
            "wacc": self.wacc,
            "revenue_cagr_5y": self.revenue_cagr_5y,
            "earnings_cagr_5y": self.earnings_cagr_5y,
            "prior_gross_margin": self.prior_gross_margin,
        }

        results = []
        for signal_fn in ALL_SIGNALS:
            try:
                # Only pass kwargs that the signal function actually accepts
                sig_params = inspect.signature(signal_fn).parameters
                kwargs = {
                    k: v for k, v in optional_kwargs.items()
                    if k in sig_params
                }
                sig = signal_fn(stock, **kwargs)
                results.append(sig)
            except Exception:
                # Gracefully handle any unexpected errors
                results.append(MoatSignal(
                    name=signal_fn.__name__,
                    category=MoatSignalCategory.PROFITABILITY,
                    value=0, score=0,
                    strength=SignalStrength.NONE,
                    description="Error computing signal",
                    is_available=False,
                ))
        return results

    def _compose_result(self, ticker: str, signals: List[MoatSignal]) -> MoatResult:
        """Aggregate signals into final MoatResult."""
        # Build weights map
        weights = dict(DEFAULT_CATEGORY_WEIGHTS)
        if self.category_weights:
            for cat_str, w in self.category_weights.items():
                weights[MoatSignalCategory(cat_str)] = w

        # Calculate category sub-scores
        category_scores: Dict[MoatSignalCategory, list] = {}
        for sig in signals:
            if not sig.is_available:
                continue
            category_scores.setdefault(sig.category, []).append(sig)

        category_results = {}
        for cat in MoatSignalCategory:
            cat_signals = category_scores.get(cat, [])
            if not cat_signals:
                category_results[cat] = 0.0
                continue
            # Weighted average within category
            total_weight = sum(s.weight for s in cat_signals)
            if total_weight > 0:
                cat_score = sum(s.score * s.weight for s in cat_signals) / total_weight
            else:
                cat_score = sum(s.score for s in cat_signals) / len(cat_signals)
            category_results[cat] = cat_score

        # Redistribute weights from unavailable categories
        available_weight = 0
        for cat, score in category_results.items():
            if score > 0:
                available_weight += weights[cat]

        # Composite score
        if available_weight > 0:
            composite = 0
            for cat, score in category_results.items():
                if score > 0:
                    # Normalize weight to available categories
                    normalized_weight = weights[cat] / available_weight
                    composite += score * normalized_weight
        else:
            # No signals available at all
            composite = 0

        composite = max(0, min(100, composite))

        # Build evidence lists
        strengths = [s.description for s in signals if s.is_available and s.score >= 65]
        weaknesses = [s.description for s in signals if s.is_available and s.score <= 30]
        warnings = [s.description for s in signals if not s.is_available]

        # Analysis
        analysis = self._build_analysis(ticker, composite, category_results, signals)

        return MoatResult(
            ticker=ticker,
            moat_type=_score_to_moat_type(composite),
            moat_score=composite,
            profitability_score=category_results.get(MoatSignalCategory.PROFITABILITY, 0),
            efficiency_score=category_results.get(MoatSignalCategory.EFFICIENCY, 0),
            growth_score=category_results.get(MoatSignalCategory.GROWTH, 0),
            market_position_score=category_results.get(MoatSignalCategory.MARKET_POSITION, 0),
            financial_fortress_score=category_results.get(MoatSignalCategory.FINANCIAL_FORTRESS, 0),
            signals=signals,
            strengths=strengths,
            weaknesses=weaknesses,
            warnings=warnings,
            analysis=analysis,
        )

    def _build_analysis(
        self,
        ticker: str,
        score: float,
        category_scores: Dict[MoatSignalCategory, float],
        signals: List[MoatSignal],
    ) -> List[str]:
        """Build analysis text."""
        lines = []
        moat_type = _score_to_moat_type(score)
        lines.append(f"{ticker}: Moat assessment = {moat_type.value.upper()} ({score:.0f}/100)")

        if score >= 55:
            lines.append("Strong financial indicators suggest durable competitive advantages")
        elif score >= 35:
            lines.append("Some moat indicators present but not conclusive")
        else:
            lines.append("Weak moat indicators — competitive advantages not evident")

        # Highlight strongest/weakest categories
        available_cats = {c: s for c, s in category_scores.items() if s > 0}
        if available_cats:
            best_cat = max(available_cats, key=available_cats.get)
            worst_cat = min(available_cats, key=available_cats.get)
            if best_cat != worst_cat:
                lines.append(f"Strongest: {best_cat.value} ({available_cats[best_cat]:.0f}/100)")
                lines.append(f"Weakest: {worst_cat.value} ({available_cats[worst_cat]:.0f}/100)")

        return lines
