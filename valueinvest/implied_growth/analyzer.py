"""Core calculation functions for implied growth rate analysis."""

from typing import Optional

from valueinvest.stock import Stock

from .base import (
    GrowthComparison,
    GrowthReasonableness,
    ImpliedGrowthDetail,
)


def calculate_reverse_dcf_implied_growth(
    stock: Stock,
) -> Optional[ImpliedGrowthDetail]:
    """Derive implied growth rate from current price using reverse DCF (binary search).

    Uses a 10-year DCF model with:
    - Years 1-5: growth rate = g (searched via binary search)
    - Years 6-10: growth rate = g * 0.5
    - Terminal growth and discount rate from stock attributes

    Args:
        stock: Stock instance with financial data

    Returns:
        ImpliedGrowthDetail with implied growth rate, or None if not applicable
    """
    fcf = stock.fcf
    shares = stock.shares_outstanding
    current_price = stock.current_price
    net_debt = stock.net_debt

    # Validate required data
    if fcf <= 0 or shares <= 0 or current_price <= 0:
        return None

    r = stock.discount_rate / 100
    g_term = stock.terminal_growth / 100

    if r <= g_term:
        return None

    # Target enterprise value implied by current price
    target_equity_value = current_price * shares
    target_ev = target_equity_value + net_debt

    if target_ev <= 0:
        return None

    # Binary search parameters
    growth_min = -10.0
    growth_max = 100.0
    max_iterations = 200
    tolerance = 0.001

    low, high = growth_min, growth_max
    mid = 0.0
    converged = False

    for _ in range(max_iterations):
        mid = (low + high) / 2
        g1 = mid / 100
        g2 = g1 * 0.5

        if g1 <= -1:
            low = mid
            continue

        implied_ev = _calculate_dcf_ev(fcf, g1, g2, g_term, r)

        if implied_ev <= 0:
            low = mid
            continue

        relative_error = abs(implied_ev - target_ev) / target_ev

        if relative_error < tolerance:
            converged = True
            break

        if implied_ev < target_ev:
            low = mid
        else:
            high = mid

        if high - low < 0.01:
            converged = True
            break

    # Determine confidence
    if converged and 0 <= mid <= 30:
        confidence = "High"
    elif converged:
        confidence = "Medium"
    else:
        confidence = "Low"

    # Build notes
    notes = []
    if not converged:
        notes.append("Binary search did not fully converge")
    if mid < 0:
        notes.append("Negative implied growth - potential value trap")
    elif mid > 30:
        notes.append("Very high implied growth - likely unsustainable")

    notes.append(f"Years 6-10 growth assumed at {mid * 0.5:.1f}%")

    assumptions = {
        "fcf": fcf,
        "shares": shares,
        "discount_rate": stock.discount_rate,
        "terminal_growth": stock.terminal_growth,
        "growth_6_10_ratio": 0.5,
        "projection_years": 10,
    }

    return ImpliedGrowthDetail(
        method="Reverse DCF",
        implied_growth_rate=round(mid, 2),
        confidence=confidence,
        assumptions=assumptions,
        notes=notes,
    )


def calculate_peg_implied_growth(
    stock: Stock,
    fair_peg_ratio: float = 1.0,
) -> Optional[ImpliedGrowthDetail]:
    """Derive implied growth rate from PEG ratio.

    At fair PEG ratio: PEG = PE / Growth => Growth = PE / PEG
    A fair_peg_ratio of 1.0 means PE equals expected growth rate.

    Args:
        stock: Stock instance with financial data
        fair_peg_ratio: Assumed fair PEG ratio (default 1.0)

    Returns:
        ImpliedGrowthDetail with implied growth rate, or None if not applicable
    """
    pe = stock.pe_ratio
    if pe <= 0:
        return None

    implied_growth = pe / fair_peg_ratio

    # Confidence depends on data quality
    if stock.eps > 0 and stock.growth_rate > 0:
        confidence = "High"
    elif stock.eps > 0:
        confidence = "Medium"
    else:
        confidence = "Low"

    notes = []
    if stock.growth_rate > 0:
        actual_peg = pe / stock.growth_rate if stock.growth_rate > 0 else 0
        notes.append(f"Current PEG ratio: {actual_peg:.2f}")

    assumptions = {
        "pe_ratio": pe,
        "fair_peg_ratio": fair_peg_ratio,
        "eps": stock.eps,
    }

    return ImpliedGrowthDetail(
        method="PEG Implied",
        implied_growth_rate=round(implied_growth, 2),
        confidence=confidence,
        assumptions=assumptions,
        notes=notes,
    )


def calculate_gordon_growth_implied_growth(
    stock: Stock,
) -> Optional[ImpliedGrowthDetail]:
    """Derive implied growth rate using Gordon Growth Model.

    Gordon Growth Model: P = D1 / (r - g)
    => g = r - D1 / P

    Where D1 = dividend_per_share * (1 + dividend_growth_rate / 100)

    Args:
        stock: Stock instance with financial data

    Returns:
        ImpliedGrowthDetail with implied growth rate, or None if not applicable
    """
    dividend_per_share = stock.dividend_per_share
    current_price = stock.current_price

    # Requires positive dividend
    if dividend_per_share <= 0 or current_price <= 0:
        return None

    r = stock.discount_rate / 100
    dividend_growth = stock.dividend_growth_rate / 100

    # D1 = D0 * (1 + g_div)
    d1 = dividend_per_share * (1 + dividend_growth)

    # g = r - D1 / P
    implied_growth_decimal = r - d1 / current_price
    implied_growth = implied_growth_decimal * 100

    # Sanity check: growth should be reasonable
    if implied_growth > 100 or implied_growth < -50:
        return None

    # Confidence depends on data quality
    if dividend_growth > 0 and stock.dividend_yield > 0:
        confidence = "High"
    elif stock.dividend_yield > 0:
        confidence = "Medium"
    else:
        confidence = "Low"

    notes = []
    if implied_growth < 0:
        notes.append("Negative implied growth - market expects dividend cuts")
    elif implied_growth < stock.terminal_growth:
        notes.append(
            f"Implied growth ({implied_growth:.1f}%) below terminal growth "
            f"({stock.terminal_growth:.1f}%)"
        )

    assumptions = {
        "dividend_per_share": dividend_per_share,
        "dividend_growth_rate": stock.dividend_growth_rate,
        "discount_rate": stock.discount_rate,
        "current_price": current_price,
        "d1": d1,
    }

    return ImpliedGrowthDetail(
        method="Gordon Growth",
        implied_growth_rate=round(implied_growth, 2),
        confidence=confidence,
        assumptions=assumptions,
        notes=notes,
    )


def calculate_earnings_yield_implied_growth(
    stock: Stock,
) -> Optional[ImpliedGrowthDetail]:
    """Derive implied growth rate from earnings yield.

    If we assume earnings yield should equal discount rate minus terminal growth:
        earnings_yield = 1 / PE
        g_implied = r - earnings_yield = r - 1/PE

    Args:
        stock: Stock instance with financial data

    Returns:
        ImpliedGrowthDetail with implied growth rate, or None if not applicable
    """
    pe = stock.pe_ratio
    if pe <= 0:
        return None

    r = stock.discount_rate / 100
    earnings_yield = 1.0 / pe

    implied_growth_decimal = r - earnings_yield
    implied_growth = implied_growth_decimal * 100

    # Confidence
    if stock.eps > 0 and stock.net_income > 0:
        confidence = "High"
    elif stock.eps > 0:
        confidence = "Medium"
    else:
        confidence = "Low"

    notes = []
    if implied_growth < 0:
        notes.append("Negative implied growth - earnings yield exceeds discount rate")
        notes.append("Market may be pricing in earnings decline")

    assumptions = {
        "pe_ratio": pe,
        "earnings_yield": earnings_yield * 100,
        "discount_rate": stock.discount_rate,
    }

    return ImpliedGrowthDetail(
        method="Earnings Yield",
        implied_growth_rate=round(implied_growth, 2),
        confidence=confidence,
        assumptions=assumptions,
        notes=notes,
    )


def compare_with_historical(
    stock: Stock,
    implied_growth: float,
) -> GrowthComparison:
    """Compare implied growth rate with historical growth rates.

    Verdict logic (based on 5-year CAGR when available, falls back to 1Y growth):
    - implied > historical_5y_cagr + 10pp: "Extremely Aggressive"
    - implied > historical_5y_cagr + 5pp: "Aggressive"
    - implied > historical_5y_cagr + 2pp: "Moderate"
    - Otherwise: "Conservative"

    Args:
        stock: Stock instance with financial data
        implied_growth: Weighted implied growth rate (percentage)

    Returns:
        GrowthComparison with gaps and verdict
    """
    historical_revenue_growth = stock.revenue_growth
    historical_earnings_growth = stock.earnings_growth
    historical_revenue_cagr_5y = stock.extra.get("revenue_cagr_5y", 0.0) or 0.0
    historical_earnings_cagr_5y = stock.extra.get("earnings_cagr_5y", 0.0) or 0.0

    gap_revenue = implied_growth - historical_revenue_growth
    gap_earnings = implied_growth - historical_earnings_growth
    gap_revenue_cagr_5y = implied_growth - historical_revenue_cagr_5y
    gap_earnings_cagr_5y = implied_growth - historical_earnings_cagr_5y

    # Use the best available historical benchmark for verdict
    # Prefer earnings CAGR 5Y, then revenue CAGR 5Y, then 1Y growth
    historical_benchmark = 0.0
    if historical_earnings_cagr_5y != 0:
        historical_benchmark = historical_earnings_cagr_5y
    elif historical_revenue_cagr_5y != 0:
        historical_benchmark = historical_revenue_cagr_5y
    elif historical_earnings_growth != 0:
        historical_benchmark = historical_earnings_growth
    elif historical_revenue_growth != 0:
        historical_benchmark = historical_revenue_growth

    # Determine verdict
    if historical_benchmark == 0:
        # No historical data - default to moderate if implied growth is reasonable
        if implied_growth > 20:
            verdict = "Aggressive"
        elif implied_growth > 10:
            verdict = "Moderate"
        else:
            verdict = "Conservative"
    else:
        gap = implied_growth - historical_benchmark
        if gap > 10:
            verdict = "Extremely Aggressive"
        elif gap > 5:
            verdict = "Aggressive"
        elif gap > 2:
            verdict = "Moderate"
        else:
            verdict = "Conservative"

    return GrowthComparison(
        implied_growth=implied_growth,
        historical_revenue_growth=historical_revenue_growth,
        historical_earnings_growth=historical_earnings_growth,
        historical_revenue_cagr_5y=historical_revenue_cagr_5y,
        historical_earnings_cagr_5y=historical_earnings_cagr_5y,
        gap_revenue=gap_revenue,
        gap_earnings=gap_earnings,
        gap_revenue_cagr_5y=gap_revenue_cagr_5y,
        gap_earnings_cagr_5y=gap_earnings_cagr_5y,
        verdict=verdict,
    )


def assess_reasonableness(
    stock: Stock,
    implied_growth: float,
    comparison: GrowthComparison,
) -> GrowthReasonableness:
    """Assess reasonableness of implied growth rate with scoring system.

    Scoring factors:
    - Base score = 50
    - Growth rate level adjustment
    - Verdict adjustment
    - Capability adjustments (ROE, FCF)
    - Red/green flags

    Args:
        stock: Stock instance with financial data
        implied_growth: Weighted implied growth rate (percentage)
        comparison: GrowthComparison from compare_with_historical

    Returns:
        GrowthReasonableness with score, rating, and flags
    """
    score = 50.0
    factors = []
    red_flags = []
    green_flags = []

    # --- Growth rate level adjustment ---
    if implied_growth < 5:
        score += 10
        factors.append("Low implied growth (<5%) is easy to achieve")
    elif implied_growth <= 10:
        score += 5
        factors.append("Moderate implied growth (5-10%)")
    elif implied_growth <= 15:
        factors.append("Implied growth (10-15%) is moderate")
    elif implied_growth <= 20:
        score -= 5
        factors.append("Elevated implied growth (15-20%) requires strong execution")
    elif implied_growth <= 30:
        score -= 15
        factors.append("High implied growth (20-30%) is difficult to sustain")
    else:
        score -= 25
        factors.append("Very high implied growth (>30%) is extremely ambitious")

    # --- Verdict adjustment ---
    verdict = comparison.verdict
    if verdict == "Conservative":
        score += 15
    elif verdict == "Moderate":
        score += 5
    elif verdict == "Aggressive":
        score -= 10
    elif verdict == "Extremely Aggressive":
        score -= 20

    # --- Capability adjustments ---
    if stock.roe > implied_growth:
        score += 10
        factors.append(
            f"ROE ({stock.roe:.1f}%) exceeds implied growth ({implied_growth:.1f}%) "
            f"- company has capability"
        )

    if stock.fcf > 0:
        score += 5
        factors.append("Positive free cash flow supports growth investment")
    elif stock.fcf < 0 and implied_growth > 15:
        factors.append("Negative FCF with high implied growth is concerning")

    # --- Red flags ---
    if implied_growth > 25:
        red_flags.append(f"Implied growth ({implied_growth:.1f}%) > 25% - very hard to sustain")
    if comparison.historical_earnings_cagr_5y != 0 and implied_growth > 2 * comparison.historical_earnings_cagr_5y:
        red_flags.append(
            f"Implied growth > 2x historical 5Y earnings CAGR "
            f"({comparison.historical_earnings_cagr_5y:.1f}%)"
        )
    elif comparison.historical_revenue_cagr_5y != 0 and implied_growth > 2 * comparison.historical_revenue_cagr_5y:
        red_flags.append(
            f"Implied growth > 2x historical 5Y revenue CAGR "
            f"({comparison.historical_revenue_cagr_5y:.1f}%)"
        )
    if stock.fcf < 0 and implied_growth > 15:
        red_flags.append("Negative FCF with high implied growth requires external financing")

    # --- Green flags ---
    has_historical = (
        comparison.historical_earnings_cagr_5y != 0
        or comparison.historical_revenue_cagr_5y != 0
    )
    if has_historical:
        best_historical = max(
            comparison.historical_earnings_cagr_5y,
            comparison.historical_revenue_cagr_5y,
        )
        if implied_growth < best_historical:
            green_flags.append(
                f"Implied growth below historical best CAGR ({best_historical:.1f}%)"
            )
    if stock.roe > 15:
        green_flags.append(f"Strong ROE ({stock.roe:.1f}%) indicates good capital efficiency")
    if stock.fcf > 0:
        green_flags.append("Positive free cash flow")

    # --- Clamp score ---
    score = max(0.0, min(100.0, score))

    # --- Rating ---
    if score >= 70:
        rating = "Reasonable"
    elif score >= 50:
        rating = "Somewhat Optimistic"
    elif score >= 30:
        rating = "Optimistic"
    elif score >= 10:
        rating = "Very Optimistic"
    else:
        rating = "Unreasonable"

    return GrowthReasonableness(
        score=round(score, 1),
        rating=rating,
        factors=factors,
        red_flags=red_flags,
        green_flags=green_flags,
    )


def _calculate_dcf_ev(
    fcf: float,
    g1: float,
    g2: float,
    g_term: float,
    r: float,
) -> float:
    """Calculate enterprise value from DCF parameters.

    Args:
        fcf: Base year free cash flow
        g1: Growth rate years 1-5 (decimal, e.g. 0.10 for 10%)
        g2: Growth rate years 6-10 (decimal)
        g_term: Terminal growth rate (decimal)
        r: Discount rate (decimal)

    Returns:
        Implied enterprise value
    """
    projected_fcf = fcf
    total_pv = 0.0

    for year in range(1, 11):
        if year <= 5:
            projected_fcf *= (1 + g1)
        else:
            projected_fcf *= (1 + g2)

        if projected_fcf <= 0:
            return 0.0
        total_pv += projected_fcf / ((1 + r) ** year)

    fcf_year_10 = projected_fcf
    terminal_value = (fcf_year_10 * (1 + g_term)) / (r - g_term)
    pv_terminal = terminal_value / ((1 + r) ** 10)

    return total_pv + pv_terminal
