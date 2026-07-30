"""
Financial trend & growth-signal analysis.

Provides quarterly time-series for revenue / gross margin / net margin /
fcf yield / CCC, plus a growth-signal engine that scores acceleration,
inflection, streaks and stability.

Quick start:
    from valueinvest import fetch_quarterly_trends, analyze_trend_signals
    fr = fetch_quarterly_trends("MSFT", years=5)
    result = analyze_trend_signals(fr.series)
    print(result)
"""
from .base import (
    METRIC_CATEGORY,
    TrendDirection,
    TrendFetchResult,
    TrendMetric,
    TrendRating,
    TrendRecord,
    TrendSeries,
    TrendSignal,
    TrendSignalCategory,
    TrendSignalResult,
    metric_value,
    score_to_direction,
    score_to_trend_rating,
)
from .engine import DEFAULT_METRIC_WEIGHTS, TrendSignalEngine, analyze_trend_signals
from .registry import TrendRegistry


def fetch_quarterly_trends(ticker: str, years: int = 5) -> TrendFetchResult:
    """Fetch quarterly trend data for a ticker via the market-appropriate fetcher."""
    fetcher = TrendRegistry.get_fetcher(ticker)
    return fetcher.fetch_trends(ticker, years=years)


__all__ = [
    # data layer
    "TrendRecord",
    "TrendSeries",
    "TrendFetchResult",
    "TrendMetric",
    "METRIC_CATEGORY",
    "metric_value",
    # signal layer
    "TrendSignal",
    "TrendSignalCategory",
    "TrendDirection",
    "TrendSignalResult",
    "TrendRating",
    "TrendSignalEngine",
    "DEFAULT_METRIC_WEIGHTS",
    "analyze_trend_signals",
    "score_to_trend_rating",
    "score_to_direction",
    # registry + convenience
    "TrendRegistry",
    "fetch_quarterly_trends",
]
