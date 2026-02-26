"""
Free Cash Flow (FCF) analysis module.

Provides multi-year FCF analysis including:
- FCF Yield, FCF Margin, FCF per Share
- SBC-adjusted True FCF
- FCF quality and trend analysis
- Historical FCF data

Usage:
    from valueinvest.cashflow import CashFlowRegistry
    
    fetcher = CashFlowRegistry.get_fetcher("AAPL")
    result = fetcher.fetch_cashflow("AAPL", years=5)
    
    if result.success:
        print(f"FCF Yield: {result.summary.fcf_yield:.2f}%")
        print(f"True FCF: ${result.summary.latest_true_fcf/1e9:.2f}B")
"""

from .base import (
    CashFlowRecord,
    CashFlowSummary,
    CashFlowFetchResult,
    FCFQuality,
    FCFTrend,
)
from .registry import CashFlowRegistry

__all__ = [
    "CashFlowRecord",
    "CashFlowSummary",
    "CashFlowFetchResult",
    "FCFQuality",
    "FCFTrend",
    "CashFlowRegistry",
]
