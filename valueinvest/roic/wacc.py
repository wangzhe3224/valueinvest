"""WACC (Weighted Average Cost of Capital) calculation."""

from typing import Optional

from valueinvest.stock import Stock

from .base import WACCResult


def calculate_wacc(
    stock: Stock,
    beta: Optional[float] = None,
    risk_free_rate: Optional[float] = None,
    equity_risk_premium: float = 6.0,
    cost_of_equity_override: Optional[float] = None,
    cost_of_debt_override: Optional[float] = None,
) -> WACCResult:
    """Calculate Weighted Average Cost of Capital.

    Formula:
        WACC = (E/V) * Re + (D/V) * Rd * (1 - T)
        where E = market_cap, V = enterprise_value, D = net_debt

    Cost of Equity:
        - Simplified: stock.cost_of_capital (default 10.0%)
        - CAPM: risk_free_rate + beta * equity_risk_premium

    Cost of Debt:
        - From interest_expense / total_debt if data available
        - From aaa_corporate_yield as fallback

    Args:
        stock: Stock instance with financial data
        beta: Optional beta for CAPM cost of equity
        risk_free_rate: Optional risk-free rate override.
            Defaults to china_10y_yield for CNY stocks, 4.3% for USD.
        equity_risk_premium: Market equity risk premium (default 6.0%)
        cost_of_equity_override: Override cost of equity directly
        cost_of_debt_override: Override cost of debt directly

    Returns:
        WACCResult with cost of equity, cost of debt, weights, and WACC
    """
    tax_rate = stock.tax_rate if stock.tax_rate > 0 else 25.0
    market_cap = stock.market_cap
    ev = stock.enterprise_value
    net_debt = stock.net_debt

    # Determine risk-free rate
    if risk_free_rate is not None:
        rf = risk_free_rate
        rf_source = "override"
    elif stock.currency == "USD":
        rf = 4.3
        rf_source = "US default (4.3%)"
    else:
        rf = stock.china_10y_yield
        rf_source = "china_10y_yield"

    # Calculate Cost of Equity
    if cost_of_equity_override is not None:
        cost_of_equity = cost_of_equity_override
        method = "Simplified (override)"
    elif beta is not None:
        cost_of_equity = rf + beta * equity_risk_premium
        method = "CAPM"
    else:
        cost_of_equity = stock.cost_of_capital
        method = "Simplified"

    # Calculate Cost of Debt
    if cost_of_debt_override is not None:
        cost_of_debt = cost_of_debt_override
    elif stock.interest_expense > 0:
        total_debt = stock.short_term_debt + stock.long_term_debt
        if total_debt > 0:
            cost_of_debt = stock.interest_expense / total_debt * 100
        else:
            cost_of_debt = stock.aaa_corporate_yield
    else:
        cost_of_debt = stock.aaa_corporate_yield

    # Calculate weights
    if ev > 0:
        equity_weight = market_cap / ev
        debt_weight = net_debt / ev
    elif market_cap > 0:
        equity_weight = 1.0
        debt_weight = 0.0
    else:
        equity_weight = 1.0
        debt_weight = 0.0

    # WACC = (E/V) * Re + (D/V) * Rd * (1 - T)
    after_tax_cost_of_debt = cost_of_debt * (1 - tax_rate / 100)
    wacc = equity_weight * cost_of_equity + debt_weight * after_tax_cost_of_debt

    # Determine confidence
    if method == "CAPM" and stock.interest_expense > 0:
        confidence = "High"
    elif method == "Simplified":
        confidence = "Medium"
    else:
        confidence = "Medium"

    return WACCResult(
        cost_of_equity=cost_of_equity,
        cost_of_debt=cost_of_debt,
        equity_weight=equity_weight,
        debt_weight=debt_weight,
        wacc=wacc,
        beta_used=beta,
        risk_free_rate=rf,
        equity_risk_premium=equity_risk_premium,
        tax_rate_used=tax_rate,
        method=method,
        confidence=confidence,
    )
