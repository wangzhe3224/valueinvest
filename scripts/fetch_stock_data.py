#!/usr/bin/env python3
"""
Stock Data Fetcher Script
=========================

Fetch comprehensive stock data for analysis including:
- Basic fundamentals
- Price history (QFQ and HFQ)
- Valuation results
- Value trap detection
- Buyback analysis

Usage:
    python scripts/fetch_stock_data.py MSFT
    python scripts/fetch_stock_data.py 600887 --period 3y
    python scripts/fetch_stock_data.py AAPL --output json

Output format: JSON (for programmatic use) or readable text
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Any, Optional


def fetch_stock_data(
    ticker: str,
    period: str = "5y",
    include_buyback: bool = True,
    include_trap: bool = True,
    industry: str = "",
    margin_trend: str = "stable",
    roe_trend: str = "stable",
) -> dict[str, Any]:
    """
    Fetch all stock data for analysis.

    Args:
        ticker: Stock ticker symbol
        period: Historical period (1y, 2y, 3y, 5y, 10y)
        include_buyback: Whether to include buyback analysis
        include_trap: Whether to include value trap detection
        industry: Industry for AI vulnerability assessment
        margin_trend: Margin trend (stable, compressing, expanding)
        roe_trend: ROE trend (stable, declining, improving)

    Returns:
        Dictionary containing all analysis data
    """
    from valueinvest import Stock, ValuationEngine
    from valueinvest.data.fetcher import get_fetcher

    result = {
        "ticker": ticker,
        "fetch_time": datetime.now().isoformat(),
        "period": period,
        "success": True,
        "errors": [],
    }

    history = None

    # 1. Fetch basic stock data
    try:
        fetcher = get_fetcher(ticker)
        fetch_result = fetcher.fetch_all(ticker)
        if not fetch_result.success:
            result["success"] = False
            result["errors"].extend(fetch_result.errors)
            return result

        stock = Stock.from_dict(fetch_result.data)

        result["stock"] = {
            "name": stock.name,
            "ticker": stock.ticker,
            "current_price": stock.current_price,
            "shares_outstanding": stock.shares_outstanding,
            "market_cap": stock.market_cap,
            "revenue": stock.revenue,
            "net_income": stock.net_income,
            "eps": stock.eps,
            "bvps": stock.bvps,
            "pe_ratio": stock.pe_ratio,
            "pb_ratio": stock.pb_ratio,
            "dividend_yield": stock.dividend_yield,
            "dividend_per_share": stock.dividend_per_share,
            "roe": stock.roe,
            "operating_margin": stock.operating_margin,
            "fcf": stock.fcf,
            "net_debt": stock.net_debt,
            "sbc": stock.sbc,
            "shares_issued": stock.shares_issued,
            "shares_repurchased": stock.shares_repurchased,
            "currency": stock.currency,
            "exchange": stock.exchange,
        }
    except Exception as e:
        result["success"] = False
        result["errors"].append(f"Failed to fetch stock data: {str(e)}")
        return result

    # 2. Fetch price history
    try:
        history = Stock.fetch_price_history(ticker, period=period, include_hfq=True)

        result["history"] = {
            "cagr": history.cagr,
            "cagr_hfq": history.cagr_hfq,
            "volatility": history.volatility,
            "max_drawdown": history.max_drawdown,
            "start_date": str(history.start_date) if history.start_date else None,
            "end_date": str(history.end_date) if history.end_date else None,
        }

        # Recent prices (QFQ)
        recent_prices_qfq = history.get_recent_prices(days=10, adjust="qfq")
        result["recent_prices_qfq"] = recent_prices_qfq

        # Price stats
        stats_qfq = history.get_price_stats(days=30, adjust="qfq")
        stats_hfq = history.get_price_stats(days=30, adjust="hfq")
        result["price_stats"] = {
            "qfq": stats_qfq,
            "hfq": stats_hfq,
        }
    except Exception as e:
        result["errors"].append(f"Failed to fetch price history: {str(e)}")
        result["history"] = None

    # 3. Run valuation
    try:
        engine = ValuationEngine()

        # Detect company type and run appropriate methods
        if stock.dividend_yield > 3:
            valuation_results = engine.run_dividend(stock)
            company_type = "dividend"
        elif stock.pe_ratio > 0 and stock.pe_ratio < 10:
            valuation_results = engine.run_all(stock)
            company_type = "value"
        elif history and history.cagr_hfq > 10:
            valuation_results = engine.run_growth(stock)
            company_type = "growth"
        else:
            valuation_results = engine.run_all(stock)
            company_type = "general"

        result["company_type"] = company_type

        # Process valuation results
        val_list = []
        for r in valuation_results:
            if r.fair_value > 0:  # Only include valid results
                val_list.append(
                    {
                        "method": r.method,
                        "fair_value": r.fair_value,
                        "assessment": r.assessment,
                        "premium_discount": r.premium_discount,
                        "confidence": r.confidence,
                    }
                )

        result["valuation"] = {
            "results": val_list,
            "count": len(val_list),
        }

        # Calculate statistics
        if val_list:
            fair_values = [v["fair_value"] for v in val_list]
            result["valuation"]["min_fair_value"] = min(fair_values)
            result["valuation"]["max_fair_value"] = max(fair_values)
            result["valuation"]["avg_fair_value"] = sum(fair_values) / len(fair_values)
            sorted_fv = sorted(fair_values)
            result["valuation"]["median_fair_value"] = sorted_fv[len(sorted_fv) // 2]

            undervalued = sum(1 for v in val_list if "Under" in v["assessment"])
            overvalued = sum(1 for v in val_list if "Over" in v["assessment"])
            result["valuation"]["undervalued_count"] = undervalued
            result["valuation"]["overvalued_count"] = overvalued

            avg_premium = sum(v["premium_discount"] for v in val_list) / len(val_list)
            result["valuation"]["avg_premium_discount"] = avg_premium

    except Exception as e:
        result["errors"].append(f"Failed to run valuation: {str(e)}")
        result["valuation"] = None

    # 4. Value trap detection
    if include_trap:
        try:
            from valueinvest.valuation.value_trap import detect_value_trap

            # Determine industry if not provided
            if not industry:
                industry = _detect_industry(stock, ticker)

            # Calculate revenue growth proxy
            revenue_growth_proxy = _calculate_revenue_growth_proxy(history.cagr if history else 0)

            trap_result = detect_value_trap(
                stock,
                revenue_cagr_5y=revenue_growth_proxy,
                margin_trend=margin_trend,
                roe_trend=roe_trend,
                industry=industry,
            )

            result["value_trap"] = {
                "overall_risk": trap_result.overall_risk.value,
                "trap_score": trap_result.trap_score,
                "is_trap": trap_result.is_trap,
                "should_avoid": trap_result.should_avoid,
                "financial_health_score": trap_result.financial_health_score,
                "business_deterioration_score": trap_result.business_deterioration_score,
                "moat_erosion_score": trap_result.moat_erosion_score,
                "ai_vulnerability_score": trap_result.ai_vulnerability_score,
                "dividend_signal_score": trap_result.dividend_signal_score,
                "warnings": trap_result.warnings,
                "critical_issues": trap_result.critical_issues,
            }
        except Exception as e:
            result["errors"].append(f"Failed to detect value trap: {str(e)}")
            result["value_trap"] = None

    # 5. Buyback analysis
    if include_buyback:
        try:
            from valueinvest.buyback import BuybackRegistry

            buyback_fetcher = BuybackRegistry.get_fetcher(ticker)
            buyback_result = buyback_fetcher.fetch_buyback(ticker, days=365)

            result["buyback"] = {
                "dividend_yield": buyback_result.summary.dividend_yield,
                "buyback_yield": buyback_result.summary.buyback_yield,
                "total_shareholder_yield": buyback_result.summary.total_shareholder_yield,
                "sentiment": buyback_result.summary.sentiment.value,
                "shares_reduction_rate": buyback_result.summary.shares_reduction_rate,
                "exceeds_dividend": buyback_result.summary.exceeds_dividend,
                "is_aggressive": buyback_result.summary.is_aggressive,
                "yearly_amounts": {
                    str(k): v for k, v in buyback_result.summary.yearly_amounts.items()
                },
            }
        except Exception as e:
            result["errors"].append(f"Failed to fetch buyback data: {str(e)}")
            result["buyback"] = None

    return result


def _calculate_revenue_growth_proxy(price_cagr: float) -> float:
    """
    Calculate revenue growth proxy from price CAGR.

    Uses price CAGR as proxy when historical financial data unavailable.
    Limitation: Price CAGR may diverge from actual revenue trends.

    Args:
        price_cagr: Price compound annual growth rate

    Returns:
        Revenue growth proxy (same as price_cagr for now)
    """
    return price_cagr


def _detect_industry(stock, ticker: str) -> str:
    """Detect industry from stock data or ticker pattern."""
    # Try to get from stock extra data
    if hasattr(stock, "extra") and stock.extra:
        if "industry" in stock.extra:
            return stock.extra["industry"]
        if "sector" in stock.extra:
            return stock.extra["sector"]

    # Detect from ticker pattern
    if ticker.isdigit():
        # A-share patterns
        if ticker.startswith("601") or ticker.startswith("600"):
            return "financial_services"
        return "general"
    else:
        # US stock - common tech tickers
        tech_tickers = ["AAPL", "MSFT", "GOOGL", "GOOG", "META", "AMZN", "NVDA", "TSLA"]
        if ticker.upper() in tech_tickers:
            return "software"
        return "general"


def format_readable(data: dict) -> str:
    """Format data as readable text."""
    lines = []
    lines.append("=" * 70)
    lines.append(f"Stock Data Analysis: {data['ticker']}")
    lines.append(f"Fetch Time: {data['fetch_time']}")
    lines.append("=" * 70)

    if not data["success"]:
        lines.append("ERRORS:")
        for err in data["errors"]:
            lines.append(f"  - {err}")
        return "\n".join(lines)

    # Stock info
    if "stock" in data and data["stock"]:
        s = data["stock"]
        lines.append("\n[STOCK DATA]")
        lines.append(f"  Name: {s['name']}")
        lines.append(f"  Price: ${s['current_price']:.2f}")
        lines.append(f"  Market Cap: ${s['market_cap']/1e8:.2f}B")
        lines.append(f"  Revenue: ${s['revenue']/1e8:.2f}B")
        lines.append(f"  Net Income: ${s['net_income']/1e8:.2f}B")
        lines.append(f"  EPS: ${s['eps']:.2f}")
        lines.append(f"  BVPS: ${s['bvps']:.2f}")
        lines.append(f"  PE: {s['pe_ratio']:.2f}x")
        lines.append(f"  PB: {s['pb_ratio']:.2f}x")
        lines.append(f"  Dividend Yield: {s['dividend_yield']:.2f}%")

    # History
    if "history" in data and data["history"]:
        h = data["history"]
        lines.append("\n[HISTORY]")
        lines.append(f"  CAGR (QFQ): {h['cagr']:.2f}%")
        lines.append(f"  CAGR (HFQ): {h['cagr_hfq']:.2f}%")
        lines.append(f"  Volatility: {h['volatility']:.2f}%")
        lines.append(f"  Max Drawdown: {h['max_drawdown']:.2f}%")

    # Valuation
    if "valuation" in data and data["valuation"]:
        v = data["valuation"]
        lines.append("\n[VALUATION]")
        for r in v["results"]:
            lines.append(
                f"  {r['method']}: ${r['fair_value']:.2f} ({r['assessment']}, {r['premium_discount']:+.1f}%)"
            )
        lines.append(f"  Avg Fair Value: ${v.get('avg_fair_value', 0):.2f}")
        lines.append(
            f"  Undervalued/Overvalued: {v.get('undervalued_count', 0)}/{v.get('overvalued_count', 0)}"
        )

    # Value trap
    if "value_trap" in data and data["value_trap"]:
        t = data["value_trap"]
        lines.append("\n[VALUE TRAP]")
        lines.append(f"  Overall Risk: {t['overall_risk']}")
        lines.append(f"  Trap Score: {t['trap_score']}/100")
        lines.append(f"  Is Trap: {t['is_trap']}")

    # Buyback
    if "buyback" in data and data["buyback"]:
        b = data["buyback"]
        lines.append("\n[BUYBACK]")
        lines.append(f"  Total Shareholder Yield: {b['total_shareholder_yield']:.2f}%")
        lines.append(f"  Sentiment: {b['sentiment']}")

    if data["errors"]:
        lines.append("\n[WARNINGS]")
        for err in data["errors"]:
            lines.append(f"  - {err}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Fetch comprehensive stock data for analysis")
    parser.add_argument("ticker", help="Stock ticker symbol")
    parser.add_argument(
        "--period",
        default="5y",
        choices=["1y", "2y", "3y", "5y", "10y"],
        help="Historical period",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="json",
        choices=["json", "text"],
        help="Output format",
    )
    parser.add_argument(
        "--no-buyback",
        action="store_true",
        help="Skip buyback analysis",
    )
    parser.add_argument(
        "--no-trap",
        action="store_true",
        help="Skip value trap detection",
    )
    parser.add_argument(
        "--industry",
        default="",
        help="Industry for AI vulnerability assessment",
    )
    parser.add_argument(
        "--margin-trend",
        default="stable",
        choices=["stable", "compressing", "expanding"],
        help="Margin trend for value trap detection",
    )
    parser.add_argument(
        "--roe-trend",
        default="stable",
        choices=["stable", "declining", "improving"],
        help="ROE trend for value trap detection",
    )

    args = parser.parse_args()

    data = fetch_stock_data(
        ticker=args.ticker,
        period=args.period,
        include_buyback=not args.no_buyback,
        include_trap=not args.no_trap,
        industry=args.industry,
        margin_trend=args.margin_trend,
        roe_trend=args.roe_trend,
    )

    if args.output == "json":
        print(json.dumps(data, indent=2, default=str))
    else:
        print(format_readable(data))

    return 0 if data["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
