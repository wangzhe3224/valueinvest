#!/usr/bin/env python3
"""Generate comprehensive analysis for stock with all required data."""
import sys
import json
from datetime import datetime

from valueinvest import Stock, StockHistory, ValuationEngine
from valueinvest.valuation.value_trap import detect_value_trap
from valueinvest.buyback import BuybackRegistry
from valueinvest.cashflow import CashFlowRegistry


def run_comprehensive_analysis(ticker: str, period: str = "5y"):
    """Run all analyses and return structured data."""
    print(f"Fetching basic data for {ticker}...")
    stock = Stock.from_api(ticker)

    print(f"Fetching price history ({period})...")
    history = Stock.fetch_price_history(ticker, period=period)

    # Detect company type
    company_type = "general"
    if stock.dividend_yield and stock.dividend_yield > 3:
        company_type = "dividend"
    elif history.cagr_hfq and history.cagr_hfq > 10:
        company_type = "growth"
    elif history.cagr_hfq and history.cagr_hfq < 5:
        company_type = "value"

    # Set valuation parameters
    stock.cost_of_capital = 9.0
    stock.discount_rate = 9.0
    stock.terminal_growth = 2.5

    if history.cagr and history.cagr > 0:
        stock.growth_rate = min(history.cagr, 10)
    else:
        stock.growth_rate = 3.0

    stock.growth_rate_1_5 = stock.growth_rate
    stock.growth_rate_6_10 = stock.growth_rate * 0.6

    if company_type == "dividend" and stock.dividend_growth_rate == 0:
        stock.dividend_growth_rate = min(stock.growth_rate, 5)
        stock.dividend_growth_rate = min(stock.growth_rate, 5)
    elif company_type == "growth":
        stock.cost_of_capital = 10.0
        stock.discount_rate = 10.0

    print("Running valuation...")
    engine = ValuationEngine()

    if company_type == "dividend":
        results = engine.run_dividend(stock)
    elif company_type == "growth":
        results = engine.run_growth(stock)
    else:
        results = engine.run_all(stock)

    # Filter valid results
    valid_results = [
        r for r in results if r.fair_value and r.fair_value > 0 and "Error" not in r.assessment
    ]

    # Value trap detection
    print("Detecting value trap...")
    trap_result = detect_value_trap(
        stock,
        revenue_cagr_5y=history.cagr,
        margin_trend="stable",
        roe_trend="stable",
        industry="consumer_staples",
    )

    # Buyback analysis
    print("Fetching buyback data...")
    buyback_result = None
    try:
        buyback_fetcher = BuybackRegistry.get_fetcher(ticker)
        buyback_result = buyback_fetcher.fetch_buyback(ticker, days=365)
    except Exception as e:
        print(f"Warning: Buyback fetch failed - {e}")

    # FCF analysis
    print("Fetching FCF data...")
    fcf_result = None
    try:
        fcf_fetcher = CashFlowRegistry.get_fetcher(ticker)
        fcf_result = fcf_fetcher.fetch_cashflow(ticker, years=5)
    except Exception as e:
        print(f"Warning: FCF fetch failed - {e}")

    # Compile all data
    data = {
        "ticker": ticker,
        "stock": {
            "name": stock.name,
            "ticker": stock.ticker,
            "current_price": stock.current_price,
            "shares_outstanding": stock.shares_outstanding,
            "revenue": stock.revenue,
            "net_income": stock.net_income,
            "eps": stock.eps,
            "bvps": stock.bvps,
            "pe_ratio": stock.pe_ratio,
            "pb_ratio": stock.pb_ratio,
            "dividend_yield": stock.dividend_yield,
            "roe": stock.roe,
            "fcf": stock.fcf,
            "operating_margin": stock.operating_margin,
            "growth_rate": stock.growth_rate,
            "cost_of_capital": stock.cost_of_capital,
            "total_assets": stock.total_assets,
            "total_liabilities": stock.total_liabilities,
            "current_assets": stock.current_assets,
        },
        "history": {
            "cagr": history.cagr,
            "cagr_hfq": history.cagr_hfq,
            "volatility": history.volatility,
            "max_drawdown": history.max_drawdown,
            "period": period,
        },
        "company_type": company_type,
        "valuation_results": [
            {
                "method": r.method,
                "fair_value": r.fair_value,
                "premium_discount": r.premium_discount,
                "assessment": r.assessment,
            }
            for r in valid_results
        ],
        "trap_result": {
            "is_trap": trap_result.is_trap,
            "trap_score": trap_result.trap_score,
            "overall_risk": trap_result.overall_risk.value,
            "financial_health_score": trap_result.financial_health_score,
            "business_deterioration_score": trap_result.business_deterioration_score,
            "moat_erosion_score": trap_result.moat_erosion_score,
            "ai_vulnerability_score": trap_result.ai_vulnerability_score,
            "dividend_signal_score": trap_result.dividend_signal_score,
            "warnings": trap_result.warnings,
            "critical_issues": trap_result.critical_issues,
        },
    }

    # Add buyback data
    if buyback_result and buyback_result.summary:
        data["buyback"] = {
            "dividend_yield": buyback_result.summary.dividend_yield,
            "buyback_yield": buyback_result.summary.buyback_yield,
            "total_shareholder_yield": buyback_result.summary.total_shareholder_yield,
            "sentiment": buyback_result.summary.sentiment.value,
            "shares_reduction_rate": buyback_result.summary.shares_reduction_rate,
            "yearly_amounts": buyback_result.summary.yearly_amounts,
            "exceeds_dividend": buyback_result.summary.exceeds_dividend,
            "is_aggressive": buyback_result.summary.is_aggressive,
        }

    # Add FCF data
    if fcf_result and fcf_result.summary:
        data["fcf"] = {
            "fcf_quality": fcf_result.summary.fcf_quality.value,
            "fcf_trend": fcf_result.summary.fcf_trend.value,
            "latest_fcf": fcf_result.summary.latest_fcf,
            "fcf_yield": fcf_result.summary.fcf_yield,
            "fcf_margin": fcf_result.summary.fcf_margin,
            "fcf_per_share": fcf_result.summary.fcf_per_share,
            "latest_true_fcf": fcf_result.summary.latest_true_fcf,
            "true_fcf_yield": fcf_result.summary.true_fcf_yield,
            "true_fcf_margin": fcf_result.summary.true_fcf_margin,
            "fcf_to_net_income": fcf_result.summary.fcf_to_net_income,
            "sbc_as_pct_of_fcf": fcf_result.summary.sbc_as_pct_of_fcf,
            "sbc_is_material": fcf_result.summary.sbc_is_material,
            "fcf_cagr": fcf_result.summary.fcf_cagr,
            "revenue_cagr": fcf_result.summary.revenue_cagr,
            "positive_fcf_years": fcf_result.summary.positive_fcf_years,
            "record_count": fcf_result.summary.record_count,
            "yearly_fcf": fcf_result.summary.yearly_fcf,
            "yearly_true_fcf": fcf_result.summary.yearly_true_fcf,
            "yearly_sbc": fcf_result.summary.yearly_sbc,
            "yearly_revenue": fcf_result.summary.yearly_revenue,
        }

    # Add recent price stats
    if history.prices:
        recent_stats = history.get_price_stats(days=30, adjust="qfq")
        if recent_stats:
            data["recent_stats"] = recent_stats

        recent_prices = history.get_recent_prices(days=10, adjust="qfq")
        if recent_prices:
            data["recent_prices"] = recent_prices

    return data


if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "600887"
    period = sys.argv[2] if len(sys.argv) > 2 else "5y"

    data = run_comprehensive_analysis(ticker, period)

    # Output as JSON
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
