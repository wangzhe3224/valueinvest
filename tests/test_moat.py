"""Tests for the Economic Moat analysis module."""

import pytest
from valueinvest.stock import Stock
from valueinvest.moat import analyze_moat, MoatAnalysisEngine, MoatType, MoatSignalCategory
from valueinvest.moat.signals import (
    roic_signal, margin_stability_signal, operating_margin_signal,
    fcf_conversion_signal, asset_turnover_signal, revenue_stability_signal,
    earnings_stability_signal, pricing_power_signal, scale_signal,
    debt_safety_signal, interest_coverage_signal,
)


@pytest.fixture
def wide_moat_stock():
    """Company with strong moat: high ROIC, high margins, low debt."""
    return Stock(
        ticker="WIDEMOAT",
        name="Wide Moat Co",
        current_price=150.0,
        shares_outstanding=1_000_000_000,
        eps=10.0,
        bvps=60.0,
        revenue=80_000_000_000,
        net_income=12_000_000_000,
        fcf=15_000_000_000,
        ebit=18_000_000_000,
        operating_margin=22.5,
        tax_rate=25.0,
        roe=25.0,
        total_assets=100_000_000_000,
        total_liabilities=25_000_000_000,
        short_term_debt=3_000_000_000,
        long_term_debt=7_000_000_000,
        interest_expense=500_000_000,
        net_working_capital=20_000_000_000,
        net_fixed_assets=55_000_000_000,
        cost_of_capital=10.0,
        growth_rate=12.0,
        prior_gross_margin=43.0,
        extra={
            "_gross_margin": 45.0,
            "_asset_turnover": 0.8,
            "revenue_cagr_5y": 12.0,
            "earnings_cagr_5y": 15.0,
        },
    )


@pytest.fixture
def no_moat_stock():
    """Company with weak moat: low margins, high debt, no growth."""
    return Stock(
        ticker="NOMOAT",
        name="No Moat Co",
        current_price=20.0,
        shares_outstanding=500_000_000,
        eps=0.5,
        bvps=10.0,
        revenue=20_000_000_000,
        net_income=250_000_000,
        fcf=50_000_000,
        ebit=400_000_000,
        operating_margin=2.0,
        tax_rate=25.0,
        roe=5.0,
        total_assets=30_000_000_000,
        total_liabilities=22_000_000_000,
        short_term_debt=8_000_000_000,
        long_term_debt=10_000_000_000,
        interest_expense=1_200_000_000,
        net_working_capital=3_000_000_000,
        net_fixed_assets=5_000_000_000,
        cost_of_capital=10.0,
        growth_rate=2.0,
        prior_gross_margin=8.0,
        extra={
            "_gross_margin": 6.0,
            "_asset_turnover": 0.67,
        },
    )


@pytest.fixture
def partial_data_stock():
    """Stock with minimal data -- many signals should be unavailable."""
    return Stock(
        ticker="PARTIAL",
        name="Partial Data Co",
        current_price=50.0,
        shares_outstanding=100_000_000,
        eps=2.0,
        revenue=5_000_000_000,
        net_income=200_000_000,
    )


class TestWideMoatStock:
    """Tests for a company with strong moat indicators."""

    def test_wide_moat_high_score(self, wide_moat_stock):
        """Wide moat stock should get composite score > 50."""
        result = analyze_moat(wide_moat_stock)
        assert result.moat_score > 50

    def test_wide_moat_type(self, wide_moat_stock):
        """Wide moat stock should have WIDE or VERY_WIDE moat type."""
        result = analyze_moat(wide_moat_stock)
        assert result.moat_type in (MoatType.WIDE, MoatType.VERY_WIDE)

    def test_has_moat_property(self, wide_moat_stock):
        """has_moat should be True for wide moat stock."""
        result = analyze_moat(wide_moat_stock)
        assert result.has_moat is True

    def test_profitability_score(self, wide_moat_stock):
        """Profitability sub-score should be high."""
        result = analyze_moat(wide_moat_stock)
        assert result.profitability_score > 60

    def test_financial_fortress_score(self, wide_moat_stock):
        """Financial fortress should be strong due to low debt."""
        result = analyze_moat(wide_moat_stock)
        assert result.financial_fortress_score > 70

    def test_growth_score(self, wide_moat_stock):
        """Growth score should be high with 12-15% CAGR."""
        result = analyze_moat(wide_moat_stock)
        assert result.growth_score > 70

    def test_strengths_populated(self, wide_moat_stock):
        """Wide moat stock should have identified strengths."""
        result = analyze_moat(wide_moat_stock)
        assert len(result.strengths) >= 3


class TestNoMoatStock:
    """Tests for a company with weak moat indicators."""

    def test_no_moat_low_score(self, no_moat_stock):
        """No moat stock should get composite score < 40."""
        result = analyze_moat(no_moat_stock)
        assert result.moat_score < 40

    def test_no_moat_type(self, no_moat_stock):
        """No moat stock should have NONE or NARROW moat type."""
        result = analyze_moat(no_moat_stock)
        assert result.moat_type in (MoatType.NONE, MoatType.NARROW)

    def test_no_moat_has_moat_false(self, no_moat_stock):
        """has_moat should be False for NONE moat type."""
        result = analyze_moat(no_moat_stock)
        if result.moat_type == MoatType.NONE:
            assert result.has_moat is False

    def test_weaknesses_populated(self, no_moat_stock):
        """No moat stock should have identified weaknesses."""
        result = analyze_moat(no_moat_stock)
        assert len(result.weaknesses) >= 2

    def test_low_profitability_score(self, no_moat_stock):
        """Profitability should be low for no-moat company."""
        result = analyze_moat(no_moat_stock)
        assert result.profitability_score < 30

    def test_low_financial_fortress_score(self, no_moat_stock):
        """Financial fortress should be low due to high debt."""
        result = analyze_moat(no_moat_stock)
        assert result.financial_fortress_score < 20


class TestPartialDataStock:
    """Tests for a stock with minimal data."""

    def test_unavailable_signals(self, partial_data_stock):
        """Partial data stock should have some unavailable signals."""
        result = analyze_moat(partial_data_stock)
        unavailable = [s for s in result.signals if not s.is_available]
        assert len(unavailable) > 0

    def test_available_signal_count_less_than_total(self, partial_data_stock):
        """Available signals should be fewer than total signals."""
        result = analyze_moat(partial_data_stock)
        assert result.available_signal_count < result.total_signal_count


class TestSignalComputation:
    """Tests for individual signal computation."""

    def test_all_signals_computed(self, wide_moat_stock):
        """Engine should produce exactly 11 signals."""
        result = analyze_moat(wide_moat_stock)
        assert result.total_signal_count == 11

    def test_category_sub_scores_range(self, wide_moat_stock):
        """All category sub-scores should be in 0-100 range."""
        result = analyze_moat(wide_moat_stock)
        for attr in (
            "profitability_score", "efficiency_score", "growth_score",
            "market_position_score", "financial_fortress_score",
        ):
            score = getattr(result, attr)
            assert 0 <= score <= 100, f"{attr} = {score} out of range"

    def test_moat_score_range(self, wide_moat_stock, no_moat_stock):
        """Moat score should always be in 0-100 range."""
        for stock in (wide_moat_stock, no_moat_stock):
            result = analyze_moat(stock)
            assert 0 <= result.moat_score <= 100

    def test_individual_signal_scores_range(self, wide_moat_stock):
        """Individual signal scores should be in 0-100 range."""
        result = analyze_moat(wide_moat_stock)
        for sig in result.signals:
            assert 0 <= sig.score <= 100, f"{sig.name} score = {sig.score}"


class TestScaleSignal:
    """Tests for the scale signal (always unavailable placeholder)."""

    def test_scale_signal_always_unavailable(self, wide_moat_stock):
        """Scale signal should always be unavailable (placeholder)."""
        sig = scale_signal(wide_moat_stock)
        assert sig.is_available is False
        assert sig.score == 0
        assert sig.name == "Scale Advantage"

    def test_scale_signal_in_result(self, wide_moat_stock):
        """Scale signal should appear in full result as unavailable."""
        result = analyze_moat(wide_moat_stock)
        scale_sigs = [s for s in result.signals if s.name == "Scale Advantage"]
        assert len(scale_sigs) == 1
        assert scale_sigs[0].is_available is False


class TestMarginStabilityNoPrior:
    """Tests for margin stability without prior gross margin."""

    def test_margin_stability_no_prior_data(self, partial_data_stock):
        """Stock with prior_gross_margin=0 and no gross margin should be unavailable."""
        sig = margin_stability_signal(partial_data_stock)
        # partial_data_stock has no _gross_margin in extra, so gross_margin=0
        assert sig.is_available is False

    def test_margin_stability_with_engine_override(self, wide_moat_stock):
        """Engine prior_gross_margin override should be used by margin_stability_signal."""
        engine = MoatAnalysisEngine(prior_gross_margin=40.0)
        result = engine.analyze(wide_moat_stock)
        margin_sigs = [s for s in result.signals if s.name == "Margin Stability"]
        assert len(margin_sigs) == 1
        assert margin_sigs[0].is_available is True
        # gm=45, prior=40, change=5 -> improving -> +5 -> score=85
        assert margin_sigs[0].score == 85


class TestROICSignal:
    """Tests for ROIC signal with explicit parameters."""

    def test_roic_signal_with_explicit_params(self, wide_moat_stock):
        """ROIC signal with explicit roic/wacc should use provided values."""
        sig = roic_signal(wide_moat_stock, roic=20.0, wacc=8.0)
        assert sig.is_available is True
        assert sig.score == 90  # spread=12 > 10
        assert sig.value == pytest.approx(12.0)

    def test_roic_signal_negative_spread(self, wide_moat_stock):
        """ROIC signal with negative spread should score low."""
        sig = roic_signal(wide_moat_stock, roic=5.0, wacc=12.0)
        assert sig.is_available is True
        assert sig.score == 10  # spread=-7 < -2

    def test_roic_signal_computed_from_stock(self, wide_moat_stock):
        """ROIC signal computed from stock fields when no explicit params."""
        sig = roic_signal(wide_moat_stock)
        assert sig.is_available is True
        # nopat=18B*0.75=13.5B, ic=75B, roic=18%, spread=8.0 > 5 -> score=70
        assert sig.score == 70


class TestOutputFormatting:
    """Tests for string output and summary."""

    def test_to_summary_format(self, wide_moat_stock):
        """to_summary() should contain ticker, score, type, and signal counts."""
        result = analyze_moat(wide_moat_stock)
        summary = result.to_summary()
        assert "WIDEMOAT" in summary
        assert "Moat(" in summary
        assert "/100" in summary
        assert result.moat_type.value.upper() in summary

    def test_str_output_multiline(self, wide_moat_stock):
        """__str__() should produce multi-line output."""
        result = analyze_moat(wide_moat_stock)
        output = str(result)
        lines = output.strip().split("\n")
        assert len(lines) > 3

    def test_str_contains_category_scores(self, wide_moat_stock):
        """__str__() should contain category score lines."""
        result = analyze_moat(wide_moat_stock)
        output = str(result)
        assert "Profitability:" in output
        assert "Efficiency:" in output
        assert "Growth:" in output
        assert "Market Position:" in output
        assert "Financial Fortress:" in output

    def test_str_contains_signal_details(self, wide_moat_stock):
        """__str__() should contain individual signal lines."""
        result = analyze_moat(wide_moat_stock)
        output = str(result)
        assert "ROIC vs WACC" in output
        assert "FCF Conversion" in output


class TestConvenienceFunction:
    """Tests for the analyze_moat convenience function."""

    def test_analyze_moat_returns_result(self, wide_moat_stock):
        """analyze_moat should return MoatResult instance."""
        result = analyze_moat(wide_moat_stock)
        assert hasattr(result, "moat_type")
        assert hasattr(result, "moat_score")
        assert hasattr(result, "signals")

    def test_analyze_moat_passes_kwargs(self, wide_moat_stock):
        """analyze_moat should forward kwargs to engine."""
        result = analyze_moat(wide_moat_stock, roic=25.0, wacc=8.0)
        roic_sigs = [s for s in result.signals if s.name == "ROIC vs WACC"]
        assert len(roic_sigs) == 1
        # spread=17 > 10 -> score=90
        assert roic_sigs[0].score == 90


class TestCustomWeights:
    """Tests for custom category weights."""

    def test_custom_weights_affect_composite(self, wide_moat_stock):
        """Custom weights should change the composite score."""
        result_default = analyze_moat(wide_moat_stock)

        # Maximize profitability weight
        result_weighted = analyze_moat(
            wide_moat_stock,
            category_weights={"profitability": 1.0, "efficiency": 0.0, "growth": 0.0,
                              "market_position": 0.0, "financial_fortress": 0.0},
        )

        # With 100% profitability weight, score should equal profitability_score
        assert result_weighted.moat_score == pytest.approx(
            result_weighted.profitability_score, abs=0.1
        )
        # Should differ from default composite
        assert result_weighted.moat_score != pytest.approx(result_default.moat_score, abs=0.1)


class TestStrengthsAndWeaknesses:
    """Tests for evidence collection."""

    def test_wide_moat_has_strengths(self, wide_moat_stock):
        """Wide moat stock should have more strengths than weaknesses."""
        result = analyze_moat(wide_moat_stock)
        assert len(result.strengths) > len(result.weaknesses)

    def test_no_moat_has_weaknesses(self, no_moat_stock):
        """No moat stock should have more weaknesses than strengths."""
        result = analyze_moat(no_moat_stock)
        assert len(result.weaknesses) > len(result.strengths)

    def test_strengths_threshold(self, wide_moat_stock):
        """Strengths should only include signals with score >= 65."""
        result = analyze_moat(wide_moat_stock)
        for sig in result.signals:
            if sig.description in result.strengths:
                assert sig.score >= 65

    def test_weaknesses_threshold(self, no_moat_stock):
        """Weaknesses should only include signals with score <= 30."""
        result = analyze_moat(no_moat_stock)
        for sig in result.signals:
            if sig.description in result.weaknesses:
                assert sig.score <= 30

    def test_warnings_for_unavailable(self, partial_data_stock):
        """Warnings should list unavailable signals."""
        result = analyze_moat(partial_data_stock)
        assert len(result.warnings) > 0


class TestAnalysisOutput:
    """Tests for analysis text generation."""

    def test_analysis_contains_ticker(self, wide_moat_stock):
        """Analysis text should include the ticker."""
        result = analyze_moat(wide_moat_stock)
        assert any("WIDEMOAT" in line for line in result.analysis)

    def test_analysis_contains_moat_type(self, wide_moat_stock):
        """Analysis text should include the moat type."""
        result = analyze_moat(wide_moat_stock)
        assert any(result.moat_type.value.upper() in line for line in result.analysis)

    def test_analysis_not_empty(self, wide_moat_stock, no_moat_stock):
        """Analysis should have at least 2 lines for any stock."""
        for stock in (wide_moat_stock, no_moat_stock):
            result = analyze_moat(stock)
            assert len(result.analysis) >= 2


class TestEdgeCases:
    """Edge case tests."""

    def test_engine_default_construction(self):
        """Engine should construct with all defaults."""
        engine = MoatAnalysisEngine()
        assert engine.roic is None
        assert engine.wacc is None
        assert engine.category_weights is None

    def test_repr_returns_summary(self, wide_moat_stock):
        """__repr__ should return the same as to_summary()."""
        result = analyze_moat(wide_moat_stock)
        assert repr(result) == result.to_summary()

    def test_fcf_conversion_negative_income(self, partial_data_stock):
        """FCF conversion should be unavailable for negative net income."""
        stock = Stock(
            ticker="LOSS",
            name="Loss Co",
            revenue=5_000_000_000,
            net_income=-100_000_000,
        )
        sig = fcf_conversion_signal(stock)
        assert sig.is_available is False

    def test_interest_coverage_no_debt(self, wide_moat_stock):
        """Interest coverage should be unavailable when interest_expense=0."""
        stock = Stock(
            ticker="NODEBT",
            name="No Debt Co",
            ebit=10_000_000_000,
            interest_expense=0,
        )
        sig = interest_coverage_signal(stock)
        assert sig.is_available is False

    def test_operating_margin_zero(self, partial_data_stock):
        """Operating margin should be unavailable when operating_margin=0."""
        sig = operating_margin_signal(partial_data_stock)
        assert sig.is_available is False
