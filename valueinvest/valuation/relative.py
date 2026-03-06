"""
Relative Valuation Methods

Compares current multiples (PE, PB, PS, EV/EBITDA) to:
1. Historical averages
2. Peer group averages
3. Industry benchmarks

Professional equity research standard approach.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from .base import BaseValuation, ValuationResult, FieldRequirement


@dataclass
class RelativeMultiples:
    """Container for relative valuation multiples."""

    current: float
    historical_avg: float
    historical_median: float
    historical_low: float
    historical_high: float
    peer_avg: Optional[float] = None
    industry_avg: Optional[float] = None

    @property
    def vs_historical(self) -> float:
        """Premium/discount vs historical average (%)"""
        if self.historical_avg <= 0:
            return 0
        return ((self.current - self.historical_avg) / self.historical_avg) * 100

    @property
    def vs_peer(self) -> Optional[float]:
        """Premium/discount vs peer average (%)"""
        if not self.peer_avg or self.peer_avg <= 0:
            return None
        return ((self.current - self.peer_avg) / self.peer_avg) * 100

    @property
    def vs_industry(self) -> Optional[float]:
        """Premium/discount vs industry average (%)"""
        if not self.industry_avg or self.industry_avg <= 0:
            return None
        return ((self.current - self.industry_avg) / self.industry_avg) * 100

    @property
    def percentile_in_history(self) -> float:
        """Where current multiple sits in historical range (0-100)"""
        if self.historical_high <= self.historical_low:
            return 50
        return (
            (self.current - self.historical_low) / (self.historical_high - self.historical_low)
        ) * 100


class PERelativeValuation(BaseValuation):
    """
    PE Relative Valuation

    Compares current P/E ratio to:
    - 5-year historical average
    - Peer group average (if provided)
    - Industry average (if provided)

    Professional equity research standard approach for identifying
    overvalued/undervalued stocks relative to their own history and peers.
    """

    method_name = "PE Relative"

    required_fields = [
        FieldRequirement("current_price", "Current Stock Price", is_critical=True, min_value=0.01),
        FieldRequirement("eps", "Earnings Per Share", is_critical=True),
        FieldRequirement("historical_pe", "Historical PE Ratios (5Y)", is_critical=False),
    ]

    best_for = [
        "Profitable companies with stable earnings",
        "Mature companies with trading history",
        "Peer comparison analysis",
    ]

    not_for = [
        "Negative earnings companies",
        "Early-stage startups",
        "Highly cyclical companies (use normalized PE)",
    ]

    def __init__(
        self,
        peer_group: Optional[List[str]] = None,
        industry_avg_pe: Optional[float] = None,
        historical_years: int = 5,
        fair_multiple_range: tuple = (-15, 15),  # ±15% from fair
    ):
        """
        Initialize PE Relative Valuation.

        Args:
            peer_group: List of peer ticker symbols (e.g., ["MSFT", "GOOGL", "AMZN"])
            industry_avg_pe: Industry average P/E ratio
            historical_years: Years of historical data to consider
            fair_multiple_range: Range (low, high) considered "fair" vs historical
        """
        self.peer_group = peer_group or []
        self.industry_avg_pe = industry_avg_pe
        self.historical_years = historical_years
        self.fair_multiple_range = fair_multiple_range

    def calculate(self, stock) -> ValuationResult:
        """Calculate PE relative valuation."""
        is_valid, missing, warnings = self.validate_data(stock)
        if not is_valid:
            return self._create_error_result(
                stock, f"Missing required data: {', '.join(missing)}", missing
            )

        current_pe = stock.pe_ratio

        if current_pe <= 0:
            return self._create_error_result(
                stock, "P/E ratio must be positive (company must be profitable)", ["pe_ratio"]
            )

        # Calculate historical statistics
        historical_pe = stock.historical_pe if stock.historical_pe else []

        if historical_pe and len(historical_pe) > 0:
            hist_avg = sum(historical_pe) / len(historical_pe)
            sorted_pe = sorted(historical_pe)
            hist_median = sorted_pe[len(sorted_pe) // 2]
            hist_low = min(historical_pe)
            hist_high = max(historical_pe)
        else:
            # If no historical data, use current PE as baseline (limited analysis)
            hist_avg = current_pe
            hist_median = current_pe
            hist_low = current_pe
            hist_high = current_pe
            warnings.append("No historical PE data available - using current PE as baseline")

        # Peer group analysis (if data available)
        peer_avg = None
        if self.peer_group:
            # Note: In production, would fetch peer PE data from API
            # For now, expect it to be passed via extra dict
            peer_data = stock.extra.get("peer_pe_ratios", {})
            if peer_data:
                peer_pes = [pe for pe in peer_data.values() if pe > 0]
                if peer_pes:
                    peer_avg = sum(peer_pes) / len(peer_pes)

        # Industry comparison
        industry_avg = self.industry_avg_pe or stock.extra.get("industry_avg_pe")

        # Build multiples object
        multiples = RelativeMultiples(
            current=current_pe,
            historical_avg=hist_avg,
            historical_median=hist_median,
            historical_low=hist_low,
            historical_high=hist_high,
            peer_avg=peer_avg,
            industry_avg=industry_avg,
        )

        # Calculate implied fair value using historical average as baseline
        fair_value_pe = hist_avg
        fair_value = stock.eps * fair_value_pe

        # Adjust if significantly different from peers
        if peer_avg and peer_avg > 0:
            # Blend historical and peer (70% historical, 30% peer)
            blended_pe = (hist_avg * 0.7) + (peer_avg * 0.3)
            fair_value = stock.eps * blended_pe

        premium_discount = ((fair_value - stock.current_price) / stock.current_price) * 100

        # Assessment based on historical position
        percentile = multiples.percentile_in_history

        if percentile < 25:
            assessment = "Undervalued (bottom quartile historically)"
        elif percentile < 40:
            assessment = "Undervalued"
        elif percentile <= 60:
            assessment = "Fair Value"
        elif percentile <= 75:
            assessment = "Overvalued"
        else:
            assessment = "Overvalued (top quartile historically)"

        # Build analysis text
        analysis = [
            f"Current P/E: {current_pe:.1f}x",
            f"Historical Average (5Y): {hist_avg:.1f}x",
            f"Historical Median: {hist_median:.1f}x",
            f"Historical Range: {hist_low:.1f}x - {hist_high:.1f}x",
            f"Current Percentile: {percentile:.0f}th (in historical range)",
            f"vs Historical: {multiples.vs_historical:+.1f}%",
        ]

        if peer_avg:
            analysis.append(f"Peer Average: {peer_avg:.1f}x")
            analysis.append(f"vs Peers: {multiples.vs_peer:+.1f}%")

        if industry_avg:
            analysis.append(f"Industry Average: {industry_avg:.1f}x")
            analysis.append(f"vs Industry: {multiples.vs_industry:+.1f}%")

        analysis.extend(
            [
                "",
                f"Fair Value (using {hist_avg:.1f}x P/E): ${fair_value:.2f}",
                f"Current Price: ${stock.current_price:.2f}",
                f"Premium/Discount: {premium_discount:+.1f}%",
            ]
        )

        # Interpretation
        if abs(multiples.vs_historical) < 10:
            analysis.append(
                "\nInterpretation: Stock trades close to historical average - fair value."
            )
        elif multiples.vs_historical < -20:
            analysis.append(
                "\n⚠️  Significant discount to history - potential opportunity or deteriorating fundamentals."
            )
        elif multiples.vs_historical > 20:
            analysis.append(
                "\n⚠️  Significant premium to history - stretched valuation or improving fundamentals."
            )

        if warnings:
            analysis.extend(["", "Notes:"] + [f"  - {w}" for w in warnings])

        confidence = (
            "High" if len(historical_pe) >= 10 else ("Medium" if len(historical_pe) >= 5 else "Low")
        )

        return ValuationResult(
            method=self.method_name,
            fair_value=round(fair_value, 2),
            current_price=stock.current_price,
            premium_discount=round(premium_discount, 1),
            assessment=assessment,
            details={
                "current_pe": round(current_pe, 2),
                "historical_avg_pe": round(hist_avg, 2),
                "historical_median_pe": round(hist_median, 2),
                "historical_low_pe": round(hist_low, 2),
                "historical_high_pe": round(hist_high, 2),
                "percentile_in_history": round(percentile, 1),
                "vs_historical_pct": round(multiples.vs_historical, 1),
                "peer_avg_pe": round(peer_avg, 2) if peer_avg else None,
                "industry_avg_pe": round(industry_avg, 2) if industry_avg else None,
                "data_points": len(historical_pe),
            },
            components={
                "current_pe": current_pe,
                "historical_avg": hist_avg,
            },
            analysis=analysis,
            confidence=confidence,
            applicability="Applicable" if current_pe > 0 else "Limited",
        )


class PBRelativeValuation(BaseValuation):
    """
    P/B Relative Valuation

    Compares current P/B ratio to historical and peer averages.
    Most useful for:
    - Financial companies (banks, insurance)
    - Asset-heavy companies
    - Value investing
    """

    method_name = "PB Relative"

    required_fields = [
        FieldRequirement("current_price", "Current Stock Price", is_critical=True, min_value=0.01),
        FieldRequirement("bvps", "Book Value Per Share", is_critical=True),
        FieldRequirement("historical_pb", "Historical PB Ratios (5Y)", is_critical=False),
    ]

    best_for = [
        "Banks and financials",
        "Asset-heavy companies",
        "Value investing",
        "Companies with tangible book value",
    ]

    not_for = [
        "Asset-light companies (software, services)",
        "Companies with significant intangibles",
        "Negative book value companies",
    ]

    def __init__(
        self,
        peer_group: Optional[List[str]] = None,
        industry_avg_pb: Optional[float] = None,
        historical_years: int = 5,
    ):
        self.peer_group = peer_group or []
        self.industry_avg_pb = industry_avg_pb
        self.historical_years = historical_years

    def calculate(self, stock) -> ValuationResult:
        """Calculate PB relative valuation."""
        is_valid, missing, warnings = self.validate_data(stock)
        if not is_valid:
            return self._create_error_result(
                stock, f"Missing required data: {', '.join(missing)}", missing
            )

        current_pb = stock.pb_ratio

        if current_pb <= 0:
            return self._create_error_result(stock, "P/B ratio must be positive", ["pb_ratio"])

        # Historical statistics
        historical_pb = stock.historical_pb if stock.historical_pb else []

        if historical_pb and len(historical_pb) > 0:
            hist_avg = sum(historical_pb) / len(historical_pb)
            sorted_pb = sorted(historical_pb)
            hist_median = sorted_pb[len(sorted_pb) // 2]
            hist_low = min(historical_pb)
            hist_high = max(historical_pb)
        else:
            hist_avg = current_pb
            hist_median = current_pb
            hist_low = current_pb
            hist_high = current_pb
            warnings.append("No historical PB data available - using current PB as baseline")

        # Peer/industry data
        peer_avg = None
        if self.peer_group:
            peer_data = stock.extra.get("peer_pb_ratios", {})
            if peer_data:
                peer_pbs = [pb for pb in peer_data.values() if pb > 0]
                if peer_pbs:
                    peer_avg = sum(peer_pbs) / len(peer_pbs)

        industry_avg = self.industry_avg_pb or stock.extra.get("industry_avg_pb")

        # Build multiples object
        multiples = RelativeMultiples(
            current=current_pb,
            historical_avg=hist_avg,
            historical_median=hist_median,
            historical_low=hist_low,
            historical_high=hist_high,
            peer_avg=peer_avg,
            industry_avg=industry_avg,
        )

        # Fair value using historical average P/B
        fair_value_pb = hist_avg
        fair_value = stock.bvps * fair_value_pb

        if peer_avg and peer_avg > 0:
            blended_pb = (hist_avg * 0.7) + (peer_avg * 0.3)
            fair_value = stock.bvps * blended_pb

        premium_discount = ((fair_value - stock.current_price) / stock.current_price) * 100

        percentile = multiples.percentile_in_history

        if percentile < 25:
            assessment = "Undervalued (bottom quartile historically)"
        elif percentile < 40:
            assessment = "Undervalued"
        elif percentile <= 60:
            assessment = "Fair Value"
        elif percentile <= 75:
            assessment = "Overvalued"
        else:
            assessment = "Overvalued (top quartile historically)"

        analysis = [
            f"Current P/B: {current_pb:.2f}x",
            f"Historical Average (5Y): {hist_avg:.2f}x",
            f"Historical Median: {hist_median:.2f}x",
            f"Historical Range: {hist_low:.2f}x - {hist_high:.2f}x",
            f"Current Percentile: {percentile:.0f}th",
            f"vs Historical: {multiples.vs_historical:+.1f}%",
        ]

        if peer_avg:
            analysis.append(f"Peer Average: {peer_avg:.2f}x")
            analysis.append(f"vs Peers: {multiples.vs_peer:+.1f}%")

        if industry_avg:
            analysis.append(f"Industry Average: {industry_avg:.2f}x")

        analysis.extend(
            [
                "",
                f"Fair Value (using {hist_avg:.2f}x P/B): ${fair_value:.2f}",
                f"Current Price: ${stock.current_price:.2f}",
                f"Premium/Discount: {premium_discount:+.1f}%",
            ]
        )

        # P/B specific interpretation
        if current_pb < 1.0:
            analysis.append(
                f"\n💡 Trading below book value (P/B < 1.0) - potential deep value or distress."
            )
        elif current_pb < 1.5:
            analysis.append(f"\n💡 Modest premium to book - reasonable for most industries.")

        if warnings:
            analysis.extend(["", "Notes:"] + [f"  - {w}" for w in warnings])

        confidence = (
            "High" if len(historical_pb) >= 10 else ("Medium" if len(historical_pb) >= 5 else "Low")
        )

        return ValuationResult(
            method=self.method_name,
            fair_value=round(fair_value, 2),
            current_price=stock.current_price,
            premium_discount=round(premium_discount, 1),
            assessment=assessment,
            details={
                "current_pb": round(current_pb, 2),
                "historical_avg_pb": round(hist_avg, 2),
                "historical_median_pb": round(hist_median, 2),
                "historical_low_pb": round(hist_low, 2),
                "historical_high_pb": round(hist_high, 2),
                "percentile_in_history": round(percentile, 1),
                "vs_historical_pct": round(multiples.vs_historical, 1),
                "peer_avg_pb": round(peer_avg, 2) if peer_avg else None,
                "industry_avg_pb": round(industry_avg, 2) if industry_avg else None,
                "data_points": len(historical_pb),
            },
            components={
                "current_pb": current_pb,
                "historical_avg": hist_avg,
            },
            analysis=analysis,
            confidence=confidence,
            applicability="Applicable" if current_pb > 0 else "Limited",
        )
