"""
Core data structures for the stock screening system.

This module provides:
- ScreeningResult: Comprehensive result for a screened stock
- FilterResult: Result of applying a single filter
- ScreeningStrategy: Strategy configuration with filters and weights
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from abc import ABC, abstractmethod
from enum import Enum


class FilterCategory(Enum):
    """Category of screening filter."""

    VALUATION = "valuation"
    QUALITY = "quality"
    SENTIMENT = "sentiment"
    MOMENTUM = "momentum"
    DIVIDEND = "dividend"


@dataclass
class FilterResult:
    """Result of applying a single filter."""

    filter_name: str
    passed: bool
    reason: str
    value: Optional[float] = None
    threshold: Optional[float] = None
    category: FilterCategory = FilterCategory.VALUATION


@dataclass
class ScoringWeights:
    """Weights for multi-factor scoring model."""

    valuation: float = 0.40  # 估值因子权重
    quality: float = 0.30  # 质量因子权重
    sentiment: float = 0.20  # 情感因子权重
    momentum: float = 0.10  # 动量因子权重

    def normalize(self) -> "ScoringWeights":
        """Normalize weights to sum to 1.0."""
        total = self.valuation + self.quality + self.sentiment + self.momentum
        if total == 0:
            return ScoringWeights(0.25, 0.25, 0.25, 0.25)
        return ScoringWeights(
            valuation=self.valuation / total,
            quality=self.quality / total,
            sentiment=self.sentiment / total,
            momentum=self.momentum / total,
        )

    def to_dict(self) -> Dict[str, float]:
        return {
            "valuation": self.valuation,
            "quality": self.quality,
            "sentiment": self.sentiment,
            "momentum": self.momentum,
        }


@dataclass
class ScreeningResult:
    """Comprehensive screening result for a single stock."""

    # Basic info
    ticker: str
    name: str = ""
    current_price: float = 0.0
    market_cap: float = 0.0

    # Composite scores (0-100)
    composite_score: float = 0.0
    valuation_score: float = 0.0
    quality_score: float = 0.0
    sentiment_score: float = 0.0
    momentum_score: float = 0.0

    # Valuation metrics
    fair_value_median: float = 0.0
    fair_value_avg: float = 0.0
    margin_of_safety: float = 0.0  # 安全边际 %
    undervalued_methods: int = 0  # 认为低估的方法数
    total_methods: int = 0  # 总估值方法数
    pe_ratio: float = 0.0
    pb_ratio: float = 0.0

    # Quality metrics
    roe: float = 0.0  # 净资产收益率 %
    fcf_yield: float = 0.0  # 自由现金流收益率 %
    altman_z: float = 0.0  # Altman Z-Score
    roic: float = 0.0  # 投入资本回报率 %
    operating_margin: float = 0.0  # 营业利润率 %

    # Dividend metrics
    dividend_yield: float = 0.0
    payout_ratio: float = 0.0
    dividend_growth_rate: float = 0.0

    # Sentiment signals
    news_sentiment: float = 0.0  # -1 to 1
    news_sentiment_label: str = "neutral"
    insider_sentiment: str = "neutral"  # bullish/bearish/neutral
    insider_net_value: float = 0.0

    # Momentum metrics
    cagr_1y: float = 0.0  # 1年CAGR (HFQ)
    cagr_3y: float = 0.0  # 3年CAGR (HFQ)
    price_vs_52w_high: float = 0.0  # 当前价 vs 52周最高 %
    price_vs_52w_low: float = 0.0  # 当前价 vs 52周最低 %

    # Growth metrics
    revenue_growth: float = 0.0
    earnings_growth: float = 0.0
    peg_ratio: float = 0.0

    # Filter results
    passed_filters: List[str] = field(default_factory=list)
    failed_filters: List[str] = field(default_factory=list)
    filter_details: List[FilterResult] = field(default_factory=list)

    # Status
    is_qualified: bool = False
    errors: List[str] = field(default_factory=list)

    @property
    def valuation_assessment(self) -> str:
        """Overall valuation assessment."""
        if self.margin_of_safety >= 20:
            return "Undervalued"
        elif self.margin_of_safety >= 10:
            return "Slightly Undervalued"
        elif self.margin_of_safety >= -10:
            return "Fair"
        elif self.margin_of_safety >= -20:
            return "Slightly Overvalued"
        else:
            return "Overvalued"

    @property
    def quality_assessment(self) -> str:
        """Overall quality assessment."""
        score = 0
        if self.roe >= 15:
            score += 1
        if self.fcf_yield >= 5:
            score += 1
        if self.altman_z >= 3:
            score += 1
        if self.operating_margin >= 15:
            score += 1

        if score >= 3:
            return "High Quality"
        elif score >= 2:
            return "Good Quality"
        elif score >= 1:
            return "Average Quality"
        else:
            return "Low Quality"

    @property
    def sentiment_assessment(self) -> str:
        """Overall sentiment assessment."""
        signals = []
        if self.news_sentiment > 0.3:
            signals.append("positive news")
        elif self.news_sentiment < -0.3:
            signals.append("negative news")

        if self.insider_sentiment == "bullish":
            signals.append("insider buying")
        elif self.insider_sentiment == "bearish":
            signals.append("insider selling")

        if not signals:
            return "Neutral"
        return ", ".join(signals)

    @property
    def grade(self) -> str:
        """Letter grade based on composite score."""
        if self.composite_score >= 85:
            return "A+"
        elif self.composite_score >= 80:
            return "A"
        elif self.composite_score >= 75:
            return "A-"
        elif self.composite_score >= 70:
            return "B+"
        elif self.composite_score >= 65:
            return "B"
        elif self.composite_score >= 60:
            return "B-"
        elif self.composite_score >= 55:
            return "C+"
        elif self.composite_score >= 50:
            return "C"
        elif self.composite_score >= 45:
            return "C-"
        else:
            return "D"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "ticker": self.ticker,
            "name": self.name,
            "current_price": self.current_price,
            "market_cap": self.market_cap,
            "composite_score": round(self.composite_score, 1),
            "grade": self.grade,
            "valuation_score": round(self.valuation_score, 1),
            "quality_score": round(self.quality_score, 1),
            "sentiment_score": round(self.sentiment_score, 1),
            "momentum_score": round(self.momentum_score, 1),
            "margin_of_safety": round(self.margin_of_safety, 1),
            "valuation_assessment": self.valuation_assessment,
            "quality_assessment": self.quality_assessment,
            "roe": round(self.roe, 1),
            "fcf_yield": round(self.fcf_yield, 1),
            "altman_z": round(self.altman_z, 2),
            "dividend_yield": round(self.dividend_yield, 2),
            "news_sentiment": round(self.news_sentiment, 2),
            "insider_sentiment": self.insider_sentiment,
            "passed_filters": self.passed_filters,
            "failed_filters": self.failed_filters,
            "is_qualified": self.is_qualified,
        }


class BaseFilter(ABC):
    """Abstract base class for screening filters."""

    name: str = "base_filter"
    description: str = "Base filter"
    category: FilterCategory = FilterCategory.VALUATION

    @abstractmethod
    def apply(self, result: ScreeningResult) -> FilterResult:
        """
        Apply the filter to a screening result.

        Returns:
            FilterResult with pass/fail status and reason
        """
        pass

    def _create_result(
        self,
        passed: bool,
        reason: str,
        value: Optional[float] = None,
        threshold: Optional[float] = None,
    ) -> FilterResult:
        """Helper to create a FilterResult."""
        return FilterResult(
            filter_name=self.name,
            passed=passed,
            reason=reason,
            value=value,
            threshold=threshold,
            category=self.category,
        )


@dataclass
class ScreeningStrategy:
    """Configuration for a screening strategy."""

    name: str
    description: str
    filters: List[BaseFilter]
    weights: ScoringWeights = field(default_factory=ScoringWeights)

    def apply_filters(self, result: ScreeningResult) -> Tuple[bool, List[FilterResult]]:
        """
        Apply all filters to a screening result.

        Returns:
            Tuple of (all_passed, filter_results)
        """
        all_passed = True
        filter_results = []

        for f in self.filters:
            try:
                fr = f.apply(result)
                filter_results.append(fr)

                if fr.passed:
                    result.passed_filters.append(fr.filter_name)
                else:
                    result.failed_filters.append(fr.filter_name)
                    all_passed = False
            except Exception as e:
                filter_results.append(
                    FilterResult(
                        filter_name=f.name,
                        passed=False,
                        reason=f"Error: {str(e)}",
                        category=f.category,
                    )
                )
                result.failed_filters.append(f.name)
                all_passed = False

        result.filter_details = filter_results
        result.is_qualified = all_passed

        return all_passed, filter_results
