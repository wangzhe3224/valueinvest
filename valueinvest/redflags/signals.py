"""Individual accounting red flag signal calculators."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from valueinvest.stock import Stock

from .base import RedFlagSignal, RedFlagCategory, RedFlagSeverity, _score_to_severity


def cfo_vs_net_income_signal(stock: "Stock") -> RedFlagSignal:
    """OCF below net income suggests accrual manipulation."""
    ocf = stock.operating_cash_flow
    ni = stock.net_income

    if ocf == 0 or ni == 0:
        return RedFlagSignal(
            name="CFO vs Net Income",
            category=RedFlagCategory.EARNINGS_QUALITY,
            value=0, score=0, severity=RedFlagSeverity.NONE,
            description="No OCF or net income data", is_available=False,
        )

    if ni > 0:
        ratio = ocf / ni
        value = ratio
        if ratio >= 1.2:
            score = 5
        elif ratio >= 0.8:
            score = 20
        elif ratio >= 0.5:
            score = 50
        elif ratio >= 0.2:
            score = 75
        else:
            score = 95
    elif ni < 0 and ocf < 0:
        ratio = ni / ocf if ocf != 0 else 0
        value = ratio
        score = 60
    else:
        value = -1
        score = 35

    return RedFlagSignal(
        name="CFO vs Net Income",
        category=RedFlagCategory.EARNINGS_QUALITY,
        value=value, score=score, severity=_score_to_severity(score),
        description=f"OCF/NI ratio: {value:.2f}x",
    )


def sloan_accrual_signal(stock: "Stock") -> RedFlagSignal:
    """Sloan Accrual Ratio: (Net Income - OCF) / Total Assets.
    High accruals indicate earnings not backed by cash flow."""
    if stock.total_assets <= 0:
        return RedFlagSignal(
            name="Sloan Accrual Ratio",
            category=RedFlagCategory.EARNINGS_QUALITY,
            value=0, score=0, severity=RedFlagSeverity.NONE,
            description="No total assets data", is_available=False,
        )

    ocf = stock.operating_cash_flow
    if ocf == 0:
        return RedFlagSignal(
            name="Sloan Accrual Ratio",
            category=RedFlagCategory.EARNINGS_QUALITY,
            value=0, score=0, severity=RedFlagSeverity.NONE,
            description="No operating cash flow data", is_available=False,
        )

    accruals = (stock.net_income - ocf) / stock.total_assets
    value = accruals

    abs_accruals = abs(accruals)
    if abs_accruals <= 0.02:
        score = 5
    elif abs_accruals <= 0.05:
        score = 20
    elif abs_accruals <= 0.10:
        score = 45
    elif abs_accruals <= 0.15:
        score = 65
    else:
        score = 90

    if accruals > 0.05:
        score = min(100, score + 10)

    return RedFlagSignal(
        name="Sloan Accrual Ratio",
        category=RedFlagCategory.EARNINGS_QUALITY,
        value=value, score=score, severity=_score_to_severity(score),
        description=f"Accrual ratio: {accruals:.3f} ({accruals * 100:.1f}% of assets)",
    )


def earnings_persistence_signal(stock: "Stock") -> RedFlagSignal:
    """Negative net income with positive OCF (or vice versa) signals quality issues."""
    ni = stock.net_income
    ocf = stock.operating_cash_flow

    if ni == 0 and ocf == 0:
        return RedFlagSignal(
            name="Earnings Persistence",
            category=RedFlagCategory.EARNINGS_QUALITY,
            value=0, score=0, severity=RedFlagSeverity.NONE,
            description="No earnings or cash flow data", is_available=False,
        )

    if ni > 0 and ocf > 0:
        divergence = abs(ni - ocf) / max(abs(ni), abs(ocf))
        value = divergence
        if divergence < 0.1:
            score = 5
        elif divergence < 0.3:
            score = 25
        elif divergence < 0.5:
            score = 50
        else:
            score = 70
        desc = f"NI and OCF both positive, divergence: {divergence:.1%}"
    elif ni < 0 and ocf > 0:
        score = 35
        value = -1
        desc = f"Net loss with positive OCF -- non-cash charges"
    elif ni > 0 and ocf < 0:
        score = 95
        value = 1
        desc = f"CRITICAL: Net income positive but OCF negative"
    else:
        score = 60
        value = -1
        desc = "Both net income and OCF negative"

    return RedFlagSignal(
        name="Earnings Persistence",
        category=RedFlagCategory.EARNINGS_QUALITY,
        value=value, score=score, severity=_score_to_severity(score),
        description=desc,
    )


def ar_vs_revenue_signal(stock: "Stock") -> RedFlagSignal:
    """AR growing faster than revenue suggests channel stuffing.
    Uses AR/Revenue ratio to estimate Days Sales Outstanding."""
    if stock.revenue <= 0 or stock.accounts_receivable == 0:
        return RedFlagSignal(
            name="AR vs Revenue",
            category=RedFlagCategory.REVENUE_RECOGNITION,
            value=0, score=0, severity=RedFlagSeverity.NONE,
            description="No revenue or AR data", is_available=False,
        )

    ar_ratio = stock.accounts_receivable / stock.revenue
    dso = ar_ratio * 365
    value = dso

    if dso <= 30:
        score = 5
    elif dso <= 45:
        score = 15
    elif dso <= 60:
        score = 30
    elif dso <= 90:
        score = 55
    elif dso <= 120:
        score = 75
    else:
        score = 95

    return RedFlagSignal(
        name="AR vs Revenue",
        category=RedFlagCategory.REVENUE_RECOGNITION,
        value=value, score=score, severity=_score_to_severity(score),
        description=f"Implied DSO: {dso:.0f} days (AR/Revenue: {ar_ratio:.3f})",
    )


def revenue_quality_signal(stock: "Stock") -> RedFlagSignal:
    """OCF/Revenue ratio -- low or negative ratio suggests revenue quality issues."""
    if stock.revenue <= 0:
        return RedFlagSignal(
            name="Revenue Quality",
            category=RedFlagCategory.REVENUE_RECOGNITION,
            value=0, score=0, severity=RedFlagSeverity.NONE,
            description="No revenue data", is_available=False,
        )

    ocf = stock.operating_cash_flow
    if ocf == 0:
        return RedFlagSignal(
            name="Revenue Quality",
            category=RedFlagCategory.REVENUE_RECOGNITION,
            value=0, score=0, severity=RedFlagSeverity.NONE,
            description="No OCF data", is_available=False,
        )

    ratio = ocf / stock.revenue
    value = ratio

    if ratio >= 0.20:
        score = 5
    elif ratio >= 0.15:
        score = 15
    elif ratio >= 0.10:
        score = 30
    elif ratio >= 0.05:
        score = 55
    elif ratio >= 0:
        score = 70
    else:
        score = 95

    return RedFlagSignal(
        name="Revenue Quality",
        category=RedFlagCategory.REVENUE_RECOGNITION,
        value=value, score=score, severity=_score_to_severity(score),
        description=f"OCF/Revenue ratio: {ratio:.1%}",
    )


def inventory_buildup_signal(stock: "Stock") -> RedFlagSignal:
    """Inventory/Revenue ratio -- high ratio suggests potential obsolescence."""
    if stock.revenue <= 0:
        return RedFlagSignal(
            name="Inventory Buildup",
            category=RedFlagCategory.ASSET_WORKING_CAPITAL,
            value=0, score=0, severity=RedFlagSeverity.NONE,
            description="No revenue data", is_available=False,
        )

    if stock.inventory == 0:
        return RedFlagSignal(
            name="Inventory Buildup",
            category=RedFlagCategory.ASSET_WORKING_CAPITAL,
            value=0, score=0, severity=RedFlagSeverity.NONE,
            description="No inventory (service/software company)", is_available=False,
        )

    inv_ratio = stock.inventory / stock.revenue
    dio = inv_ratio * 365
    value = dio

    if dio <= 30:
        score = 5
    elif dio <= 60:
        score = 15
    elif dio <= 90:
        score = 30
    elif dio <= 120:
        score = 50
    elif dio <= 180:
        score = 70
    else:
        score = 90

    return RedFlagSignal(
        name="Inventory Buildup",
        category=RedFlagCategory.ASSET_WORKING_CAPITAL,
        value=value, score=score, severity=_score_to_severity(score),
        description=f"Implied DIO: {dio:.0f} days (Inv/Revenue: {inv_ratio:.3f})",
    )


def working_capital_efficiency_signal(stock: "Stock") -> RedFlagSignal:
    """Working capital efficiency via current ratio trend."""
    current = stock.current_ratio
    prior = stock.prior_current_ratio

    if current <= 0 and prior <= 0:
        return RedFlagSignal(
            name="Working Capital Efficiency",
            category=RedFlagCategory.ASSET_WORKING_CAPITAL,
            value=0, score=0, severity=RedFlagSeverity.NONE,
            description="No current ratio data", is_available=False,
        )

    if current > 0 and prior > 0:
        change = current - prior
        value = change
        if change >= 0:
            score = 10
        elif change > -0.3:
            score = 30
        elif change > -0.5:
            score = 55
        elif change > -1.0:
            score = 75
        else:
            score = 90
        desc = f"Current ratio: {current:.2f} (prior: {prior:.2f}, change: {change:+.2f})"
    elif current > 0:
        value = current
        if current >= 2.0:
            score = 10
        elif current >= 1.5:
            score = 25
        elif current >= 1.0:
            score = 45
        else:
            score = 80
        desc = f"Current ratio: {current:.2f} (no prior data for trend)"
    else:
        value = 0
        score = 40
        desc = "Only prior current ratio available"

    return RedFlagSignal(
        name="Working Capital Efficiency",
        category=RedFlagCategory.ASSET_WORKING_CAPITAL,
        value=value, score=score, severity=_score_to_severity(score),
        description=desc,
    )


def capex_vs_depreciation_signal(stock: "Stock") -> RedFlagSignal:
    """CapEx dropping sharply below depreciation signals asset starvation."""
    if stock.depreciation <= 0:
        return RedFlagSignal(
            name="CapEx vs Depreciation",
            category=RedFlagCategory.ASSET_WORKING_CAPITAL,
            value=0, score=0, severity=RedFlagSeverity.NONE,
            description="No depreciation data", is_available=False,
        )

    capex = abs(stock.capex)
    ratio = capex / stock.depreciation
    value = ratio

    if ratio >= 1.5:
        score = 5
    elif ratio >= 1.0:
        score = 15
    elif ratio >= 0.7:
        score = 40
    elif ratio >= 0.4:
        score = 65
    elif ratio >= 0.2:
        score = 85
    else:
        score = 95

    return RedFlagSignal(
        name="CapEx vs Depreciation",
        category=RedFlagCategory.ASSET_WORKING_CAPITAL,
        value=value, score=score, severity=_score_to_severity(score),
        description=f"CapEx/Depreciation: {ratio:.2f}x",
    )


def debt_trend_signal(stock: "Stock") -> RedFlagSignal:
    """Rising debt ratio signals potential leverage concerns."""
    current = stock.debt_ratio
    prior = stock.prior_debt_ratio

    if current <= 0 and prior <= 0:
        return RedFlagSignal(
            name="Debt Trend",
            category=RedFlagCategory.CAPITAL_STRUCTURE,
            value=0, score=0, severity=RedFlagSeverity.NONE,
            description="No debt ratio data", is_available=False,
        )

    if current > 0 and prior > 0:
        change = current - prior
        value = change
        if change > 10:
            score = 90
        elif change > 5:
            score = 70
        elif change > 2:
            score = 50
        elif change > 0:
            score = 30
        elif change > -3:
            score = 15
        else:
            score = 5
        desc = f"Debt ratio: {current:.1f}% (prior: {prior:.1f}%, change: {change:+.1f}pp)"
    elif current > 0:
        value = current
        if current >= 80:
            score = 85
        elif current >= 60:
            score = 60
        elif current >= 40:
            score = 35
        else:
            score = 15
        desc = f"Debt ratio: {current:.1f}% (no prior for trend)"
    else:
        value = 0
        score = 40
        desc = "Only prior debt ratio available"

    return RedFlagSignal(
        name="Debt Trend",
        category=RedFlagCategory.CAPITAL_STRUCTURE,
        value=value, score=score, severity=_score_to_severity(score),
        description=desc,
    )


def sbc_revenue_signal(stock: "Stock") -> RedFlagSignal:
    """Excessive SBC as % of revenue -- dilution disguised as 'compensation'."""
    if stock.revenue <= 0:
        return RedFlagSignal(
            name="SBC/Revenue",
            category=RedFlagCategory.CAPITAL_STRUCTURE,
            value=0, score=0, severity=RedFlagSeverity.NONE,
            description="No revenue data", is_available=False,
        )

    sbc_pct = stock.sbc_margin
    value = sbc_pct

    if sbc_pct < 1:
        score = 5
    elif sbc_pct < 2:
        score = 15
    elif sbc_pct < 3:
        score = 30
    elif sbc_pct < 5:
        score = 55
    elif sbc_pct < 8:
        score = 75
    else:
        score = 95

    if stock.net_income > 0 and stock.sbc > stock.net_income:
        score = min(100, score + 15)

    return RedFlagSignal(
        name="SBC/Revenue",
        category=RedFlagCategory.CAPITAL_STRUCTURE,
        value=value, score=score, severity=_score_to_severity(score),
        description=f"SBC/Revenue: {sbc_pct:.1f}%",
    )


def fcf_quality_signal(stock: "Stock") -> RedFlagSignal:
    """FCF negative while net income positive -- earnings not converting to cash."""
    ni = stock.net_income
    fcf_val = stock.fcf

    if ni == 0 and fcf_val == 0:
        return RedFlagSignal(
            name="FCF Quality",
            category=RedFlagCategory.CAPITAL_STRUCTURE,
            value=0, score=0, severity=RedFlagSeverity.NONE,
            description="No net income or FCF data", is_available=False,
        )

    if ni > 0 and fcf_val <= 0:
        value = fcf_val / ni
        score = 95
        desc = "CRITICAL: Positive NI but negative FCF"
    elif ni > 0:
        ratio = fcf_val / ni
        value = ratio
        if ratio >= 1.0:
            score = 5
        elif ratio >= 0.7:
            score = 20
        elif ratio >= 0.4:
            score = 45
        elif ratio >= 0.2:
            score = 65
        else:
            score = 85
        desc = f"FCF/NI ratio: {ratio:.2f}x"
    else:
        value = 0
        score = 50
        desc = "Negative net income"

    return RedFlagSignal(
        name="FCF Quality",
        category=RedFlagCategory.CAPITAL_STRUCTURE,
        value=value, score=score, severity=_score_to_severity(score),
        description=desc,
    )


ALL_SIGNALS = [
    cfo_vs_net_income_signal,
    sloan_accrual_signal,
    earnings_persistence_signal,
    ar_vs_revenue_signal,
    revenue_quality_signal,
    inventory_buildup_signal,
    working_capital_efficiency_signal,
    capex_vs_depreciation_signal,
    debt_trend_signal,
    sbc_revenue_signal,
    fcf_quality_signal,
]
