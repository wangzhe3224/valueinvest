import pytest
from valueinvest.stock import Stock
from valueinvest.capital import (
    analyze_capital_allocation, CapitalAllocationEngine,
    AllocationRating, AllocationCategory,
)


@pytest.fixture
def excellent_allocator_stock():
    """Well-managed company: good dividends, net buyback, moderate capex, low debt."""
    return Stock(
        ticker="GOODMGT",
        name="Good Management Co",
        current_price=100.0,
        shares_outstanding=1_000_000_000,
        eps=8.0,
        bvps=40.0,
        revenue=50_000_000_000,
        net_income=8_000_000_000,
        fcf=10_000_000_000,
        ebit=12_000_000_000,
        operating_margin=24.0,
        tax_rate=25.0,
        roe=20.0,
        total_assets=80_000_000_000,
        total_liabilities=20_000_000_000,
        short_term_debt=3_000_000_000,
        long_term_debt=7_000_000_000,
        interest_expense=500_000_000,
        net_working_capital=12_000_000_000,
        net_fixed_assets=40_000_000_000,
        depreciation=3_000_000_000,
        capex=4_500_000_000,
        dividend_per_share=3.0,
        dividend_yield=3.0,
        dividend_growth_rate=8.0,
        shares_issued=30_000_000,
        shares_repurchased=150_000_000,
        sbc=500_000_000,
        cost_of_capital=10.0,
        growth_rate=8.0,
        prior_debt_ratio=28.0,
        extra={"_debt_ratio": 25.0},
    )


@pytest.fixture
def poor_allocator_stock():
    """Poorly managed company: no dividend, heavy dilution, high SBC, high debt."""
    return Stock(
        ticker="POORMGT",
        name="Poor Management Co",
        current_price=30.0,
        shares_outstanding=500_000_000,
        eps=1.0,
        bvps=8.0,
        revenue=15_000_000_000,
        net_income=500_000_000,
        fcf=100_000_000,
        ebit=800_000_000,
        operating_margin=5.3,
        tax_rate=25.0,
        roe=12.5,
        total_assets=20_000_000_000,
        total_liabilities=14_000_000_000,
        short_term_debt=5_000_000_000,
        long_term_debt=7_000_000_000,
        interest_expense=1_000_000_000,
        net_working_capital=2_000_000_000,
        net_fixed_assets=4_000_000_000,
        depreciation=1_000_000_000,
        capex=2_000_000_000,
        dividend_per_share=0.0,
        dividend_yield=0.0,
        dividend_growth_rate=0.0,
        shares_issued=100_000_000,
        shares_repurchased=0,
        sbc=1_500_000_000,
        cost_of_capital=10.0,
        growth_rate=3.0,
        prior_debt_ratio=65.0,
        extra={"_debt_ratio": 70.0},
    )


@pytest.fixture
def high_sbc_stock():
    """Tech company with very high SBC."""
    return Stock(
        ticker="HIGHSBC",
        name="High SBC Co",
        current_price=200.0,
        shares_outstanding=500_000_000,
        eps=5.0,
        revenue=20_000_000_000,
        net_income=2_500_000_000,
        fcf=1_000_000_000,
        shares_issued=80_000_000,
        shares_repurchased=20_000_000,
        sbc=2_000_000_000,
        dividend_per_share=0.0,
        dividend_yield=0.0,
        total_assets=30_000_000_000,
        total_liabilities=10_000_000_000,
        cost_of_capital=10.0,
        extra={"_debt_ratio": 33.3},
    )


# --- 1. Excellent allocator gets high overall score ---
def test_excellent_allocator_high_score(excellent_allocator_stock):
    engine = CapitalAllocationEngine()
    result = engine.analyze(excellent_allocator_stock)
    assert result.overall_score > 55


# --- 2. Excellent allocator gets GOOD or EXCELLENT rating ---
def test_excellent_allocator_rating(excellent_allocator_stock):
    engine = CapitalAllocationEngine()
    result = engine.analyze(excellent_allocator_stock)
    assert result.rating in (AllocationRating.GOOD, AllocationRating.EXCELLENT)


# --- 3. Poor allocator gets low overall score ---
def test_poor_allocator_low_score(poor_allocator_stock):
    engine = CapitalAllocationEngine()
    result = engine.analyze(poor_allocator_stock)
    assert result.overall_score < 40


# --- 4. Poor allocator gets POOR or DESTRUCTIVE rating ---
def test_poor_allocator_rating(poor_allocator_stock):
    engine = CapitalAllocationEngine()
    result = engine.analyze(poor_allocator_stock)
    assert result.rating in (AllocationRating.POOR, AllocationRating.DESTRUCTIVE)


# --- 5. High SBC stock has low dilution score ---
def test_high_sbc_dilution_penalty(high_sbc_stock):
    engine = CapitalAllocationEngine()
    result = engine.analyze(high_sbc_stock)
    # SBC is 10% of revenue -> very low dilution sub-score
    assert result.dilution_score < 20


# --- 6. Excellent allocator has positive net buyback signal ---
def test_net_buyback_positive(excellent_allocator_stock):
    engine = CapitalAllocationEngine()
    result = engine.analyze(excellent_allocator_stock)
    buyback_sigs = [s for s in result.signals if s.name == "Net Buyback"]
    assert len(buyback_sigs) == 1
    sig = buyback_sigs[0]
    assert sig.is_available is True
    # Net buyback yield should be positive (150M repurchased - 30M issued)
    assert sig.value > 0
    assert sig.score > 60


# --- 7. Poor allocator has low net dilution score ---
def test_net_dilution_penalty(poor_allocator_stock):
    engine = CapitalAllocationEngine()
    result = engine.analyze(poor_allocator_stock)
    dilution_sigs = [s for s in result.signals if s.name == "Net Dilution"]
    assert len(dilution_sigs) == 1
    sig = dilution_sigs[0]
    assert sig.is_available is True
    # 100M issued, 0 repurchased -> 20% dilution rate
    assert sig.score < 15


# --- 8. Excellent allocator has sustainable dividend (payout ~37.5%) ---
def test_sustainable_dividend(excellent_allocator_stock):
    engine = CapitalAllocationEngine()
    result = engine.analyze(excellent_allocator_stock)
    payout_sigs = [s for s in result.signals if s.name == "Payout Ratio"]
    assert len(payout_sigs) == 1
    sig = payout_sigs[0]
    assert sig.is_available is True
    # payout = 3/8 = 37.5%, falls in the 30-60% sweet spot
    assert sig.value == pytest.approx(37.5, abs=0.1)
    assert sig.score >= 80


# --- 9. Poor allocator has low dividend signals ---
def test_no_dividend_penalty(poor_allocator_stock):
    engine = CapitalAllocationEngine()
    result = engine.analyze(poor_allocator_stock)
    # Dividend yield and dividend growth signals should be unavailable (no dividend)
    dy_sigs = [s for s in result.signals if s.name == "Dividend Yield"]
    dg_sigs = [s for s in result.signals if s.name == "Dividend Growth"]
    assert dy_sigs[0].is_available is False
    assert dg_sigs[0].is_available is False
    # Shareholder return sub-score should be low
    assert result.shareholder_return_score < 50


# --- 10. Excellent allocator has positive shareholder yield ---
def test_shareholder_yield(excellent_allocator_stock):
    engine = CapitalAllocationEngine()
    result = engine.analyze(excellent_allocator_stock)
    # dividend_yield (3%) + true_buyback_yield (~12%) = ~15%
    assert result.shareholder_yield > 5
    # Corresponding signal should also reflect high yield
    sy_sigs = [s for s in result.signals if s.name == "Shareholder Yield"]
    assert sy_sigs[0].value > 5
    assert sy_sigs[0].score >= 80


# --- 11. Convenience function works ---
def test_convenience_function(excellent_allocator_stock):
    result = analyze_capital_allocation(excellent_allocator_stock)
    assert isinstance(result, type(analyze_capital_allocation(excellent_allocator_stock)))
    assert result.ticker == "GOODMGT"
    assert result.overall_score > 0
    assert len(result.signals) > 0


# --- 12. to_summary() contains key info ---
def test_to_summary_format(excellent_allocator_stock):
    result = analyze_capital_allocation(excellent_allocator_stock)
    summary = result.to_summary()
    assert "GOODMGT" in summary
    assert "Score=" in summary
    assert "Rating=" in summary
    assert "ShareholderYield=" in summary


# --- 13. __str__() is multi-line ---
def test_str_output(excellent_allocator_stock):
    result = analyze_capital_allocation(excellent_allocator_stock)
    text = str(result)
    lines = text.strip().split("\n")
    assert len(lines) > 3
    # Should contain category sub-scores
    assert "Shareholder Return:" in text
    assert "Reinvestment:" in text
    assert "Balance Sheet:" in text
    assert "Dilution:" in text


# --- 14. All 12 signals are computed ---
def test_all_signals_computed(excellent_allocator_stock):
    result = analyze_capital_allocation(excellent_allocator_stock)
    assert len(result.signals) == 12
    signal_names = {s.name for s in result.signals}
    expected = {
        "Dividend Yield", "Payout Ratio", "Dividend Growth",
        "Net Buyback", "Shareholder Yield",
        "CapEx/Revenue", "CapEx/Depreciation", "Reinvestment ROIC",
        "Debt Trend", "Interest Coverage",
        "SBC Burden", "Net Dilution",
    }
    assert signal_names == expected


# --- 15. Four category sub-scores present ---
def test_category_sub_scores(excellent_allocator_stock):
    result = analyze_capital_allocation(excellent_allocator_stock)
    assert result.shareholder_return_score > 0
    assert result.reinvestment_score > 0
    assert result.balance_sheet_score > 0
    assert result.dilution_score > 0


# --- 16. is_shareholder_friendly matches rating ---
def test_is_shareholder_friendly(excellent_allocator_stock, poor_allocator_stock):
    good_result = analyze_capital_allocation(excellent_allocator_stock)
    poor_result = analyze_capital_allocation(poor_allocator_stock)
    assert good_result.is_shareholder_friendly is True
    assert poor_result.is_shareholder_friendly is False


# --- 17. Custom category weights affect result ---
def test_custom_weights(excellent_allocator_stock):
    # Default result
    default_result = analyze_capital_allocation(excellent_allocator_stock)

    # Heavily weight dilution (which has a lower score for this stock)
    # by setting other weights very low
    custom_weights = {
        "shareholder_return": 0.05,
        "reinvestment": 0.05,
        "balance_sheet": 0.05,
        "dilution": 0.85,
    }
    custom_result = analyze_capital_allocation(
        excellent_allocator_stock, category_weights=custom_weights
    )

    # The custom result should differ from the default
    # because dilution is weighted much more heavily
    assert custom_result.overall_score != default_result.overall_score


# --- 18. Passing roic/wacc to engine improves reinvestment signal ---
def test_roic_param_in_reinvestment(excellent_allocator_stock):
    # Without roic/wacc: uses ROE proxy (20 - 10 = 10pp spread, score=85)
    engine_default = CapitalAllocationEngine()
    result_default = engine_default.analyze(excellent_allocator_stock)
    default_roic_sig = [s for s in result_default.signals if s.name == "Reinvestment ROIC"][0]

    # With explicit roic=15, wacc=8: spread=7pp, score=90
    engine_explicit = CapitalAllocationEngine(roic=15.0, wacc=8.0)
    result_explicit = engine_explicit.analyze(excellent_allocator_stock)
    explicit_roic_sig = [s for s in result_explicit.signals if s.name == "Reinvestment ROIC"][0]

    # The explicit ROIC/WACC should give a higher reinvestment ROIC score
    assert explicit_roic_sig.score > default_roic_sig.score
    assert explicit_roic_sig.value == pytest.approx(7.0, abs=0.1)
    # Description should mention ROIC/WACC, not ROE proxy
    assert "ROIC" in explicit_roic_sig.description
    assert "WACC" in explicit_roic_sig.description
