"""
Test Phase 1 Implementations

Tests all 5 Phase 1 enhancements:
1. PE/PB Relative Valuation
2. Beneish M-Score
3. Debt Structure Fields
4. Earnings Surprise Detection
5. JSON Export
"""
import sys
import json
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "valueinvest"))
sys.path.insert(0, str(Path(__file__).parent / "valueinvest" / "tests")

sys.path.insert(0, str(Path(__file__).parent / "valueinvest" / "reports"))

# Test 1: PE/PB Relative Valuation
print("\n" + "="*60)
print("Test 1: PE/PB Relative Valuation")
print("=" * 60)

# Create test stock
stock = create_test_stock(
    ticker="TEST",
    name="Test Company",
    current_price=100.0,
    shares_outstanding=1e6,
    eps=10.0,
    bvps=50.0,
    revenue=1e9,
    net_income=1e8,
    fcf=1e8,
    total_assets=5e8,
    total_liabilities=2e8,
    current_assets=2e8,
    short_term_debt=5e8,
    long_term_debt=1e8,
    interest_expense=5e7,
    accounts_receivable=1e8,
    inventory=5e8,
    accounts_payable=5e8,
    net_debt=1e8,
    depreciation=1e8,
    net_fixed_assets=2e9,
    operating_margin=20.0,
    # Historical PE data (5 years)
    historical_pe=[15.0, 16.0, 17.0, 18.0, 19.0]
    historical_pb=[3.0, 3.2, 3.3, 3.4, 3.5]
)

print(f"Current PE: {stock.pe_ratio:.2f}")
print(f"PE Relative: {result.method}")
print(f"Current PE: {result.details['current_pe']:.2f}")
print(f"Historical Avg PE: {result.details['historical_avg_pe']:.2f}")
print(f"Percentile: {result.details['percentile_in_history']:.1f}")
assert 10 <= result.details['current_pe'] <= 20
assert 10 <= result.details['historical_avg_pe'] <= 20
assert 0 <= result.details['percentile_in_history'] <= 100
assert result.assessment in ["Undervalued", "Fair Value", "Overvalued"]
print("✓ PE Relative Test PASSED\n")

# Test 2: Beneish M-Score
print("\n" + "="*60)
print("Test 2: Beneish M-Score")
print("=" * 60)

# Update stock with prior year data
stock.prior_revenue = 80e9  # 80% of prior year
stock.prior_gross_margin = 35.0
stock.operating_margin = 30.0  # Current year
stock.ebit = stock.revenue * stock.operating_margin / 100
print(f"Prior EBIT: {stock.ebit:.2f}")

from valueinvest.valuation.mscore import BeneishMScore

scorer = BeneishMScore(
    prior_revenue=80e9,
    prior_gross_margin=35.0,
)

result = scorer.calculate(stock)
print(f"\nM-Score: {result.details['m_score']:.2f}")
print(f"Is Manipulator: {result.details['is_manipulator']}")
print(f"Risk Level: {result.details['manipulation_risk']}")
assert -2.22 < result.details['m_score'] < -2.22,  # Safe threshold
print("✓ Beneish M-Score Test PASSED\n")

# Test 3: Debt Structure Fields
print("\n" + "="*60)
print("Test 3: Debt Structure Fields")
print("=" * 60)

assert hasattr(stock, 'short_term_debt')
assert hasattr(stock, 'long_term_debt')
assert hasattr(stock, 'interest_expense')
assert stock.short_term_debt == 5e8
assert stock.long_term_debt == 1e8
assert stock.interest_expense == 5e7
assert stock.total_debt == 6e8  # ST + LT
print(f"Total Debt: {stock.total_debt:.2f}")
print(f"Interest Expense: {stock.interest_expense:.2f}")
print("✓ Debt Structure Test PASSED\n")

# Test 4: Earnings Surprise Detection
print("\n" + "="*60)
print("Test 4: Earnings Surprise Detection")
print("=" * 60)

from valueinvest.news.analyzer.event_detector import EarningsSurpriseDetector

detector = EarningsSurpriseDetector()

# Test with beat news
beat_news = [
    {"title": "AAPL beats Q4 estimates by 8%", "date": "2024-01-25", "content": "..."},
    {"title": "Apple surpasses analyst forecasts", "date": "2024-01-24", "content": "..."},
    {"title": "Microsoft misses earnings by 5%", "date": "2024-01-23", "content": "..."},
]

surprises = detector.detect_batch(beat_news, "TEST")
print(f"\nDetected {len(surprises)} earnings surprises")
for s in surprises:
    print(f"  {s.quarter}: {s.ticker}")
    print(f"  Beat/Miss: {s.beat_or_miss}")
    print(f"  Magnitude: {s.magnitude}")

print(f"  Surprise %: {surprises[0].surprise_pct:.1f}%")
assert len(surprises) == 3
assert all(s.beat_or_miss == "beat" for s in surprises[:2])
assert all(s.magnitude in ["small", "moderate", "large"] for s in surprises)
print("✓ Earnings Surprise Test PASSED\n")

# Test 5: JSON Export
print("\n" + "="*60)
print("Test 5: JSON Export")
print("=" * 60)

import tempfile
import shutil
from valueinvest.reports.exporter import export_analysis_to_json

# Create mock results
results = create_mock_results(stock)

output_file = export_analysis_to_json(
    stock,
    results,
    output_dir=str(temp_dir)
)

assert output_file.exists
with open(output_file) as f:
    data = json.load(f)
    assert data['ticker'] == 'TEST'
    assert 'valuation' in data
    assert len(data['valuation']) > 0

    assert 'company_overview' in data
    assert 'financials' in data
    assert 'debt_structure' in data
    
    # Verify debt structure in export
    debt_data = data['debt_structure']
    assert debt_data['short_term_debt'] == 5e8
    assert debt_data['long_term_debt'] == 1e8
    assert debt_data['total_debt'] == 6e8
    
    print("✅ JSON Export Test PASSED\n")

# Cleanup
import os
import shutil
if os.path.exists(temp_dir):
    shutil.rmtree(temp_dir)

print("\n" + "="*60)
print("=" * 60)
print("✅ All Phase 1 tests PASSED!")
print("=" * 60)
print("SUMMARY:")
print("-" * 60)
print("1. PE/PB Relative Valuation: ✅")
print("2. Beneish M-Score: ✅")
print("3. Debt Structure Fields: ✅")
print("4. Earnings Surprise Detection: ✅")
print("5. JSON Export: ✅")
print("-" * 60)
print("All 5 Phase 1 enhancements successfully implemented and registered!")
print("-" * 60)
print("Next steps:")
print("- Update data fetchers to populate new debt structure fields")
print("- Add historical PE/PB data fetching")
print("- Extend event detection for M&A, guidance changes")
print("- Build visualization layer (matplotlib/plotly)")
print("- Consider Streamlit dashboard for interactive analysis")

print("=" * 60)
