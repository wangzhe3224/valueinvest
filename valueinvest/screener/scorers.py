"""
Multi-factor scoring system for stock screening.

This module provides:
- CompositeScorer: Main scorer that combines multiple factors
- Individual factor scoring functions
- Score normalization utilities
"""
from typing import Dict, Any, Optional
from .base import ScreeningResult, ScoringWeights


def clamp(value: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
    """Clamp a value to a range."""
    return max(min_val, min(max_val, value))


def normalize_to_score(
    value: float, min_val: float, max_val: float, reverse: bool = False
) -> float:
    """
    Normalize a value to 0-100 score.

    Args:
        value: The value to normalize
        min_val: Value that maps to 0 (or 100 if reverse)
        max_val: Value that maps to 100 (or 0 if reverse)
        reverse: If True, higher values get lower scores

    Returns:
        Score from 0 to 100
    """
    if max_val == min_val:
        return 50.0

    normalized = (value - min_val) / (max_val - min_val) * 100

    if reverse:
        normalized = 100 - normalized

    return clamp(normalized)


class CompositeScorer:
    """
    Multi-factor composite scorer for stock screening.

    Scoring factors:
    - Valuation (40%): Based on margin of safety and method consensus
    - Quality (30%): Based on ROE, FCF yield, Altman Z
    - Sentiment (20%): Based on news and insider sentiment
    - Momentum (10%): Based on CAGR and price position
    """

    def __init__(self, weights: Optional[ScoringWeights] = None):
        self.weights = weights or ScoringWeights()
        self.weights = self.weights.normalize()

    def score(self, result: ScreeningResult) -> float:
        """
        Calculate composite score for a screening result.

        Updates result in-place with individual factor scores.
        Returns composite score (0-100).
        """
        # Calculate individual factor scores
        result.valuation_score = self._calc_valuation_score(result)
        result.quality_score = self._calc_quality_score(result)
        result.sentiment_score = self._calc_sentiment_score(result)
        result.momentum_score = self._calc_momentum_score(result)

        # Calculate weighted composite
        composite = (
            result.valuation_score * self.weights.valuation
            + result.quality_score * self.weights.quality
            + result.sentiment_score * self.weights.sentiment
            + result.momentum_score * self.weights.momentum
        )

        result.composite_score = clamp(composite)
        return result.composite_score

    def _calc_valuation_score(self, result: ScreeningResult) -> float:
        """
        Calculate valuation score (0-100).

        Components:
        - Margin of Safety: Higher is better
        - Method Consensus: More undervalued methods = higher score
        """
        scores = []

        # Margin of Safety score
        # -30% MOS -> 0, 0% MOS -> 50, +30% MOS -> 100
        mos_score = normalize_to_score(result.margin_of_safety, -30, 30)
        scores.append(mos_score)

        # Method consensus score
        # What % of methods agree it's undervalued?
        if result.total_methods > 0:
            consensus = (result.undervalued_methods / result.total_methods) * 100
            scores.append(consensus)

        # P/E relative score (inverse - lower P/E is better)
        if result.pe_ratio > 0:
            pe_score = normalize_to_score(result.pe_ratio, 5, 40, reverse=True)
            scores.append(pe_score)

        return sum(scores) / len(scores) if scores else 50.0

    def _calc_quality_score(self, result: ScreeningResult) -> float:
        """
        Calculate quality score (0-100).

        Components:
        - ROE: Higher is better
        - FCF Yield: Higher is better
        - Altman Z: Higher is better (safety)
        - Operating Margin: Higher is better
        """
        scores = []

        # ROE score: 0% -> 0, 10% -> 50, 25%+ -> 100
        if result.roe != 0:
            roe_score = normalize_to_score(result.roe, 0, 25)
            scores.append(roe_score)

        # FCF Yield score: 0% -> 0, 5% -> 50, 10%+ -> 100
        if result.fcf_yield != 0:
            fcf_score = normalize_to_score(result.fcf_yield, 0, 10)
            scores.append(fcf_score)

        # Altman Z score: 1.8 -> 0, 3.0 -> 80, 5.0+ -> 100
        if result.altman_z != 0:
            z_score = normalize_to_score(result.altman_z, 1.8, 5.0)
            scores.append(z_score)

        # Operating Margin score: 0% -> 0, 15% -> 50, 30%+ -> 100
        if result.operating_margin != 0:
            margin_score = normalize_to_score(result.operating_margin, 0, 30)
            scores.append(margin_score)

        # ROIC score if available: 0% -> 0, 15% -> 50, 30%+ -> 100
        if result.roic != 0:
            roic_score = normalize_to_score(result.roic, 0, 30)
            scores.append(roic_score)

        return sum(scores) / len(scores) if scores else 50.0

    def _calc_sentiment_score(self, result: ScreeningResult) -> float:
        """
        Calculate sentiment score (0-100).

        Components:
        - News Sentiment: -1 -> 0, 0 -> 50, +1 -> 100
        - Insider Sentiment: bearish -> 20, neutral -> 50, bullish -> 80
        """
        scores = []

        # News sentiment score: -1 to 1 maps to 0-100
        news_score = normalize_to_score(result.news_sentiment, -1, 1)
        scores.append(news_score)

        # Insider sentiment score
        insider_scores = {
            "bullish": 80,
            "neutral": 50,
            "bearish": 20,
        }
        insider_score = insider_scores.get(result.insider_sentiment, 50)
        scores.append(insider_score)

        return sum(scores) / len(scores)

    def _calc_momentum_score(self, result: ScreeningResult) -> float:
        """
        Calculate momentum score (0-100).

        Components:
        - 3Y CAGR: -10% -> 0, 5% -> 50, 20%+ -> 100
        - Price vs 52w High: 50% below -> 0, 20% below -> 50, at high -> 100
        """
        scores = []

        # CAGR score
        if result.cagr_3y != 0:
            cagr_score = normalize_to_score(result.cagr_3y, -10, 20)
            scores.append(cagr_score)

        # Price position score (how close to 52w high)
        # price_vs_52w_high is % below high, so we want lower values
        if result.price_vs_52w_high != 0:
            position_score = normalize_to_score(result.price_vs_52w_high, 50, 0)
            scores.append(position_score)

        # Growth rate if available
        if result.earnings_growth != 0:
            growth_score = normalize_to_score(result.earnings_growth, -10, 30)
            scores.append(growth_score)

        return sum(scores) / len(scores) if scores else 50.0

    def get_score_breakdown(self, result: ScreeningResult) -> Dict[str, Any]:
        """Get detailed score breakdown for a result."""
        return {
            "composite": round(result.composite_score, 1),
            "grade": result.grade,
            "factors": {
                "valuation": {
                    "score": round(result.valuation_score, 1),
                    "weight": round(self.weights.valuation * 100, 0),
                    "components": {
                        "margin_of_safety": round(result.margin_of_safety, 1),
                        "undervalued_methods": f"{result.undervalued_methods}/{result.total_methods}",
                        "pe_ratio": round(result.pe_ratio, 1),
                    },
                },
                "quality": {
                    "score": round(result.quality_score, 1),
                    "weight": round(self.weights.quality * 100, 0),
                    "components": {
                        "roe": round(result.roe, 1),
                        "fcf_yield": round(result.fcf_yield, 1),
                        "altman_z": round(result.altman_z, 2),
                        "operating_margin": round(result.operating_margin, 1),
                    },
                },
                "sentiment": {
                    "score": round(result.sentiment_score, 1),
                    "weight": round(self.weights.sentiment * 100, 0),
                    "components": {
                        "news_sentiment": round(result.news_sentiment, 2),
                        "insider_sentiment": result.insider_sentiment,
                    },
                },
                "momentum": {
                    "score": round(result.momentum_score, 1),
                    "weight": round(self.weights.momentum * 100, 0),
                    "components": {
                        "cagr_3y": round(result.cagr_3y, 1),
                        "price_vs_52w_high": round(result.price_vs_52w_high, 1),
                        "earnings_growth": round(result.earnings_growth, 1),
                    },
                },
            },
            "assessments": {
                "valuation": result.valuation_assessment,
                "quality": result.quality_assessment,
                "sentiment": result.sentiment_assessment,
            },
        }


class ValuationScorer(CompositeScorer):
    """Scorer focused on valuation (60% valuation weight)."""

    def __init__(self):
        super().__init__(
            ScoringWeights(
                valuation=0.60,
                quality=0.25,
                sentiment=0.10,
                momentum=0.05,
            )
        )


class QualityScorer(CompositeScorer):
    """Scorer focused on quality (50% quality weight)."""

    def __init__(self):
        super().__init__(
            ScoringWeights(
                valuation=0.25,
                quality=0.50,
                sentiment=0.15,
                momentum=0.10,
            )
        )


class GrowthScorer(CompositeScorer):
    """Scorer focused on growth (momentum + valuation)."""

    def __init__(self):
        super().__init__(
            ScoringWeights(
                valuation=0.30,
                quality=0.25,
                sentiment=0.15,
                momentum=0.30,
            )
        )


class DividendScorer(CompositeScorer):
    """Scorer for dividend stocks (quality + valuation focus)."""

    def __init__(self):
        super().__init__(
            ScoringWeights(
                valuation=0.35,
                quality=0.45,
                sentiment=0.15,
                momentum=0.05,
            )
        )

    def _calc_quality_score(self, result: ScreeningResult) -> float:
        """Enhanced quality score including dividend metrics."""
        base_score = super()._calc_quality_score(result)

        # Add dividend-specific quality metrics
        dividend_scores = []

        # Payout ratio score (inverse - lower is safer)
        if result.payout_ratio > 0:
            payout_score = normalize_to_score(result.payout_ratio, 30, 80, reverse=True)
            dividend_scores.append(payout_score)

        # Dividend growth score
        if result.dividend_growth_rate != 0:
            growth_score = normalize_to_score(result.dividend_growth_rate, 0, 15)
            dividend_scores.append(growth_score)

        if dividend_scores:
            return (base_score + sum(dividend_scores) / len(dividend_scores)) / 2
        return base_score


# Scorer registry
SCORER_REGISTRY = {
    "default": CompositeScorer,
    "valuation": ValuationScorer,
    "value": ValuationScorer,  # alias
    "quality": QualityScorer,
    "growth": GrowthScorer,
    "dividend": DividendScorer,
    "garp": GrowthScorer,  # GARP uses growth scorer
}


def get_scorer(name: str = "default", weights: Optional[ScoringWeights] = None) -> CompositeScorer:
    """Get a scorer instance by name or with custom weights."""
    if weights:
        return CompositeScorer(weights)

    if name not in SCORER_REGISTRY:
        raise ValueError(f"Unknown scorer: {name}. Available: {list(SCORER_REGISTRY.keys())}")

    return SCORER_REGISTRY[name]()
