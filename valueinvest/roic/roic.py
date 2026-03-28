"""ROIC (Return on Invested Capital) calculation."""

from typing import Optional

from valueinvest.stock import Stock

from .base import ROICResult


def calculate_roic(
    stock: Stock,
    invested_capital_override: Optional[float] = None,
) -> ROICResult:
    """Calculate Return on Invested Capital.

    Formula:
        NOPAT = EBIT * (1 - tax_rate / 100)
        IC = net_working_capital + net_fixed_assets
        ROIC = NOPAT / IC * 100

    Args:
        stock: Stock instance with financial data
        invested_capital_override: Override invested capital value

    Returns:
        ROICResult with NOPAT, invested capital, ROIC, and components
    """
    tax_rate = stock.tax_rate if stock.tax_rate > 0 else 25.0

    # Calculate NOPAT
    if stock.ebit > 0:
        nopat = stock.ebit * (1 - tax_rate / 100)
        nopat_source = "EBIT"
    elif stock.net_income > 0:
        nopat = stock.net_income
        nopat_source = "Net Income (EBIT unavailable)"
    else:
        nopat = 0.0
        nopat_source = "Zero (no earnings)"

    # Calculate Invested Capital
    if invested_capital_override is not None:
        invested_capital = invested_capital_override
        ic_source = "override"
    elif stock.net_working_capital > 0 or stock.net_fixed_assets > 0:
        invested_capital = stock.net_working_capital + stock.net_fixed_assets
        ic_source = "NWC + NFA"
    else:
        invested_capital = 0.0
        ic_source = "Zero (no data)"

    # Calculate ROIC
    if invested_capital > 0:
        roic = nopat / invested_capital * 100
    else:
        roic = 0.0

    # Determine confidence
    if nopat_source == "EBIT" and ic_source == "NWC + NFA":
        confidence = "High"
    elif nopat_source == "Net Income (EBIT unavailable)" or ic_source == "NWC + NFA":
        confidence = "Medium"
    else:
        confidence = "Low"

    components = {
        "ebit": stock.ebit,
        "tax_rate": tax_rate,
        "nopat": nopat,
        "nopat_source": nopat_source,
        "net_working_capital": stock.net_working_capital,
        "net_fixed_assets": stock.net_fixed_assets,
        "invested_capital": invested_capital,
        "ic_source": ic_source,
    }

    return ROICResult(
        nopat=nopat,
        invested_capital=invested_capital,
        roic=roic,
        components=components,
        method="ROIC",
        confidence=confidence,
    )
