"""
ValueInvest - Comprehensive Stock Valuation Library

A modular library implementing multiple valuation methodologies:
- Graham Valuation (Defensive, Growth, NCAV)
- Discounted Cash Flow (DCF)
- Earnings Power Value (EPV)
- Dividend Discount Model (DDM)
- Growth Valuation (PEG, Reverse DCF, GARP)
- Bank Valuation (P/B, Residual Income)
"""

from .stock import Stock
from .valuation.engine import ValuationEngine
from .valuation.base import ValuationResult

__version__ = "1.0.0"
__all__ = ["Stock", "ValuationEngine", "ValuationResult"]
