"""
Predefined screening strategies.

This module provides ready-to-use strategies:
- VALUE: Deep value investing (Benjamin Graham style)
- GROWTH: High growth at reasonable price
- DIVIDEND: Dividend income and safety
- QUALITY: High-quality compounders
- GARP: Growth at reasonable price
"""
from typing import List, Dict, Any
from .base import ScreeningStrategy, ScoringWeights
from .filters import (
    MarginOfSafetyFilter,
    ROEFilter,
    AltmanZFilter,
    PEFilter,
    PBFilter,
    PEGFilter,
    GrowthFilter,
    RuleOf40Filter,
    DividendYieldFilter,
    PayoutRatioFilter,
    DividendGrowthFilter,
    FCFYieldFilter,
    ROICFilter,
    NewsSentimentFilter,
    InsiderSentimentFilter,
)


# ============================================================================
# Value Strategy - Deep value investing
# ============================================================================


def create_value_strategy(
    min_mos: float = 20.0,
    min_roe: float = 10.0,
    min_z: float = 2.99,
    max_pe: float = 15.0,
    max_pb: float = 1.5,
) -> ScreeningStrategy:
    """
    Create a deep value screening strategy (Benjamin Graham style).

    Focus: Safety margin, low valuations, quality fundamentals.
    Best for: Patient investors seeking undervalued stocks.

    Filters:
    - Margin of Safety >= 20%
    - ROE >= 10%
    - Altman Z >= 2.99 (safe zone)
    - P/E <= 15
    - P/B <= 1.5 (optional)
    """
    return ScreeningStrategy(
        name="value",
        description="深度价值 - 安全边际优先，Graham风格",
        filters=[
            MarginOfSafetyFilter(min_mos=min_mos),
            ROEFilter(min_roe=min_roe),
            AltmanZFilter(min_z=min_z),
            PEFilter(max_pe=max_pe),
        ],
        weights=ScoringWeights(
            valuation=0.50,
            quality=0.30,
            sentiment=0.15,
            momentum=0.05,
        ),
    )


# ============================================================================
# Growth Strategy - High growth companies
# ============================================================================


def create_growth_strategy(
    min_growth: float = 15.0,
    max_peg: float = 1.5,
    min_rule40: float = 30.0,
    min_roe: float = 12.0,
) -> ScreeningStrategy:
    """
    Create a growth screening strategy.

    Focus: High earnings growth at reasonable valuations.
    Best for: Investors seeking capital appreciation.

    Filters:
    - Earnings Growth >= 15%
    - PEG <= 1.5
    - Rule of 40 >= 30
    - ROE >= 12%
    """
    return ScreeningStrategy(
        name="growth",
        description="成长股 - 高增长，合理估值",
        filters=[
            GrowthFilter(min_growth=min_growth),
            PEGFilter(max_peg=max_peg),
            RuleOf40Filter(min_score=min_rule40),
            ROEFilter(min_roe=min_roe),
        ],
        weights=ScoringWeights(
            valuation=0.25,
            quality=0.25,
            sentiment=0.15,
            momentum=0.35,
        ),
    )


# ============================================================================
# Dividend Strategy - Dividend income
# ============================================================================


def create_dividend_strategy(
    min_yield: float = 3.0,
    max_payout: float = 70.0,
    min_div_growth: float = 5.0,
    min_mos: float = 10.0,
) -> ScreeningStrategy:
    """
    Create a dividend screening strategy.

    Focus: Sustainable dividend yield with growth potential.
    Best for: Income-focused investors.

    Filters:
    - Dividend Yield >= 3%
    - Payout Ratio <= 70%
    - Dividend Growth >= 5%
    - Margin of Safety >= 10%
    """
    return ScreeningStrategy(
        name="dividend",
        description="红利股 - 稳定分红，可持续增长",
        filters=[
            DividendYieldFilter(min_yield=min_yield),
            PayoutRatioFilter(max_ratio=max_payout),
            DividendGrowthFilter(min_growth=min_div_growth),
            MarginOfSafetyFilter(min_mos=min_mos),
        ],
        weights=ScoringWeights(
            valuation=0.30,
            quality=0.45,
            sentiment=0.20,
            momentum=0.05,
        ),
    )


# ============================================================================
# Quality Strategy - High-quality compounders
# ============================================================================


def create_quality_strategy(
    min_roe: float = 15.0,
    min_fcf_yield: float = 3.0,
    min_z: float = 3.0,
    min_roic: float = 12.0,
) -> ScreeningStrategy:
    """
    Create a quality screening strategy.

    Focus: High-return businesses with strong fundamentals.
    Best for: Long-term compounder investors.

    Filters:
    - ROE >= 15%
    - FCF Yield >= 3%
    - Altman Z >= 3.0
    - ROIC >= 12%
    """
    return ScreeningStrategy(
        name="quality",
        description="高质量 - 优质企业，长期复利",
        filters=[
            ROEFilter(min_roe=min_roe),
            FCFYieldFilter(min_yield=min_fcf_yield),
            AltmanZFilter(min_z=min_z),
            ROICFilter(min_roic=min_roic),
        ],
        weights=ScoringWeights(
            valuation=0.25,
            quality=0.50,
            sentiment=0.15,
            momentum=0.10,
        ),
    )


# ============================================================================
# GARP Strategy - Growth at Reasonable Price
# ============================================================================


def create_garp_strategy(
    min_growth: float = 10.0,
    max_peg: float = 1.2,
    min_roe: float = 12.0,
    min_mos: float = 10.0,
) -> ScreeningStrategy:
    """
    Create a GARP (Growth at Reasonable Price) strategy.

    Focus: Balance between growth and valuation.
    Best for: Investors wanting growth without overpaying.

    Filters:
    - Earnings Growth >= 10%
    - PEG <= 1.2
    - ROE >= 12%
    - Margin of Safety >= 10%
    """
    return ScreeningStrategy(
        name="garp",
        description="GARP - 合理价格下的成长",
        filters=[
            GrowthFilter(min_growth=min_growth),
            PEGFilter(max_peg=max_peg),
            ROEFilter(min_roe=min_roe),
            MarginOfSafetyFilter(min_mos=min_mos),
        ],
        weights=ScoringWeights(
            valuation=0.35,
            quality=0.30,
            sentiment=0.15,
            momentum=0.20,
        ),
    )


# ============================================================================
# Strategy Registry
# ============================================================================

STRATEGY_BUILDERS = {
    "value": create_value_strategy,
    "growth": create_growth_strategy,
    "dividend": create_dividend_strategy,
    "quality": create_quality_strategy,
    "garp": create_garp_strategy,
}


def get_strategy(name: str, **kwargs) -> ScreeningStrategy:
    """
    Get a predefined strategy by name.

    Args:
        name: Strategy name (value, growth, dividend, quality, garp)
        **kwargs: Custom parameters for the strategy

    Returns:
        ScreeningStrategy instance
    """
    if name not in STRATEGY_BUILDERS:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGY_BUILDERS.keys())}")

    return STRATEGY_BUILDERS[name](**kwargs)


def list_strategies() -> List[Dict[str, Any]]:
    """List all available strategies with descriptions."""
    return [
        {
            "name": "value",
            "description": "深度价值 - 安全边际优先，Graham风格",
            "default_filters": ["MOS>=20%", "ROE>=10%", "Z>=2.99", "PE<=15"],
            "weights": {"valuation": 50, "quality": 30, "sentiment": 15, "momentum": 5},
        },
        {
            "name": "growth",
            "description": "成长股 - 高增长，合理估值",
            "default_filters": ["Growth>=15%", "PEG<=1.5", "Rule40>=30", "ROE>=12%"],
            "weights": {"valuation": 25, "quality": 25, "sentiment": 15, "momentum": 35},
        },
        {
            "name": "dividend",
            "description": "红利股 - 稳定分红，可持续增长",
            "default_filters": ["Yield>=3%", "Payout<=70%", "DivGrowth>=5%", "MOS>=10%"],
            "weights": {"valuation": 30, "quality": 45, "sentiment": 20, "momentum": 5},
        },
        {
            "name": "quality",
            "description": "高质量 - 优质企业，长期复利",
            "default_filters": ["ROE>=15%", "FCF>=3%", "Z>=3.0", "ROIC>=12%"],
            "weights": {"valuation": 25, "quality": 50, "sentiment": 15, "momentum": 10},
        },
        {
            "name": "garp",
            "description": "GARP - 合理价格下的成长",
            "default_filters": ["Growth>=10%", "PEG<=1.2", "ROE>=12%", "MOS>=10%"],
            "weights": {"valuation": 35, "quality": 30, "sentiment": 15, "momentum": 20},
        },
    ]


# Pre-built default instances for convenience
VALUE_STRATEGY = create_value_strategy()
GROWTH_STRATEGY = create_growth_strategy()
DIVIDEND_STRATEGY = create_dividend_strategy()
QUALITY_STRATEGY = create_quality_strategy()
GARP_STRATEGY = create_garp_strategy()
