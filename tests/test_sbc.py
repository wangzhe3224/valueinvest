#!/usr/bin/env python3
"""
Test script for SBC Analysis with mock data
"""

from valueinvest.stock import Stock
from valueinvest.valuation.sbc import SBCAnalysis

def test_sbc():
    print("\n=== Testing SBC Analysis with Mock Data ===\n")
    
    # Create mock stock data similar to Adobe
    stock = Stock(
        ticker="TEST",
        name="Test SaaS Company",
        current_price=260.0,
        shares_outstanding=410_000_000,
        revenue=23_770_000_000,  # $23.77B
        net_income=5_560_000_000,  # $5.56B
        fcf=7_870_000_000,  # $7.87B
        sbc=4_830_000_000,  # $4.83B (20.3% of revenue)
        shares_issued=0,  # Will be estimated
        shares_repurchased=0,  # Will be estimated
        dividend_yield=0.0,
    )
    
    print(f"Ticker: {stock.ticker}")
    print(f"Current Price: ${stock.current_price:.2f}")
    print(f"Revenue: ${stock.revenue/1e9:.2f}B")
    print(f"FCF: ${stock.fcf/1e9:.2f}B")
    print(f"SBC: ${stock.sbc/1e9:.2f}B")
    print(f"SBC Margin: {stock.sbc_margin:.2f}%")
    print(f"True FCF: ${stock.true_fcf/1e9:.2f}B")
    print(f"True FCF Margin: {stock.true_fcf / stock.revenue * 100:.2f}%")
    print()
    
    # Test SBC analysis with mature company
    print("--- Test 1: Mature SaaS Company ---")
    analyzer = SBCAnalysis(company_stage="mature", industry="saas")
    result = analyzer.calculate(stock)
    
    print(f"\nAssessment: {result.assessment}")
    print(f"Risk Level: {result.details['risk_level']}")
    print()
    
    for line in result.analysis:
        print(line)
    
    # Test SBC analysis with early-stage company
    print("\n--- Test 2: Early-stage SaaS Company (same data) ---")
    analyzer = SBCAnalysis(company_stage="early", industry="saas")
    result = analyzer.calculate(stock)
    
    print(f"\nAssessment: {result.assessment}")
    print(f"Risk Level: {result.details['risk_level']}")
    
    # Test SBC analysis with hardware company
    print("\n--- Test 3: Hardware Company (same data) ---")
    analyzer = SBCAnalysis(company_stage="mature", industry="hardware")
    result = analyzer.calculate(stock)
    
    print(f"\nAssessment: {result.assessment}")
    print(f"Risk Level: {result.details['risk_level']}")
    
    # Test with lower SBC
    print("\n--- Test 4: Low SBC Company ---")
    stock_low_sbc = Stock(
        ticker="LOW_SBC",
        name="Low SBC Company",
        current_price=260.0,
        shares_outstanding=410_000_000,
        revenue=23_770_000_000,
        net_income=5_560_000_000,
        fcf=7_870_000_000,
        sbc=1_900_000_000,  # $1.9B (8% of revenue)
        shares_issued=0,
        shares_repurchased=0,
        dividend_yield=0.0,
    )
    
    analyzer = SBCAnalysis(company_stage="mature", industry="saas")
    result = analyzer.calculate(stock_low_sbc)
    
    print(f"SBC Margin: {stock_low_sbc.sbc_margin:.2f}%")
    print(f"\nAssessment: {result.assessment}")
    print(f"Risk Level: {result.details['risk_level']}")
    
    print("\n=== All Tests Complete ===\n")
    return True

if __name__ == "__main__":
    test_sbc()
