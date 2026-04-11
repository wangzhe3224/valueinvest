"""
Tests for Implied Growth Rate Analysis module.
"""

import pytest

from valueinvest.stock import Stock
from valueinvest.implied_growth.base import (
    GrowthComparison,
    GrowthReasonableness,
    ImpliedGrowthDetail,
    ImpliedGrowthResult,
)
from valueinvest.implied_growth.analyzer import (
    assess_reasonableness,
    calculate_earnings_yield_implied_growth,
    calculate_gordon_growth_implied_growth,
    calculate_peg_implied_growth,
    calculate_reverse_dcf_implied_growth,
    compare_with_historical,
)
from valueinvest.implied_growth.engine import ImpliedGrowthEngine
from valueinvest.implied_growth import analyze_implied_growth


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def healthy_stock():
    """A healthy Chinese company (similar to 伊利股份)."""
    return Stock(
        ticker="600887",
        name="伊利股份",
        current_price=26.0,
        shares_outstanding=64e9,
        eps=1.65,
        bvps=8.0,
        revenue=90.0e9,
        net_income=10.4e9,
        fcf=8.0e9,
        operating_cash_flow=9.0e9,
        net_debt=2.0e9,
        total_assets=30.0e9,
        total_liabilities=15.0e9,
        depreciation=2.5e9,
        capex=4.0e9,
        ebit=3.0e9,
        ebitda=5.5e9,
        roe=20.0,
        operating_margin=15.0,
        tax_rate=25.0,
        growth_rate=8.0,
        revenue_growth=7.0,
        earnings_growth=9.0,
        dividend_per_share=0.8,
        dividend_yield=3.0,
        dividend_growth_rate=5.0,
        cost_of_capital=10.0,
        discount_rate=10.0,
        terminal_growth=2.0,
        growth_rate_1_5=8.0,
        growth_rate_6_10=4.0,
        extra={
            "revenue_cagr_5y": 6.5,
            "earnings_cagr_5y": 8.0,
        },
    )


@pytest.fixture
def growth_stock():
    """A high-growth company."""
    return Stock(
        ticker="300750",
        name="宁德时代",
        current_price=180.0,
        shares_outstanding=2.4e9,
        eps=4.5,
        bvps=25.0,
        revenue=400.0e9,
        net_income=44.0e9,
        fcf=30.0e9,
        net_debt=50.0e9,
        roe=22.0,
        growth_rate=25.0,
        revenue_growth=30.0,
        earnings_growth=20.0,
        dividend_per_share=0.5,
        dividend_yield=0.3,
        cost_of_capital=10.0,
        discount_rate=10.0,
        terminal_growth=2.0,
        growth_rate_1_5=20.0,
        growth_rate_6_10=10.0,
        extra={
            "revenue_cagr_5y": 35.0,
            "earnings_cagr_5y": 30.0,
        },
    )


@pytest.fixture
def minimal_stock():
    """Stock with minimal data."""
    return Stock(
        ticker="MINIMAL",
        name="最少数据",
        current_price=50.0,
        shares_outstanding=100e6,
        eps=2.0,
        discount_rate=10.0,
        terminal_growth=2.0,
    )


# ---------------------------------------------------------------------------
# TestImpliedGrowthDetail
# ---------------------------------------------------------------------------

class TestImpliedGrowthDetail:
    """Tests for ImpliedGrowthDetail data class."""

    def test_creation_with_defaults(self):
        """Test creation with required fields and default notes."""
        detail = ImpliedGrowthDetail(
            method="Reverse DCF",
            implied_growth_rate=5.5,
            confidence="High",
            assumptions={"fcf": 1e9},
        )
        assert detail.method == "Reverse DCF"
        assert detail.implied_growth_rate == 5.5
        assert detail.confidence == "High"
        assert detail.assumptions == {"fcf": 1e9}
        assert detail.notes == []  # default factory

    def test_to_dict_if_exists(self):
        """Test that ImpliedGrowthDetail can be converted to dict-like access."""
        detail = ImpliedGrowthDetail(
            method="PEG Implied",
            implied_growth_rate=12.0,
            confidence="Medium",
            assumptions={"pe_ratio": 12.0},
            notes=["Note 1", "Note 2"],
        )
        # Verify all attributes are accessible
        assert detail.method == "PEG Implied"
        assert detail.implied_growth_rate == 12.0
        assert detail.confidence == "Medium"
        assert len(detail.notes) == 2
        # Verify to_summary works
        summary = detail.to_summary()
        assert "PEG Implied" in summary
        assert "12.00%" in summary
        assert "Medium" in summary
        assert "Note 1" in summary


# ---------------------------------------------------------------------------
# TestGrowthComparison
# ---------------------------------------------------------------------------

class TestGrowthComparison:
    """Tests for GrowthComparison verdict logic."""

    def test_conservative_verdict(self):
        """Implied growth close to or below historical should be Conservative."""
        stock = Stock(
            ticker="TEST",
            name="Test",
            current_price=10.0,
            earnings_growth=8.0,
            revenue_growth=7.0,
            extra={"earnings_cagr_5y": 8.0, "revenue_cagr_5y": 7.0},
        )
        # implied_growth = 6.0, benchmark = earnings_cagr_5y = 8.0
        # gap = 6.0 - 8.0 = -2.0 <= 2 => Conservative
        comparison = compare_with_historical(stock, 6.0)
        assert comparison.verdict == "Conservative"

    def test_moderate_verdict(self):
        """Implied slightly above historical 5y CAGR should be Moderate."""
        stock = Stock(
            ticker="TEST",
            name="Test",
            current_price=10.0,
            earnings_growth=8.0,
            revenue_growth=7.0,
            extra={"earnings_cagr_5y": 8.0, "revenue_cagr_5y": 7.0},
        )
        # implied_growth = 11.0, benchmark = earnings_cagr_5y = 8.0
        # gap = 11.0 - 8.0 = 3.0 > 2 => Moderate
        comparison = compare_with_historical(stock, 11.0)
        assert comparison.verdict == "Moderate"

    def test_aggressive_verdict(self):
        """Implied well above historical should be Aggressive."""
        stock = Stock(
            ticker="TEST",
            name="Test",
            current_price=10.0,
            earnings_growth=8.0,
            revenue_growth=7.0,
            extra={"earnings_cagr_5y": 8.0, "revenue_cagr_5y": 7.0},
        )
        # implied_growth = 15.0, benchmark = earnings_cagr_5y = 8.0
        # gap = 15.0 - 8.0 = 7.0 > 5 => Aggressive
        comparison = compare_with_historical(stock, 15.0)
        assert comparison.verdict == "Aggressive"

    def test_extremely_aggressive_verdict(self):
        """Implied far above historical should be Extremely Aggressive."""
        stock = Stock(
            ticker="TEST",
            name="Test",
            current_price=10.0,
            earnings_growth=8.0,
            revenue_growth=7.0,
            extra={"earnings_cagr_5y": 8.0, "revenue_cagr_5y": 7.0},
        )
        # implied_growth = 25.0, benchmark = earnings_cagr_5y = 8.0
        # gap = 25.0 - 8.0 = 17.0 > 10 => Extremely Aggressive
        comparison = compare_with_historical(stock, 25.0)
        assert comparison.verdict == "Extremely Aggressive"

    def test_missing_historical_data(self):
        """When all historical data is 0, verdict should be based on implied growth level."""
        stock = Stock(
            ticker="TEST",
            name="Test",
            current_price=10.0,
        )
        # implied_growth = 5.0, all historical = 0
        # No historical benchmark => implied_growth <= 10 => Conservative
        comparison = compare_with_historical(stock, 5.0)
        assert comparison.verdict == "Conservative"

        # implied_growth = 15.0, all historical = 0
        # No historical benchmark => 10 < implied_growth <= 20 => Moderate
        comparison2 = compare_with_historical(stock, 15.0)
        assert comparison2.verdict == "Moderate"

        # implied_growth = 25.0, all historical = 0
        # No historical benchmark => implied_growth > 20 => Aggressive
        comparison3 = compare_with_historical(stock, 25.0)
        assert comparison3.verdict == "Aggressive"


# ---------------------------------------------------------------------------
# TestGrowthReasonableness
# ---------------------------------------------------------------------------

class TestGrowthReasonableness:
    """Tests for GrowthReasonableness scoring and flag logic."""

    def _make_comparison(self, verdict, earnings_cagr_5y=8.0, revenue_cagr_5y=7.0):
        """Helper to build a GrowthComparison with specific verdict."""
        return GrowthComparison(
            implied_growth=5.0,
            historical_revenue_growth=7.0,
            historical_earnings_growth=8.0,
            historical_revenue_cagr_5y=revenue_cagr_5y,
            historical_earnings_cagr_5y=earnings_cagr_5y,
            gap_revenue=-2.0,
            gap_earnings=-3.0,
            gap_revenue_cagr_5y=-2.0,
            gap_earnings_cagr_5y=-3.0,
            verdict=verdict,
        )

    def test_reasonable_rating(self):
        """Low implied growth with conservative verdict should be Reasonable."""
        stock = Stock(
            ticker="TEST",
            name="Test",
            current_price=10.0,
            roe=20.0,
            fcf=5.0e9,
        )
        comparison = self._make_comparison("Conservative")
        result = assess_reasonableness(stock, 3.0, comparison)
        assert result.rating == "Reasonable"
        assert result.score >= 70

    def test_optimistic_rating(self):
        """High implied growth with aggressive verdict should be Optimistic or lower."""
        stock = Stock(
            ticker="TEST",
            name="Test",
            current_price=10.0,
            roe=10.0,
            fcf=1.0e9,
        )
        comparison = self._make_comparison("Aggressive")
        result = assess_reasonableness(stock, 28.0, comparison)
        assert result.rating in ("Optimistic", "Very Optimistic", "Unreasonable")
        assert result.score < 50

    def test_red_flags_generated(self):
        """High growth triggers red flags."""
        stock = Stock(
            ticker="TEST",
            name="Test",
            current_price=10.0,
            roe=15.0,
            fcf=2.0e9,
        )
        # implied_growth = 35.0, earnings_cagr_5y = 8.0 => 35 > 2*8 = 16
        comparison = GrowthComparison(
            implied_growth=35.0,
            historical_revenue_growth=7.0,
            historical_earnings_growth=8.0,
            historical_revenue_cagr_5y=7.0,
            historical_earnings_cagr_5y=8.0,
            gap_revenue=28.0,
            gap_earnings=27.0,
            gap_revenue_cagr_5y=28.0,
            gap_earnings_cagr_5y=27.0,
            verdict="Extremely Aggressive",
        )
        result = assess_reasonableness(stock, 35.0, comparison)
        assert len(result.red_flags) > 0
        # Should flag > 25% growth
        assert any("25%" in f for f in result.red_flags)

    def test_green_flags_generated(self):
        """Strong fundamentals trigger green flags."""
        stock = Stock(
            ticker="TEST",
            name="Test",
            current_price=10.0,
            roe=20.0,
            fcf=5.0e9,
        )
        # implied_growth = 5.0, earnings_cagr_5y = 8.0 => 5 < 8
        comparison = GrowthComparison(
            implied_growth=5.0,
            historical_revenue_growth=7.0,
            historical_earnings_growth=8.0,
            historical_revenue_cagr_5y=7.0,
            historical_earnings_cagr_5y=8.0,
            gap_revenue=-2.0,
            gap_earnings=-3.0,
            gap_revenue_cagr_5y=-2.0,
            gap_earnings_cagr_5y=-3.0,
            verdict="Conservative",
        )
        result = assess_reasonableness(stock, 5.0, comparison)
        assert len(result.green_flags) > 0
        # Should have positive FCF green flag
        assert any("Positive free cash flow" in f for f in result.green_flags)
        # Should have ROE green flag since roe=20 > 15
        assert any("ROE" in f for f in result.green_flags)

    def test_score_clamped_to_range(self):
        """Score should always be between 0 and 100."""
        stock = Stock(
            ticker="TEST",
            name="Test",
            current_price=10.0,
            roe=50.0,
            fcf=10.0e9,
        )
        comparison = self._make_comparison("Conservative")
        result = assess_reasonableness(stock, 1.0, comparison)
        assert 0 <= result.score <= 100


# ---------------------------------------------------------------------------
# TestReverseDCFImpliedGrowth
# ---------------------------------------------------------------------------

class TestReverseDCFImpliedGrowth:
    """Tests for reverse DCF implied growth calculation."""

    def test_normal_calculation(self, healthy_stock):
        """Healthy company with positive FCF should produce a result."""
        result = calculate_reverse_dcf_implied_growth(healthy_stock)
        assert result is not None
        assert result.method == "Reverse DCF"
        assert isinstance(result.implied_growth_rate, float)
        assert isinstance(result.confidence, str)
        assert "fcf" in result.assumptions

    def test_negative_fcf_returns_error(self):
        """Company with negative/zero FCF should return None."""
        stock = Stock(
            ticker="LOSS",
            name="亏损公司",
            current_price=10.0,
            shares_outstanding=100e6,
            fcf=-5.0e9,
            discount_rate=10.0,
            terminal_growth=2.0,
        )
        result = calculate_reverse_dcf_implied_growth(stock)
        assert result is None

        # Also test zero FCF
        stock2 = Stock(
            ticker="ZERO",
            name="零FCF",
            current_price=10.0,
            shares_outstanding=100e6,
            fcf=0,
            discount_rate=10.0,
            terminal_growth=2.0,
        )
        result2 = calculate_reverse_dcf_implied_growth(stock2)
        assert result2 is None

    def test_convergence(self, healthy_stock):
        """Verify the calculation converges to a stable result."""
        result = calculate_reverse_dcf_implied_growth(healthy_stock)
        assert result is not None
        # Confidence should be at least Medium for a reasonable company
        assert result.confidence in ("High", "Medium", "Low")
        # Implied growth should be a reasonable number
        assert -10 <= result.implied_growth_rate <= 100


# ---------------------------------------------------------------------------
# TestPEGImpliedGrowth
# ---------------------------------------------------------------------------

class TestPEGImpliedGrowth:
    """Tests for PEG implied growth calculation."""

    def test_normal_calculation(self, healthy_stock):
        """Company with positive PE and growth should produce a result."""
        result = calculate_peg_implied_growth(healthy_stock)
        assert result is not None
        assert result.method == "PEG Implied"
        # PE = 26.0 / 1.65 = 15.76
        # implied_growth = 15.76 / 1.0 = 15.76
        expected_growth = healthy_stock.pe_ratio / 1.0
        assert abs(result.implied_growth_rate - round(expected_growth, 2)) < 0.1

    def test_zero_pe_skipped(self):
        """Company with zero PE (zero EPS) should return None."""
        stock = Stock(
            ticker="NOEPS",
            name="无盈利",
            current_price=10.0,
            shares_outstanding=100e6,
            eps=0,  # zero EPS => PE = 0
        )
        result = calculate_peg_implied_growth(stock)
        assert result is None


# ---------------------------------------------------------------------------
# TestGordonGrowthImpliedGrowth
# ---------------------------------------------------------------------------

class TestGordonGrowthImpliedGrowth:
    """Tests for Gordon Growth Model implied growth calculation."""

    def test_dividend_stock(self, healthy_stock):
        """Company with dividends should produce a result."""
        result = calculate_gordon_growth_implied_growth(healthy_stock)
        assert result is not None
        assert result.method == "Gordon Growth"
        # g = r - D1/P = 0.10 - (0.8 * 1.05) / 26.0
        d1 = healthy_stock.dividend_per_share * (1 + healthy_stock.dividend_growth_rate / 100)
        expected_growth = (healthy_stock.discount_rate / 100 - d1 / healthy_stock.current_price) * 100
        assert abs(result.implied_growth_rate - round(expected_growth, 2)) < 0.1

    def test_no_dividend_skipped(self):
        """Company without dividends should return None."""
        stock = Stock(
            ticker="NODIV",
            name="无分红",
            current_price=10.0,
            shares_outstanding=100e6,
            eps=2.0,
            dividend_per_share=0,
            discount_rate=10.0,
            terminal_growth=2.0,
        )
        result = calculate_gordon_growth_implied_growth(stock)
        assert result is None


# ---------------------------------------------------------------------------
# TestEarningsYieldImpliedGrowth
# ---------------------------------------------------------------------------

class TestEarningsYieldImpliedGrowth:
    """Tests for earnings yield implied growth calculation."""

    def test_normal_calculation(self, healthy_stock):
        """Company with positive EPS should produce a result."""
        result = calculate_earnings_yield_implied_growth(healthy_stock)
        assert result is not None
        assert result.method == "Earnings Yield"
        # g = r - 1/PE = 0.10 - 1/(26/1.65) = 0.10 - 0.0635 = 0.0365 = 3.65%
        expected_growth = (healthy_stock.discount_rate / 100 - 1.0 / healthy_stock.pe_ratio) * 100
        assert abs(result.implied_growth_rate - round(expected_growth, 2)) < 0.1

    def test_zero_eps_skipped(self):
        """Company with zero EPS should return None (PE = 0)."""
        stock = Stock(
            ticker="NOEPS",
            name="无盈利",
            current_price=10.0,
            shares_outstanding=100e6,
            eps=0,
            discount_rate=10.0,
            terminal_growth=2.0,
        )
        result = calculate_earnings_yield_implied_growth(stock)
        assert result is None


# ---------------------------------------------------------------------------
# TestCompareWithHistorical
# ---------------------------------------------------------------------------

class TestCompareWithHistorical:
    """Tests for compare_with_historical function."""

    def test_with_full_historical_data(self, healthy_stock):
        """All historical fields populated should use earnings CAGR 5Y as benchmark."""
        comparison = compare_with_historical(healthy_stock, 10.0)
        assert comparison.historical_revenue_growth == 7.0
        assert comparison.historical_earnings_growth == 9.0
        assert comparison.historical_revenue_cagr_5y == 6.5
        assert comparison.historical_earnings_cagr_5y == 8.0
        # gap calculations
        assert comparison.gap_revenue == 10.0 - 7.0
        assert comparison.gap_earnings == 10.0 - 9.0
        assert comparison.gap_revenue_cagr_5y == 10.0 - 6.5
        assert comparison.gap_earnings_cagr_5y == 10.0 - 8.0

    def test_with_minimal_data(self):
        """Only basic growth rate available."""
        stock = Stock(
            ticker="MIN",
            name="Minimal",
            current_price=10.0,
            earnings_growth=5.0,
            revenue_growth=3.0,
        )
        comparison = compare_with_historical(stock, 8.0)
        assert comparison.historical_revenue_growth == 3.0
        assert comparison.historical_earnings_growth == 5.0
        assert comparison.historical_revenue_cagr_5y == 0.0
        assert comparison.historical_earnings_cagr_5y == 0.0
        # Benchmark should be earnings_growth = 5.0 (first non-zero fallback)
        # gap = 8.0 - 5.0 = 3.0 > 2 => Moderate
        assert comparison.verdict == "Moderate"

    def test_verdict_logic(self):
        """Verify boundary conditions for verdict thresholds."""
        stock = Stock(
            ticker="TEST",
            name="Test",
            current_price=10.0,
            extra={"earnings_cagr_5y": 10.0},
        )

        # gap = 0 => Conservative (gap <= 2)
        c1 = compare_with_historical(stock, 10.0)
        assert c1.verdict == "Conservative"

        # gap = 2.0 => Conservative (gap <= 2)
        c2 = compare_with_historical(stock, 12.0)
        assert c2.verdict == "Conservative"

        # gap = 2.01 => Moderate (2 < gap <= 5)
        c3 = compare_with_historical(stock, 12.01)
        assert c3.verdict == "Moderate"

        # gap = 5.0 => Moderate (2 < gap <= 5)
        c4 = compare_with_historical(stock, 15.0)
        assert c4.verdict == "Moderate"

        # gap = 5.01 => Aggressive (5 < gap <= 10)
        c5 = compare_with_historical(stock, 15.01)
        assert c5.verdict == "Aggressive"

        # gap = 10.0 => Aggressive (5 < gap <= 10)
        c6 = compare_with_historical(stock, 20.0)
        assert c6.verdict == "Aggressive"

        # gap = 10.01 => Extremely Aggressive (gap > 10)
        c7 = compare_with_historical(stock, 20.01)
        assert c7.verdict == "Extremely Aggressive"


# ---------------------------------------------------------------------------
# TestImpliedGrowthEngine
# ---------------------------------------------------------------------------

class TestImpliedGrowthEngine:
    """Tests for the main ImpliedGrowthEngine."""

    def test_full_analysis_healthy_company(self, healthy_stock):
        """Comprehensive test with a well-populated Stock (600887 伊利股份 style)."""
        engine = ImpliedGrowthEngine()
        result = engine.analyze(healthy_stock)

        assert isinstance(result, ImpliedGrowthResult)
        assert result.ticker == "600887"
        assert result.name == "伊利股份"
        assert result.current_price == 26.0
        assert result.weighted_implied_growth > 0
        assert len(result.details) > 0

        # Should have multiple methods applicable
        method_names = [d.method for d in result.details]
        assert "Reverse DCF" in method_names
        assert "PEG Implied" in method_names
        assert "Gordon Growth" in method_names
        assert "Earnings Yield" in method_names

        # Comparison should have verdict
        assert result.comparison.verdict in ("Conservative", "Moderate", "Aggressive", "Extremely Aggressive")

        # Reasonableness should have score
        assert 0 <= result.reasonableness.score <= 100
        assert result.reasonableness.rating in ("Reasonable", "Somewhat Optimistic", "Optimistic", "Very Optimistic", "Unreasonable")

        # Analysis should have content
        assert len(result.analysis) > 0

        # to_summary should work
        summary = result.to_summary()
        assert "600887" in summary
        assert "伊利股份" in summary

        # __str__ should work
        s = str(result)
        assert "600887" in s

    def test_minimal_data_company(self, minimal_stock):
        """Stock with only essential fields should still produce a result."""
        engine = ImpliedGrowthEngine()
        result = engine.analyze(minimal_stock)

        assert isinstance(result, ImpliedGrowthResult)
        assert result.ticker == "MINIMAL"
        assert result.current_price == 50.0

        # With only eps=2.0, only PEG and Earnings Yield should work
        # (no FCF for reverse DCF, no dividend for Gordon Growth)
        method_names = [d.method for d in result.details]
        assert "PEG Implied" in method_names
        assert "Earnings Yield" in method_names
        # Should NOT have Reverse DCF (no FCF) or Gordon Growth (no dividend)
        assert "Reverse DCF" not in method_names
        assert "Gordon Growth" not in method_names

        # Warnings should mention missing data
        assert any("FCF" in w for w in result.warnings)
        assert any("dividend" in w.lower() or "Gordon" in w for w in result.warnings)

    def test_convenience_function(self, healthy_stock):
        """Test the analyze_implied_growth() convenience function from __init__.py."""
        result = analyze_implied_growth(healthy_stock)

        assert isinstance(result, ImpliedGrowthResult)
        assert result.ticker == "600887"
        assert result.name == "伊利股份"
        assert result.weighted_implied_growth > 0
        assert len(result.details) > 0

        # Should produce same result as engine
        engine = ImpliedGrowthEngine()
        engine_result = engine.analyze(healthy_stock)
        assert result.weighted_implied_growth == engine_result.weighted_implied_growth
        assert result.comparison.verdict == engine_result.comparison.verdict
