#!/usr/bin/env python3
"""Generate US Robotics Industry Analysis Report"""

import json
from datetime import datetime
from valueinvest import Stock, StockHistory, ValuationEngine

# Define companies by supply chain position
COMPANIES = {
    "upstream": [
        ("NVDA", "NVIDIA", "英伟达"),
        ("CGNX", "Cognex", "康耐视"),
        ("MOG.A", "Moog Inc.", "穆格"),
        ("OUST", "Ouster", "Ouster"),
        ("PH", "Parker Hannifin", "派克汉尼汾"),
        ("PATH", "UiPath", "UiPath"),
        ("TDY", "Teledyne Technologies", "特雷迪恩"),
        ("ZBRA", "Zebra Technologies", "斑马技术"),
        ("ROK", "Rockwell Automation", "罗克韦尔自动化"),
    ],
    "midstream": [
        ("TSLA", "Tesla", "特斯拉"),
        ("TER", "Teradyne", "泰瑞达"),
        ("FANUY", "FANUC", "发那科"),
        ("ABBNY", "ABB", "ABB集团"),
    ],
    "downstream": [
        ("ISRG", "Intuitive Surgical", "直觉外科"),
        ("SYK", "Stryker", "史赛克"),
        ("MDT", "Medtronic", "美敦力"),
        ("ZBH", "Zimmer Biomet", "捷迈邦美"),
        ("SYM", "Symbotic", "Symbotic"),
        ("GXO", "GXO Logistics", "GXO物流"),
        ("DE", "Deere & Company", "迪尔公司"),
        ("AVAV", "AeroVironment", "AeroVironment"),
    ],
}


def fetch_company_data(ticker, name, cn_name):
    """Fetch stock data and history for a company"""
    result = {
        "ticker": ticker,
        "name": name,
        "cn_name": cn_name,
        "error": None,
        "stock": None,
        "history": None,
        "valuation": None,
    }

    try:
        print(f"Fetching {ticker} ({name})...")
        stock = Stock.from_api(ticker)
        result["stock"] = {
            "current_price": stock.current_price,
            "market_cap": stock.current_price * stock.shares_outstanding
            if stock.shares_outstanding
            else 0,
            "revenue": stock.revenue,
            "net_income": stock.net_income,
            "eps": stock.eps,
            "bvps": stock.bvps,
            "pe_ratio": stock.pe_ratio,
            "pb_ratio": stock.pb_ratio,
            "dividend_yield": getattr(stock, "dividend_yield", 0),
            "shares_outstanding": stock.shares_outstanding,
        }
    except Exception as e:
        result["error"] = f"Stock fetch error: {str(e)}"
        print(f"  Error fetching stock: {e}")
        return result

    try:
        history = Stock.fetch_price_history(ticker, period="5y")
        result["history"] = {
            "cagr": history.cagr,
            "cagr_hfq": history.cagr_hfq,
            "volatility": history.volatility,
            "max_drawdown": history.max_drawdown,
        }
    except Exception as e:
        result["error"] = f"History fetch error: {str(e)}"
        print(f"  Error fetching history: {e}")
        return result

    try:
        engine = ValuationEngine()
        # Set reasonable parameters for growth stocks
        stock.growth_rate = min(max(history.cagr * 0.7, 3), 15)  # Conservative growth estimate
        stock.cost_of_capital = 10.0
        stock.discount_rate = 10.0
        stock.terminal_growth = 2.5

        valuation_results = engine.run_growth(stock)
        result["valuation"] = []
        for v in valuation_results:
            result["valuation"].append(
                {
                    "method": v.method_name,
                    "fair_value": v.fair_value,
                    "premium_discount": v.premium_discount,
                    "assessment": v.assessment,
                }
            )
    except Exception as e:
        print(f"  Error running valuation: {e}")
        result["valuation"] = []

    return result


def main():
    """Main function to fetch all data"""
    all_data = {
        "upstream": [],
        "midstream": [],
        "downstream": [],
        "fetch_date": datetime.now().strftime("%Y-%m-%d"),
    }

    for position, companies in COMPANIES.items():
        print(f"\n=== Fetching {position} companies ===")
        for ticker, name, cn_name in companies:
            data = fetch_company_data(ticker, name, cn_name)
            data["position"] = position
            all_data[position].append(data)

    # Save to JSON
    output_path = "reports/robot/us_robot_data.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print(f"\nData saved to {output_path}")

    # Print summary
    print("\n=== Summary ===")
    for position, companies in all_data.items():
        if position == "fetch_date":
            continue
        success = sum(1 for c in companies if c["stock"] is not None)
        print(f"{position}: {success}/{len(companies)} successful")


if __name__ == "__main__":
    main()
