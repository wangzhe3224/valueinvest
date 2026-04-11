"""Peer Comparison Analysis Module.

Compares a stock's financial metrics against industry peers
to assess relative valuation, profitability, growth, and scale.
"""

from .base import (
    ComparisonRating,
    MetricComparison,
    MetricDirection,
    PeerComparisonResult,
)
from .engine import PeerComparisonEngine


def analyze_peers(stock, **kwargs):
    """Convenience function for peer comparison analysis.

    Args:
        stock: Stock instance with financial data
        **kwargs: Passed to PeerComparisonEngine
            - peers: Optional list of PeerCompany objects (for US stocks)
            - metric_weights: Dict of metric_key -> weight overrides
            - min_peers: Minimum peers required (default 3)

    Returns:
        PeerComparisonResult with metric comparisons and composite score
    """
    engine = PeerComparisonEngine(**kwargs)
    return engine.analyze(stock)


__all__ = [
    "PeerComparisonResult",
    "MetricComparison",
    "MetricDirection",
    "ComparisonRating",
    "PeerComparisonEngine",
    "analyze_peers",
]
