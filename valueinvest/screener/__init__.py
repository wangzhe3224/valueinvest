"""
Stock Screening System for ValueInvest.

This module provides a multi-factor stock screening system with:
- Predefined strategies (value, growth, dividend, quality, garp)
- 18+ filtering criteria
- Composite scoring with customizable weights
- Concurrent data processing

Quick Start:
    from valueinvest.screener import screen_stocks, get_strategy
    
    # Screen stocks with a predefined strategy
    result = screen_stocks(
        ["600887", "600900", "601398"],
        strategy="value",
    )
    
    # Access qualified stocks
    for stock in result.qualified:
        print(f"{stock.ticker}: {stock.grade} ({stock.composite_score})")
    
    # Create custom strategy
    strategy = get_strategy("value", min_mos=25.0, min_roe=15.0)

CLI Usage:
    python -m valueinvest.screener.cli --strategy value --tickers 600887,600900
    python -m valueinvest.screener.cli --list-strategies
"""

from .base import (
    ScreeningResult,
    ScreeningStrategy,
    ScoringWeights,
    FilterResult,
    FilterCategory,
    BaseFilter,
)

from .filters import (
    # Valuation filters
    MarginOfSafetyFilter,
    PEFilter,
    PBFilter,
    PEGFilter,
    UndervaluedMethodsFilter,
    # Quality filters
    ROEFilter,
    FCFYieldFilter,
    AltmanZFilter,
    ROICFilter,
    OperatingMarginFilter,
    # Dividend filters
    DividendYieldFilter,
    PayoutRatioFilter,
    DividendGrowthFilter,
    # Sentiment filters
    NewsSentimentFilter,
    InsiderSentimentFilter,
    # Momentum filters
    GrowthFilter,
    RuleOf40Filter,
    CAGRFilter,
    PriceVs52WeekFilter,
    # Registry
    FILTER_REGISTRY,
    get_filter,
    list_filters,
)

from .scorers import (
    CompositeScorer,
    ValuationScorer,
    QualityScorer,
    GrowthScorer,
    DividendScorer,
    get_scorer,
    SCORER_REGISTRY,
)

from .strategies import (
    create_value_strategy,
    create_growth_strategy,
    create_dividend_strategy,
    create_quality_strategy,
    create_garp_strategy,
    get_strategy,
    list_strategies,
    VALUE_STRATEGY,
    GROWTH_STRATEGY,
    DIVIDEND_STRATEGY,
    QUALITY_STRATEGY,
    GARP_STRATEGY,
)

from .pipeline import (
    ScreeningPipeline,
    ScreeningOutput,
    ScreeningSummary,
    screen_stocks,
)


__all__ = [
    # Base classes
    "ScreeningResult",
    "ScreeningStrategy",
    "ScoringWeights",
    "FilterResult",
    "FilterCategory",
    "BaseFilter",
    # Filters
    "MarginOfSafetyFilter",
    "PEFilter",
    "PBFilter",
    "PEGFilter",
    "UndervaluedMethodsFilter",
    "ROEFilter",
    "FCFYieldFilter",
    "AltmanZFilter",
    "ROICFilter",
    "OperatingMarginFilter",
    "DividendYieldFilter",
    "PayoutRatioFilter",
    "DividendGrowthFilter",
    "NewsSentimentFilter",
    "InsiderSentimentFilter",
    "GrowthFilter",
    "RuleOf40Filter",
    "CAGRFilter",
    "PriceVs52WeekFilter",
    "FILTER_REGISTRY",
    "get_filter",
    "list_filters",
    # Scorers
    "CompositeScorer",
    "ValuationScorer",
    "QualityScorer",
    "GrowthScorer",
    "DividendScorer",
    "get_scorer",
    "SCORER_REGISTRY",
    # Strategies
    "create_value_strategy",
    "create_growth_strategy",
    "create_dividend_strategy",
    "create_quality_strategy",
    "create_garp_strategy",
    "get_strategy",
    "list_strategies",
    "VALUE_STRATEGY",
    "GROWTH_STRATEGY",
    "DIVIDEND_STRATEGY",
    "QUALITY_STRATEGY",
    "GARP_STRATEGY",
    # Pipeline
    "ScreeningPipeline",
    "ScreeningOutput",
    "ScreeningSummary",
    "screen_stocks",
]
