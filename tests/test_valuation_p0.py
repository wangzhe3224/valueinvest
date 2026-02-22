"""
Tests for P0 valuation models: OwnerEarnings, AltmanZScore, EVEBITDA
"""
import pytest

from valueinvest.stock import Stock
from valueinvest.valuation.engine import ValuationEngine
from valueinvest.valuation.quality import OwnerEarnings, AltmanZScore
from valueinvest.valuation.growth import EVEBITDA


class TestOwnerEarnings:
    """Tests for Warren Buffett's Owner Earnings valuation."""

    @pytest.fixture
    def healthy_stock(self):
        """A healthy company with positive owner earnings."""
        return Stock(
            ticker="600887",
            name="伊利股份",
            current_price=26.0,
            shares_outstanding=64e9,  # 64 billion shares
            net_income=10.4e9,  # 10.4 billion net income
            depreciation=2.5e9,  # 2.5 billion depreciation
            capex=4.0e9,  # 4 billion capex (3B maintenance)
            net_working_capital=5.0e9,
            revenue=90.0e9,
            cost_of_capital=10.0,
            growth_rate=5.0,
            eps=1.65,
        )

    @pytest.fixture
    def value_destructive_stock(self):
        """A company with negative owner earnings."""
        return Stock(
            ticker="LOSS",
            name="亏损公司",
            current_price=10.0,
            shares_outstanding=100e6,
            net_income=1.0e9,
            depreciation=0.5e9,
            capex=5.0e9,  # Capex exceeds earnings
            net_working_capital=0,
            revenue=5.0e9,
            cost_of_capital=10.0,
            growth_rate=0,
            eps=0.1,
        )

    def test_owner_earnings_calculation(self, healthy_stock):
        """Test basic owner earnings calculation."""
        model = OwnerEarnings()
        result = model.calculate(healthy_stock)

        assert result.method == "Owner Earnings"
        # Owner earnings = net_income + depreciation - maintenance_capex - nwc_change
        # 10.4B + 2.5B - 2.8B (70% of 4B) - 0.5B (10% of 5B NWC)
        # = 10.4 + 2.5 - 2.8 - 0.5 = 9.6B
        assert result.fair_value > 0
        assert "Owner Earnings" in result.analysis[0]
        assert result.applicability == "Applicable"

    def test_owner_earnings_quality_metrics(self, healthy_stock):
        """Test earnings quality assessment."""
        model = OwnerEarnings()
        result = model.calculate(healthy_stock)

        assert "earnings_quality" in result.details
        # Earnings quality should be positive for healthy company
        assert result.details["earnings_quality"] > 0

    def test_value_destructive_company(self, value_destructive_stock):
        """Test handling of value-destructive companies."""
        model = OwnerEarnings()
        result = model.calculate(value_destructive_stock)

        # Should return error for negative owner earnings
        assert result.fair_value == 0
        assert "negative" in result.assessment.lower() or "error" in result.assessment.lower()

    def test_owner_earnings_custom_params(self, healthy_stock):
        """Test custom parameters."""
        model = OwnerEarnings(maintenance_capex_pct=0.6, cost_of_capital=12.0)
        result = model.calculate(healthy_stock)

        assert result.fair_value > 0

    def test_missing_data_estimates(self):
        """Test estimation when data is missing."""
        stock = Stock(
            ticker="MINIMAL",
            name="数据不足",
            current_price=50.0,
            shares_outstanding=100e6,
            net_income=5.0e9,
            revenue=50.0e9,
            cost_of_capital=10.0,
            eps=0.5,
        )

        model = OwnerEarnings()
        result = model.calculate(stock)

        # Should estimate missing values and still calculate
        assert result.method == "Owner Earnings"
        # Should have warnings about estimates
        assert len([a for a in result.analysis if "estimated" in a.lower() or "Note" in a]) > 0


class TestAltmanZScore:
    """Tests for Altman Z-Score bankruptcy prediction."""

    @pytest.fixture
    def safe_company(self):
        """A financially healthy company (Safe Zone)."""
        return Stock(
            ticker="SAFE",
            name="安全公司",
            current_price=100.0,
            shares_outstanding=100e6,
            current_assets=8.0e9,
            total_assets=10.0e9,
            total_liabilities=3.0e9,
            retained_earnings=4.0e9,
            ebit=2.0e9,
            revenue=15.0e9,
            net_income=1.5e9,
            net_working_capital=5.0e9,  # CA - CL
            operating_margin=15.0,
        )

    @pytest.fixture
    def distressed_company(self):
        """A financially distressed company (Distress Zone)."""
        return Stock(
            ticker="DIST",
            name="困境公司",
            current_price=5.0,
            shares_outstanding=100e6,
            current_assets=1.0e9,
            total_assets=10.0e9,
            total_liabilities=9.0e9,
            retained_earnings=-2.0e9,
            ebit=0.1e9,
            revenue=3.0e9,
            net_income=-0.5e9,
            net_working_capital=-0.5e9,
            operating_margin=3.0,
        )

    def test_safe_zone_company(self, safe_company):
        """Test company in safe zone (Z > 2.99)."""
        model = AltmanZScore()
        result = model.calculate(safe_company)

        assert result.method == "Altman Z-Score"
        assert result.details["z_score"] > 2.99
        assert result.details["zone"] == "Safe Zone"
        assert result.details["risk_level"] == "Low"
        assert "Low Bankruptcy Risk" in result.assessment

    def test_distress_zone_company(self, distressed_company):
        """Test company in distress zone (Z < 1.81)."""
        model = AltmanZScore()
        result = model.calculate(distressed_company)

        assert result.details["z_score"] < 1.81
        assert result.details["zone"] == "Distress Zone"
        assert result.details["risk_level"] == "High"

    def test_z_score_components(self, safe_company):
        """Test Z-Score component analysis."""
        model = AltmanZScore()
        result = model.calculate(safe_company)

        assert "X1_WorkingCapital" in result.components
        assert "X2_RetainedEarnings" in result.components
        assert "X3_EBIT" in result.components
        assert "X4_MarketCap_Liabilities" in result.components
        assert "X5_AssetTurnover" in result.components

    def test_weakest_factor_identified(self, safe_company):
        """Test that weakest factor is identified."""
        model = AltmanZScore()
        result = model.calculate(safe_company)

        # Should identify the weakest factor
        assert "Weakest factor" in str(result.analysis)

    def test_missing_data_estimates(self):
        """Test handling of missing data with estimates."""
        stock = Stock(
            ticker="PARTIAL",
            name="部分数据",
            current_price=50.0,
            shares_outstanding=100e6,
            total_assets=5.0e9,
            total_liabilities=2.0e9,
            net_income=0.5e9,
        )

        model = AltmanZScore()
        result = model.calculate(stock)

        assert result.method == "Altman Z-Score"
        # Should have estimates in analysis
        assert result.confidence in ["Low", "Medium"]  # Lower confidence with estimates


class TestEVEBITDA:
    """Tests for EV/EBITDA valuation."""

    @pytest.fixture
    def typical_company(self):
        """A typical company for EV/EBITDA analysis."""
        return Stock(
            ticker="TYP",
            name="典型公司",
            current_price=50.0,
            shares_outstanding=100e6,  # Market cap = 5B
            ebitda=1.0e9,  # EBITDA = 1B
            ebit=0.8e9,
            depreciation=0.2e9,
            net_debt=1.0e9,  # EV = 6B, EV/EBITDA = 6x
            revenue=10.0e9,
            operating_margin=10.0,
            roe=15.0,
            growth_rate=8.0,
            net_income=0.6e9,
        )

    @pytest.fixture
    def high_leverage_company(self):
        """A high-leverage company."""
        return Stock(
            ticker="LEV",
            name="高杠杆公司",
            current_price=30.0,
            shares_outstanding=100e6,  # Market cap = 3B
            ebitda=0.5e9,
            net_debt=4.0e9,  # EV = 7B, high debt
            revenue=5.0e9,
        )

    def test_ev_ebitda_calculation(self, typical_company):
        """Test basic EV/EBITDA calculation."""
        model = EVEBITDA()
        result = model.calculate(typical_company)

        assert result.method == "EV/EBITDA"
        assert result.fair_value > 0
        # Current EV/EBITDA should be calculated
        assert "current_ev_ebitda" in result.details
        assert result.details["current_ev_ebitda"] > 0

    def test_fair_multiple_applied(self, typical_company):
        """Test custom fair multiple."""
        model = EVEBITDA(fair_multiple=12.0)
        result = model.calculate(typical_company)

        assert result.details["fair_ev_ebitda_multiple"] == 12.0

    def test_ebitda_estimation_from_ebit(self):
        """Test EBITDA estimation when only EBIT available."""
        stock = Stock(
            ticker="NO_EBITDA",
            name="无EBITDA",
            current_price=40.0,
            shares_outstanding=100e6,
            ebit=0.5e9,
            depreciation=0.1e9,
            net_debt=0.5e9,
        )

        model = EVEBITDA()
        result = model.calculate(stock)

        assert result.method == "EV/EBITDA"
        # Should calculate EBITDA from EBIT + Depreciation
        assert "ebitda" in result.details

    def test_multiple_assessment(self, typical_company):
        """Test multiple assessment categories."""
        model = EVEBITDA()
        result = model.calculate(typical_company)

        # Should have multiple assessment
        assert any(
            term in result.analysis[0].lower()
            for term in ["cheap", "attractive", "reasonable", "expensive"]
        )

    def test_high_leverage_discount(self, high_leverage_company):
        """Test that high leverage is handled."""
        model = EVEBITDA()
        result = model.calculate(high_leverage_company)

        # Should still calculate but may have notes about leverage
        assert result.method == "EV/EBITDA"

    def test_negative_ebitda_handling(self):
        """Test handling of negative EBITDA."""
        stock = Stock(
            ticker="NEG",
            name="负EBITDA",
            current_price=10.0,
            shares_outstanding=100e6,
            ebit=-0.1e9,  # Negative EBIT
            depreciation=0.05e9,
            net_debt=0,
            net_income=-0.1e9,
        )

        model = EVEBITDA()
        result = model.calculate(stock)

        # Should return error for negative EBITDA
        assert result.fair_value == 0 or "Cannot estimate" in result.assessment


class TestValuationEngineIntegration:
    """Integration tests for ValuationEngine with new methods."""

    @pytest.fixture
    def engine(self):
        return ValuationEngine()

    @pytest.fixture
    def test_stock(self):
        return Stock(
            ticker="TEST",
            name="测试公司",
            current_price=50.0,
            shares_outstanding=100e6,
            eps=2.0,
            bvps=20.0,
            revenue=10.0e9,
            net_income=2.0e9,
            fcf=1.5e9,
            current_assets=3.0e9,
            total_liabilities=2.0e9,
            total_assets=5.0e9,
            net_debt=0.5e9,
            depreciation=0.3e9,
            capex=0.5e9,
            net_working_capital=1.0e9,
            ebit=0.5e9,
            ebitda=0.8e9,
            retained_earnings=1.5e9,
            operating_margin=5.0,
            tax_rate=25.0,
            roe=20.0,
            growth_rate=10.0,
            dividend_per_share=0.5,
            dividend_yield=1.0,
            cost_of_capital=10.0,
            discount_rate=10.0,
        )

    def test_owner_earnings_in_engine(self, engine, test_stock):
        """Test Owner Earnings accessible via engine."""
        result = engine.run_single(test_stock, "owner_earnings")
        assert result.method == "Owner Earnings"

    def test_altman_z_in_engine(self, engine, test_stock):
        """Test Altman Z-Score accessible via engine."""
        result = engine.run_single(test_stock, "altman_z")
        assert result.method == "Altman Z-Score"

    def test_ev_ebitda_in_engine(self, engine, test_stock):
        """Test EV/EBITDA accessible via engine."""
        result = engine.run_single(test_stock, "ev_ebitda")
        assert result.method == "EV/EBITDA"

    def test_new_methods_in_run_all(self, engine, test_stock):
        """Test new methods included in run_all."""
        results = engine.run_all(test_stock)
        method_names = [r.method for r in results]

        assert "Owner Earnings" in method_names
        assert "Altman Z-Score" in method_names
        assert "EV/EBITDA" in method_names

    def test_value_methods_includes_new(self, engine, test_stock):
        """Test new methods in VALUE_METHODS."""
        results = engine.run_value(test_stock)
        method_names = [r.method for r in results]

        # VALUE_METHODS should include owner_earnings and altman_z
        assert "Owner Earnings" in method_names
        assert "Altman Z-Score" in method_names

    def test_growth_methods_includes_ev_ebitda(self, engine, test_stock):
        """Test EV/EBITDA in GROWTH_METHODS."""
        results = engine.run_growth(test_stock)
        method_names = [r.method for r in results]

        assert "EV/EBITDA" in method_names

    def test_get_available_methods(self, engine):
        """Test new methods in available methods list."""
        methods = engine.get_available_methods()

        assert "owner_earnings" in methods
        assert "altman_z" in methods
        assert "ev_ebitda" in methods

    def test_custom_kwargs_passed(self, engine, test_stock):
        """Test custom kwargs are passed to models."""
        result = engine.run_single(
            test_stock,
            "ev_ebitda",
            fair_multiple=15.0,
        )

        # Should use the custom multiple
        assert result.details["fair_ev_ebitda_multiple"] == 15.0
