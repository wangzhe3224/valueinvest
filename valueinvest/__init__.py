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
    - Economic moat scoring
    - ROIC vs WACC analysis
    - Capital allocation quality

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
from .valuation.engine import ValuationEngine, StockAnalysis, BatchAnalysisResult
from .valuation.mscore import calculate_m_score

# Convenience functions
from .valuation.quality import calculate_f_score

# Economic analysis
from .moat.engine import MoatAnalysisEngine
from .moat.base import MoatResult
from .roic.engine import EconomicProfitEngine
from .roic.base import EconomicProfitResult
from .capital.engine import CapitalAllocationEngine
from .capital.base import CapitalAllocationResult

# Peer comparison
from .peer_comparison.engine import PeerComparisonEngine
from .peer_comparison.base import PeerComparisonResult

# Implied growth analysis
from .implied_growth.engine import ImpliedGrowthEngine
from .implied_growth.base import ImpliedGrowthResult

__version__ = "1.2.1"

__all__ = [
    # Core
    "Stock",
    "StockHistory",
    "ValuationEngine",
    "ValuationResult",
    "StockAnalysis",
    "BatchAnalysisResult",
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
    # Economic analysis
    "MoatAnalysisEngine",
    "MoatResult",
    "EconomicProfitEngine",
    "EconomicProfitResult",
    "CapitalAllocationEngine",
    "CapitalAllocationResult",
    # Peer comparison
    "PeerComparisonEngine",
    "PeerComparisonResult",
    # Implied growth analysis
    "ImpliedGrowthEngine",
    "ImpliedGrowthResult",
]
