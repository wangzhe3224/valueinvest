"""Individual capital allocation signal calculators."""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from valueinvest.stock import Stock

from .base import AllocationSignal, AllocationCategory, SignalLevel, _score_to_level


def dividend_yield_signal(stock: "Stock") -> AllocationSignal:
    """Dividend yield level."""
    dy = stock.dividend_yield
    if dy <= 0:
        return AllocationSignal(name="Dividend Yield", category=AllocationCategory.SHAREHOLDER_RETURN,
                                value=0, score=0, level=SignalLevel.POOR,
                                description="No dividend", is_available=False)

    if dy > 5:
        score = 70  # Very high yield may indicate risk
    elif dy > 3:
        score = 85
    elif dy > 2:
        score = 75
    elif dy > 1:
        score = 55
    else:
        score = 35  # Low yield but not zero

    return AllocationSignal(name="Dividend Yield", category=AllocationCategory.SHAREHOLDER_RETURN,
                            value=dy, score=score, level=_score_to_level(score),
                            description=f"Dividend yield: {dy:.1f}%")


def dividend_payout_signal(stock: "Stock") -> AllocationSignal:
    """Dividend payout ratio reasonableness (30-60% optimal)."""
    pr = stock.payout_ratio
    if stock.eps <= 0:
        return AllocationSignal(name="Payout Ratio", category=AllocationCategory.SHAREHOLDER_RETURN,
                                value=0, score=0, level=SignalLevel.POOR,
                                description="No earnings for payout calculation", is_available=False)

    if 30 <= pr <= 60:
        score = 85
    elif 20 <= pr <= 70:
        score = 70
    elif 70 < pr <= 90:
        score = 45
    elif pr > 90:
        score = 15
    elif pr > 0:
        score = 50  # Low but positive
    else:
        score = 40  # No dividend

    return AllocationSignal(name="Payout Ratio", category=AllocationCategory.SHAREHOLDER_RETURN,
                            value=pr, score=score, level=_score_to_level(score),
                            description=f"Payout ratio: {pr:.0f}%")


def dividend_growth_signal(stock: "Stock") -> AllocationSignal:
    """Dividend growth consistency."""
    dg = stock.dividend_growth_rate
    if stock.dividend_per_share <= 0:
        return AllocationSignal(name="Dividend Growth", category=AllocationCategory.SHAREHOLDER_RETURN,
                                value=0, score=0, level=SignalLevel.POOR,
                                description="No dividend", is_available=False)

    if dg > 10:
        score = 90
    elif dg > 5:
        score = 80
    elif dg > 0:
        score = 60
    elif dg > -5:
        score = 30
    else:
        score = 10

    return AllocationSignal(name="Dividend Growth", category=AllocationCategory.SHAREHOLDER_RETURN,
                            value=dg, score=score, level=_score_to_level(score),
                            description=f"Dividend growth: {dg:.1f}%")


def buyback_signal(stock: "Stock") -> AllocationSignal:
    """Net buyback yield (net of dilution)."""
    # true_buyback_yield is net of dilution
    by = stock.true_buyback_yield
    if stock.shares_outstanding <= 0 or stock.market_cap <= 0:
        return AllocationSignal(name="Net Buyback", category=AllocationCategory.SHAREHOLDER_RETURN,
                                value=0, score=0, level=SignalLevel.POOR,
                                description="No market data", is_available=False)

    if by > 4:
        score = 90
    elif by > 2:
        score = 80
    elif by > 0:
        score = 60
    elif by > -1:
        score = 40
    elif by > -3:
        score = 20
    else:
        score = 5

    return AllocationSignal(name="Net Buyback", category=AllocationCategory.SHAREHOLDER_RETURN,
                            value=by, score=score, level=_score_to_level(score),
                            description=f"Net buyback yield: {by:.1f}%")


def shareholder_yield_signal(stock: "Stock") -> AllocationSignal:
    """Total shareholder yield (dividend + net buyback)."""
    sy = stock.shareholder_yield()
    if sy <= 0:
        score = 30
    elif sy > 6:
        score = 90
    elif sy > 4:
        score = 80
    elif sy > 2:
        score = 65
    elif sy > 0:
        score = 50
    else:
        score = 20

    return AllocationSignal(name="Shareholder Yield", category=AllocationCategory.SHAREHOLDER_RETURN,
                            value=sy, score=score, level=_score_to_level(score),
                            description=f"Total shareholder yield: {sy:.1f}%")


def capex_to_revenue_signal(stock: "Stock") -> AllocationSignal:
    """CapEx as % of revenue — reinvestment intensity."""
    if stock.revenue <= 0:
        return AllocationSignal(name="CapEx/Revenue", category=AllocationCategory.REINVESTMENT,
                                value=0, score=0, level=SignalLevel.POOR,
                                description="No revenue data", is_available=False)

    ratio = abs(stock.capex) / stock.revenue * 100
    value = ratio

    # Scoring: moderate reinvestment is healthy
    if 3 <= ratio <= 8:
        score = 75
    elif 2 <= ratio <= 12:
        score = 60
    elif ratio < 2:
        score = 45  # Under-investing
    elif ratio <= 15:
        score = 40  # Aggressive
    else:
        score = 20  # Very aggressive / empire building

    return AllocationSignal(name="CapEx/Revenue", category=AllocationCategory.REINVESTMENT,
                            value=value, score=score, level=_score_to_level(score),
                            description=f"CapEx/Revenue: {ratio:.1f}%")


def capex_to_depreciation_signal(stock: "Stock") -> AllocationSignal:
    """CapEx / Depreciation ratio — growth vs maintenance spending."""
    if stock.depreciation <= 0:
        return AllocationSignal(name="CapEx/Depreciation", category=AllocationCategory.REINVESTMENT,
                                value=0, score=0, level=SignalLevel.POOR,
                                description="No depreciation data", is_available=False)

    ratio = abs(stock.capex) / stock.depreciation
    value = ratio

    if 1.0 <= ratio <= 1.5:
        score = 80  # Healthy reinvestment
    elif 0.8 <= ratio <= 2.0:
        score = 65
    elif 0.5 <= ratio < 0.8:
        score = 35  # Consuming assets
    elif ratio > 2.0:
        score = 50  # Aggressive growth
    else:
        score = 15  # Severe under-investment

    return AllocationSignal(name="CapEx/Depreciation", category=AllocationCategory.REINVESTMENT,
                            value=value, score=score, level=_score_to_level(score),
                            description=f"CapEx/Depreciation: {ratio:.2f}x")


def roic_on_reinvestment_signal(stock: "Stock", roic: Optional[float] = None, wacc: Optional[float] = None) -> AllocationSignal:
    """Is reinvestment at above-WACC returns?"""
    if roic is not None and wacc is not None:
        spread = roic - wacc
        value = spread
        if spread > 5:
            score = 90
        elif spread > 0:
            score = 70
        elif spread > -3:
            score = 40
        else:
            score = 15
        description = f"Reinvestment ROIC ({roic:.1f}%) vs WACC ({wacc:.1f}%): {spread:+.1f}pp"
    else:
        # Use ROE as proxy
        roe = stock.roe
        coc = stock.cost_of_capital
        if roe <= 0:
            return AllocationSignal(name="Reinvestment ROIC", category=AllocationCategory.REINVESTMENT,
                                    value=0, score=0, level=SignalLevel.POOR,
                                    description="No profitability data", is_available=False)
        spread = roe - coc
        value = spread
        if spread > 5:
            score = 85
        elif spread > 0:
            score = 65
        elif spread > -3:
            score = 35
        else:
            score = 15
        description = f"ROE ({roe:.1f}%) vs CoC ({coc:.1f}%): {spread:+.1f}pp (ROE proxy)"

    return AllocationSignal(name="Reinvestment ROIC", category=AllocationCategory.REINVESTMENT,
                            value=value, score=score, level=_score_to_level(score),
                            description=description)


def debt_trend_signal(stock: "Stock", prior_debt_ratio: Optional[float] = None) -> AllocationSignal:
    """Debt ratio change — improving or deteriorating."""
    current = stock.debt_ratio
    prior = prior_debt_ratio if prior_debt_ratio is not None else stock.prior_debt_ratio

    if current <= 0:
        return AllocationSignal(name="Debt Trend", category=AllocationCategory.BALANCE_SHEET,
                                value=0, score=0, level=SignalLevel.POOR,
                                description="No debt ratio data", is_available=False)

    if prior > 0:
        change = current - prior
        value = change
        if change < -3:
            score = 85  # Significant deleveraging
        elif change < 0:
            score = 70  # Improving
        elif change < 2:
            score = 55  # Stable
        elif change < 5:
            score = 35  # Increasing
        else:
            score = 15  # Rapid increase
        description = f"Debt ratio: {current:.1f}% (Δ={change:+.1f}pp)"
    else:
        # Only current available
        value = current
        if current < 30:
            score = 75
        elif current < 50:
            score = 55
        elif current < 70:
            score = 35
        else:
            score = 15
        description = f"Debt ratio: {current:.1f}% (no prior data for trend)"

    return AllocationSignal(name="Debt Trend", category=AllocationCategory.BALANCE_SHEET,
                            value=value, score=score, level=_score_to_level(score),
                            description=description)


def interest_coverage_signal(stock: "Stock") -> AllocationSignal:
    """EBIT / Interest Expense — debt service ability."""
    if stock.interest_expense <= 0:
        return AllocationSignal(name="Interest Coverage", category=AllocationCategory.BALANCE_SHEET,
                                value=0, score=0, level=SignalLevel.ADEQUATE,
                                description="No interest expense (zero-debt)", is_available=False)

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

    return AllocationSignal(name="Interest Coverage", category=AllocationCategory.BALANCE_SHEET,
                            value=value, score=score, level=_score_to_level(score),
                            description=f"Interest coverage: {coverage:.1f}x")


def sbc_signal(stock: "Stock") -> AllocationSignal:
    """Stock-based compensation burden."""
    if stock.revenue <= 0:
        return AllocationSignal(name="SBC Burden", category=AllocationCategory.DILUTION,
                                value=0, score=0, level=SignalLevel.POOR,
                                description="No revenue data", is_available=False)

    sbc_pct = stock.sbc_margin  # SBC as % of revenue
    value = sbc_pct

    if sbc_pct < 0.5:
        score = 90
    elif sbc_pct < 1:
        score = 80
    elif sbc_pct < 2:
        score = 65
    elif sbc_pct < 3:
        score = 50
    elif sbc_pct < 5:
        score = 30
    else:
        score = 10

    # Extra penalty if SBC > FCF
    if stock.fcf > 0 and stock.sbc > stock.fcf:
        score = min(score, 20)

    return AllocationSignal(name="SBC Burden", category=AllocationCategory.DILUTION,
                            value=value, score=score, level=_score_to_level(score),
                            description=f"SBC/Revenue: {sbc_pct:.1f}%")


def net_dilution_signal(stock: "Stock") -> AllocationSignal:
    """Net share count change."""
    if stock.shares_outstanding <= 0:
        return AllocationSignal(name="Net Dilution", category=AllocationCategory.DILUTION,
                                value=0, score=0, level=SignalLevel.POOR,
                                description="No shares data", is_available=False)

    dilution = stock.dilution_rate  # Annual dilution from share issuance
    value = dilution

    if dilution < -1:
        score = 90  # Net buyback
    elif dilution < 0:
        score = 75
    elif dilution < 1:
        score = 60  # Minimal dilution
    elif dilution < 2:
        score = 40
    elif dilution < 4:
        score = 20
    else:
        score = 5  # Heavy dilution

    return AllocationSignal(name="Net Dilution", category=AllocationCategory.DILUTION,
                            value=value, score=score, level=_score_to_level(score),
                            description=f"Net dilution rate: {dilution:.1f}%")


# All signals in order
ALL_SIGNALS = [
    dividend_yield_signal,
    dividend_payout_signal,
    dividend_growth_signal,
    buyback_signal,
    shareholder_yield_signal,
    capex_to_revenue_signal,
    capex_to_depreciation_signal,
    roic_on_reinvestment_signal,
    debt_trend_signal,
    interest_coverage_signal,
    sbc_signal,
    net_dilution_signal,
]
