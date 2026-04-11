"""Implied Growth Rate Analysis Module.

Derives the growth rate implied by the current stock price using
multiple methods (Reverse DCF, PEG, Gordon Growth, Earnings Yield),
compares with historical growth rates, and assesses reasonableness.
"""

from .base import (
    GrowthComparison,
    GrowthReasonableness,
    ImpliedGrowthDetail,
    ImpliedGrowthResult,
)
from .engine import ImpliedGrowthEngine


def analyze_implied_growth(stock, **kwargs):
    """Convenience function for implied growth rate analysis.

    Args:
        stock: Stock instance with financial data
        **kwargs: Passed to ImpliedGrowthEngine constructor
            - peg_fair_ratio: Assumed fair PEG ratio (default 1.0)

    Returns:
        ImpliedGrowthResult with implied growth rates, comparison, and reasonableness
    """
    engine = ImpliedGrowthEngine(**kwargs)
    return engine.analyze(stock)


__all__ = [
    "ImpliedGrowthEngine",
    "ImpliedGrowthResult",
    "ImpliedGrowthDetail",
    "GrowthComparison",
    "GrowthReasonableness",
    "analyze_implied_growth",
]
