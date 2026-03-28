"""Capital Allocation Quality Module.

Evaluates management capital deployment efficiency across
dividends, buybacks, reinvestment, and balance sheet management.
"""

from .base import (
    CapitalAllocationResult, AllocationSignal,
    AllocationRating, AllocationCategory, SignalLevel,
)
from .engine import CapitalAllocationEngine


def analyze_capital_allocation(stock, **kwargs):
    """Convenience function for capital allocation analysis.

    Args:
        stock: Stock instance with financial data
        **kwargs: Passed to CapitalAllocationEngine
            - roic: Pre-computed ROIC value
            - wacc: Pre-computed WACC value
            - prior_debt_ratio: Prior year debt ratio override
            - category_weights: Dict of category weight overrides

    Returns:
        CapitalAllocationResult with composite score and rating
    """
    engine = CapitalAllocationEngine(**kwargs)
    return engine.analyze(stock)


__all__ = [
    "CapitalAllocationResult",
    "AllocationSignal",
    "AllocationRating",
    "AllocationCategory",
    "SignalLevel",
    "CapitalAllocationEngine",
    "analyze_capital_allocation",
]
