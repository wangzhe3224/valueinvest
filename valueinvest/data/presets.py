"""
Preset stock data for common companies.
"""
from ..stock import Stock


def google() -> Stock:
    return Stock(
        ticker="GOOGL",
        name="Alphabet Inc.",
        exchange="NASDAQ",
        currency="USD",
        current_price=309.00,
        shares_outstanding=13.31e9,
        eps=8.13,
        bvps=24.42,
        revenue=350.02e9,
        net_income=100.12e9,
        fcf=72.8e9,
        current_assets=163.71e9,
        total_liabilities=125.18e9,
        total_assets=450.256e9,
        net_debt=-95.66e9,
        depreciation=15.5e9,
        capex=52.5e9,
        net_working_capital=-10.0e9,
        operating_margin=32.0,
        tax_rate=16.5,
        roe=14.9,
        growth_rate=12.0,
        dividend_per_share=0.0,
        dividend_yield=0.0,
        dividend_growth_rate=0.0,
        cost_of_capital=9.0,
        discount_rate=9.0,
        terminal_growth=2.5,
        growth_rate_1_5=14.0,
        growth_rate_6_10=8.0,
        sectors=["Technology", "Internet Services"],
    )


def china_yangtze_power() -> Stock:
    return Stock(
        ticker="600900.SH",
        name="长江电力 / China Yangtze Power",
        exchange="SH",
        currency="CNY",
        current_price=27.50,
        shares_outstanding=24.468e9,
        eps=1.35,
        bvps=9.07,
        revenue=844.92e9,
        net_income=325.0e9,
        fcf=300.0e9,
        current_assets=27.11e9,
        total_liabilities=335.77e9,
        total_assets=568.77e9,
        net_debt=284.55e9,
        depreciation=12.0e9,
        capex=35.0e9,
        net_working_capital=-5.0e9,
        operating_margin=53.7,
        tax_rate=25.0,
        roe=14.9,
        growth_rate=3.0,
        dividend_per_share=0.943,
        dividend_yield=3.43,
        dividend_growth_rate=3.0,
        cost_of_capital=8.5,
        discount_rate=8.5,
        terminal_growth=2.0,
        growth_rate_1_5=3.0,
        growth_rate_6_10=2.0,
        sectors=["Utilities", "Hydropower"],
    )


def icbc() -> Stock:
    return Stock(
        ticker="601398.SH",
        name="工商银行 / ICBC",
        exchange="SH",
        currency="CNY",
        current_price=7.30,
        shares_outstanding=3564.06e9,
        eps=0.98,
        bvps=10.68,
        revenue=8218.03e9,
        net_income=3658.63e9,
        fcf=0,
        current_assets=0,
        total_liabilities=0,
        total_assets=48821.75e9,
        net_debt=0,
        depreciation=0,
        capex=0,
        net_working_capital=0,
        operating_margin=0,
        tax_rate=25.0,
        roe=9.22,
        growth_rate=2.0,
        dividend_per_share=0.308,
        dividend_yield=4.22,
        dividend_growth_rate=2.5,
        cost_of_capital=10.0,
        discount_rate=10.0,
        terminal_growth=2.0,
        growth_rate_1_5=2.0,
        growth_rate_6_10=2.0,
        npl_ratio=1.34,
        provision_coverage=214.91,
        capital_adequacy_ratio=19.39,
        sectors=["Financials", "Banking"],
    )


PRESETS = {
    "google": google,
    "googl": google,
    "yangtze": china_yangtze_power,
    "cyp": china_yangtze_power,
    "600900": china_yangtze_power,
    "icbc": icbc,
    "601398": icbc,
}


def get_preset(name: str) -> Stock:
    name_lower = name.lower()
    if name_lower in PRESETS:
        return PRESETS[name_lower]()
    raise ValueError(f"Unknown preset: {name}. Available: {list(PRESETS.keys())}")
