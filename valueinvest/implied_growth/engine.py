"""Implied Growth Rate Engine: orchestrates multi-method implied growth analysis."""

from typing import List

from valueinvest.stock import Stock

from .analyzer import (
    assess_reasonableness,
    calculate_earnings_yield_implied_growth,
    calculate_gordon_growth_implied_growth,
    calculate_peg_implied_growth,
    calculate_reverse_dcf_implied_growth,
    compare_with_historical,
)
from .base import (
    GrowthComparison,
    GrowthReasonableness,
    ImpliedGrowthDetail,
    ImpliedGrowthResult,
)

# Confidence weights for weighted average
_CONFIDENCE_WEIGHTS = {"High": 3, "Medium": 2, "Low": 1}


class ImpliedGrowthEngine:
    """Main engine for implied growth rate analysis.

    Derives the growth rate implied by the current stock price using
    multiple methods, compares with historical growth, and assesses
    whether the implied growth is reasonable.
    """

    def __init__(self, peg_fair_ratio: float = 1.0):
        """Initialize the implied growth engine.

        Args:
            peg_fair_ratio: Assumed fair PEG ratio for PEG-based method (default 1.0)
        """
        self.peg_fair_ratio = peg_fair_ratio

    def analyze(self, stock: Stock) -> ImpliedGrowthResult:
        """Run full implied growth rate analysis.

        Steps:
        1. Run all applicable implied growth methods
        2. Calculate weighted average across methods
        3. Compare with historical growth rates
        4. Assess reasonableness of implied growth
        5. Build analysis summary

        Args:
            stock: Stock instance with financial data

        Returns:
            ImpliedGrowthResult with complete analysis
        """
        # Step 1: Run all applicable methods
        details = self._run_all_methods(stock)

        # Step 2: Calculate weighted average
        weighted_growth = self._calculate_weighted_average(details)

        # Step 3: Compare with historical
        comparison = compare_with_historical(stock, weighted_growth)

        # Step 4: Assess reasonableness
        reasonableness = assess_reasonableness(stock, weighted_growth, comparison)

        # Step 5: Build analysis summary
        analysis = self._build_analysis(stock, details, weighted_growth, comparison, reasonableness)

        # Collect warnings
        warnings = self._collect_warnings(stock, details, weighted_growth)

        return ImpliedGrowthResult(
            ticker=stock.ticker,
            name=stock.name,
            current_price=stock.current_price,
            details=details,
            weighted_implied_growth=round(weighted_growth, 2),
            comparison=comparison,
            reasonableness=reasonableness,
            analysis=analysis,
            warnings=warnings,
        )

    def _run_all_methods(self, stock: Stock) -> List[ImpliedGrowthDetail]:
        """Run all applicable implied growth methods and return results."""
        results: List[ImpliedGrowthDetail] = []

        # Method 1: Reverse DCF (most robust, always try)
        detail = calculate_reverse_dcf_implied_growth(stock)
        if detail is not None:
            results.append(detail)

        # Method 2: PEG Implied (requires positive PE)
        detail = calculate_peg_implied_growth(stock, fair_peg_ratio=self.peg_fair_ratio)
        if detail is not None:
            results.append(detail)

        # Method 3: Gordon Growth Model (requires positive dividend)
        detail = calculate_gordon_growth_implied_growth(stock)
        if detail is not None:
            results.append(detail)

        # Method 4: Earnings Yield (requires positive PE)
        detail = calculate_earnings_yield_implied_growth(stock)
        if detail is not None:
            results.append(detail)

        return results

    def _calculate_weighted_average(self, details: List[ImpliedGrowthDetail]) -> float:
        """Calculate weighted average implied growth across methods.

        Weights: High confidence = 3, Medium = 2, Low = 1

        Args:
            details: List of ImpliedGrowthDetail from various methods

        Returns:
            Weighted average implied growth rate (percentage)
        """
        if not details:
            return 0.0

        total_weight = 0.0
        weighted_sum = 0.0

        for detail in details:
            weight = _CONFIDENCE_WEIGHTS.get(detail.confidence, 1)
            weighted_sum += detail.implied_growth_rate * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _build_analysis(
        self,
        stock: Stock,
        details: List[ImpliedGrowthDetail],
        weighted_growth: float,
        comparison: GrowthComparison,
        reasonableness: GrowthReasonableness,
    ) -> List[str]:
        """Build human-readable analysis summary."""
        lines = []

        # Overview
        lines.append(
            f"{stock.ticker} ({stock.name}): Current price of {stock.current_price} "
            f"implies {weighted_growth:.1f}% annual growth"
        )

        # Method breakdown
        if details:
            method_strs = [f"{d.method} ({d.confidence}): {d.implied_growth_rate:.1f}%" for d in details]
            lines.append(f"Methods used: {len(details)} - " + "; ".join(method_strs))
        else:
            lines.append("No applicable methods found - insufficient data for analysis")

        # Comparison verdict
        lines.append(f"Growth assessment: {comparison.verdict}")

        # Reasonableness
        lines.append(
            f"Reasonableness: {reasonableness.score:.0f}/100 ({reasonableness.rating})"
        )

        # Interpretation
        if reasonableness.rating in ("Reasonable", "Somewhat Optimistic"):
            lines.append(
                "The market-implied growth rate appears achievable based on "
                "historical performance and company fundamentals"
            )
        elif reasonableness.rating == "Optimistic":
            lines.append(
                "The market-implied growth rate is somewhat optimistic - "
                "requires above-historical execution"
            )
        elif reasonableness.rating == "Very Optimistic":
            lines.append(
                "The market-implied growth rate is very optimistic - "
                "significant outperformance vs history required"
            )
        else:
            lines.append(
                "The market-implied growth rate appears unreasonable based on "
                "historical growth and company capabilities"
            )

        return lines

    def _collect_warnings(
        self,
        stock: Stock,
        details: List[ImpliedGrowthDetail],
        weighted_growth: float,
    ) -> List[str]:
        """Collect warnings about data quality and analysis limitations."""
        warnings = []

        if not details:
            warnings.append("No applicable methods - cannot derive implied growth")
            return warnings

        # Data quality warnings
        if stock.fcf <= 0:
            warnings.append("Negative or zero FCF - Reverse DCF not applicable")

        if stock.pe_ratio <= 0:
            warnings.append("Negative or zero PE - PEG and Earnings Yield methods not applicable")

        if stock.dividend_per_share <= 0:
            warnings.append("No dividend - Gordon Growth Model not applicable")

        # Method count warning
        if len(details) < 2:
            warnings.append(
                "Only 1 method applicable - implied growth estimate has low reliability"
            )

        # High growth warning
        if weighted_growth > 25:
            warnings.append(
                f"Very high implied growth ({weighted_growth:.1f}%) - "
                "verify sustainability assumptions"
            )

        # Method divergence warning
        if len(details) >= 2:
            rates = [d.implied_growth_rate for d in details]
            spread = max(rates) - min(rates)
            if spread > 15:
                warnings.append(
                    f"Large divergence between methods ({min(rates):.1f}% to "
                    f"{max(rates):.1f}%) - results may be unreliable"
                )

        return warnings
