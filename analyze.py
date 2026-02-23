"""
ValueInvest - Stock Valuation Library Demo

Usage:
    python analyze.py google
    python analyze.py icbc
    python analyze.py yangtze --methods ddm,pb
"""

import sys
from valueinvest import Stock, ValuationEngine
from valueinvest.data.presets import get_preset, PRESETS
from valueinvest.reports.reporter import format_report, format_summary


def analyze_stock(stock: Stock, methods: list = None, preset_name: str = None):
    engine = ValuationEngine()
    
    if preset_name and preset_name.lower() in ["icbc", "601398"]:
        results = engine.run_bank(stock)
    elif preset_name and preset_name.lower() in ["yangtze", "cyp", "600900"]:
        results = engine.run_dividend(stock)
    elif preset_name and preset_name.lower() in ["google", "googl"]:
        results = engine.run_growth(stock)
    elif methods:
        results = engine.run_multiple(stock, methods)
    else:
        results = engine.run_all(stock)
    
    title = f"{stock.name or stock.ticker} - Valuation Analysis"
    print(format_report(results, title))
    print(format_summary(results))
    
    summary = engine.summary(results)
    print(f"\nEngine Summary: {summary}")
    
    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze.py <stock_preset> [--methods method1,method2]")
        print(f"\nAvailable presets: {list(PRESETS.keys())}")
        print("\nExample:")
        print("  python analyze.py google")
        print("  python analyze.py icbc")
        print("  python analyze.py yangtze --methods ddm,two_stage_ddm,pb")
        sys.exit(1)
    
    preset_name = sys.argv[1]
    methods = None
    
    if "--methods" in sys.argv:
        idx = sys.argv.index("--methods")
        if idx + 1 < len(sys.argv):
            methods = sys.argv[idx + 1].split(",")
    
    try:
        stock = get_preset(preset_name)
    except ValueError:
        print(f"Unknown preset: {preset_name}")
        print(f"Available: {list(PRESETS.keys())}")
        sys.exit(1)
    
    analyze_stock(stock, methods, preset_name)


if __name__ == "__main__":
    main()
