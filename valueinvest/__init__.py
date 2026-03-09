"""ValueInvest - Comprehensive Stock Analysis Library

A modular Python library for stock valuation using multiple methodologies
with real-time data fetching and news sentiment analysis.

Quick Start:
    >>> from valueinvest import Stock, ValuationEngine
    >>> stock = Stock.from_api('AAPL')
    >>> engine = ValuationEngine()
    >>> results = engine.run_all(stock)
    >>> for r in results:
    ...     print(f"{r.method}: ${r.fair_value:.2f}")

Core Features:
    - 20+ valuation methods (Graham, DCF, DDM, PEG, etc.)
    - Auto-detect market (A-share vs US)
    - News & sentiment analysis
    - Insider trading tracking
    - Buyback analysis
    - Cyclical stock analysis

For AI Agents:
    See AGENTS.md for command-first task templates and quick reference.
"""

# Core classes
from .buyback.registry import BuybackRegistry
from .cashflow.registry import CashFlowRegistry
from .cyclical.base import CyclicalAnalysisResult, CyclicalStock

# Cyclical analysis
from .cyclical.engine import CyclicalAnalysisEngine
from .insider.registry import InsiderRegistry

# Registries (most commonly used)
from .news.registry import NewsRegistry
from .stock import Stock, StockHistory
from .valuation.base import ValuationResult
from .valuation.engine import ValuationEngine
from .valuation.mscore import calculate_m_score

# Convenience functions
from .valuation.quality import calculate_f_score

__version__ = "1.0.0"

__all__ = [
    # Core
    "Stock",
    "StockHistory",
    "ValuationEngine",
    "ValuationResult",
    # Registries
    "NewsRegistry",
    "InsiderRegistry",
    "BuybackRegistry",
    "CashFlowRegistry",
    # Cyclical
    "CyclicalAnalysisEngine",
    "CyclicalStock",
    "CyclicalAnalysisResult",
    # Convenience
    "calculate_f_score",
    "calculate_m_score",
]
