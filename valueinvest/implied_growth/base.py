"""Base dataclasses for Implied Growth Rate analysis."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ImpliedGrowthDetail:
    """Result from a single implied growth method."""

    method: str  # e.g. "Reverse DCF", "PEG Implied", "Gordon Growth"
    implied_growth_rate: float  # percentage
    confidence: str  # "High", "Medium", "Low"
    assumptions: Dict[str, Any]  # key assumptions used
    notes: List[str] = field(default_factory=list)

    def to_summary(self) -> str:
        lines = [
            f"{self.method}: {self.implied_growth_rate:.2f}%",
            f"Confidence: {self.confidence}",
        ]
        if self.notes:
            lines.extend(f"  - {note}" for note in self.notes)
        return "\n".join(lines)


@dataclass
class GrowthComparison:
    """Comparison of implied vs historical growth."""

    implied_growth: float  # weighted average implied growth
    historical_revenue_growth: float  # revenue growth rate %
    historical_earnings_growth: float  # earnings growth rate %
    historical_revenue_cagr_5y: float  # 5y revenue CAGR from stock.extra
    historical_earnings_cagr_5y: float  # 5y earnings CAGR from stock.extra
    gap_revenue: float  # implied - historical revenue growth
    gap_earnings: float  # implied - historical earnings growth
    gap_revenue_cagr_5y: float  # implied - 5y revenue CAGR
    gap_earnings_cagr_5y: float  # implied - 5y earnings CAGR
    verdict: str  # "Conservative", "Moderate", "Aggressive", "Extremely Aggressive"

    def to_summary(self) -> str:
        lines = [
            f"Implied Growth: {self.implied_growth:.2f}%",
            f"Revenue Growth (1Y): {self.historical_revenue_growth:.2f}% (gap: {self.gap_revenue:+.2f}pp)",
            f"Earnings Growth (1Y): {self.historical_earnings_growth:.2f}% (gap: {self.gap_earnings:+.2f}pp)",
        ]
        if self.historical_revenue_cagr_5y != 0:
            lines.append(
                f"Revenue CAGR 5Y: {self.historical_revenue_cagr_5y:.2f}% (gap: {self.gap_revenue_cagr_5y:+.2f}pp)"
            )
        if self.historical_earnings_cagr_5y != 0:
            lines.append(
                f"Earnings CAGR 5Y: {self.historical_earnings_cagr_5y:.2f}% (gap: {self.gap_earnings_cagr_5y:+.2f}pp)"
            )
        lines.append(f"Verdict: {self.verdict}")
        return "\n".join(lines)


@dataclass
class GrowthReasonableness:
    """Reasonableness assessment of implied growth."""

    score: float  # 0-100, higher = more reasonable
    rating: str  # "Reasonable", "Somewhat Optimistic", "Optimistic", "Very Optimistic", "Unreasonable"
    factors: List[str]  # individual factor assessments
    red_flags: List[str]  # warning signs
    green_flags: List[str]  # positive signs

    def to_summary(self) -> str:
        lines = [
            f"Reasonableness Score: {self.score:.0f}/100 ({self.rating})",
        ]
        if self.factors:
            lines.append("Factors:")
            for f in self.factors:
                lines.append(f"  - {f}")
        if self.green_flags:
            lines.append("Green Flags: " + "; ".join(self.green_flags))
        if self.red_flags:
            lines.append("Red Flags: " + "; ".join(self.red_flags))
        return "\n".join(lines)


@dataclass
class ImpliedGrowthResult:
    """Complete implied growth analysis result."""

    ticker: str
    name: str
    current_price: float
    details: List[ImpliedGrowthDetail]  # results from each method
    weighted_implied_growth: float  # weighted average across methods
    comparison: GrowthComparison
    reasonableness: GrowthReasonableness
    analysis: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_summary(self) -> str:
        lines = [
            f"=== {self.ticker} {self.name} Implied Growth Analysis ===",
            f"Current Price: {self.current_price}",
            f"Weighted Implied Growth: {self.weighted_implied_growth:.2f}%",
            "",
            "Method Details:",
        ]
        for detail in self.details:
            lines.append(f"  {detail.to_summary()}")
            lines.append("")
        lines.append("Historical Comparison:")
        for line in self.comparison.to_summary().split("\n"):
            lines.append(f"  {line}")
        lines.append("")
        lines.append("Reasonableness Assessment:")
        for line in self.reasonableness.to_summary().split("\n"):
            lines.append(f"  {line}")
        if self.warnings:
            lines.append("")
            lines.append("Warnings:")
            for w in self.warnings:
                lines.append(f"  [!] {w}")
        return "\n".join(lines)

    def __str__(self) -> str:
        parts = [
            f"{self.ticker} ({self.name}):",
            f"Implied Growth = {self.weighted_implied_growth:.2f}%",
            f"Verdict = {self.comparison.verdict}",
            f"Reasonableness = {self.reasonableness.score:.0f}/100 ({self.reasonableness.rating})",
        ]
        return " | ".join(parts)
