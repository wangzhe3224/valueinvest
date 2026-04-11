"""Data structures for Peer Comparison Analysis."""

from dataclasses import dataclass, field
from typing import List
from enum import Enum


class ComparisonRating(Enum):
    """Overall peer comparison rating."""

    OUTSTANDING = "outstanding"  # Top decile
    ABOVE_AVERAGE = "above_average"
    AVERAGE = "average"
    BELOW_AVERAGE = "below_average"
    LAGGING = "lagging"  # Bottom quartile


class MetricDirection(Enum):
    """Whether higher or lower is better for a metric."""

    HIGHER_BETTER = "higher_better"  # ROE, margins, growth
    LOWER_BETTER = "lower_better"  # PE, PB, debt_ratio


@dataclass
class MetricComparison:
    """Comparison of a single metric against peers."""

    metric_name: str  # e.g. "PE Ratio"
    metric_key: str  # e.g. "pe_ratio"
    target_value: float  # Target stock's value
    peer_avg: float  # Average across peers
    peer_median: float  # Median across peers
    peer_count: int  # Number of peers with valid data
    percentile: float  # Target stock's percentile (0-100)
    direction: MetricDirection  # Higher or lower is better
    is_available: bool = True  # Whether sufficient data was available

    @property
    def vs_avg_pct(self) -> float:
        """Percentage difference vs peer average."""
        if self.peer_avg == 0 or not self.is_available:
            return 0.0
        return ((self.target_value - self.peer_avg) / abs(self.peer_avg)) * 100

    @property
    def assessment(self) -> str:
        """Brief assessment string."""
        if not self.is_available:
            return "N/A"
        if self.direction == MetricDirection.HIGHER_BETTER:
            if self.percentile >= 75:
                return "significantly above peers"
            elif self.percentile >= 50:
                return "above peers"
            elif self.percentile >= 25:
                return "below peers"
            else:
                return "significantly below peers"
        else:  # LOWER_BETTER
            if self.percentile <= 25:
                return "significantly below peers (good)"
            elif self.percentile <= 50:
                return "below peers (good)"
            elif self.percentile <= 75:
                return "above peers (concerning)"
            else:
                return "significantly above peers (concerning)"


@dataclass
class PeerComparisonResult:
    """Complete peer comparison analysis result."""

    ticker: str
    industry_name: str
    market: str
    composite_score: float  # 0-100 weighted composite
    rating: ComparisonRating

    # Individual metric comparisons
    metric_comparisons: List[MetricComparison] = field(default_factory=list)

    # Summary statistics
    peer_count: int = 0
    rank_in_peers: int = 0
    percentile_rank: float = 0.0  # Market-cap based percentile

    # Key highlights
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    analysis: List[str] = field(default_factory=list)

    @property
    def has_sufficient_peers(self) -> bool:
        """Whether there are enough peers for meaningful comparison."""
        return self.peer_count >= 3

    @property
    def valuation_score(self) -> float:
        """Average percentile for valuation metrics (PE, PB)."""
        val_metrics = [
            m
            for m in self.metric_comparisons
            if m.metric_key in ("pe_ratio", "pb_ratio") and m.is_available
        ]
        if not val_metrics:
            return 0.0
        return sum(m.percentile for m in val_metrics) / len(val_metrics)

    @property
    def profitability_score(self) -> float:
        """Average percentile for profitability metrics (ROE, net_margin, operating_margin)."""
        prof_metrics = [
            m
            for m in self.metric_comparisons
            if m.metric_key in ("roe", "net_margin", "operating_margin")
            and m.is_available
        ]
        if not prof_metrics:
            return 0.0
        return sum(m.percentile for m in prof_metrics) / len(prof_metrics)

    @property
    def growth_score(self) -> float:
        """Percentile for revenue growth."""
        growth = [
            m
            for m in self.metric_comparisons
            if m.metric_key == "revenue_growth" and m.is_available
        ]
        return growth[0].percentile if growth else 0.0

    @property
    def size_score(self) -> float:
        """Percentile for market cap (scale)."""
        size = [
            m
            for m in self.metric_comparisons
            if m.metric_key == "market_cap" and m.is_available
        ]
        return size[0].percentile if size else 0.0

    def to_summary(self) -> str:
        """One-line summary."""
        return (
            f"PeerComparison({self.ticker}): Score={self.composite_score:.0f}/100 | "
            f"Rating={self.rating.value.upper()} | "
            f"Peers={self.peer_count} | "
            f"Industry={self.industry_name}"
        )

    def __str__(self) -> str:
        lines = [self.to_summary()]
        lines.append(
            f"  Rank: #{self.rank_in_peers} / {self.peer_count} "
            f"(Percentile: {self.percentile_rank:.0f}th)"
        )
        for m in self.metric_comparisons:
            avail = "" if m.is_available else " [N/A]"
            direction = (
                "\u2191" if m.direction == MetricDirection.HIGHER_BETTER else "\u2193"
            )
            lines.append(
                f"  {direction} {m.metric_name}: {m.target_value:.1f} "
                f"(Avg: {m.peer_avg:.1f}, P{m.percentile:.0f}){avail}"
            )
        if self.strengths:
            lines.append("  Strengths: " + "; ".join(self.strengths[:3]))
        if self.weaknesses:
            lines.append("  Weaknesses: " + "; ".join(self.weaknesses[:3]))
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.to_summary()


def _score_to_rating(score: float) -> ComparisonRating:
    """Convert 0-100 composite score to ComparisonRating."""
    if score >= 80:
        return ComparisonRating.OUTSTANDING
    elif score >= 60:
        return ComparisonRating.ABOVE_AVERAGE
    elif score >= 40:
        return ComparisonRating.AVERAGE
    elif score >= 20:
        return ComparisonRating.BELOW_AVERAGE
    else:
        return ComparisonRating.LAGGING
