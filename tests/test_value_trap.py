"""
Tests for Value Trap Detection module.

Covers:
- Financial health checks (Altman Z-Score based)
- Business deterioration detection
- Moat erosion detection
- AI vulnerability assessment
- Dividend signal detection
- Overall trap risk scoring
"""
import pytest

from valueinvest.stock import Stock
from valueinvest.valuation.value_trap import (
    ValueTrapDetector,
    ValueTrapResult,
    TrapRiskLevel,
    TrapCategory,
    TrapIndicator,
    detect_value_trap,
)


class TestValueTrapDetector:
    """Tests for ValueTrapDetector class."""

    @pytest.fixture
    def healthy_stock(self):
        """A healthy company with low trap risk."""
        return Stock(
            ticker="HEALTHY",
            name="健康公司",
            current_price=100.0,
            shares_outstanding=1e9,
            eps=5.0,
            bvps=50.0,
            revenue=50e9,
            net_income=5e9,
            fcf=4e9,
            roe=20.0,
            operating_margin=15.0,
            total_assets=60e9,
            total_liabilities=20e9,
            current_assets=25e9,
            net_working_capital=10e9,
            retained_earnings=15e9,
            ebit=7.5e9,
            dividend_per_share=2.0,
            dividend_yield=2.0,
            dividend_growth_rate=8.0,
            growth_rate=10.0,
            cost_of_capital=10.0,
        )

    @pytest.fixture
    def distressed_stock(self):
        """A distressed company with high trap risk."""
        return Stock(
            ticker="DISTRESS",
            name="困境公司",
            current_price=10.0,
            shares_outstanding=1e9,
            eps=0.5,
            bvps=5.0,
            revenue=10e9,
            net_income=-0.5e9,  # Negative earnings
            fcf=-1e9,  # Negative FCF
            roe=3.0,  # Low ROE
            operating_margin=2.0,  # Low margin
            total_assets=20e9,
            total_liabilities=18e9,  # High debt
            current_assets=8e9,
            net_working_capital=-2e9,  # Negative working capital
            retained_earnings=-5e9,  # Negative retained earnings
            ebit=0.5e9,
            dividend_per_share=0.0,
            dividend_yield=0.0,
            growth_rate=-5.0,
            cost_of_capital=10.0,
        )

    @pytest.fixture
    def ai_vulnerable_stock(self):
        """A company in AI-vulnerable industry."""
        return Stock(
            ticker="EDTECH",
            name="教育科技公司",
            current_price=20.0,
            shares_outstanding=500e6,
            eps=1.0,
            bvps=15.0,
            revenue=5e9,
            net_income=0.5e9,
            fcf=0.3e9,
            roe=12.0,
            operating_margin=12.0,
            total_assets=10e9,
            total_liabilities=4e9,
            current_assets=5e9,
            net_working_capital=2e9,
            retained_earnings=3e9,
            ebit=0.6e9,
            dividend_per_share=0.0,
            dividend_yield=0.0,
            growth_rate=3.0,
            cost_of_capital=10.0,
        )

    @pytest.fixture
    def dividend_trap_stock(self):
        """A company with unsustainable dividend."""
        return Stock(
            ticker="DIVTRAP",
            name="分红陷阱",
            current_price=50.0,
            shares_outstanding=1e9,
            eps=1.0,
            bvps=30.0,
            revenue=20e9,
            net_income=1e9,
            fcf=0.5e9,  # Low FCF
            roe=8.0,
            operating_margin=8.0,
            total_assets=40e9,
            total_liabilities=20e9,
            current_assets=15e9,
            net_working_capital=5e9,
            retained_earnings=10e9,
            ebit=1.6e9,
            dividend_per_share=1.5,  # 150% payout ratio
            dividend_yield=3.0,
            dividend_growth_rate=-5.0,  # Dividend cut
            growth_rate=0.0,
            cost_of_capital=10.0,
        )

    def test_healthy_stock_low_risk(self, healthy_stock):
        """Test that healthy company has low trap risk."""
        detector = ValueTrapDetector(
            revenue_cagr_5y=8.0,
            margin_trend="stable",
            roe_trend="stable",
            industry="consumer_staples",
        )
        result = detector.detect(healthy_stock)

        assert result.overall_risk in (TrapRiskLevel.LOW, TrapRiskLevel.MODERATE)
        assert result.trap_score < 40
        assert not result.is_trap
        assert len(result.critical_issues) == 0

    def test_distressed_stock_high_risk(self, distressed_stock):
        """Test that distressed company has high trap risk."""
        detector = ValueTrapDetector(
            revenue_cagr_5y=-5.0,
            margin_trend="compressing",
            roe_trend="declining",
        )
        result = detector.detect(distressed_stock)

        assert result.overall_risk in (TrapRiskLevel.HIGH, TrapRiskLevel.CRITICAL)
        assert result.trap_score >= 55
        assert result.is_trap
        assert len(result.critical_issues) > 0

    def test_ai_vulnerable_industry(self, ai_vulnerable_stock):
        """Test AI vulnerability detection."""
        detector = ValueTrapDetector(
            revenue_cagr_5y=-2.0,
            industry="education",
        )
        result = detector.detect(ai_vulnerable_stock)

        # Should have AI vulnerability indicator
        ai_indicators = [
            i for i in result.indicators if i.category == TrapCategory.AI_VULNERABILITY
        ]
        assert len(ai_indicators) > 0
        assert ai_indicators[0].risk_score >= 80  # Education is high risk

    def test_dividend_trap_detection(self, dividend_trap_stock):
        """Test dividend sustainability warning."""
        detector = ValueTrapDetector()
        result = detector.detect(dividend_trap_stock)

        # Should have dividend warning
        div_indicators = [
            i for i in result.indicators if i.category == TrapCategory.DIVIDEND_SIGNAL
        ]
        assert len(div_indicators) > 0

        # Payout ratio > 100% should be flagged
        payout_indicators = [i for i in div_indicators if "Payout" in i.name]
        assert any(i.risk_score >= 70 for i in payout_indicators)

    def test_financial_health_altman_z(self, distressed_stock):
        """Test Altman Z-Score based financial health check."""
        detector = ValueTrapDetector()
        result = detector.detect(distressed_stock)

        # Should have financial health indicator
        fin_indicators = [
            i for i in result.indicators if i.category == TrapCategory.FINANCIAL_HEALTH
        ]
        assert len(fin_indicators) > 0

        # Z-Score indicator should be present
        z_indicators = [i for i in fin_indicators if "Z-Score" in i.name]
        assert len(z_indicators) > 0

    def test_business_deterioration_detection(self, healthy_stock):
        """Test business deterioration trend detection."""
        detector = ValueTrapDetector(
            revenue_cagr_5y=-3.0,  # Declining revenue
            margin_trend="compressing",
        )
        result = detector.detect(healthy_stock)

        biz_indicators = [
            i for i in result.indicators if i.category == TrapCategory.BUSINESS_DETERIORATION
        ]
        assert len(biz_indicators) > 0

        # Revenue decline should be flagged
        revenue_indicators = [i for i in biz_indicators if "Revenue" in i.name]
        assert any(i.risk_score >= 60 for i in revenue_indicators)

    def test_moat_erosion_detection(self, healthy_stock):
        """Test moat erosion detection."""
        detector = ValueTrapDetector(
            roe_trend="declining",
            market_share_trend="declining",
        )
        result = detector.detect(healthy_stock)

        moat_indicators = [i for i in result.indicators if i.category == TrapCategory.MOAT_EROSION]
        assert len(moat_indicators) > 0

    def test_convenience_function(self, healthy_stock):
        """Test detect_value_trap convenience function."""
        result = detect_value_trap(
            healthy_stock,
            revenue_cagr_5y=5.0,
            margin_trend="stable",
            roe_trend="improving",
            industry="utilities",
        )

        assert isinstance(result, ValueTrapResult)
        assert result.ticker == "HEALTHY"
        assert result.trap_score < 50

    def test_ai_vulnerability_override(self, healthy_stock):
        """Test manual AI vulnerability override."""
        detector = ValueTrapDetector(
            ai_vulnerability_override=0.9,  # High vulnerability
        )
        result = detector.detect(healthy_stock)

        ai_indicators = [
            i for i in result.indicators if i.category == TrapCategory.AI_VULNERABILITY
        ]
        assert any(i.value == 0.9 for i in ai_indicators)

    def test_calculate_method(self, healthy_stock):
        """Test calculate() method returns ValuationResult."""
        detector = ValueTrapDetector()
        result = detector.calculate(healthy_stock)

        assert result.method == "Value Trap Detector"
        assert "trap_score" in result.details
        assert "overall_risk" in result.details
        assert "is_trap" in result.details

    def test_negative_earnings_critical(self, distressed_stock):
        """Test that negative earnings is flagged as critical."""
        detector = ValueTrapDetector()
        result = detector.detect(distressed_stock)

        assert any("Negative Earnings" in issue for issue in result.critical_issues)

    def test_no_dividend_neutral(self, healthy_stock):
        """Test that no dividend is neutral for dividend check."""
        healthy_stock.dividend_yield = 0
        healthy_stock.dividend_per_share = 0

        detector = ValueTrapDetector()
        result = detector.detect(healthy_stock)

        div_indicators = [
            i for i in result.indicators if i.category == TrapCategory.DIVIDEND_SIGNAL
        ]
        # Should have one indicator saying "no dividend - not applicable"
        assert len(div_indicators) == 1
        assert div_indicators[0].risk_score == 0

    def test_result_properties(self, distressed_stock):
        """Test ValueTrapResult properties."""
        detector = ValueTrapDetector(
            revenue_cagr_5y=-10.0,
            roe_trend="declining",
        )
        result = detector.detect(distressed_stock)

        # Test is_trap property
        if result.overall_risk in (TrapRiskLevel.HIGH, TrapRiskLevel.CRITICAL):
            assert result.is_trap is True

        # Test should_avoid property
        if result.overall_risk == TrapRiskLevel.CRITICAL:
            assert result.should_avoid is True

    def test_analysis_generation(self, healthy_stock, distressed_stock):
        """Test analysis text generation."""
        detector = ValueTrapDetector()

        healthy_result = detector.detect(healthy_stock)
        distressed_result = detector.detect(distressed_stock)

        # Both should have analysis
        assert len(healthy_result.analysis) > 0
        assert len(distressed_result.analysis) > 0

        # Should include trap score
        assert any("Trap Score" in line for line in healthy_result.analysis)

    def test_recommendation_generation(self, healthy_stock, distressed_stock):
        """Test investment recommendation generation."""
        detector = ValueTrapDetector()

        healthy_result = detector.detect(healthy_stock)
        distressed_result = detector.detect(distressed_stock)

        # Healthy should have positive recommendation
        assert (
            "LOW RISK" in healthy_result.recommendation
            or "CAUTION" in healthy_result.recommendation
        )

        # Distressed should have warning
        assert (
            "AVOID" in distressed_result.recommendation
            or "HIGH RISK" in distressed_result.recommendation
        )


class TestTrapRiskLevel:
    """Tests for TrapRiskLevel enum."""

    def test_risk_levels_exist(self):
        """Test all risk levels are defined."""
        assert TrapRiskLevel.LOW.value == "low"
        assert TrapRiskLevel.MODERATE.value == "moderate"
        assert TrapRiskLevel.HIGH.value == "high"
        assert TrapRiskLevel.CRITICAL.value == "critical"


class TestTrapCategory:
    """Tests for TrapCategory enum."""

    def test_categories_exist(self):
        """Test all categories are defined."""
        assert TrapCategory.FINANCIAL_HEALTH.value == "financial_health"
        assert TrapCategory.BUSINESS_DETERIORATION.value == "business_deterioration"
        assert TrapCategory.MOAT_EROSION.value == "moat_erosion"
        assert TrapCategory.AI_VULNERABILITY.value == "ai_vulnerability"
        assert TrapCategory.DIVIDEND_SIGNAL.value == "dividend_signal"


class TestTrapIndicator:
    """Tests for TrapIndicator dataclass."""

    def test_indicator_creation(self):
        """Test creating a trap indicator."""
        indicator = TrapIndicator(
            category=TrapCategory.FINANCIAL_HEALTH,
            name="Test Indicator",
            value=1.5,
            risk_score=75.0,
            description="Test description",
            is_warning=True,
            is_critical=False,
        )

        assert indicator.category == TrapCategory.FINANCIAL_HEALTH
        assert indicator.name == "Test Indicator"
        assert indicator.value == 1.5
        assert indicator.risk_score == 75.0
        assert indicator.is_warning is True
        assert indicator.is_critical is False


class TestValueTrapResult:
    """Tests for ValueTrapResult dataclass."""

    def test_result_creation(self):
        """Test creating a trap result."""
        result = ValueTrapResult(
            ticker="TEST",
            overall_risk=TrapRiskLevel.HIGH,
            trap_score=65.0,
            financial_health_score=60.0,
            business_deterioration_score=70.0,
            moat_erosion_score=55.0,
            ai_vulnerability_score=40.0,
            dividend_signal_score=30.0,
        )

        assert result.ticker == "TEST"
        assert result.overall_risk == TrapRiskLevel.HIGH
        assert result.trap_score == 65.0
        assert result.is_trap is True
        assert result.should_avoid is False  # HIGH, not CRITICAL

    def test_critical_result(self):
        """Test critical risk result properties."""
        result = ValueTrapResult(
            ticker="CRITICAL",
            overall_risk=TrapRiskLevel.CRITICAL,
            trap_score=85.0,
        )

        assert result.is_trap is True
        assert result.should_avoid is True
