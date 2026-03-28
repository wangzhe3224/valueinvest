"""Tests for ROIC vs WACC analysis module."""
import pytest

from valueinvest.stock import Stock
from valueinvest.roic.roic import calculate_roic
from valueinvest.roic.wacc import calculate_wacc
from valueinvest.roic.engine import EconomicProfitEngine
from valueinvest.roic import analyze_economic_profit


@pytest.fixture
def value_creator_stock():
    """High ROIC company: ROIC > WACC."""
    return Stock(
        ticker="GOODCO",
        name="Good Company",
        current_price=150.0,
        shares_outstanding=1_000_000_000,
        eps=10.0,
        bvps=60.0,
        revenue=80_000_000_000,
        net_income=10_000_000_000,
        fcf=12_000_000_000,
        ebit=15_000_000_000,
        operating_margin=18.75,
        tax_rate=25.0,
        roe=20.0,
        total_assets=100_000_000_000,
        total_liabilities=30_000_000_000,
        short_term_debt=5_000_000_000,
        long_term_debt=10_000_000_000,
        interest_expense=800_000_000,
        net_working_capital=15_000_000_000,
        net_fixed_assets=50_000_000_000,
        cost_of_capital=10.0,
        china_10y_yield=1.80,
        aaa_corporate_yield=2.28,
        currency="CNY",
    )


@pytest.fixture
def value_destroyer_stock():
    """Low ROIC company: ROIC < WACC."""
    return Stock(
        ticker="BADCO",
        name="Bad Company",
        current_price=20.0,
        shares_outstanding=500_000_000,
        eps=0.5,
        bvps=10.0,
        revenue=20_000_000_000,
        net_income=250_000_000,
        fcf=100_000_000,
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
        china_10y_yield=1.80,
        aaa_corporate_yield=2.28,
        currency="CNY",
    )


@pytest.fixture
def zero_ebit_stock():
    """Stock with zero EBIT (tests fallback to net_income)."""
    return Stock(
        ticker="ZEROEBIT",
        name="Zero EBIT Co",
        current_price=50.0,
        shares_outstanding=200_000_000,
        eps=2.0,
        revenue=10_000_000_000,
        net_income=400_000_000,
        ebit=0.0,
        tax_rate=25.0,
        total_assets=15_000_000_000,
        total_liabilities=8_000_000_000,
        short_term_debt=2_000_000_000,
        long_term_debt=3_000_000_000,
        net_working_capital=4_000_000_000,
        net_fixed_assets=3_000_000_000,
        cost_of_capital=10.0,
    )


@pytest.fixture
def us_stock():
    """US stock for testing risk-free rate defaults."""
    return Stock(
        ticker="USCO",
        name="US Company",
        current_price=100.0,
        shares_outstanding=500_000_000,
        eps=8.0,
        revenue=40_000_000_000,
        net_income=4_000_000_000,
        ebit=6_000_000_000,
        tax_rate=21.0,
        total_assets=50_000_000_000,
        total_liabilities=20_000_000_000,
        short_term_debt=5_000_000_000,
        long_term_debt=10_000_000_000,
        net_working_capital=10_000_000_000,
        net_fixed_assets=20_000_000_000,
        cost_of_capital=9.0,
        currency="USD",
        aaa_corporate_yield=4.5,
    )


# === ROIC Tests ===


class TestROIC:
    """Tests for ROIC calculation."""

    def test_roic_value_creator(self, value_creator_stock):
        """value_creator_stock should have ROIC > 10% (NOPAT=11.25B, IC=65B, ROIC~17.3%)."""
        result = calculate_roic(value_creator_stock)

        # NOPAT = 15B * (1 - 25/100) = 11.25B
        assert result.nopat == pytest.approx(11_250_000_000)
        # IC = 15B + 50B = 65B
        assert result.invested_capital == pytest.approx(65_000_000_000)
        # ROIC = 11.25 / 65 * 100 ~ 17.3%
        assert result.roic == pytest.approx(17.3077, rel=1e-3)
        assert result.roic > 10.0

    def test_roic_value_destroyer(self, value_destroyer_stock):
        """value_destroyer_stock should have low ROIC (< 10%)."""
        result = calculate_roic(value_destroyer_stock)

        # NOPAT = 400M * 0.75 = 300M
        assert result.nopat == pytest.approx(300_000_000)
        # IC = 3B + 5B = 8B
        assert result.invested_capital == pytest.approx(8_000_000_000)
        # ROIC = 300M / 8B * 100 = 3.75%
        assert result.roic == pytest.approx(3.75)
        assert result.roic < 10.0

    def test_roic_zero_ebit_fallback(self, zero_ebit_stock):
        """zero_ebit_stock should use net_income as NOPAT fallback."""
        result = calculate_roic(zero_ebit_stock)

        # EBIT=0, so NOPAT = net_income = 400M
        assert result.nopat == pytest.approx(400_000_000)
        assert result.components["nopat_source"] == "Net Income (EBIT unavailable)"
        # IC = 4B + 3B = 7B
        assert result.invested_capital == pytest.approx(7_000_000_000)
        # ROIC = 400M / 7B * 100 ~ 5.71%
        assert result.roic == pytest.approx(5.714, rel=1e-3)

    def test_roic_with_override(self, value_creator_stock):
        """invested_capital_override should be used."""
        override_ic = 50_000_000_000
        result = calculate_roic(value_creator_stock, invested_capital_override=override_ic)

        assert result.invested_capital == override_ic
        # ROIC = 11.25B / 50B * 100 = 22.5%
        assert result.roic == pytest.approx(22.5)
        assert result.components["ic_source"] == "override"

    def test_edge_case_zero_invested_capital(self):
        """Stock with zero IC returns roic=0."""
        stock = Stock(
            ticker="NOIC",
            name="No IC Co",
            ebit=5_000_000_000,
            tax_rate=25.0,
            net_working_capital=0,
            net_fixed_assets=0,
            cost_of_capital=10.0,
        )
        result = calculate_roic(stock)

        assert result.invested_capital == 0.0
        assert result.roic == 0.0
        assert result.confidence == "Low"

    def test_edge_case_negative_nopat(self):
        """Negative earnings handled correctly."""
        stock = Stock(
            ticker="LOSS",
            name="Losing Co",
            ebit=-2_000_000_000,
            tax_rate=25.0,
            net_working_capital=10_000_000_000,
            net_fixed_assets=20_000_000_000,
            cost_of_capital=10.0,
        )
        result = calculate_roic(stock)

        # EBIT is negative, falls through to net_income (0) then zero
        assert result.nopat <= 0
        assert result.roic <= 0


# === WACC Tests ===


class TestWACC:
    """Tests for WACC calculation."""

    def test_wacc_simplified(self, value_creator_stock):
        """Default method uses cost_of_capital."""
        result = calculate_wacc(value_creator_stock)

        # Simplified method: cost_of_equity = stock.cost_of_capital = 10.0
        assert result.method == "Simplified"
        assert result.cost_of_equity == pytest.approx(10.0)
        # No net_debt set, so EV = market_cap, equity_weight = 1.0
        assert result.wacc == pytest.approx(10.0)

    def test_wacc_capm(self, value_creator_stock):
        """Providing beta uses CAPM formula."""
        beta = 1.2
        # risk_free_rate defaults to china_10y_yield = 1.80 for CNY
        result = calculate_wacc(value_creator_stock, beta=beta)

        # CAPM: Re = 1.80 + 1.2 * 6.0 = 1.80 + 7.20 = 9.0
        assert result.method == "CAPM"
        assert result.cost_of_equity == pytest.approx(9.0)
        assert result.beta_used == pytest.approx(1.2)

    def test_wacc_cost_of_debt_from_interest(self, value_creator_stock):
        """Cost of debt calculated from interest_expense/total_debt."""
        result = calculate_wacc(value_creator_stock)

        # total_debt = 5B + 10B = 15B, interest = 800M
        # cost_of_debt = 800M / 15B * 100 = 5.333%
        assert result.cost_of_debt == pytest.approx(5.333, rel=1e-3)

    def test_wacc_override(self, value_creator_stock):
        """cost_of_equity_override and cost_of_debt_override work."""
        result = calculate_wacc(
            value_creator_stock,
            cost_of_equity_override=12.0,
            cost_of_debt_override=5.0,
        )

        assert result.cost_of_equity == pytest.approx(12.0)
        assert result.cost_of_debt == pytest.approx(5.0)
        assert result.method == "Simplified (override)"

    def test_wacc_us_stock_risk_free(self, us_stock):
        """US stock uses 4.3% default risk-free."""
        result = calculate_wacc(us_stock, beta=1.0)

        # For USD: rf = 4.3%, CAPM: Re = 4.3 + 1.0 * 6.0 = 10.3
        assert result.risk_free_rate == pytest.approx(4.3)
        assert result.cost_of_equity == pytest.approx(10.3)


# === Economic Profit Tests ===


class TestEconomicProfit:
    """Tests for Economic Profit Engine."""

    def test_economic_profit_positive_spread(self, value_creator_stock):
        """value_creator_stock has value_created=True."""
        engine = EconomicProfitEngine()
        result = engine.analyze(value_creator_stock)

        assert result.value_created is True
        assert result.roic_wacc_spread > 0
        assert result.roic_result.roic > result.wacc_result.wacc

    def test_economic_profit_negative_spread(self, value_destroyer_stock):
        """value_destroyer_stock has value_created=False."""
        engine = EconomicProfitEngine()
        result = engine.analyze(value_destroyer_stock)

        assert result.value_created is False
        assert result.roic_wacc_spread < 0
        assert result.roic_result.roic < result.wacc_result.wacc

    def test_economic_profit_years_to_double(self, value_creator_stock):
        """value_creator_stock should have years_to_double set."""
        engine = EconomicProfitEngine()
        result = engine.analyze(value_creator_stock)

        assert result.years_to_double is not None
        # Rule of 72: 72 / spread (~7.3pp) ~ 9.85 years
        assert result.years_to_double == pytest.approx(9.85, rel=0.05)

    def test_economic_profit_engine_wacc_override(self, value_creator_stock):
        """wacc_override parameter works."""
        engine = EconomicProfitEngine(wacc_override=8.0)
        result = engine.analyze(value_creator_stock)

        assert result.wacc_result.wacc == pytest.approx(8.0)
        assert result.wacc_result.method == "Simplified (override)"

    def test_analyze_economic_profit_convenience(self, value_creator_stock):
        """Convenience function works."""
        result = analyze_economic_profit(value_creator_stock)

        assert result.ticker == "GOODCO"
        assert result.value_created is True
        assert isinstance(result.roic_result.roic, float)
        assert isinstance(result.wacc_result.wacc, float)


# === Output Format Tests ===


class TestOutputFormats:
    """Tests for output format methods."""

    def test_to_summary_format(self, value_creator_stock):
        """All result classes have to_summary()."""
        roic_result = calculate_roic(value_creator_stock)
        wacc_result = calculate_wacc(value_creator_stock)

        roic_summary = roic_result.to_summary()
        assert "ROIC:" in roic_summary
        assert "NOPAT:" in roic_summary

        wacc_summary = wacc_result.to_summary()
        assert "WACC:" in wacc_summary
        assert "Cost of Equity:" in wacc_summary

        engine = EconomicProfitEngine()
        ep_result = engine.analyze(value_creator_stock)
        ep_summary = ep_result.to_summary()
        assert "Economic Profit Analysis" in ep_summary
        assert "Spread:" in ep_summary
        assert "Value Created:" in ep_summary

    def test_str_output(self, value_creator_stock):
        """EconomicProfitResult.__str__() contains key info."""
        engine = EconomicProfitEngine()
        result = engine.analyze(value_creator_stock)

        s = str(result)
        assert "GOODCO" in s
        assert "Value Creator" in s
        assert "ROIC=" in s
        assert "WACC=" in s
        assert "Spread=" in s
