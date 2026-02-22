"""
Screening filters for the stock screening system.

This module provides filters for:
- Valuation: Margin of Safety, P/E, P/B, PEG
- Quality: ROE, FCF Yield, Altman Z, ROIC, Operating Margin
- Dividend: Dividend Yield, Payout Ratio, Dividend Growth
- Sentiment: News Sentiment, Insider Sentiment
- Momentum: CAGR, Price vs 52-week range
"""
from typing import Optional
from .base import (
    BaseFilter,
    FilterCategory,
    FilterResult,
    ScreeningResult,
)


# ============================================================================
# Valuation Filters
# ============================================================================


class MarginOfSafetyFilter(BaseFilter):
    """Filter by minimum margin of safety (%)."""

    name = "margin_of_safety"
    description = "Minimum margin of safety"
    category = FilterCategory.VALUATION

    def __init__(self, min_mos: float = 15.0):
        self.min_mos = min_mos

    def apply(self, result: ScreeningResult) -> FilterResult:
        value = result.margin_of_safety
        passed = value >= self.min_mos

        if passed:
            reason = f"MOS {value:.1f}% >= {self.min_mos}%"
        else:
            reason = f"MOS {value:.1f}% < {self.min_mos}%"

        return self._create_result(passed, reason, value, self.min_mos)


class PEFilter(BaseFilter):
    """Filter by maximum P/E ratio."""

    name = "pe_ratio"
    description = "Maximum P/E ratio"
    category = FilterCategory.VALUATION

    def __init__(self, max_pe: float = 20.0, min_pe: float = 0.0):
        self.max_pe = max_pe
        self.min_pe = min_pe

    def apply(self, result: ScreeningResult) -> FilterResult:
        value = result.pe_ratio

        if value <= 0:
            return self._create_result(False, "P/E not available or negative", value, self.max_pe)

        passed = self.min_pe <= value <= self.max_pe

        if passed:
            reason = f"P/E {value:.1f} within [{self.min_pe}, {self.max_pe}]"
        else:
            reason = f"P/E {value:.1f} outside [{self.min_pe}, {self.max_pe}]"

        return self._create_result(passed, reason, value, self.max_pe)


class PBFilter(BaseFilter):
    """Filter by maximum P/B ratio."""

    name = "pb_ratio"
    description = "Maximum P/B ratio"
    category = FilterCategory.VALUATION

    def __init__(self, max_pb: float = 3.0):
        self.max_pb = max_pb

    def apply(self, result: ScreeningResult) -> FilterResult:
        value = result.pb_ratio

        if value <= 0:
            return self._create_result(False, "P/B not available or negative", value, self.max_pb)

        passed = value <= self.max_pb

        if passed:
            reason = f"P/B {value:.2f} <= {self.max_pb}"
        else:
            reason = f"P/B {value:.2f} > {self.max_pb}"

        return self._create_result(passed, reason, value, self.max_pb)


class PEGFilter(BaseFilter):
    """Filter by maximum PEG ratio."""

    name = "peg_ratio"
    description = "Maximum PEG ratio (P/E / Growth)"
    category = FilterCategory.VALUATION

    def __init__(self, max_peg: float = 1.5):
        self.max_peg = max_peg

    def apply(self, result: ScreeningResult) -> FilterResult:
        value = result.peg_ratio

        if value <= 0:
            return self._create_result(False, "PEG not available", value, self.max_peg)

        passed = value <= self.max_peg

        if passed:
            reason = f"PEG {value:.2f} <= {self.max_peg}"
        else:
            reason = f"PEG {value:.2f} > {self.max_peg}"

        return self._create_result(passed, reason, value, self.max_peg)


class UndervaluedMethodsFilter(BaseFilter):
    """Filter by minimum number of undervalued methods."""

    name = "undervalued_methods"
    description = "Minimum undervalued valuation methods"
    category = FilterCategory.VALUATION

    def __init__(self, min_methods: int = 2):
        self.min_methods = min_methods

    def apply(self, result: ScreeningResult) -> FilterResult:
        value = result.undervalued_methods
        passed = value >= self.min_methods

        if passed:
            reason = f"{value} methods indicate undervalued >= {self.min_methods}"
        else:
            reason = f"{value} methods indicate undervalued < {self.min_methods}"

        return self._create_result(passed, reason, float(value), float(self.min_methods))


# ============================================================================
# Quality Filters
# ============================================================================


class ROEFilter(BaseFilter):
    """Filter by minimum ROE (%)."""

    name = "roe"
    description = "Minimum Return on Equity"
    category = FilterCategory.QUALITY

    def __init__(self, min_roe: float = 10.0):
        self.min_roe = min_roe

    def apply(self, result: ScreeningResult) -> FilterResult:
        value = result.roe
        passed = value >= self.min_roe

        if passed:
            reason = f"ROE {value:.1f}% >= {self.min_roe}%"
        else:
            reason = f"ROE {value:.1f}% < {self.min_roe}%"

        return self._create_result(passed, reason, value, self.min_roe)


class FCFYieldFilter(BaseFilter):
    """Filter by minimum FCF yield (%)."""

    name = "fcf_yield"
    description = "Minimum Free Cash Flow Yield"
    category = FilterCategory.QUALITY

    def __init__(self, min_yield: float = 3.0):
        self.min_yield = min_yield

    def apply(self, result: ScreeningResult) -> FilterResult:
        value = result.fcf_yield
        passed = value >= self.min_yield

        if passed:
            reason = f"FCF Yield {value:.1f}% >= {self.min_yield}%"
        else:
            reason = f"FCF Yield {value:.1f}% < {self.min_yield}%"

        return self._create_result(passed, reason, value, self.min_yield)


class AltmanZFilter(BaseFilter):
    """Filter by minimum Altman Z-Score (bankruptcy risk)."""

    name = "altman_z"
    description = "Minimum Altman Z-Score (bankruptcy safety)"
    category = FilterCategory.QUALITY

    def __init__(self, min_z: float = 2.99):
        self.min_z = min_z

    def apply(self, result: ScreeningResult) -> FilterResult:
        value = result.altman_z
        passed = value >= self.min_z

        if passed:
            reason = f"Altman Z {value:.2f} >= {self.min_z} (safe zone)"
        else:
            reason = f"Altman Z {value:.2f} < {self.min_z} (risk zone)"

        return self._create_result(passed, reason, value, self.min_z)


class ROICFilter(BaseFilter):
    """Filter by minimum ROIC (%)."""

    name = "roic"
    description = "Minimum Return on Invested Capital"
    category = FilterCategory.QUALITY

    def __init__(self, min_roic: float = 10.0):
        self.min_roic = min_roic

    def apply(self, result: ScreeningResult) -> FilterResult:
        value = result.roic
        passed = value >= self.min_roic

        if passed:
            reason = f"ROIC {value:.1f}% >= {self.min_roic}%"
        else:
            reason = f"ROIC {value:.1f}% < {self.min_roic}%"

        return self._create_result(passed, reason, value, self.min_roic)


class OperatingMarginFilter(BaseFilter):
    """Filter by minimum operating margin (%)."""

    name = "operating_margin"
    description = "Minimum Operating Margin"
    category = FilterCategory.QUALITY

    def __init__(self, min_margin: float = 10.0):
        self.min_margin = min_margin

    def apply(self, result: ScreeningResult) -> FilterResult:
        value = result.operating_margin
        passed = value >= self.min_margin

        if passed:
            reason = f"Op Margin {value:.1f}% >= {self.min_margin}%"
        else:
            reason = f"Op Margin {value:.1f}% < {self.min_margin}%"

        return self._create_result(passed, reason, value, self.min_margin)


# ============================================================================
# Dividend Filters
# ============================================================================


class DividendYieldFilter(BaseFilter):
    """Filter by minimum dividend yield (%)."""

    name = "dividend_yield"
    description = "Minimum Dividend Yield"
    category = FilterCategory.DIVIDEND

    def __init__(self, min_yield: float = 2.0):
        self.min_yield = min_yield

    def apply(self, result: ScreeningResult) -> FilterResult:
        value = result.dividend_yield
        passed = value >= self.min_yield

        if passed:
            reason = f"Div Yield {value:.2f}% >= {self.min_yield}%"
        else:
            reason = f"Div Yield {value:.2f}% < {self.min_yield}%"

        return self._create_result(passed, reason, value, self.min_yield)


class PayoutRatioFilter(BaseFilter):
    """Filter by maximum payout ratio (%)."""

    name = "payout_ratio"
    description = "Maximum Payout Ratio"
    category = FilterCategory.DIVIDEND

    def __init__(self, max_ratio: float = 70.0):
        self.max_ratio = max_ratio

    def apply(self, result: ScreeningResult) -> FilterResult:
        value = result.payout_ratio
        passed = value <= self.max_ratio

        if passed:
            reason = f"Payout {value:.1f}% <= {self.max_ratio}%"
        else:
            reason = f"Payout {value:.1f}% > {self.max_ratio}% (unsustainable)"

        return self._create_result(passed, reason, value, self.max_ratio)


class DividendGrowthFilter(BaseFilter):
    """Filter by minimum dividend growth rate (%)."""

    name = "dividend_growth"
    description = "Minimum Dividend Growth Rate"
    category = FilterCategory.DIVIDEND

    def __init__(self, min_growth: float = 3.0):
        self.min_growth = min_growth

    def apply(self, result: ScreeningResult) -> FilterResult:
        value = result.dividend_growth_rate
        passed = value >= self.min_growth

        if passed:
            reason = f"Div Growth {value:.1f}% >= {self.min_growth}%"
        else:
            reason = f"Div Growth {value:.1f}% < {self.min_growth}%"

        return self._create_result(passed, reason, value, self.min_growth)


# ============================================================================
# Sentiment Filters
# ============================================================================


class NewsSentimentFilter(BaseFilter):
    """Filter by minimum news sentiment score."""

    name = "news_sentiment"
    description = "Minimum News Sentiment Score"
    category = FilterCategory.SENTIMENT

    def __init__(self, min_sentiment: float = -0.2):
        self.min_sentiment = min_sentiment

    def apply(self, result: ScreeningResult) -> FilterResult:
        value = result.news_sentiment
        passed = value >= self.min_sentiment

        if passed:
            reason = f"News Sentiment {value:+.2f} >= {self.min_sentiment:+.2f}"
        else:
            reason = f"News Sentiment {value:+.2f} < {self.min_sentiment:+.2f} (too negative)"

        return self._create_result(passed, reason, value, self.min_sentiment)


class InsiderSentimentFilter(BaseFilter):
    """Filter by insider sentiment."""

    name = "insider_sentiment"
    description = "Insider Trading Sentiment"
    category = FilterCategory.SENTIMENT

    def __init__(self, require_bullish: bool = False, allow_neutral: bool = True):
        self.require_bullish = require_bullish
        self.allow_neutral = allow_neutral

    def apply(self, result: ScreeningResult) -> FilterResult:
        sentiment = result.insider_sentiment

        if self.require_bullish:
            passed = sentiment == "bullish"
            reason = f"Insider sentiment: {sentiment}" + (
                " (bullish required)" if not passed else ""
            )
        elif self.allow_neutral:
            passed = sentiment in ("bullish", "neutral")
            reason = f"Insider sentiment: {sentiment}" + (
                " (bearish excluded)" if not passed else ""
            )
        else:
            passed = sentiment == "bullish"
            reason = f"Insider sentiment: {sentiment}"

        return self._create_result(passed, reason, None, None)


# ============================================================================
# Momentum Filters
# ============================================================================


class GrowthFilter(BaseFilter):
    """Filter by minimum earnings/revenue growth (%)."""

    name = "growth_rate"
    description = "Minimum Growth Rate"
    category = FilterCategory.MOMENTUM

    def __init__(self, min_growth: float = 10.0, use_earnings: bool = True):
        self.min_growth = min_growth
        self.use_earnings = use_earnings

    def apply(self, result: ScreeningResult) -> FilterResult:
        value = result.earnings_growth if self.use_earnings else result.revenue_growth
        passed = value >= self.min_growth

        growth_type = "Earnings" if self.use_earnings else "Revenue"

        if passed:
            reason = f"{growth_type} Growth {value:.1f}% >= {self.min_growth}%"
        else:
            reason = f"{growth_type} Growth {value:.1f}% < {self.min_growth}%"

        return self._create_result(passed, reason, value, self.min_growth)


class RuleOf40Filter(BaseFilter):
    """Filter by Rule of 40 (Growth + Margin >= 40)."""

    name = "rule_of_40"
    description = "Rule of 40 (Growth + Margin >= 40)"
    category = FilterCategory.QUALITY

    def __init__(self, min_score: float = 30.0):
        self.min_score = min_score

    def apply(self, result: ScreeningResult) -> FilterResult:
        # Rule of 40 = Growth Rate + Operating Margin
        value = result.earnings_growth + result.operating_margin
        passed = value >= self.min_score

        if passed:
            reason = f"Rule of 40: {value:.1f} >= {self.min_score}"
        else:
            reason = f"Rule of 40: {value:.1f} < {self.min_score}"

        return self._create_result(passed, reason, value, self.min_score)


class CAGRFilter(BaseFilter):
    """Filter by minimum 3-year CAGR (%)."""

    name = "cagr"
    description = "Minimum 3-Year CAGR"
    category = FilterCategory.MOMENTUM

    def __init__(self, min_cagr: float = 5.0):
        self.min_cagr = min_cagr

    def apply(self, result: ScreeningResult) -> FilterResult:
        value = result.cagr_3y
        passed = value >= self.min_cagr

        if passed:
            reason = f"3Y CAGR {value:.1f}% >= {self.min_cagr}%"
        else:
            reason = f"3Y CAGR {value:.1f}% < {self.min_cagr}%"

        return self._create_result(passed, reason, value, self.min_cagr)


class PriceVs52WeekFilter(BaseFilter):
    """Filter by position relative to 52-week range."""

    name = "price_vs_52w"
    description = "Price vs 52-Week Range"
    category = FilterCategory.MOMENTUM

    def __init__(self, max_from_high: float = 30.0):
        """max_from_high: max acceptable % below 52-week high."""
        self.max_from_high = max_from_high

    def apply(self, result: ScreeningResult) -> FilterResult:
        # price_vs_52w_high is % below high (e.g., 20 means 20% below high)
        value = result.price_vs_52w_high
        passed = value <= self.max_from_high

        if passed:
            reason = f"Price {value:.1f}% below 52w high <= {self.max_from_high}%"
        else:
            reason = f"Price {value:.1f}% below 52w high > {self.max_from_high}%"

        return self._create_result(passed, reason, value, self.max_from_high)


# ============================================================================
# Filter Registry
# ============================================================================

FILTER_REGISTRY = {
    # Valuation
    "margin_of_safety": MarginOfSafetyFilter,
    "pe_ratio": PEFilter,
    "pb_ratio": PBFilter,
    "peg_ratio": PEGFilter,
    "undervalued_methods": UndervaluedMethodsFilter,
    # Quality
    "roe": ROEFilter,
    "fcf_yield": FCFYieldFilter,
    "altman_z": AltmanZFilter,
    "roic": ROICFilter,
    "operating_margin": OperatingMarginFilter,
    # Dividend
    "dividend_yield": DividendYieldFilter,
    "payout_ratio": PayoutRatioFilter,
    "dividend_growth": DividendGrowthFilter,
    # Sentiment
    "news_sentiment": NewsSentimentFilter,
    "insider_sentiment": InsiderSentimentFilter,
    # Momentum
    "growth_rate": GrowthFilter,
    "rule_of_40": RuleOf40Filter,
    "cagr": CAGRFilter,
    "price_vs_52w": PriceVs52WeekFilter,
}


def get_filter(name: str, **kwargs) -> BaseFilter:
    """Get a filter instance by name."""
    if name not in FILTER_REGISTRY:
        raise ValueError(f"Unknown filter: {name}. Available: {list(FILTER_REGISTRY.keys())}")
    return FILTER_REGISTRY[name](**kwargs)


def list_filters() -> list:
    """List all available filters."""
    return [
        {
            "name": name,
            "description": cls.description,
            "category": cls.category.value,
        }
        for name, cls in FILTER_REGISTRY.items()
    ]
