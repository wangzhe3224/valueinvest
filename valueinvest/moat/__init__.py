"""Economic Moat Analysis Module.

Systematically assesses competitive advantages through 11 financial
signals across 5 categories: profitability, efficiency, growth,
market position, and financial fortress.
"""

from .base import MoatResult, MoatSignal, MoatType, MoatSignalCategory, SignalStrength
from .engine import MoatAnalysisEngine


def analyze_moat(stock, **kwargs):
    """Convenience function for moat analysis.

    Args:
        stock: Stock instance with financial data
        **kwargs: Passed to MoatAnalysisEngine
            - roic: Pre-computed ROIC value
            - wacc: Pre-computed WACC value
            - revenue_cagr_5y: Revenue CAGR override
            - earnings_cagr_5y: Earnings CAGR override
            - prior_gross_margin: Prior year gross margin override
            - category_weights: Dict of category weight overrides

    Returns:
        MoatResult with composite moat score and type
    """
    engine = MoatAnalysisEngine(**kwargs)
    return engine.analyze(stock)


__all__ = [
    "MoatResult",
    "MoatSignal",
    "MoatType",
    "MoatSignalCategory",
    "SignalStrength",
    "MoatAnalysisEngine",
    "analyze_moat",
]
