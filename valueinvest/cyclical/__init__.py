"""
Cyclical Stock Analysis Module

This module provides comprehensive analysis for cyclical stocks with
different strategies for A-share and US markets.

Key Features:
- Cycle position scoring system
- Cyclical-adjusted valuation methods (PB, PE, FCF)
- Industry-specific indicators (shipping, steel, metals, chemicals)
- Differentiated strategies for A-share (trading) and US (dividend) markets

Usage:
    from valueinvest.cyclical import (
        CyclicalStock,
        CyclePositionScorer,
        CycleType,
        CyclePhase,
        MarketType,
    )
    
    stock = CyclicalStock(
        ticker="601919",
        name="中远海控",
        market=MarketType.A_SHARE,
        current_price=15.79,
        cycle_type=CycleType.SHIPPING,
        pb=1.09,
        bvps=14.5,
    )
"""

from .enums import (
    CycleType,
    CyclePhase,
    CycleStrength,
    MarketType,
    InvestmentAction,
    InvestmentStrategy,
    IndicatorCategory,
)

from .base import (
    CycleIndicator,
    CycleScore,
    CyclicalStock,
    ValuationResult,
    StrategyRecommendation,
    Checklist,
    CyclicalAnalysisResult,
)

# Import position scorer
from .position_scorer import CyclePositionScorer

# Import valuation methods
from .valuation import (
    CyclicalPBValuation,
    CyclicalPEValuation,
    CyclicalFCFValuation,
    CyclicalDividendValuation,
)

# Import strategies

# Import strategies
from .strategy import (
    AShareCyclicalStrategy,
    USCyclicalStrategy,
)

# Import engine
from .engine import CyclicalAnalysisEngine
__all__ = [
    # Enums
    "CycleType",
    "CyclePhase",
    "CycleStrength",
    "MarketType",
    "InvestmentAction",
    "InvestmentStrategy",
    "IndicatorCategory",
    # Base classes
    "CycleIndicator",
    "CycleScore",
    "CyclicalStock",
    "ValuationResult",
    "StrategyRecommendation",
    "Checklist",
    "CyclicalAnalysisResult",
    # Position scorer
    "CyclePositionScorer",
    # Valuation methods
    "CyclicalPBValuation",
    "CyclicalPEValuation",
    "CyclicalFCFValuation",
    "CyclicalDividendValuation",
    # Strategies
    "AShareCyclicalStrategy",
    "USCyclicalStrategy",
    # Engine
    "CyclicalAnalysisEngine",
]
