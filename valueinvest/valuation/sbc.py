"""
SBC (Stock-Based Compensation) Analysis Module

Analyzes the impact of SBC on true profitability and shareholder returns:
- SBC as % of revenue vs industry benchmarks
- SBC dilution impact on FCF
- Whether buybacks effectively offset dilution
- True shareholder yield

Usage:
    from valueinvest.valuation.sbc import SBCAnalysis
    
    analyzer = SBCAnalysis(company_stage="mature", industry="saas")
    result = analyzer.calculate(stock)
    
    print(f"SBC Margin: {result.details['sbc_margin']:.1f}%")
    print(f"True FCF: ${result.details['true_fcf']/1e9:.2f}B")
    print(f"Risk Level: {result.details['risk_level']}")
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from .base import BaseValuation, ValuationResult, FieldRequirement


@dataclass
class SBCBenchmark:
    """Industry SBC benchmarks"""

    # By company stage
    EARLY_STAGE_MAX = 25.0  # Early-stage: SBC/Revenue < 25%
    GROWTH_STAGE_MAX = 20.0  # Growth-stage: SBC/Revenue < 20%
    MATURE_STAGE_MAX = 15.0  # Mature: SBC/Revenue < 15%

    # By industry
    SAAS_AVERAGE = 12.0  # SaaS industry average
    ENTERPRISE_SOFTWARE = 10.0  # Enterprise software
    CONSUMER_SOFTWARE = 15.0  # Consumer software
    HARDWARE = 5.0  # Hardware
    FINTECH = 18.0  # Fintech
    BIOTECH = 25.0  # Biotech (high SBC)


class SBCAnalysis(BaseValuation):
    """
    SBC Deep Analysis

    Core questions:
    1. Is SBC as % of revenue healthy?
    2. What is SBC's real impact on FCF?
    3. Do buybacks effectively offset dilution?
    4. What is the true shareholder return?

    Example output:
    ```
    === SBC Analysis ===

    SBC: $4.83B (20.3% of revenue)
    Industry benchmark: 12.0% - Above average

    === FCF Impact ===
    Reported FCF: $7.87B
    SBC-Adjusted FCF: $6.04B (23.0% reduction)

    === Dilution ===
    Annual dilution rate: 2.50%
    Reported buyback yield: 10.42%
    True buyback yield (net): 7.92%

    === Shareholder Yield ===
    Dividend yield: 0.00%
    True shareholder yield: 7.92%

    Assessment: Elevated SBC Risk
    Risk Level: Medium-High
    ```
    """

    method_name = "SBC Analysis"

    required_fields = [
        FieldRequirement("revenue", "Revenue", is_critical=True, min_value=0.01),
        FieldRequirement("fcf", "Free Cash Flow", is_critical=True),
        FieldRequirement("sbc", "Stock-Based Compensation", is_critical=False),
        FieldRequirement("shares_outstanding", "Shares Outstanding", is_critical=True),
        FieldRequirement("current_price", "Current Stock Price", is_critical=True),
    ]

    best_for = ["SaaS companies", "High-growth tech", "Buyback analysis", "Shareholder yield"]
    not_for = ["No SBC data", "Non-tech traditional companies"]

    def __init__(
        self,
        company_stage: str = "mature",  # early, growth, mature
        industry: str = "saas",  # saas, enterprise, consumer, hardware, fintech, biotech
        peer_sbc_avg: Optional[float] = None,
    ):
        """
        Initialize SBC Analysis.

        Args:
            company_stage: Company stage - "early", "growth", or "mature"
            industry: Industry type - "saas", "enterprise", "consumer", "hardware", "fintech", "biotech"
            peer_sbc_avg: Optional peer average SBC % for comparison
        """
        self.company_stage = company_stage
        self.industry = industry
        self.peer_sbc_avg = peer_sbc_avg

    def calculate(self, stock) -> ValuationResult:
        """Execute SBC analysis"""
        is_valid, missing, warnings = self.validate_data(stock)

        # If no SBC data, estimate
        sbc = stock.sbc if stock.sbc > 0 else self._estimate_sbc(stock, warnings)

        # Core metrics calculation
        metrics = self._calculate_metrics(stock, sbc)

        # Benchmark comparison
        benchmark = self._compare_to_benchmark(metrics)

        # Generate analysis
        analysis = self._generate_analysis(metrics, benchmark, warnings)

        # Assessment
        assessment, risk_level = self._assess_sbc_health(metrics, benchmark)

        return ValuationResult(
            method=self.method_name,
            fair_value=stock.current_price,  # SBC is a quality metric, not valuation
            current_price=stock.current_price,
            premium_discount=0,
            assessment=assessment,
            details={
                "sbc": sbc,
                "sbc_margin": round(metrics["sbc_margin"], 2),
                "sbc_as_pct_of_fcf": round(metrics["sbc_as_pct_of_fcf"], 2),
                "reported_fcf": stock.fcf,
                "true_fcf": round(metrics["true_fcf"], 0),
                "true_fcf_margin": round(metrics["true_fcf_margin"], 2),
                "fcf_impact_pct": round(metrics["fcf_impact_pct"], 1),
                "dilution_rate": round(metrics["dilution_rate"], 2),
                "reported_buyback_yield": round(metrics["reported_buyback_yield"], 2),
                "true_buyback_yield": round(metrics["true_buyback_yield"], 2),
                "shareholder_yield": round(metrics["shareholder_yield"], 2),
                "risk_level": risk_level,
                "benchmark": benchmark,
                "company_stage": self.company_stage,
                "industry": self.industry,
            },
            components={
                "sbc_margin": round(metrics["sbc_margin"], 2),
                "fcf_impact_pct": round(metrics["fcf_impact_pct"], 1),
                "dilution_rate": round(metrics["dilution_rate"], 2),
                "true_buyback_yield": round(metrics["true_buyback_yield"], 2),
            },
            analysis=analysis,
            confidence="High" if stock.sbc > 0 else "Medium",
            applicability="Applicable" if sbc > 0 else "Limited",
        )

    def _estimate_sbc(self, stock, warnings: List[str]) -> float:
        """Estimate SBC if no data available"""
        industry_rates = {
            "saas": 0.12,
            "enterprise": 0.10,
            "consumer": 0.15,
            "hardware": 0.05,
            "fintech": 0.18,
            "biotech": 0.25,
        }
        rate = industry_rates.get(self.industry, 0.08)
        estimated = stock.revenue * rate
        warnings.append(f"SBC estimated at {rate*100:.0f}% of revenue based on industry average")
        return estimated

    def _calculate_metrics(self, stock, sbc: float) -> Dict[str, float]:
        """Calculate all SBC-related metrics"""
        revenue = stock.revenue
        fcf = stock.fcf
        shares = stock.shares_outstanding
        price = stock.current_price
        market_cap = stock.market_cap

        # SBC margins
        sbc_margin = (sbc / revenue * 100) if revenue > 0 else 0
        sbc_as_pct_of_fcf = (sbc / fcf * 100) if fcf > 0 else 0

        # True FCF
        true_fcf = fcf - sbc
        true_fcf_margin = (true_fcf / revenue * 100) if revenue > 0 else 0
        fcf_impact_pct = (sbc / fcf * 100) if fcf > 0 else 0

        # Dilution
        shares_issued = stock.shares_issued if stock.shares_issued > 0 else 0
        shares_repurchased = stock.shares_repurchased if stock.shares_repurchased > 0 else 0
        dilution_rate = (shares_issued / shares * 100) if shares > 0 else 0

        # Buyback yields
        reported_buyback_yield = (
            (shares_repurchased * price / market_cap * 100)
            if market_cap > 0 and shares_repurchased > 0
            else 0
        )
        net_reduction = shares_repurchased - shares_issued
        true_buyback_yield = (net_reduction * price / market_cap * 100) if market_cap > 0 else 0

        # Shareholder yield
        shareholder_yield = stock.dividend_yield + true_buyback_yield

        return {
            "sbc": sbc,
            "sbc_margin": sbc_margin,
            "sbc_as_pct_of_fcf": sbc_as_pct_of_fcf,
            "true_fcf": true_fcf,
            "true_fcf_margin": true_fcf_margin,
            "fcf_impact_pct": fcf_impact_pct,
            "shares_issued": shares_issued,
            "shares_repurchased": shares_repurchased,
            "dilution_rate": dilution_rate,
            "reported_buyback_yield": reported_buyback_yield,
            "true_buyback_yield": true_buyback_yield,
            "shareholder_yield": shareholder_yield,
        }

    def _compare_to_benchmark(self, metrics: Dict) -> Dict[str, Any]:
        """Compare to industry benchmarks"""
        sbc_margin = metrics["sbc_margin"]

        # Get stage threshold
        stage_thresholds = {
            "early": SBCBenchmark.EARLY_STAGE_MAX,
            "growth": SBCBenchmark.GROWTH_STAGE_MAX,
            "mature": SBCBenchmark.MATURE_STAGE_MAX,
        }
        stage_max = stage_thresholds.get(self.company_stage, 15.0)

        # Get industry average
        industry_avgs = {
            "saas": SBCBenchmark.SAAS_AVERAGE,
            "enterprise": SBCBenchmark.ENTERPRISE_SOFTWARE,
            "consumer": SBCBenchmark.CONSUMER_SOFTWARE,
            "hardware": SBCBenchmark.HARDWARE,
            "fintech": SBCBenchmark.FINTECH,
            "biotech": SBCBenchmark.BIOTECH,
        }
        industry_avg = industry_avgs.get(self.industry, 10.0)

        # Use peer average if provided
        if self.peer_sbc_avg is not None:
            industry_avg = self.peer_sbc_avg

        # Determine level
        if sbc_margin <= stage_max * 0.5:
            level = "Excellent"
        elif sbc_margin <= stage_max:
            level = "Good"
        elif sbc_margin <= stage_max * 1.5:
            level = "Elevated"
        else:
            level = "High Risk"

        return {
            "sbc_margin": sbc_margin,
            "stage_max": stage_max,
            "industry_avg": industry_avg,
            "vs_stage": "Within" if sbc_margin <= stage_max else "Exceeds",
            "vs_industry": "Below" if sbc_margin < industry_avg else "Above",
            "level": level,
        }

    def _assess_sbc_health(self, metrics: Dict, benchmark: Dict) -> tuple:
        """Assess SBC health level"""
        sbc_level = benchmark["level"]
        true_yield = metrics["true_buyback_yield"]
        fcf_impact = metrics["fcf_impact_pct"]

        if sbc_level == "Excellent" and true_yield > 0:
            return "Low SBC Risk - Excellent", "Low"
        elif sbc_level == "Good" and fcf_impact < 30:
            return "Moderate SBC Risk - Good", "Medium"
        elif sbc_level == "Elevated" or fcf_impact > 30:
            if true_yield < 0:
                return "High SBC Risk - Net Dilution", "High"
            return "Elevated SBC Risk", "Medium-High"
        else:
            return "High SBC Risk", "High"

    def _generate_analysis(self, metrics: Dict, benchmark: Dict, warnings: List[str]) -> List[str]:
        """Generate analysis text"""
        lines = []

        # SBC Overview
        lines.append(f"SBC: ${metrics['sbc']/1e9:.2f}B ({metrics['sbc_margin']:.1f}% of revenue)")
        lines.append(
            f"Stage benchmark ({self.company_stage}): {benchmark['stage_max']:.1f}% - {benchmark['vs_stage']}"
        )
        lines.append(
            f"Industry avg ({self.industry}): {benchmark['industry_avg']:.1f}% - {benchmark['vs_industry']} average"
        )

        # FCF Impact
        lines.append("")
        lines.append("=== FCF Impact ===")
        lines.append(f"Reported FCF: ${metrics['true_fcf']/1e9 + metrics['sbc']/1e9:.2f}B")
        lines.append(
            f"SBC-Adjusted FCF: ${metrics['true_fcf']/1e9:.2f}B ({metrics['fcf_impact_pct']:.1f}% reduction)"
        )

        if metrics["fcf_impact_pct"] > 30:
            lines.append("⚠️ SBC reduces FCF by >30% - significant impact")

        # Dilution
        lines.append("")
        lines.append("=== Dilution ===")
        lines.append(f"Annual dilution rate: {metrics['dilution_rate']:.2f}%")
        lines.append(f"Reported buyback yield: {metrics['reported_buyback_yield']:.2f}%")
        lines.append(f"True buyback yield (net): {metrics['true_buyback_yield']:.2f}%")

        if metrics["dilution_rate"] > 3:
            lines.append("⚠️ Annual dilution >3% - high equity issuance")

        # Shareholder Yield
        lines.append("")
        lines.append("=== Shareholder Yield ===")
        lines.append(f"Dividend yield: {0:.2f}%")  # Would need dividend_yield
        lines.append(f"True shareholder yield: {metrics['shareholder_yield']:.2f}%")

        # Warnings
        if metrics["sbc_margin"] > 20:
            lines.append("")
            lines.append("⚠️ WARNING: SBC exceeds 20% of revenue - high dilution risk")

        if metrics["true_buyback_yield"] < 0:
            lines.append("")
            lines.append("⚠️ WARNING: Net dilution - buybacks not offsetting SBC")

        if metrics["true_fcf"] < 0:
            lines.append("")
            lines.append("⚠️ WARNING: SBC-adjusted FCF is negative")

        if warnings:
            lines.append("")
            lines.extend([f"Note: {w}" for w in warnings])

        return lines


# Convenience function
def analyze_sbc(
    stock,
    company_stage: str = "mature",
    industry: str = "saas",
    peer_sbc_avg: Optional[float] = None,
) -> ValuationResult:
    """
    Quick SBC analysis function.

    Args:
        stock: Stock object
        company_stage: "early", "growth", or "mature"
        industry: "saas", "enterprise", "consumer", "hardware", "fintech", "biotech"
        peer_sbc_avg: Optional peer average SBC % for comparison

    Returns:
        ValuationResult with SBC analysis
    """
    analyzer = SBCAnalysis(
        company_stage=company_stage,
        industry=industry,
        peer_sbc_avg=peer_sbc_avg,
    )
    return analyzer.calculate(stock)
