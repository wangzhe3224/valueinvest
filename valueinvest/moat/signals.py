"""Individual moat signal calculators."""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from valueinvest.stock import Stock

from .base import MoatSignal, MoatSignalCategory, SignalStrength, _score_to_strength


def roic_signal(stock: "Stock", roic: Optional[float] = None, wacc: Optional[float] = None) -> MoatSignal:
    """ROIC vs WACC spread — strongest moat indicator."""
    if roic is not None and wacc is not None:
        spread = roic - wacc
        value = spread
        # Score based on spread
        if spread > 10:
            score = 90
        elif spread > 5:
            score = 75
        elif spread > 2:
            score = 60
        elif spread > 0:
            score = 45
        elif spread > -2:
            score = 25
        else:
            score = 10
        description = f"ROIC ({roic:.1f}%) vs WACC ({wacc:.1f}%): spread={spread:+.1f}pp"
    elif stock.ebit > 0 and (stock.net_working_capital > 0 or stock.net_fixed_assets > 0):
        tax_rate = stock.tax_rate if stock.tax_rate > 0 else 25.0
        nopat = stock.ebit * (1 - tax_rate / 100)
        ic = stock.net_working_capital + stock.net_fixed_assets
        if ic > 0:
            computed_roic = (nopat / ic) * 100
            spread = computed_roic - stock.cost_of_capital
            value = spread
            if spread > 10:
                score = 85
            elif spread > 5:
                score = 70
            elif spread > 2:
                score = 55
            elif spread > 0:
                score = 40
            else:
                score = 20
            description = f"ROIC ({computed_roic:.1f}%) vs CoC ({stock.cost_of_capital:.1f}%): spread={spread:+.1f}pp"
        else:
            return MoatSignal(name="ROIC vs WACC", category=MoatSignalCategory.PROFITABILITY,
                              value=0, score=0, strength=SignalStrength.NONE,
                              description="Insufficient data for invested capital", is_available=False)
    else:
        return MoatSignal(name="ROIC vs WACC", category=MoatSignalCategory.PROFITABILITY,
                          value=0, score=0, strength=SignalStrength.NONE,
                          description="No EBIT data available", is_available=False)

    return MoatSignal(name="ROIC vs WACC", category=MoatSignalCategory.PROFITABILITY,
                      value=value, score=score, strength=_score_to_strength(score),
                      weight=1.5, description=description)


def margin_stability_signal(stock: "Stock", prior_gross_margin: Optional[float] = None) -> MoatSignal:
    """Gross margin level and stability."""
    gm = stock.gross_margin
    if gm <= 0:
        return MoatSignal(name="Margin Stability", category=MoatSignalCategory.PROFITABILITY,
                          value=0, score=0, strength=SignalStrength.NONE,
                          description="No gross margin data", is_available=False)

    prior = prior_gross_margin if prior_gross_margin is not None else stock.prior_gross_margin

    # Level scoring
    if gm > 40:
        level_score = 80
    elif gm > 30:
        level_score = 65
    elif gm > 20:
        level_score = 50
    elif gm > 10:
        level_score = 35
    else:
        level_score = 20

    # Stability bonus/penalty
    stability_adj = 0
    stability_text = ""
    if prior > 0:
        change = gm - prior
        if abs(change) < 1:
            stability_adj = 10
            stability_text = f" (stable, Δ={change:+.1f}pp)"
        elif change > 0:
            stability_adj = 5
            stability_text = f" (improving, Δ={change:+.1f}pp)"
        elif change > -3:
            stability_adj = 0
            stability_text = f" (slight decline, Δ={change:+.1f}pp)"
        else:
            stability_adj = -10
            stability_text = f" (declining, Δ={change:+.1f}pp)"

    score = max(0, min(100, level_score + stability_adj))
    return MoatSignal(name="Margin Stability", category=MoatSignalCategory.PROFITABILITY,
                      value=gm, score=score, strength=_score_to_strength(score),
                      description=f"Gross margin: {gm:.1f}%{stability_text}")


def operating_margin_signal(stock: "Stock") -> MoatSignal:
    """Operating margin level as moat indicator."""
    om = stock.operating_margin
    if om <= 0:
        return MoatSignal(name="Operating Margin", category=MoatSignalCategory.PROFITABILITY,
                          value=0, score=0, strength=SignalStrength.NONE,
                          description="No operating margin data", is_available=False)

    if om > 30:
        score = 85
    elif om > 25:
        score = 75
    elif om > 20:
        score = 60
    elif om > 15:
        score = 45
    elif om > 10:
        score = 30
    else:
        score = 15

    return MoatSignal(name="Operating Margin", category=MoatSignalCategory.PROFITABILITY,
                      value=om, score=score, strength=_score_to_strength(score),
                      description=f"Operating margin: {om:.1f}%")


def fcf_conversion_signal(stock: "Stock") -> MoatSignal:
    """FCF / Net Income ratio — earnings quality."""
    if stock.net_income <= 0:
        return MoatSignal(name="FCF Conversion", category=MoatSignalCategory.EFFICIENCY,
                          value=0, score=0, strength=SignalStrength.NONE,
                          description="Negative net income", is_available=False)

    ratio = stock.fcf / stock.net_income
    if ratio > 1.5:
        score = 90
    elif ratio > 1.2:
        score = 80
    elif ratio > 0.8:
        score = 60
    elif ratio > 0.5:
        score = 40
    else:
        score = 20

    return MoatSignal(name="FCF Conversion", category=MoatSignalCategory.EFFICIENCY,
                      value=ratio, score=score, strength=_score_to_strength(score),
                      description=f"FCF/NI ratio: {ratio:.2f}x")


def asset_turnover_signal(stock: "Stock") -> MoatSignal:
    """Asset turnover efficiency."""
    if stock.total_assets <= 0:
        return MoatSignal(name="Asset Turnover", category=MoatSignalCategory.EFFICIENCY,
                          value=0, score=0, strength=SignalStrength.NONE,
                          description="No total assets data", is_available=False)

    turnover = stock.revenue / stock.total_assets
    if turnover > 1.5:
        score = 80
    elif turnover > 1.0:
        score = 65
    elif turnover > 0.7:
        score = 50
    elif turnover > 0.4:
        score = 35
    else:
        score = 20

    return MoatSignal(name="Asset Turnover", category=MoatSignalCategory.EFFICIENCY,
                      value=turnover, score=score, strength=_score_to_strength(score),
                      description=f"Asset turnover: {turnover:.2f}x")


def revenue_stability_signal(stock: "Stock", revenue_cagr_5y: Optional[float] = None) -> MoatSignal:
    """Revenue growth stability."""
    cagr = revenue_cagr_5y if revenue_cagr_5y is not None else stock.revenue_cagr_5y
    if cagr <= 0 and stock.growth_rate <= 0:
        return MoatSignal(name="Revenue Stability", category=MoatSignalCategory.GROWTH,
                          value=0, score=0, strength=SignalStrength.NONE,
                          description="No revenue growth data", is_available=False)

    growth = cagr if cagr > 0 else stock.growth_rate
    value = growth

    if growth > 15:
        score = 85
    elif growth > 10:
        score = 75
    elif growth > 5:
        score = 60
    elif growth > 0:
        score = 45
    else:
        score = 15

    return MoatSignal(name="Revenue Stability", category=MoatSignalCategory.GROWTH,
                      value=value, score=score, strength=_score_to_strength(score),
                      description=f"Revenue CAGR 5Y: {growth:.1f}%")


def earnings_stability_signal(stock: "Stock", earnings_cagr_5y: Optional[float] = None) -> MoatSignal:
    """Earnings growth stability."""
    cagr = earnings_cagr_5y if earnings_cagr_5y is not None else stock.earnings_cagr_5y
    if cagr <= 0 and stock.earnings_growth <= 0:
        return MoatSignal(name="Earnings Stability", category=MoatSignalCategory.GROWTH,
                          value=0, score=0, strength=SignalStrength.NONE,
                          description="No earnings growth data", is_available=False)

    growth = cagr if cagr > 0 else stock.earnings_growth
    value = growth

    if growth > 15:
        score = 85
    elif growth > 10:
        score = 70
    elif growth > 5:
        score = 55
    elif growth > 0:
        score = 40
    else:
        score = 10

    return MoatSignal(name="Earnings Stability", category=MoatSignalCategory.GROWTH,
                      value=value, score=score, strength=_score_to_strength(score),
                      description=f"Earnings CAGR 5Y: {growth:.1f}%")


def pricing_power_signal(stock: "Stock", prior_gross_margin: Optional[float] = None) -> MoatSignal:
    """Pricing power via margin expansion."""
    gm = stock.gross_margin
    prior = prior_gross_margin if prior_gross_margin is not None else stock.prior_gross_margin

    if gm <= 0 or prior <= 0:
        return MoatSignal(name="Pricing Power", category=MoatSignalCategory.MARKET_POSITION,
                          value=0, score=0, strength=SignalStrength.NONE,
                          description="No margin history for comparison", is_available=False)

    change = gm - prior
    value = change

    if change > 3:
        score = 85
    elif change > 1:
        score = 70
    elif change > 0:
        score = 55
    elif change > -2:
        score = 35
    else:
        score = 15

    return MoatSignal(name="Pricing Power", category=MoatSignalCategory.MARKET_POSITION,
                      value=value, score=score, strength=_score_to_strength(score),
                      description=f"GM change: {change:+.1f}pp (current {gm:.1f}% vs prior {prior:.1f}%)")


def scale_signal(stock: "Stock") -> MoatSignal:
    """Scale advantage — placeholder, needs industry data."""
    return MoatSignal(name="Scale Advantage", category=MoatSignalCategory.MARKET_POSITION,
                      value=0, score=0, strength=SignalStrength.NONE,
                      description="Requires industry comparison data (future enhancement)",
                      is_available=False)


def debt_safety_signal(stock: "Stock") -> MoatSignal:
    """Low debt ratio = financial flexibility."""
    if stock.total_assets <= 0:
        return MoatSignal(name="Debt Safety", category=MoatSignalCategory.FINANCIAL_FORTRESS,
                          value=0, score=0, strength=SignalStrength.NONE,
                          description="No total assets data", is_available=False)

    ratio = (stock.total_liabilities / stock.total_assets) * 100
    value = ratio

    # Lower debt ratio = higher score (reverse scoring)
    if ratio < 20:
        score = 85
    elif ratio < 30:
        score = 75
    elif ratio < 40:
        score = 60
    elif ratio < 50:
        score = 45
    elif ratio < 65:
        score = 30
    else:
        score = 15

    return MoatSignal(name="Debt Safety", category=MoatSignalCategory.FINANCIAL_FORTRESS,
                      value=value, score=score, strength=_score_to_strength(score),
                      description=f"Debt ratio: {ratio:.1f}%")


def interest_coverage_signal(stock: "Stock") -> MoatSignal:
    """EBIT / Interest Expense coverage."""
    if stock.interest_expense <= 0:
        return MoatSignal(name="Interest Coverage", category=MoatSignalCategory.FINANCIAL_FORTRESS,
                          value=0, score=0, strength=SignalStrength.NONE,
                          description="No interest expense (zero-debt or data missing)", is_available=False)

    coverage = stock.ebit / stock.interest_expense
    value = coverage

    if coverage > 15:
        score = 90
    elif coverage > 10:
        score = 80
    elif coverage > 5:
        score = 65
    elif coverage > 3:
        score = 45
    elif coverage > 1:
        score = 25
    else:
        score = 5

    return MoatSignal(name="Interest Coverage", category=MoatSignalCategory.FINANCIAL_FORTRESS,
                      value=value, score=score, strength=_score_to_strength(score),
                      description=f"Interest coverage: {coverage:.1f}x")


# All signals in order
ALL_SIGNALS = [
    roic_signal,
    margin_stability_signal,
    operating_margin_signal,
    fcf_conversion_signal,
    asset_turnover_signal,
    revenue_stability_signal,
    earnings_stability_signal,
    pricing_power_signal,
    scale_signal,
    debt_safety_signal,
    interest_coverage_signal,
]
