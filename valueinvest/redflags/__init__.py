"""Accounting Red Flags Detection Module.

Detects accounting manipulation risks through 11 financial
signals across 4 categories: earnings quality, revenue recognition,
asset & working capital, and capital structure.
"""

from .base import (
    RedFlagResult, RedFlagSignal, RiskLevel,
    RedFlagCategory, RedFlagSeverity,
)
from .engine import AccountingRedFlagsEngine


def analyze_red_flags(stock, **kwargs):
    """Convenience function for accounting red flags analysis.

    Args:
        stock: Stock instance with financial data
        **kwargs: Passed to AccountingRedFlagsEngine
            - category_weights: Dict of category weight overrides

    Returns:
        RedFlagResult with composite score and risk level
    """
    engine = AccountingRedFlagsEngine(**kwargs)
    return engine.analyze(stock)


__all__ = [
    "RedFlagResult",
    "RedFlagSignal",
    "RiskLevel",
    "RedFlagCategory",
    "RedFlagSeverity",
    "AccountingRedFlagsEngine",
    "analyze_red_flags",
]
