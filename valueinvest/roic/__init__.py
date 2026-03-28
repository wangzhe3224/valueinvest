"""ROIC vs WACC Analysis Module.

Analyzes whether a company creates or destroys economic value
by comparing Return on Invested Capital (ROIC) against the
Weighted Average Cost of Capital (WACC).
"""

from .base import ROICResult, WACCResult, EconomicProfitResult
from .engine import EconomicProfitEngine


def analyze_economic_profit(stock, **kwargs):
    """Convenience function for ROIC vs WACC analysis.

    Args:
        stock: Stock instance with financial data
        **kwargs: Passed to EconomicProfitEngine constructor
            - beta: Optional beta for CAPM cost of equity
            - risk_free_rate: Optional risk-free rate override
            - equity_risk_premium: Market risk premium (default 6.0)
            - cost_of_equity_override: Override cost of equity directly
            - cost_of_debt_override: Override cost of debt directly
            - wacc_override: Override entire WACC directly

    Returns:
        EconomicProfitResult with ROIC, WACC, spread, and economic profit
    """
    engine = EconomicProfitEngine(**kwargs)
    return engine.analyze(stock)


__all__ = [
    "ROICResult",
    "WACCResult",
    "EconomicProfitResult",
    "EconomicProfitEngine",
    "analyze_economic_profit",
]
