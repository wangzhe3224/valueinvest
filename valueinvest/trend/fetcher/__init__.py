"""Quarterly trend data fetchers."""
from .base import BaseTrendFetcher
from .stockanalysis_trend import StockAnalysisTrendFetcher
from .fmp_trend import FMPTrendFetcher
from .yfinance_trend import YFinanceTrendFetcher
from .tushare_trend import TushareTrendFetcher

__all__ = [
    "BaseTrendFetcher",
    "StockAnalysisTrendFetcher",
    "FMPTrendFetcher",
    "YFinanceTrendFetcher",
    "TushareTrendFetcher",
]
