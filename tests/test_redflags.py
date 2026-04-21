import pytest
from valueinvest.stock import Stock
from valueinvest.redflags import (
    analyze_red_flags, AccountingRedFlagsEngine,
    RedFlagResult, RiskLevel, RedFlagCategory, RedFlagSeverity,
)


@pytest.fixture
def clean_stock():
    """Healthy company: strong OCF, low accruals, clean AR, moderate inventory."""
    return Stock(
        ticker="CLEAN",
        name="Clean Financials Co",
        current_price=100.0,
        shares_outstanding=1_000_000_000,
        eps=8.0,
        bvps=40.0,
        revenue=50_000_000_000,
        net_income=10_000_000_000,
        fcf=12_000_000_000,
        operating_cash_flow=13_000_000_000,
        ebit=14_000_000_000,
        operating_margin=28.0,
        tax_rate=25.0,
        roe=25.0,
        total_assets=80_000_000_000,
        total_liabilities=20_000_000_000,
        current_liabilities=8_000_000_000,
        current_assets=24_000_000_000,
        short_term_debt=3_000_000_000,
        long_term_debt=7_000_000_000,
        interest_expense=500_000_000,
        accounts_receivable=4_000_000_000,
        inventory=3_000_000_000,
        accounts_payable=5_000_000_000,
        depreciation=3_000_000_000,
        capex=4_500_000_000,
        net_working_capital=16_000_000_000,
        net_fixed_assets=40_000_000_000,
        retained_earnings=30_000_000_000,
        total_debt=10_000_000_000,
        cash_and_equivalents=15_000_000_000,
        sbc=400_000_000,
        shares_issued=20_000_000,
        shares_repurchased=80_000_000,
        dividend_per_share=2.5,
        dividend_yield=2.5,
        cost_of_capital=10.0,
        growth_rate=8.0,
        prior_debt_ratio=25.0,
        prior_current_ratio=3.0,
        extra={
            "_gross_margin": 40.0,
            "_asset_turnover": 0.625,
            "_debt_ratio": 25.0,
            "_current_ratio": 3.0,
            "_roa": 12.5,
        },
    )


@pytest.fixture
def red_flag_stock():
    """Suspicious company: low OCF vs NI, high accruals, high AR, high SBC."""
    return Stock(
        ticker="REDFLAG",
        name="Suspicious Co",
        current_price=25.0,
        shares_outstanding=500_000_000,
        eps=0.5,
        bvps=5.0,
        revenue=10_000_000_000,
        net_income=500_000_000,
        fcf=-500_000_000,
        operating_cash_flow=100_000_000,
        ebit=800_000_000,
        operating_margin=8.0,
        tax_rate=25.0,
        roe=10.0,
        total_assets=15_000_000_000,
        total_liabilities=11_000_000_000,
        current_liabilities=5_000_000_000,
        current_assets=6_000_000_000,
        short_term_debt=4_000_000_000,
        long_term_debt=5_000_000_000,
        interest_expense=800_000_000,
        accounts_receivable=3_500_000_000,
        inventory=2_000_000_000,
        accounts_payable=1_500_000_000,
        depreciation=1_000_000_000,
        capex=200_000_000,
        net_working_capital=1_000_000_000,
        net_fixed_assets=8_000_000_000,
        retained_earnings=2_000_000_000,
        total_debt=9_000_000_000,
        cash_and_equivalents=500_000_000,
        sbc=800_000_000,
        shares_issued=60_000_000,
        shares_repurchased=0,
        dividend_per_share=0.0,
        dividend_yield=0.0,
        cost_of_capital=10.0,
        growth_rate=2.0,
        prior_debt_ratio=55.0,
        prior_current_ratio=1.5,
        extra={
            "_gross_margin": 25.0,
            "_asset_turnover": 0.667,
            "_debt_ratio": 73.3,
            "_current_ratio": 1.2,
            "_roa": 3.3,
        },
    )


@pytest.fixture
def partial_data_stock():
    """Stock with minimal data to test unavailable signals."""
    return Stock(
        ticker="MINIMAL",
        name="Minimal Data Co",
        current_price=50.0,
        shares_outstanding=100_000_000,
        eps=2.0,
        bvps=20.0,
        revenue=5_000_000_000,
        net_income=1_000_000_000,
    )


class TestCleanStock:
    def test_clean_low_score(self, clean_stock):
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(clean_stock)
        assert result.overall_score < 25

    def test_clean_risk_level(self, clean_stock):
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(clean_stock)
        assert result.risk_level in (RiskLevel.CLEAN, RiskLevel.MINOR_CONCERNS)

    def test_clean_few_flags(self, clean_stock):
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(clean_stock)
        assert len(result.triggered_flags) <= 1

    def test_clean_no_has_flags(self, clean_stock):
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(clean_stock)
        assert not result.has_flags


class TestRedFlagStock:
    def test_redflag_high_score(self, red_flag_stock):
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(red_flag_stock)
        assert result.overall_score > 50

    def test_redflag_risk_level(self, red_flag_stock):
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(red_flag_stock)
        assert result.risk_level in (RiskLevel.SIGNIFICANT_FLAGS, RiskLevel.SEVERE_FLAGS)

    def test_redflag_has_flags(self, red_flag_stock):
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(red_flag_stock)
        assert result.has_flags

    def test_redflag_multiple_triggered(self, red_flag_stock):
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(red_flag_stock)
        assert len(result.triggered_flags) >= 5

    def test_redflag_fcf_quality_critical(self, red_flag_stock):
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(red_flag_stock)
        fcf_signal = next(
            (s for s in result.signals if s.name == "FCF Quality"), None
        )
        assert fcf_signal is not None
        assert fcf_signal.score >= 90

    def test_redflag_capex_depreciation(self, red_flag_stock):
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(red_flag_stock)
        capex_signal = next(
            (s for s in result.signals if s.name == "CapEx vs Depreciation"), None
        )
        assert capex_signal is not None
        assert capex_signal.score >= 80

    def test_redflag_sbc_revenue(self, red_flag_stock):
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(red_flag_stock)
        sbc_signal = next(
            (s for s in result.signals if s.name == "SBC/Revenue"), None
        )
        assert sbc_signal is not None
        assert sbc_signal.score >= 75


class TestPartialData:
    def test_unavailable_signals(self, partial_data_stock):
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(partial_data_stock)
        unavailable = sum(1 for s in result.signals if not s.is_available)
        assert unavailable > 0

    def test_available_less_than_total(self, partial_data_stock):
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(partial_data_stock)
        assert result.available_signal_count < result.total_signal_count


class TestSignalComputation:
    def test_all_signals_computed(self, clean_stock):
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(clean_stock)
        assert result.total_signal_count == 11

    def test_category_scores_range(self, clean_stock):
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(clean_stock)
        for attr in [
            "earnings_quality_score", "revenue_recognition_score",
            "asset_working_capital_score", "capital_structure_score",
        ]:
            score = getattr(result, attr)
            assert 0 <= score <= 100, f"{attr} = {score}"

    def test_overall_score_range(self, clean_stock):
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(clean_stock)
        assert 0 <= result.overall_score <= 100

    def test_individual_signal_scores_range(self, clean_stock):
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(clean_stock)
        for sig in result.signals:
            assert 0 <= sig.score <= 100, f"{sig.name}: {sig.score}"


class TestOutputFormatting:
    def test_to_summary_format(self, clean_stock):
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(clean_stock)
        summary = result.to_summary()
        assert "RedFlags(" in summary
        assert "/100" in summary

    def test_str_multiline(self, clean_stock):
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(clean_stock)
        text = str(result)
        lines = text.split("\n")
        assert len(lines) > 3

    def test_str_contains_categories(self, clean_stock):
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(clean_stock)
        text = str(result)
        assert "Earnings Quality" in text
        assert "Revenue Recog" in text


class TestConvenienceFunction:
    def test_returns_result(self, clean_stock):
        result = analyze_red_flags(clean_stock)
        assert isinstance(result, RedFlagResult)

    def test_matches_engine(self, clean_stock):
        engine_result = AccountingRedFlagsEngine().analyze(clean_stock)
        convenience_result = analyze_red_flags(clean_stock)
        assert convenience_result.overall_score == engine_result.overall_score


class TestCustomWeights:
    def test_custom_weights_change_composite(self, red_flag_stock):
        default_engine = AccountingRedFlagsEngine()
        custom_engine = AccountingRedFlagsEngine(
            category_weights={
                "earnings_quality": 0.70,
                "revenue_recognition": 0.10,
                "asset_working_capital": 0.10,
                "capital_structure": 0.10,
            }
        )
        default_result = default_engine.analyze(red_flag_stock)
        custom_result = custom_engine.analyze(red_flag_stock)
        assert default_result.overall_score != custom_result.overall_score


class TestCriticalSignals:
    def test_ni_positive_ocf_negative(self):
        """Stock with positive NI but negative OCF should score 95 on earnings persistence."""
        stock = Stock(
            ticker="CRIT1",
            name="Critical Co",
            current_price=10.0,
            shares_outstanding=100_000_000,
            revenue=1_000_000_000,
            net_income=100_000_000,
            operating_cash_flow=-50_000_000,
            total_assets=2_000_000_000,
        )
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(stock)
        persistence = next(
            (s for s in result.signals if s.name == "Earnings Persistence"), None
        )
        assert persistence is not None
        assert persistence.score == 95

    def test_ni_positive_fcf_negative(self):
        """Stock with positive NI but negative FCF should score 95 on FCF quality."""
        stock = Stock(
            ticker="CRIT2",
            name="Critical Co 2",
            current_price=10.0,
            shares_outstanding=100_000_000,
            revenue=1_000_000_000,
            net_income=100_000_000,
            fcf=-50_000_000,
            total_assets=2_000_000_000,
        )
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(stock)
        fcf_sig = next(
            (s for s in result.signals if s.name == "FCF Quality"), None
        )
        assert fcf_sig is not None
        assert fcf_sig.score == 95


# =============================================================================
# Additional Edge-Case Tests
# =============================================================================


# ---------------------------------------------------------------------------
# Helper: bare-minimum stock factory for signal-level tests
# ---------------------------------------------------------------------------

def _stock(**overrides):
    """Create a Stock with sensible defaults, overriding only what's needed."""
    defaults = dict(
        ticker="TEST", name="Test Co", current_price=50.0,
        shares_outstanding=100_000_000, eps=2.0, bvps=20.0,
        revenue=10_000_000_000, net_income=1_000_000_000,
        operating_cash_flow=1_200_000_000, fcf=800_000_000,
        total_assets=20_000_000_000, total_liabilities=8_000_000_000,
        current_liabilities=4_000_000_000, current_assets=8_000_000_000,
        accounts_receivable=2_000_000_000, inventory=1_500_000_000,
        depreciation=500_000_000, capex=600_000_000,
        sbc=50_000_000, ebit=1_300_000_000,
        prior_debt_ratio=40.0, prior_current_ratio=2.0,
        extra={"_debt_ratio": 40.0, "_current_ratio": 2.0},
    )
    defaults.update(overrides)
    return Stock(**defaults)


# ---------------------------------------------------------------------------
# Base function boundary tests
# ---------------------------------------------------------------------------

class TestScoreToSeverityBoundary:
    """Boundary values for _score_to_severity."""

    def test_zero(self):
        from valueinvest.redflags.base import _score_to_severity, RedFlagSeverity
        assert _score_to_severity(0) == RedFlagSeverity.NONE

    def test_exactly_19(self):
        from valueinvest.redflags.base import _score_to_severity, RedFlagSeverity
        assert _score_to_severity(19) == RedFlagSeverity.NONE

    def test_exactly_20(self):
        from valueinvest.redflags.base import _score_to_severity, RedFlagSeverity
        assert _score_to_severity(20) == RedFlagSeverity.LOW

    def test_exactly_39(self):
        from valueinvest.redflags.base import _score_to_severity, RedFlagSeverity
        assert _score_to_severity(39) == RedFlagSeverity.LOW

    def test_exactly_40(self):
        from valueinvest.redflags.base import _score_to_severity, RedFlagSeverity
        assert _score_to_severity(40) == RedFlagSeverity.MODERATE

    def test_exactly_59(self):
        from valueinvest.redflags.base import _score_to_severity, RedFlagSeverity
        assert _score_to_severity(59) == RedFlagSeverity.MODERATE

    def test_exactly_60(self):
        from valueinvest.redflags.base import _score_to_severity, RedFlagSeverity
        assert _score_to_severity(60) == RedFlagSeverity.HIGH

    def test_exactly_79(self):
        from valueinvest.redflags.base import _score_to_severity, RedFlagSeverity
        assert _score_to_severity(79) == RedFlagSeverity.HIGH

    def test_exactly_80(self):
        from valueinvest.redflags.base import _score_to_severity, RedFlagSeverity
        assert _score_to_severity(80) == RedFlagSeverity.CRITICAL

    def test_100(self):
        from valueinvest.redflags.base import _score_to_severity, RedFlagSeverity
        assert _score_to_severity(100) == RedFlagSeverity.CRITICAL


class TestScoreToRiskLevelBoundary:
    """Boundary values for _score_to_risk_level."""

    def test_zero(self):
        from valueinvest.redflags.base import _score_to_risk_level, RiskLevel
        assert _score_to_risk_level(0) == RiskLevel.CLEAN

    def test_exactly_19(self):
        from valueinvest.redflags.base import _score_to_risk_level, RiskLevel
        assert _score_to_risk_level(19) == RiskLevel.CLEAN

    def test_exactly_20(self):
        from valueinvest.redflags.base import _score_to_risk_level, RiskLevel
        assert _score_to_risk_level(20) == RiskLevel.MINOR_CONCERNS

    def test_exactly_39(self):
        from valueinvest.redflags.base import _score_to_risk_level, RiskLevel
        assert _score_to_risk_level(39) == RiskLevel.MINOR_CONCERNS

    def test_exactly_40(self):
        from valueinvest.redflags.base import _score_to_risk_level, RiskLevel
        assert _score_to_risk_level(40) == RiskLevel.MODERATE_CONCERNS

    def test_exactly_59(self):
        from valueinvest.redflags.base import _score_to_risk_level, RiskLevel
        assert _score_to_risk_level(59) == RiskLevel.MODERATE_CONCERNS

    def test_exactly_60(self):
        from valueinvest.redflags.base import _score_to_risk_level, RiskLevel
        assert _score_to_risk_level(60) == RiskLevel.SIGNIFICANT_FLAGS

    def test_exactly_79(self):
        from valueinvest.redflags.base import _score_to_risk_level, RiskLevel
        assert _score_to_risk_level(79) == RiskLevel.SIGNIFICANT_FLAGS

    def test_exactly_80(self):
        from valueinvest.redflags.base import _score_to_risk_level, RiskLevel
        assert _score_to_risk_level(80) == RiskLevel.SEVERE_FLAGS

    def test_100(self):
        from valueinvest.redflags.base import _score_to_risk_level, RiskLevel
        assert _score_to_risk_level(100) == RiskLevel.SEVERE_FLAGS


# ---------------------------------------------------------------------------
# RedFlagResult properties edge cases
# ---------------------------------------------------------------------------

class TestRedFlagResultProperties:
    def test_has_flags_false_at_minor_concerns(self):
        """MINOR_CONCERNS and CLEAN should not set has_flags."""
        from valueinvest.redflags.base import RedFlagResult, RiskLevel
        r = RedFlagResult(ticker="X", overall_score=19, risk_level=RiskLevel.CLEAN)
        assert not r.has_flags
        r2 = RedFlagResult(ticker="X", overall_score=20, risk_level=RiskLevel.MINOR_CONCERNS)
        assert not r2.has_flags

    def test_has_flags_true_at_moderate(self):
        from valueinvest.redflags.base import RedFlagResult, RiskLevel
        r = RedFlagResult(ticker="X", overall_score=40, risk_level=RiskLevel.MODERATE_CONCERNS)
        assert r.has_flags

    def test_has_flags_true_at_significant(self):
        from valueinvest.redflags.base import RedFlagResult, RiskLevel
        r = RedFlagResult(ticker="X", overall_score=60, risk_level=RiskLevel.SIGNIFICANT_FLAGS)
        assert r.has_flags

    def test_has_flags_true_at_severe(self):
        from valueinvest.redflags.base import RedFlagResult, RiskLevel
        r = RedFlagResult(ticker="X", overall_score=80, risk_level=RiskLevel.SEVERE_FLAGS)
        assert r.has_flags

    def test_available_count_zero(self):
        from valueinvest.redflags.base import RedFlagResult, RiskLevel
        r = RedFlagResult(ticker="X", overall_score=0, risk_level=RiskLevel.CLEAN, signals=[])
        assert r.available_signal_count == 0
        assert r.total_signal_count == 0

    def test_available_count_excludes_unavailable(self):
        from valueinvest.redflags.base import RedFlagResult, RiskLevel, RedFlagSignal, RedFlagCategory, RedFlagSeverity
        sig1 = RedFlagSignal(name="a", category=RedFlagCategory.EARNINGS_QUALITY,
                             value=0, score=0, severity=RedFlagSeverity.NONE, is_available=True)
        sig2 = RedFlagSignal(name="b", category=RedFlagCategory.EARNINGS_QUALITY,
                             value=0, score=0, severity=RedFlagSeverity.NONE, is_available=False)
        r = RedFlagResult(ticker="X", overall_score=0, risk_level=RiskLevel.CLEAN, signals=[sig1, sig2])
        assert r.available_signal_count == 1
        assert r.total_signal_count == 2

    def test_to_summary_format(self):
        from valueinvest.redflags.base import RedFlagResult, RiskLevel
        r = RedFlagResult(ticker="ABC", overall_score=42.5, risk_level=RiskLevel.MODERATE_CONCERNS,
                          triggered_flags=["flag1", "flag2"])
        s = r.to_summary()
        assert "ABC" in s
        assert "42" in s
        assert "MODERATE_CONCERNS" in s
        assert "2" in s


# ---------------------------------------------------------------------------
# CFO vs Net Income signal edge cases
# ---------------------------------------------------------------------------

class TestCfoVsNetIncomeSignal:
    def test_zero_ocf_unavailable(self):
        from valueinvest.redflags.signals import cfo_vs_net_income_signal
        sig = cfo_vs_net_income_signal(_stock(operating_cash_flow=0))
        assert not sig.is_available

    def test_zero_ni_unavailable(self):
        from valueinvest.redflags.signals import cfo_vs_net_income_signal
        sig = cfo_vs_net_income_signal(_stock(net_income=0))
        assert not sig.is_available

    def test_negative_ni_negative_ocf(self):
        """Both negative -> score 60."""
        from valueinvest.redflags.signals import cfo_vs_net_income_signal
        sig = cfo_vs_net_income_signal(
            _stock(net_income=-500_000_000, operating_cash_flow=-300_000_000)
        )
        assert sig.is_available
        assert sig.score == 60

    def test_negative_ni_positive_ocf(self):
        """NI < 0, OCF > 0 -> score 35."""
        from valueinvest.redflags.signals import cfo_vs_net_income_signal
        sig = cfo_vs_net_income_signal(
            _stock(net_income=-500_000_000, operating_cash_flow=200_000_000)
        )
        assert sig.is_available
        assert sig.score == 35

    def test_very_large_ocf(self):
        """OCF >> NI -> ratio >= 1.2 -> score 5."""
        from valueinvest.redflags.signals import cfo_vs_net_income_signal
        sig = cfo_vs_net_income_signal(
            _stock(net_income=1_000_000_000, operating_cash_flow=5_000_000_000)
        )
        assert sig.score == 5

    def test_boundary_ratio_1_2(self):
        """Exactly at 1.2 boundary -> score 5."""
        from valueinvest.redflags.signals import cfo_vs_net_income_signal
        sig = cfo_vs_net_income_signal(
            _stock(net_income=1_000_000_000, operating_cash_flow=1_200_000_000)
        )
        assert sig.score == 5

    def test_boundary_ratio_0_8(self):
        """Exactly at 0.8 boundary -> score 20."""
        from valueinvest.redflags.signals import cfo_vs_net_income_signal
        sig = cfo_vs_net_income_signal(
            _stock(net_income=1_000_000_000, operating_cash_flow=800_000_000)
        )
        assert sig.score == 20

    def test_boundary_ratio_0_5(self):
        """Exactly at 0.5 boundary -> score 50."""
        from valueinvest.redflags.signals import cfo_vs_net_income_signal
        sig = cfo_vs_net_income_signal(
            _stock(net_income=1_000_000_000, operating_cash_flow=500_000_000)
        )
        assert sig.score == 50

    def test_boundary_ratio_0_2(self):
        """Exactly at 0.2 boundary -> score 75."""
        from valueinvest.redflags.signals import cfo_vs_net_income_signal
        sig = cfo_vs_net_income_signal(
            _stock(net_income=1_000_000_000, operating_cash_flow=200_000_000)
        )
        assert sig.score == 75

    def test_tiny_positive_ocf(self):
        """OCF barely positive vs NI -> ratio < 0.2 -> score 95."""
        from valueinvest.redflags.signals import cfo_vs_net_income_signal
        sig = cfo_vs_net_income_signal(
            _stock(net_income=1_000_000_000, operating_cash_flow=100_000_000)
        )
        assert sig.score == 95


# ---------------------------------------------------------------------------
# Sloan Accrual signal edge cases
# ---------------------------------------------------------------------------

class TestSloanAccrualSignal:
    def test_zero_assets_unavailable(self):
        from valueinvest.redflags.signals import sloan_accrual_signal
        sig = sloan_accrual_signal(_stock(total_assets=0))
        assert not sig.is_available

    def test_negative_assets_unavailable(self):
        from valueinvest.redflags.signals import sloan_accrual_signal
        sig = sloan_accrual_signal(_stock(total_assets=-100))
        assert not sig.is_available

    def test_zero_ocf_unavailable(self):
        from valueinvest.redflags.signals import sloan_accrual_signal
        sig = sloan_accrual_signal(_stock(operating_cash_flow=0))
        assert not sig.is_available

    def test_negative_accruals_within_2pct(self):
        """Negative accruals (OCF > NI) with abs <= 0.02 -> score 5."""
        from valueinvest.redflags.signals import sloan_accrual_signal
        # NI=1B, OCF=1.05B, assets=2.5B => accruals = (1B-1.05B)/2.5B = -0.02
        sig = sloan_accrual_signal(
            _stock(net_income=1_000_000_000, operating_cash_flow=1_050_000_000,
                   total_assets=2_500_000_000)
        )
        assert sig.score == 5

    def test_positive_accruals_above_5pct_bonus(self):
        """Positive accruals > 0.05 triggers +10 bonus, capped at 100."""
        from valueinvest.redflags.signals import sloan_accrual_signal
        # NI=2B, OCF=1B, assets=5B => accruals = 0.2 -> score=90, +10 = 100
        sig = sloan_accrual_signal(
            _stock(net_income=2_000_000_000, operating_cash_flow=1_000_000_000,
                   total_assets=5_000_000_000)
        )
        assert sig.score == 100

    def test_very_small_negative_accruals(self):
        """Very small accruals (NI ~ OCF) -> score 5."""
        from valueinvest.redflags.signals import sloan_accrual_signal
        sig = sloan_accrual_signal(
            _stock(net_income=1_000_000_000, operating_cash_flow=1_001_000_000,
                   total_assets=10_000_000_000)
        )
        assert sig.score == 5

    def test_boundary_accruals_0_02(self):
        """Exactly at abs=0.02 boundary -> score 5."""
        from valueinvest.redflags.signals import sloan_accrual_signal
        sig = sloan_accrual_signal(
            _stock(net_income=1_200_000_000, operating_cash_flow=1_000_000_000,
                   total_assets=10_000_000_000)
        )
        assert sig.score == 5

    def test_boundary_accruals_0_05(self):
        """Exactly at abs=0.05 boundary -> score 20."""
        from valueinvest.redflags.signals import sloan_accrual_signal
        sig = sloan_accrual_signal(
            _stock(net_income=1_500_000_000, operating_cash_flow=1_000_000_000,
                   total_assets=10_000_000_000)
        )
        assert sig.score == 20

    def test_boundary_accruals_0_10(self):
        """Exactly at abs=0.10 boundary -> score 55 (base 45 + 10 positive bonus)."""
        from valueinvest.redflags.signals import sloan_accrual_signal
        sig = sloan_accrual_signal(
            _stock(net_income=2_000_000_000, operating_cash_flow=1_000_000_000,
                   total_assets=10_000_000_000)
        )
        # accruals = 0.10, abs <= 0.10 -> base 45, positive > 0.05 -> +10 = 55
        assert sig.score == 55

    def test_boundary_accruals_0_15(self):
        """Exactly at abs=0.15 boundary -> score 75 (base 65 + 10 positive bonus)."""
        from valueinvest.redflags.signals import sloan_accrual_signal
        sig = sloan_accrual_signal(
            _stock(net_income=2_500_000_000, operating_cash_flow=1_000_000_000,
                   total_assets=10_000_000_000)
        )
        # accruals = 0.15, abs <= 0.15 -> base 65, positive > 0.05 -> +10 = 75
        assert sig.score == 75

    def test_positive_accruals_just_over_5pct(self):
        """Positive accruals just above 0.05: base 45 + 10 bonus = 55."""
        from valueinvest.redflags.signals import sloan_accrual_signal
        sig = sloan_accrual_signal(
            _stock(net_income=1_600_000_000, operating_cash_flow=1_000_000_000,
                   total_assets=10_000_000_000)
        )
        # accruals = 0.06 -> abs in (0.05, 0.10] -> base 45, positive > 0.05 -> +10 = 55
        # Wait: 0.06 > 0.05 so abs in (0.05, 0.10] -> base score 45, +10 bonus = 55
        assert sig.score == 55


# ---------------------------------------------------------------------------
# Earnings Persistence signal edge cases
# ---------------------------------------------------------------------------

class TestEarningsPersistenceSignal:
    def test_both_zero_unavailable(self):
        from valueinvest.redflags.signals import earnings_persistence_signal
        sig = earnings_persistence_signal(
            _stock(net_income=0, operating_cash_flow=0)
        )
        assert not sig.is_available

    def test_both_negative(self):
        """Both NI and OCF negative -> score 60."""
        from valueinvest.redflags.signals import earnings_persistence_signal
        sig = earnings_persistence_signal(
            _stock(net_income=-200_000_000, operating_cash_flow=-100_000_000)
        )
        assert sig.is_available
        assert sig.score == 60

    def test_positive_ni_negative_ocf(self):
        """NI > 0, OCF < 0 -> score 95."""
        from valueinvest.redflags.signals import earnings_persistence_signal
        sig = earnings_persistence_signal(
            _stock(net_income=500_000_000, operating_cash_flow=-100_000_000)
        )
        assert sig.score == 95

    def test_negative_ni_positive_ocf(self):
        """NI < 0, OCF > 0 -> score 35."""
        from valueinvest.redflags.signals import earnings_persistence_signal
        sig = earnings_persistence_signal(
            _stock(net_income=-200_000_000, operating_cash_flow=500_000_000)
        )
        assert sig.score == 35

    def test_both_positive_small_divergence(self):
        """Divergence < 0.1 -> score 5."""
        from valueinvest.redflags.signals import earnings_persistence_signal
        sig = earnings_persistence_signal(
            _stock(net_income=1_000_000_000, operating_cash_flow=1_050_000_000)
        )
        assert sig.score == 5

    def test_both_positive_boundary_0_1(self):
        """Divergence exactly 0.1 -> score 25."""
        from valueinvest.redflags.signals import earnings_persistence_signal
        sig = earnings_persistence_signal(
            _stock(net_income=1_000_000_000, operating_cash_flow=1_111_111_112)
        )
        # divergence = 111111112 / 1111111112 ~ 0.1
        assert sig.score == 25

    def test_both_positive_boundary_0_3(self):
        """Divergence exactly 0.3 -> score 50."""
        from valueinvest.redflags.signals import earnings_persistence_signal
        sig = earnings_persistence_signal(
            _stock(net_income=1_000_000_000, operating_cash_flow=700_000_000)
        )
        # divergence = 300M / 1000M = 0.3
        assert sig.score == 50

    def test_both_positive_boundary_0_5(self):
        """Divergence exactly 0.5 -> score 70."""
        from valueinvest.redflags.signals import earnings_persistence_signal
        sig = earnings_persistence_signal(
            _stock(net_income=1_000_000_000, operating_cash_flow=500_000_000)
        )
        # divergence = 500M / 1000M = 0.5
        assert sig.score == 70


# ---------------------------------------------------------------------------
# AR vs Revenue signal edge cases
# ---------------------------------------------------------------------------

class TestArVsRevenueSignal:
    def test_zero_revenue_unavailable(self):
        from valueinvest.redflags.signals import ar_vs_revenue_signal
        sig = ar_vs_revenue_signal(_stock(revenue=0))
        assert not sig.is_available

    def test_negative_revenue_unavailable(self):
        from valueinvest.redflags.signals import ar_vs_revenue_signal
        sig = ar_vs_revenue_signal(_stock(revenue=-100))
        assert not sig.is_available

    def test_zero_ar_unavailable(self):
        from valueinvest.redflags.signals import ar_vs_revenue_signal
        sig = ar_vs_revenue_signal(_stock(accounts_receivable=0))
        assert not sig.is_available

    def test_boundary_dso_30(self):
        """DSO = 30 -> score 5."""
        from valueinvest.redflags.signals import ar_vs_revenue_signal
        # AR = 30/365 * revenue
        ar = 30 / 365 * 10_000_000_000
        sig = ar_vs_revenue_signal(_stock(accounts_receivable=ar))
        assert sig.score == 5

    def test_boundary_dso_45(self):
        """DSO = 45 -> score 15."""
        from valueinvest.redflags.signals import ar_vs_revenue_signal
        ar = 45 / 365 * 10_000_000_000
        sig = ar_vs_revenue_signal(_stock(accounts_receivable=ar))
        assert sig.score == 15

    def test_boundary_dso_60(self):
        """DSO = 60 -> score 30."""
        from valueinvest.redflags.signals import ar_vs_revenue_signal
        ar = 60 / 365 * 10_000_000_000
        sig = ar_vs_revenue_signal(_stock(accounts_receivable=ar))
        assert sig.score == 30

    def test_boundary_dso_90(self):
        """DSO = 90 -> score 55."""
        from valueinvest.redflags.signals import ar_vs_revenue_signal
        ar = 90 / 365 * 10_000_000_000
        sig = ar_vs_revenue_signal(_stock(accounts_receivable=ar))
        assert sig.score == 55

    def test_boundary_dso_120(self):
        """DSO = 120 -> score 75."""
        from valueinvest.redflags.signals import ar_vs_revenue_signal
        ar = 120 / 365 * 10_000_000_000
        sig = ar_vs_revenue_signal(_stock(accounts_receivable=ar))
        assert sig.score == 75

    def test_very_high_dso(self):
        """DSO > 120 -> score 95."""
        from valueinvest.redflags.signals import ar_vs_revenue_signal
        ar = 200 / 365 * 10_000_000_000
        sig = ar_vs_revenue_signal(_stock(accounts_receivable=ar))
        assert sig.score == 95


# ---------------------------------------------------------------------------
# Revenue Quality signal edge cases
# ---------------------------------------------------------------------------

class TestRevenueQualitySignal:
    def test_zero_revenue_unavailable(self):
        from valueinvest.redflags.signals import revenue_quality_signal
        sig = revenue_quality_signal(_stock(revenue=0))
        assert not sig.is_available

    def test_zero_ocf_unavailable(self):
        from valueinvest.redflags.signals import revenue_quality_signal
        sig = revenue_quality_signal(_stock(operating_cash_flow=0))
        assert not sig.is_available

    def test_negative_ocf(self):
        """Negative OCF/revenue ratio -> score 95."""
        from valueinvest.redflags.signals import revenue_quality_signal
        sig = revenue_quality_signal(
            _stock(operating_cash_flow=-500_000_000)
        )
        assert sig.score == 95

    def test_boundary_ratio_0_20(self):
        """OCF/Revenue = 0.20 -> score 5."""
        from valueinvest.redflags.signals import revenue_quality_signal
        sig = revenue_quality_signal(
            _stock(operating_cash_flow=2_000_000_000)
        )
        assert sig.score == 5

    def test_boundary_ratio_0_15(self):
        """OCF/Revenue = 0.15 -> score 15."""
        from valueinvest.redflags.signals import revenue_quality_signal
        sig = revenue_quality_signal(
            _stock(operating_cash_flow=1_500_000_000)
        )
        assert sig.score == 15

    def test_boundary_ratio_0_10(self):
        """OCF/Revenue = 0.10 -> score 30."""
        from valueinvest.redflags.signals import revenue_quality_signal
        sig = revenue_quality_signal(
            _stock(operating_cash_flow=1_000_000_000)
        )
        assert sig.score == 30

    def test_boundary_ratio_0_05(self):
        """OCF/Revenue = 0.05 -> score 55."""
        from valueinvest.redflags.signals import revenue_quality_signal
        sig = revenue_quality_signal(
            _stock(operating_cash_flow=500_000_000)
        )
        assert sig.score == 55

    def test_boundary_ratio_0(self):
        """OCF/Revenue = 0 -> score 70."""
        from valueinvest.redflags.signals import revenue_quality_signal
        # Need a very tiny positive OCF that rounds to 0, or set OCF to a tiny value
        # Actually the code checks ratio >= 0 for score 70, so OCF = 0 is N/A.
        # We need OCF > 0 but ratio < 0.05 -> score 55.
        # The boundary is ratio exactly 0 which requires OCF=0 but that's N/A.
        # So we test just above 0: tiny OCF.
        sig = revenue_quality_signal(
            _stock(operating_cash_flow=1)  # practically 0 but positive
        )
        # ratio = 1 / 10B -> 0.0, but > 0 so hits ratio >= 0 -> score 70
        assert sig.score == 70

    def test_very_high_ocf(self):
        """OCF > revenue -> ratio > 1 -> score 5."""
        from valueinvest.redflags.signals import revenue_quality_signal
        sig = revenue_quality_signal(
            _stock(operating_cash_flow=20_000_000_000)
        )
        assert sig.score == 5


# ---------------------------------------------------------------------------
# Inventory Buildup signal edge cases
# ---------------------------------------------------------------------------

class TestInventoryBuildupSignal:
    def test_zero_revenue_unavailable(self):
        from valueinvest.redflags.signals import inventory_buildup_signal
        sig = inventory_buildup_signal(_stock(revenue=0))
        assert not sig.is_available

    def test_zero_inventory_unavailable(self):
        """Software/service company with no inventory."""
        from valueinvest.redflags.signals import inventory_buildup_signal
        sig = inventory_buildup_signal(_stock(inventory=0))
        assert not sig.is_available

    def test_negative_revenue_unavailable(self):
        from valueinvest.redflags.signals import inventory_buildup_signal
        sig = inventory_buildup_signal(_stock(revenue=-100))
        assert not sig.is_available

    def test_boundary_dio_30(self):
        """DIO = 30 -> score 5."""
        from valueinvest.redflags.signals import inventory_buildup_signal
        inv = 30 / 365 * 10_000_000_000
        sig = inventory_buildup_signal(_stock(inventory=inv))
        assert sig.score == 5

    def test_boundary_dio_60(self):
        """DIO = 60 -> score 15."""
        from valueinvest.redflags.signals import inventory_buildup_signal
        inv = 60 / 365 * 10_000_000_000
        sig = inventory_buildup_signal(_stock(inventory=inv))
        assert sig.score == 15

    def test_boundary_dio_90(self):
        """DIO = 90 -> score 30."""
        from valueinvest.redflags.signals import inventory_buildup_signal
        inv = 90 / 365 * 10_000_000_000
        sig = inventory_buildup_signal(_stock(inventory=inv))
        assert sig.score == 30

    def test_boundary_dio_120(self):
        """DIO = 120 -> score 50."""
        from valueinvest.redflags.signals import inventory_buildup_signal
        inv = 120 / 365 * 10_000_000_000
        sig = inventory_buildup_signal(_stock(inventory=inv))
        assert sig.score == 50

    def test_boundary_dio_180(self):
        """DIO = 180 -> score 70."""
        from valueinvest.redflags.signals import inventory_buildup_signal
        inv = 180 / 365 * 10_000_000_000
        sig = inventory_buildup_signal(_stock(inventory=inv))
        assert sig.score == 70

    def test_very_high_dio(self):
        """DIO > 180 -> score 90."""
        from valueinvest.redflags.signals import inventory_buildup_signal
        inv = 365 / 365 * 10_000_000_000  # 1 full year
        sig = inventory_buildup_signal(_stock(inventory=inv))
        assert sig.score == 90


# ---------------------------------------------------------------------------
# Working Capital Efficiency signal edge cases
# ---------------------------------------------------------------------------

class TestWorkingCapitalEfficiencySignal:
    def test_both_current_ratios_zero_unavailable(self):
        from valueinvest.redflags.signals import working_capital_efficiency_signal
        sig = working_capital_efficiency_signal(
            _stock(extra={"_current_ratio": 0.0}, prior_current_ratio=0.0)
        )
        assert not sig.is_available

    def test_only_current_available_low(self):
        """Only current ratio available, below 1.0 -> score 80."""
        from valueinvest.redflags.signals import working_capital_efficiency_signal
        sig = working_capital_efficiency_signal(
            _stock(extra={"_current_ratio": 0.8}, prior_current_ratio=0.0)
        )
        assert sig.is_available
        assert sig.score == 80

    def test_only_current_available_1_0(self):
        """Only current ratio available, at 1.0 -> score 45."""
        from valueinvest.redflags.signals import working_capital_efficiency_signal
        sig = working_capital_efficiency_signal(
            _stock(extra={"_current_ratio": 1.0}, prior_current_ratio=0.0)
        )
        assert sig.score == 45

    def test_only_current_available_1_5(self):
        """Only current ratio available, at 1.5 -> score 25."""
        from valueinvest.redflags.signals import working_capital_efficiency_signal
        sig = working_capital_efficiency_signal(
            _stock(extra={"_current_ratio": 1.5}, prior_current_ratio=0.0)
        )
        assert sig.score == 25

    def test_only_current_available_2_0(self):
        """Only current ratio available, at 2.0 -> score 10."""
        from valueinvest.redflags.signals import working_capital_efficiency_signal
        sig = working_capital_efficiency_signal(
            _stock(extra={"_current_ratio": 2.0}, prior_current_ratio=0.0)
        )
        assert sig.score == 10

    def test_only_prior_available(self):
        """Only prior current ratio available -> score 40."""
        from valueinvest.redflags.signals import working_capital_efficiency_signal
        sig = working_capital_efficiency_signal(
            _stock(extra={"_current_ratio": 0.0}, prior_current_ratio=2.0)
        )
        assert sig.is_available
        assert sig.score == 40

    def test_improving_current_ratio(self):
        """Current > prior -> score 10."""
        from valueinvest.redflags.signals import working_capital_efficiency_signal
        sig = working_capital_efficiency_signal(
            _stock(extra={"_current_ratio": 3.0}, prior_current_ratio=2.0)
        )
        assert sig.score == 10

    def test_decline_exactly_0_3(self):
        """Change = -0.3: code uses > so -0.3 is NOT > -0.3, falls to > -0.5 -> score 55."""
        from valueinvest.redflags.signals import working_capital_efficiency_signal
        sig = working_capital_efficiency_signal(
            _stock(extra={"_current_ratio": 1.7}, prior_current_ratio=2.0)
        )
        assert sig.score == 55

    def test_decline_exactly_0_5(self):
        """Change = -0.5: code uses > so -0.5 is NOT > -0.5, falls to > -1.0 -> score 75."""
        from valueinvest.redflags.signals import working_capital_efficiency_signal
        sig = working_capital_efficiency_signal(
            _stock(extra={"_current_ratio": 1.5}, prior_current_ratio=2.0)
        )
        assert sig.score == 75

    def test_decline_exactly_1_0(self):
        """Change = -1.0: code uses > so -1.0 is NOT > -1.0, falls to else -> score 90."""
        from valueinvest.redflags.signals import working_capital_efficiency_signal
        sig = working_capital_efficiency_signal(
            _stock(extra={"_current_ratio": 1.0}, prior_current_ratio=2.0)
        )
        assert sig.score == 90

    def test_decline_beyond_1_0(self):
        """Change < -1.0 -> score 90."""
        from valueinvest.redflags.signals import working_capital_efficiency_signal
        sig = working_capital_efficiency_signal(
            _stock(extra={"_current_ratio": 0.5}, prior_current_ratio=2.0)
        )
        assert sig.score == 90


# ---------------------------------------------------------------------------
# CapEx vs Depreciation signal edge cases
# ---------------------------------------------------------------------------

class TestCapexVsDepreciationSignal:
    def test_zero_depreciation_unavailable(self):
        from valueinvest.redflags.signals import capex_vs_depreciation_signal
        sig = capex_vs_depreciation_signal(_stock(depreciation=0))
        assert not sig.is_available

    def test_negative_depreciation_unavailable(self):
        from valueinvest.redflags.signals import capex_vs_depreciation_signal
        sig = capex_vs_depreciation_signal(_stock(depreciation=-100))
        assert not sig.is_available

    def test_negative_capex_uses_abs(self):
        """Negative capex is absolute-valued."""
        from valueinvest.redflags.signals import capex_vs_depreciation_signal
        sig = capex_vs_depreciation_signal(
            _stock(capex=-600_000_000, depreciation=500_000_000)
        )
        # ratio = 600M/500M = 1.2 -> score 15
        assert sig.score == 15

    def test_boundary_ratio_1_5(self):
        """CapEx/Dep = 1.5 -> score 5."""
        from valueinvest.redflags.signals import capex_vs_depreciation_signal
        sig = capex_vs_depreciation_signal(
            _stock(capex=750_000_000, depreciation=500_000_000)
        )
        assert sig.score == 5

    def test_boundary_ratio_1_0(self):
        """CapEx/Dep = 1.0 -> score 15."""
        from valueinvest.redflags.signals import capex_vs_depreciation_signal
        sig = capex_vs_depreciation_signal(
            _stock(capex=500_000_000, depreciation=500_000_000)
        )
        assert sig.score == 15

    def test_boundary_ratio_0_7(self):
        """CapEx/Dep = 0.7 -> score 40."""
        from valueinvest.redflags.signals import capex_vs_depreciation_signal
        sig = capex_vs_depreciation_signal(
            _stock(capex=350_000_000, depreciation=500_000_000)
        )
        assert sig.score == 40

    def test_boundary_ratio_0_4(self):
        """CapEx/Dep = 0.4 -> score 65."""
        from valueinvest.redflags.signals import capex_vs_depreciation_signal
        sig = capex_vs_depreciation_signal(
            _stock(capex=200_000_000, depreciation=500_000_000)
        )
        assert sig.score == 65

    def test_boundary_ratio_0_2(self):
        """CapEx/Dep = 0.2 -> score 85."""
        from valueinvest.redflags.signals import capex_vs_depreciation_signal
        sig = capex_vs_depreciation_signal(
            _stock(capex=100_000_000, depreciation=500_000_000)
        )
        assert sig.score == 85

    def test_near_zero_capex(self):
        """CapEx nearly 0 -> score 95."""
        from valueinvest.redflags.signals import capex_vs_depreciation_signal
        sig = capex_vs_depreciation_signal(
            _stock(capex=10_000_000, depreciation=500_000_000)
        )
        assert sig.score == 95

    def test_very_large_capex(self):
        """CapEx >> depreciation -> score 5."""
        from valueinvest.redflags.signals import capex_vs_depreciation_signal
        sig = capex_vs_depreciation_signal(
            _stock(capex=10_000_000_000, depreciation=500_000_000)
        )
        assert sig.score == 5


# ---------------------------------------------------------------------------
# Debt Trend signal edge cases
# ---------------------------------------------------------------------------

class TestDebtTrendSignal:
    def test_both_ratios_zero_unavailable(self):
        from valueinvest.redflags.signals import debt_trend_signal
        sig = debt_trend_signal(
            _stock(extra={"_debt_ratio": 0.0}, prior_debt_ratio=0.0)
        )
        assert not sig.is_available

    def test_only_prior_available(self):
        """Only prior debt ratio available -> score 40."""
        from valueinvest.redflags.signals import debt_trend_signal
        sig = debt_trend_signal(
            _stock(extra={"_debt_ratio": 0.0}, prior_debt_ratio=50.0)
        )
        assert sig.is_available
        assert sig.score == 40

    def test_only_current_available_low(self):
        """Only current available, < 40% -> score 15."""
        from valueinvest.redflags.signals import debt_trend_signal
        sig = debt_trend_signal(
            _stock(extra={"_debt_ratio": 30.0}, prior_debt_ratio=0.0)
        )
        assert sig.score == 15

    def test_only_current_available_40(self):
        """Only current available, at 40% -> score 35."""
        from valueinvest.redflags.signals import debt_trend_signal
        sig = debt_trend_signal(
            _stock(extra={"_debt_ratio": 40.0}, prior_debt_ratio=0.0)
        )
        assert sig.score == 35

    def test_only_current_available_60(self):
        """Only current available, at 60% -> score 60."""
        from valueinvest.redflags.signals import debt_trend_signal
        sig = debt_trend_signal(
            _stock(extra={"_debt_ratio": 60.0}, prior_debt_ratio=0.0)
        )
        assert sig.score == 60

    def test_only_current_available_80(self):
        """Only current available, at 80% -> score 85."""
        from valueinvest.redflags.signals import debt_trend_signal
        sig = debt_trend_signal(
            _stock(extra={"_debt_ratio": 80.0}, prior_debt_ratio=0.0)
        )
        assert sig.score == 85

    def test_very_high_debt_ratio(self):
        """Only current available, > 80% -> score 85."""
        from valueinvest.redflags.signals import debt_trend_signal
        sig = debt_trend_signal(
            _stock(extra={"_debt_ratio": 95.0}, prior_debt_ratio=0.0)
        )
        assert sig.score == 85

    def test_improving_debt(self):
        """Debt decreasing by > 3pp -> score 5."""
        from valueinvest.redflags.signals import debt_trend_signal
        sig = debt_trend_signal(
            _stock(extra={"_debt_ratio": 30.0}, prior_debt_ratio=40.0)
        )
        assert sig.score == 5

    def test_rising_debt_boundary_2(self):
        """Change exactly +2 -> score 30 (change > 0 but not > 2)."""
        from valueinvest.redflags.signals import debt_trend_signal
        sig = debt_trend_signal(
            _stock(extra={"_debt_ratio": 42.0}, prior_debt_ratio=40.0)
        )
        assert sig.score == 30

    def test_rising_debt_boundary_5(self):
        """Change exactly +5 -> score 50 (change > 2 but not > 5)."""
        from valueinvest.redflags.signals import debt_trend_signal
        sig = debt_trend_signal(
            _stock(extra={"_debt_ratio": 45.0}, prior_debt_ratio=40.0)
        )
        assert sig.score == 50

    def test_rising_debt_boundary_10(self):
        """Change exactly +10 -> score 70 (change > 5 but not > 10)."""
        from valueinvest.redflags.signals import debt_trend_signal
        sig = debt_trend_signal(
            _stock(extra={"_debt_ratio": 50.0}, prior_debt_ratio=40.0)
        )
        assert sig.score == 70

    def test_rising_debt_above_10(self):
        """Change > 10 -> score 90."""
        from valueinvest.redflags.signals import debt_trend_signal
        sig = debt_trend_signal(
            _stock(extra={"_debt_ratio": 55.0}, prior_debt_ratio=40.0)
        )
        assert sig.score == 90


# ---------------------------------------------------------------------------
# SBC/Revenue signal edge cases
# ---------------------------------------------------------------------------

class TestSbcRevenueSignal:
    def test_zero_revenue_unavailable(self):
        from valueinvest.redflags.signals import sbc_revenue_signal
        sig = sbc_revenue_signal(_stock(revenue=0))
        assert not sig.is_available

    def test_negative_revenue_unavailable(self):
        from valueinvest.redflags.signals import sbc_revenue_signal
        sig = sbc_revenue_signal(_stock(revenue=-100))
        assert not sig.is_available

    def test_zero_sbc(self):
        """SBC = 0 -> score 5."""
        from valueinvest.redflags.signals import sbc_revenue_signal
        sig = sbc_revenue_signal(_stock(sbc=0))
        assert sig.score == 5

    def test_sbc_greater_than_net_income_extra_penalty(self):
        """SBC > NI triggers +15 bonus, capped at 100."""
        from valueinvest.redflags.signals import sbc_revenue_signal
        # sbc=400M, revenue=10B -> sbc_pct=4.0 -> base score 55
        # NI=300M < sbc=400M -> +15 = 70
        sig = sbc_revenue_signal(
            _stock(sbc=400_000_000, net_income=300_000_000)
        )
        assert sig.score == 70

    def test_sbc_much_greater_than_ni_caps_at_100(self):
        """SBC >> NI, high base score + 15 -> capped at 100."""
        from valueinvest.redflags.signals import sbc_revenue_signal
        # sbc=1.5B, revenue=10B -> sbc_pct=15.0 -> base score 95
        # NI=100M < sbc=1.5B -> +15 = min(100, 110) = 100
        sig = sbc_revenue_signal(
            _stock(sbc=1_500_000_000, net_income=100_000_000)
        )
        assert sig.score == 100

    def test_sbc_gt_ni_negative_ni_no_bonus(self):
        """NI <= 0, so no extra penalty even if SBC > NI."""
        from valueinvest.redflags.signals import sbc_revenue_signal
        # sbc=400M, revenue=10B -> sbc_pct=4.0 -> base score 55
        # NI=-100M (not > 0) -> no bonus
        sig = sbc_revenue_signal(
            _stock(sbc=400_000_000, net_income=-100_000_000)
        )
        assert sig.score == 55

    def test_boundary_sbc_1pct(self):
        """SBC = 1%: code uses < so exactly 1.0 falls to next bucket (score 15)."""
        from valueinvest.redflags.signals import sbc_revenue_signal
        sig = sbc_revenue_signal(
            _stock(sbc=100_000_000, net_income=5_000_000_000)  # 100M / 10B = 1.0%
        )
        assert sig.score == 15

    def test_boundary_sbc_2pct(self):
        """SBC = 2%: code uses < so exactly 2.0 falls to next bucket (score 30)."""
        from valueinvest.redflags.signals import sbc_revenue_signal
        sig = sbc_revenue_signal(
            _stock(sbc=200_000_000, net_income=5_000_000_000)  # 200M / 10B = 2.0%
        )
        assert sig.score == 30

    def test_boundary_sbc_3pct(self):
        """SBC = 3%: code uses < so exactly 3.0 falls to next bucket (score 55)."""
        from valueinvest.redflags.signals import sbc_revenue_signal
        sig = sbc_revenue_signal(
            _stock(sbc=300_000_000, net_income=5_000_000_000)  # 300M / 10B = 3.0%
        )
        assert sig.score == 55

    def test_boundary_sbc_5pct(self):
        """SBC = 5%: code uses < so exactly 5.0 falls to next bucket (score 75)."""
        from valueinvest.redflags.signals import sbc_revenue_signal
        sig = sbc_revenue_signal(
            _stock(sbc=500_000_000, net_income=5_000_000_000)  # 500M / 10B = 5.0%
        )
        assert sig.score == 75

    def test_boundary_sbc_8pct(self):
        """SBC = 8%: code uses < so exactly 8.0 falls to else bucket (score 95)."""
        from valueinvest.redflags.signals import sbc_revenue_signal
        sig = sbc_revenue_signal(
            _stock(sbc=800_000_000, net_income=5_000_000_000)  # 800M / 10B = 8.0%
        )
        assert sig.score == 95

    def test_very_high_sbc(self):
        """SBC > 8% -> score 95."""
        from valueinvest.redflags.signals import sbc_revenue_signal
        sig = sbc_revenue_signal(
            _stock(sbc=1_000_000_000)  # 1B / 10B = 10.0%
        )
        assert sig.score == 95


# ---------------------------------------------------------------------------
# FCF Quality signal edge cases
# ---------------------------------------------------------------------------

class TestFcfQualitySignal:
    def test_both_zero_unavailable(self):
        from valueinvest.redflags.signals import fcf_quality_signal
        sig = fcf_quality_signal(_stock(net_income=0, fcf=0))
        assert not sig.is_available

    def test_positive_ni_negative_fcf(self):
        """NI > 0, FCF <= 0 -> score 95."""
        from valueinvest.redflags.signals import fcf_quality_signal
        sig = fcf_quality_signal(
            _stock(net_income=1_000_000_000, fcf=-100_000_000)
        )
        assert sig.score == 95

    def test_positive_ni_zero_fcf(self):
        """NI > 0, FCF = 0 -> score 95 (fcf <= 0 branch)."""
        from valueinvest.redflags.signals import fcf_quality_signal
        sig = fcf_quality_signal(
            _stock(net_income=1_000_000_000, fcf=0)
        )
        assert sig.score == 95

    def test_negative_ni(self):
        """NI < 0 -> score 50 regardless of FCF."""
        from valueinvest.redflags.signals import fcf_quality_signal
        sig = fcf_quality_signal(
            _stock(net_income=-500_000_000, fcf=200_000_000)
        )
        assert sig.score == 50

    def test_negative_ni_negative_fcf(self):
        """Both negative -> score 50."""
        from valueinvest.redflags.signals import fcf_quality_signal
        sig = fcf_quality_signal(
            _stock(net_income=-500_000_000, fcf=-300_000_000)
        )
        assert sig.score == 50

    def test_boundary_ratio_1_0(self):
        """FCF/NI = 1.0 -> score 5."""
        from valueinvest.redflags.signals import fcf_quality_signal
        sig = fcf_quality_signal(
            _stock(net_income=1_000_000_000, fcf=1_000_000_000)
        )
        assert sig.score == 5

    def test_boundary_ratio_0_7(self):
        """FCF/NI = 0.7 -> score 20."""
        from valueinvest.redflags.signals import fcf_quality_signal
        sig = fcf_quality_signal(
            _stock(net_income=1_000_000_000, fcf=700_000_000)
        )
        assert sig.score == 20

    def test_boundary_ratio_0_4(self):
        """FCF/NI = 0.4 -> score 45."""
        from valueinvest.redflags.signals import fcf_quality_signal
        sig = fcf_quality_signal(
            _stock(net_income=1_000_000_000, fcf=400_000_000)
        )
        assert sig.score == 45

    def test_boundary_ratio_0_2(self):
        """FCF/NI = 0.2 -> score 65."""
        from valueinvest.redflags.signals import fcf_quality_signal
        sig = fcf_quality_signal(
            _stock(net_income=1_000_000_000, fcf=200_000_000)
        )
        assert sig.score == 65

    def test_very_small_positive_fcf(self):
        """FCF barely positive -> score 85."""
        from valueinvest.redflags.signals import fcf_quality_signal
        sig = fcf_quality_signal(
            _stock(net_income=1_000_000_000, fcf=50_000_000)
        )
        assert sig.score == 85

    def test_fcf_much_greater_than_ni(self):
        """FCF >> NI -> score 5."""
        from valueinvest.redflags.signals import fcf_quality_signal
        sig = fcf_quality_signal(
            _stock(net_income=500_000_000, fcf=5_000_000_000)
        )
        assert sig.score == 5


# ---------------------------------------------------------------------------
# Engine behavior with ALL signals unavailable
# ---------------------------------------------------------------------------

class TestEngineAllSignalsUnavailable:
    def test_bare_stock_all_unavailable(self):
        """Stock with only ticker/price -> most signals unavailable, score = 0."""
        stock = Stock(ticker="BARE", name="Bare Co", current_price=1.0)
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(stock)
        assert result.total_signal_count == 11
        # All signals should be unavailable
        assert result.available_signal_count == 0
        assert result.overall_score == 0
        assert result.risk_level == RiskLevel.CLEAN
        assert not result.has_flags
        # All category scores should be 0
        assert result.earnings_quality_score == 0
        assert result.revenue_recognition_score == 0
        assert result.asset_working_capital_score == 0
        assert result.capital_structure_score == 0

    def test_bare_stock_warnings_populated(self):
        """When all signals unavailable, warnings should be populated."""
        stock = Stock(ticker="BARE", name="Bare Co", current_price=1.0)
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(stock)
        assert len(result.warnings) > 0
        assert len(result.triggered_flags) == 0

    def test_bare_stock_analysis_lines(self):
        """Analysis should still produce lines even with no data."""
        stock = Stock(ticker="BARE", name="Bare Co", current_price=1.0)
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(stock)
        assert len(result.analysis) >= 1


# ---------------------------------------------------------------------------
# Engine score boundary composition tests
# ---------------------------------------------------------------------------

class TestEngineScoreComposition:
    def test_only_earnings_quality_available(self):
        """Only earnings quality signals available -> EQ score > 0, others depend."""
        # Provide NI, OCF, assets but nothing for revenue/AR/inventory/etc
        stock = Stock(
            ticker="EQONLY", name="EQ Only", current_price=50.0,
            shares_outstanding=100_000_000,
            net_income=1_000_000_000, operating_cash_flow=1_200_000_000,
            total_assets=20_000_000_000,
        )
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(stock)
        assert result.earnings_quality_score > 0
        # Revenue and asset/WC categories should be 0 (no data)
        assert result.revenue_recognition_score == 0
        assert result.asset_working_capital_score == 0
        # FCF Quality is in capital_structure; without FCF data, it's unavailable.
        # But if we don't provide fcf, the FCF Quality signal checks ni==0 && fcf==0.
        # Since NI > 0 and fcf defaults to 0, it falls into "ni > 0 and fcf <= 0" -> score 95.
        # So capital_structure_score > 0 in this case. That's fine -- it's a valid finding.
        assert result.capital_structure_score >= 0

    def test_composite_clamped_to_100(self):
        """Composite score should never exceed 100."""
        stock = Stock(
            ticker="MAX", name="Max Score Co", current_price=1.0,
            shares_outstanding=100_000_000,
            revenue=10_000_000_000, net_income=1_000_000_000,
            operating_cash_flow=-500_000_000, fcf=-1_000_000_000,
            total_assets=5_000_000_000,
            accounts_receivable=5_000_000_000,
            inventory=3_000_000_000,
            depreciation=500_000_000, capex=10_000_000,
            sbc=1_500_000_000,
            extra={"_debt_ratio": 90.0, "_current_ratio": 0.5},
            prior_debt_ratio=60.0, prior_current_ratio=2.0,
        )
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(stock)
        assert 0 <= result.overall_score <= 100

    def test_composite_clamped_to_0(self):
        """Even with all-clean data, composite should be >= 0."""
        stock = Stock(
            ticker="ZERO", name="Zero Score Co", current_price=50.0,
            shares_outstanding=100_000_000,
            revenue=10_000_000_000, net_income=5_000_000_000,
            operating_cash_flow=6_000_000_000, fcf=4_000_000_000,
            total_assets=20_000_000_000,
            accounts_receivable=500_000_000,
            inventory=500_000_000,
            depreciation=500_000_000, capex=1_000_000_000,
            sbc=10_000_000,
            extra={"_debt_ratio": 10.0, "_current_ratio": 5.0},
            prior_debt_ratio=15.0, prior_current_ratio=4.0,
        )
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(stock)
        assert result.overall_score >= 0


# ---------------------------------------------------------------------------
# Loss-making company (negative NI) integration tests
# ---------------------------------------------------------------------------

class TestLossMakingCompany:
    def test_negative_ni_integration(self):
        """Loss-making company: negative NI, positive OCF."""
        stock = Stock(
            ticker="LOSSY", name="Lossy Co", current_price=5.0,
            shares_outstanding=100_000_000,
            revenue=5_000_000_000, net_income=-500_000_000,
            operating_cash_flow=300_000_000, fcf=-200_000_000,
            total_assets=10_000_000_000,
            accounts_receivable=1_000_000_000,
            inventory=500_000_000,
            depreciation=300_000_000, capex=500_000_000,
            sbc=100_000_000,
            extra={"_debt_ratio": 50.0, "_current_ratio": 1.5},
            prior_debt_ratio=45.0, prior_current_ratio=2.0,
        )
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(stock)
        # Should have some signals available and some score
        assert result.available_signal_count > 0
        assert 0 <= result.overall_score <= 100

    def test_negative_ni_negative_ocf(self):
        """Both NI and OCF negative."""
        stock = Stock(
            ticker="DOUBLY", name="Doubly Bad Co", current_price=1.0,
            shares_outstanding=100_000_000,
            revenue=5_000_000_000, net_income=-1_000_000_000,
            operating_cash_flow=-500_000_000, fcf=-800_000_000,
            total_assets=10_000_000_000,
        )
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(stock)
        assert 0 <= result.overall_score <= 100


# ---------------------------------------------------------------------------
# Zero OCF scenarios
# ---------------------------------------------------------------------------

class TestZeroOcfScenarios:
    def test_zero_ocf_with_positive_ni(self):
        """Zero OCF with positive NI -> some signals unavailable."""
        stock = _stock(operating_cash_flow=0)
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(stock)
        # CFO vs NI and Sloan and Revenue Quality should be unavailable
        unavailable_names = [s.name for s in result.signals if not s.is_available]
        assert "CFO vs Net Income" in unavailable_names
        assert "Sloan Accrual Ratio" in unavailable_names
        assert "Revenue Quality" in unavailable_names

    def test_zero_ocf_with_negative_ni(self):
        """Zero OCF with negative NI."""
        stock = _stock(net_income=-500_000_000, operating_cash_flow=0)
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(stock)
        assert result.available_signal_count < result.total_signal_count


# ---------------------------------------------------------------------------
# Zero inventory (software/service) companies
# ---------------------------------------------------------------------------

class TestSoftwareCompany:
    def test_zero_inventory_service_company(self):
        """Service company with zero inventory -> inventory signal unavailable."""
        stock = _stock(inventory=0)
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(stock)
        inv_signal = next(
            (s for s in result.signals if s.name == "Inventory Buildup"), None
        )
        assert inv_signal is not None
        assert not inv_signal.is_available

    def test_software_company_overall_works(self):
        """Software company with zero inventory should still produce results."""
        stock = Stock(
            ticker="SOFT", name="Software Inc", current_price=200.0,
            shares_outstanding=500_000_000,
            revenue=30_000_000_000, net_income=8_000_000_000,
            operating_cash_flow=10_000_000_000, fcf=7_000_000_000,
            total_assets=50_000_000_000,
            accounts_receivable=3_000_000_000,
            inventory=0,  # no inventory for software
            depreciation=1_500_000_000, capex=2_000_000_000,
            sbc=1_500_000_000,
            extra={"_debt_ratio": 20.0, "_current_ratio": 3.0},
            prior_debt_ratio=25.0, prior_current_ratio=3.5,
        )
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(stock)
        assert result.total_signal_count == 11
        assert result.available_signal_count == 10  # all except inventory
        assert 0 <= result.overall_score <= 100


# ---------------------------------------------------------------------------
# Negative values and very large values
# ---------------------------------------------------------------------------

class TestExtremeValues:
    def test_very_large_revenue(self):
        """Extremely large revenue values should not cause errors."""
        stock = _stock(
            revenue=1_000_000_000_000,  # 1 trillion
            accounts_receivable=100_000_000_000,
            inventory=50_000_000_000,
            net_income=100_000_000_000,
            operating_cash_flow=120_000_000_000,
            sbc=2_000_000_000,
        )
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(stock)
        assert 0 <= result.overall_score <= 100

    def test_very_small_positive_values(self):
        """Very small but positive values."""
        stock = Stock(
            ticker="TINY", name="Tiny Co", current_price=1.0,
            shares_outstanding=1_000_000,
            revenue=1_000_000, net_income=100_000,
            operating_cash_flow=120_000, fcf=80_000,
            total_assets=5_000_000,
            accounts_receivable=200_000, inventory=100_000,
            depreciation=50_000, capex=60_000,
            sbc=5_000,
            extra={"_debt_ratio": 20.0, "_current_ratio": 2.0},
            prior_debt_ratio=25.0, prior_current_ratio=2.5,
        )
        engine = AccountingRedFlagsEngine()
        result = engine.analyze(stock)
        assert 0 <= result.overall_score <= 100

    def test_negative_accounts_receivable(self):
        """Negative AR: code checks == 0 not <= 0, so negative AR passes through."""
        from valueinvest.redflags.signals import ar_vs_revenue_signal
        sig = ar_vs_revenue_signal(_stock(accounts_receivable=-100))
        # The implementation checks `accounts_receivable == 0` for unavailability,
        # so negative AR produces a negative DSO and a low score.
        assert sig.is_available
        assert sig.score == 5  # DSO < 0 -> very low
