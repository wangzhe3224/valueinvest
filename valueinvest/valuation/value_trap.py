"""
Value Trap Detection Module

Identifies companies that appear cheap but may be in terminal decline.

Based on research from:
- Warren Buffett's "cigar butt" warnings
- Howard Marks' "melting ice cube" concept
- Kevin Daly's value trap framework
- AI disruption risk analysis (2023-2026)

Key detection dimensions:
1. Financial Health - Altman Z-Score based
2. Business Deterioration - Revenue, margin, ROE trends
3. Moat Erosion - Competitive advantage decay
4. AI Vulnerability - Industry disruption risk
5. Dividend Signal - Payout sustainability

Author: ValueInvest Project
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from .base import BaseValuation, ValuationResult, FieldRequirement


class TrapRiskLevel(Enum):
    """Value trap risk levels."""

    LOW = "low"  # Minimal trap risk
    MODERATE = "moderate"  # Some warning signs
    HIGH = "high"  # Significant trap risk
    CRITICAL = "critical"  # Extreme trap risk - avoid


class TrapCategory(Enum):
    """Categories of value trap indicators."""

    FINANCIAL_HEALTH = "financial_health"
    BUSINESS_DETERIORATION = "business_deterioration"
    MOAT_EROSION = "moat_erosion"
    AI_VULNERABILITY = "ai_vulnerability"
    DIVIDEND_SIGNAL = "dividend_signal"


@dataclass
class TrapIndicator:
    """Single value trap indicator."""

    category: TrapCategory
    name: str
    value: float
    risk_score: float  # 0-100, higher = more risky
    description: str
    is_warning: bool = False
    is_critical: bool = False


@dataclass
class ValueTrapResult:
    """Complete value trap detection result."""

    ticker: str
    overall_risk: TrapRiskLevel
    trap_score: float  # 0-100, higher = more risky

    # Category scores
    financial_health_score: float = 0.0
    business_deterioration_score: float = 0.0
    moat_erosion_score: float = 0.0
    ai_vulnerability_score: float = 0.0
    dividend_signal_score: float = 0.0

    # Individual indicators
    indicators: List[TrapIndicator] = field(default_factory=list)

    # Warnings and critical issues
    warnings: List[str] = field(default_factory=list)
    critical_issues: List[str] = field(default_factory=list)

    # Analysis and recommendations
    analysis: List[str] = field(default_factory=list)
    recommendation: str = ""

    @property
    def is_trap(self) -> bool:
        """Check if this is likely a value trap."""
        return self.overall_risk in (TrapRiskLevel.HIGH, TrapRiskLevel.CRITICAL)

    @property
    def should_avoid(self) -> bool:
        """Check if investor should avoid this stock."""
        return self.overall_risk == TrapRiskLevel.CRITICAL


class ValueTrapDetector(BaseValuation):
    """
    Value Trap Detection System.

    Detects companies that appear cheap based on traditional metrics
    but may be in terminal decline due to:
    - Financial distress
    - Business deterioration
    - Competitive moat erosion
    - AI/technology disruption
    - Dividend sustainability issues

    Usage:
        detector = ValueTrapDetector()
        result = detector.detect(stock)

        if result.is_trap:
            print(f"WARNING: {stock.ticker} shows value trap signals!")
            for issue in result.critical_issues:
                print(f"  - {issue}")
    """

    method_name = "Value Trap Detector"

    required_fields = [
        FieldRequirement("current_price", "Current Stock Price", is_critical=True, min_value=0.01),
        FieldRequirement("total_assets", "Total Assets", is_critical=True, min_value=0.01),
        FieldRequirement("net_income", "Net Income", is_critical=False),
        FieldRequirement("revenue", "Revenue", is_critical=False),
        FieldRequirement("roe", "Return on Equity", is_critical=False),
    ]

    best_for = ["Value trap avoidance", "Deep value screening", "Risk assessment"]
    not_for = ["Growth stocks", "Early-stage companies"]

    # AI-vulnerable industries (2024-2026 research)
    AI_VULNERABLE_INDUSTRIES = {
        # High vulnerability
        "education": 0.9,
        "edtech": 0.9,
        "online_education": 0.95,
        "homework_help": 0.95,
        "tutoring": 0.85,
        "content_writing": 0.85,
        "translation": 0.8,
        "customer_service": 0.75,
        "data_entry": 0.8,
        "legal_services": 0.7,
        "accounting": 0.65,
        # Moderate vulnerability
        "software": 0.6,
        "saas": 0.65,
        "consulting": 0.5,
        "advertising": 0.55,
        "market_research": 0.6,
        # Low vulnerability
        "utilities": 0.1,
        "healthcare": 0.2,
        "pharmaceuticals": 0.15,
        "consumer_staples": 0.15,
        "food_beverage": 0.1,
        "infrastructure": 0.1,
        "real_estate": 0.15,
    }

    # Altman Z-Score thresholds
    Z_SAFE = 2.99
    Z_DISTRESS = 1.81

    def __init__(
        self,
        # Historical trend data (optional, for trend analysis)
        revenue_cagr_3y: Optional[float] = None,
        revenue_cagr_5y: Optional[float] = None,
        margin_trend: Optional[str] = None,  # "expanding", "stable", "compressing"
        roe_trend: Optional[str] = None,  # "improving", "stable", "declining"
        market_share_trend: Optional[str] = None,  # "growing", "stable", "declining"
        # Industry context
        industry: Optional[str] = None,
        sector: Optional[str] = None,
        # AI vulnerability override
        ai_vulnerability_override: Optional[float] = None,
        # Thresholds
        low_roe_threshold: float = 8.0,
        high_payout_threshold: float = 80.0,
        negative_income_years: int = 0,
    ):
        """
        Initialize Value Trap Detector.

        Args:
            revenue_cagr_3y: 3-year revenue CAGR (optional)
            revenue_cagr_5y: 5-year revenue CAGR (optional)
            margin_trend: Gross margin trend direction
            roe_trend: ROE trend direction
            market_share_trend: Market share trend direction
            industry: Industry classification
            sector: Sector classification
            ai_vulnerability_override: Manual AI vulnerability score (0-1)
            low_roe_threshold: ROE below this is concerning
            high_payout_threshold: Payout ratio above this is risky
            negative_income_years: Years of negative net income
        """
        self.revenue_cagr_3y = revenue_cagr_3y
        self.revenue_cagr_5y = revenue_cagr_5y
        self.margin_trend = margin_trend
        self.roe_trend = roe_trend
        self.market_share_trend = market_share_trend
        self.industry = industry
        self.sector = sector
        self.ai_vulnerability_override = ai_vulnerability_override
        self.low_roe_threshold = low_roe_threshold
        self.high_payout_threshold = high_payout_threshold
        self.negative_income_years = negative_income_years

    def calculate(self, stock) -> ValuationResult:
        """
        Run value trap detection on a stock.

        Returns a ValuationResult with trap analysis in details.
        """
        result = self.detect(stock)

        # Convert to ValuationResult format
        return ValuationResult(
            method=self.method_name,
            fair_value=stock.current_price,  # This is risk assessment, not valuation
            current_price=stock.current_price,
            premium_discount=0,
            assessment=f"Trap Risk: {result.overall_risk.value.upper()}",
            details={
                "trap_score": result.trap_score,
                "overall_risk": result.overall_risk.value,
                "is_trap": result.is_trap,
                "should_avoid": result.should_avoid,
                "financial_health_score": result.financial_health_score,
                "business_deterioration_score": result.business_deterioration_score,
                "moat_erosion_score": result.moat_erosion_score,
                "ai_vulnerability_score": result.ai_vulnerability_score,
                "dividend_signal_score": result.dividend_signal_score,
                "warnings": result.warnings,
                "critical_issues": result.critical_issues,
            },
            analysis=result.analysis,
            confidence="High" if result.trap_score > 70 or result.trap_score < 30 else "Medium",
            applicability="Applicable",
        )

    def detect(self, stock) -> ValueTrapResult:
        """
        Comprehensive value trap detection.

        Returns detailed ValueTrapResult with all indicators and scores.
        """
        indicators: List[TrapIndicator] = []
        warnings: List[str] = []
        critical_issues: List[str] = []
        analysis: List[str] = []

        # 1. Financial Health Check (Altman Z-Score based)
        financial_score, financial_indicators = self._check_financial_health(stock)
        indicators.extend(financial_indicators)

        # 2. Business Deterioration Check
        biz_score, biz_indicators = self._check_business_deterioration(stock)
        indicators.extend(biz_indicators)

        # 3. Moat Erosion Check
        moat_score, moat_indicators = self._check_moat_erosion(stock)
        indicators.extend(moat_indicators)

        # 4. AI Vulnerability Check
        ai_score, ai_indicators = self._check_ai_vulnerability(stock)
        indicators.extend(ai_indicators)

        # 5. Dividend Signal Check
        div_score, div_indicators = self._check_dividend_signal(stock)
        indicators.extend(div_indicators)

        # Collect warnings and critical issues
        for ind in indicators:
            if ind.is_critical:
                critical_issues.append(f"{ind.name}: {ind.description}")
            elif ind.is_warning:
                warnings.append(f"{ind.name}: {ind.description}")

        # Calculate overall trap score (weighted average)
        weights = {
            "financial": 0.30,
            "business": 0.25,
            "moat": 0.20,
            "ai": 0.15,
            "dividend": 0.10,
        }

        # Adjust weights if no dividend
        if stock.dividend_yield <= 0:
            weights["dividend"] = 0
            weights["financial"] += 0.05
            weights["business"] += 0.05

        trap_score = (
            financial_score * weights["financial"]
            + biz_score * weights["business"]
            + moat_score * weights["moat"]
            + ai_score * weights["ai"]
            + div_score * weights["dividend"]
        )

        # Determine overall risk level
        if trap_score >= 75:
            overall_risk = TrapRiskLevel.CRITICAL
        elif trap_score >= 55:
            overall_risk = TrapRiskLevel.HIGH
        elif trap_score >= 35:
            overall_risk = TrapRiskLevel.MODERATE
        else:
            overall_risk = TrapRiskLevel.LOW

        # Generate analysis
        analysis = self._generate_analysis(
            stock,
            trap_score,
            overall_risk,
            financial_score,
            biz_score,
            moat_score,
            ai_score,
            div_score,
        )

        # Generate recommendation
        recommendation = self._generate_recommendation(overall_risk, critical_issues)

        return ValueTrapResult(
            ticker=stock.ticker,
            overall_risk=overall_risk,
            trap_score=round(trap_score, 1),
            financial_health_score=round(financial_score, 1),
            business_deterioration_score=round(biz_score, 1),
            moat_erosion_score=round(moat_score, 1),
            ai_vulnerability_score=round(ai_score, 1),
            dividend_signal_score=round(div_score, 1),
            indicators=indicators,
            warnings=warnings,
            critical_issues=critical_issues,
            analysis=analysis,
            recommendation=recommendation,
        )

    def _check_financial_health(self, stock) -> tuple:
        """Check financial health using Altman Z-Score components."""
        indicators: List[TrapIndicator] = []
        score = 0.0

        total_assets = stock.total_assets
        if total_assets <= 0:
            return 50.0, [
                TrapIndicator(
                    category=TrapCategory.FINANCIAL_HEALTH,
                    name="Total Assets",
                    value=0,
                    risk_score=50,
                    description="Missing asset data",
                    is_warning=True,
                )
            ]

        total_liabilities = stock.total_liabilities
        if total_liabilities <= 0:
            total_liabilities = total_assets * 0.5  # Estimate

        # X1: Working Capital / Total Assets
        nwc = stock.net_working_capital
        if nwc == 0 and stock.current_assets > 0:
            nwc = stock.current_assets - (total_liabilities * 0.3)
        x1 = nwc / total_assets if total_assets > 0 else 0

        # X2: Retained Earnings / Total Assets
        re = stock.retained_earnings
        if re == 0:
            equity = total_assets - total_liabilities
            re = equity * 0.3  # Estimate
        x2 = re / total_assets if total_assets > 0 else 0

        # X3: EBIT / Total Assets
        ebit = stock.ebit
        if ebit == 0 and stock.operating_margin > 0 and stock.revenue > 0:
            ebit = stock.revenue * (stock.operating_margin / 100)
        elif ebit == 0 and stock.net_income > 0:
            ebit = stock.net_income * 1.3
        x3 = ebit / total_assets if total_assets > 0 else 0

        # X4: Market Cap / Total Liabilities
        x4 = stock.market_cap / total_liabilities if total_liabilities > 0 else 0

        # X5: Revenue / Total Assets
        x5 = stock.revenue / total_assets if total_assets > 0 else 0

        # Calculate Z-Score
        z_score = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5

        # Z-Score indicator
        if z_score < self.Z_DISTRESS:
            z_risk = 95
            z_desc = f"Z-Score {z_score:.2f} in DISTRESS zone (<{self.Z_DISTRESS})"
            is_critical = True
        elif z_score < self.Z_SAFE:
            z_risk = 50
            z_desc = f"Z-Score {z_score:.2f} in GREY zone ({self.Z_DISTRESS}-{self.Z_SAFE})"
            is_critical = False
        else:
            z_risk = 10
            z_desc = f"Z-Score {z_score:.2f} in SAFE zone (>{self.Z_SAFE})"
            is_critical = False

        indicators.append(
            TrapIndicator(
                category=TrapCategory.FINANCIAL_HEALTH,
                name="Altman Z-Score",
                value=z_score,
                risk_score=z_risk,
                description=z_desc,
                is_warning=z_risk >= 50,
                is_critical=is_critical,
            )
        )
        score = z_risk

        # Negative net income check
        if stock.net_income < 0:
            indicators.append(
                TrapIndicator(
                    category=TrapCategory.FINANCIAL_HEALTH,
                    name="Negative Earnings",
                    value=stock.net_income,
                    risk_score=85,
                    description=f"Net income is negative ({stock.net_income/1e9:.2f}B)",
                    is_critical=True,
                )
            )
            score = max(score, 85)
        elif self.negative_income_years > 0:
            indicators.append(
                TrapIndicator(
                    category=TrapCategory.FINANCIAL_HEALTH,
                    name="Earnings History",
                    value=self.negative_income_years,
                    risk_score=60 + self.negative_income_years * 10,
                    description=f"{self.negative_income_years} consecutive years of losses",
                    is_warning=True,
                    is_critical=self.negative_income_years >= 2,
                )
            )

        return score, indicators

    def _check_business_deterioration(self, stock) -> tuple:
        """Check for signs of business deterioration."""
        indicators: List[TrapIndicator] = []
        scores = []

        # Revenue growth check
        if self.revenue_cagr_5y is not None:
            if self.revenue_cagr_5y < -5:
                risk = 90
                desc = f"Revenue CAGR 5Y: {self.revenue_cagr_5y:.1f}% (severe decline)"
                is_critical = True
            elif self.revenue_cagr_5y < 0:
                risk = 70
                desc = f"Revenue CAGR 5Y: {self.revenue_cagr_5y:.1f}% (declining)"
                is_critical = False
            elif self.revenue_cagr_5y < 3:
                risk = 40
                desc = f"Revenue CAGR 5Y: {self.revenue_cagr_5y:.1f}% (stagnant)"
                is_critical = False
            else:
                risk = 10
                desc = f"Revenue CAGR 5Y: {self.revenue_cagr_5y:.1f}% (healthy)"
                is_critical = False

            indicators.append(
                TrapIndicator(
                    category=TrapCategory.BUSINESS_DETERIORATION,
                    name="Revenue Trend (5Y)",
                    value=self.revenue_cagr_5y,
                    risk_score=risk,
                    description=desc,
                    is_warning=risk >= 40,
                    is_critical=is_critical,
                )
            )
            scores.append(risk)
        elif self.revenue_cagr_3y is not None:
            if self.revenue_cagr_3y < -3:
                risk = 80
                desc = f"Revenue CAGR 3Y: {self.revenue_cagr_3y:.1f}% (declining)"
            else:
                risk = 20
                desc = f"Revenue CAGR 3Y: {self.revenue_cagr_3y:.1f}%"

            indicators.append(
                TrapIndicator(
                    category=TrapCategory.BUSINESS_DETERIORATION,
                    name="Revenue Trend (3Y)",
                    value=self.revenue_cagr_3y,
                    risk_score=risk,
                    description=desc,
                    is_warning=risk >= 50,
                )
            )
            scores.append(risk)

        # Margin trend check
        if self.margin_trend:
            if self.margin_trend == "compressing":
                risk = 75
                desc = "Gross margins are compressing"
            elif self.margin_trend == "stable":
                risk = 25
                desc = "Gross margins are stable"
            else:  # expanding
                risk = 10
                desc = "Gross margins are expanding"

            indicators.append(
                TrapIndicator(
                    category=TrapCategory.BUSINESS_DETERIORATION,
                    name="Margin Trend",
                    value=0,
                    risk_score=risk,
                    description=desc,
                    is_warning=risk >= 50,
                    is_critical=risk >= 70,
                )
            )
            scores.append(risk)

        # Operating margin level check
        if stock.operating_margin > 0:
            if stock.operating_margin < 5:
                risk = 70
                desc = f"Low operating margin: {stock.operating_margin:.1f}%"
            elif stock.operating_margin < 10:
                risk = 40
                desc = f"Moderate operating margin: {stock.operating_margin:.1f}%"
            else:
                risk = 15
                desc = f"Healthy operating margin: {stock.operating_margin:.1f}%"

            indicators.append(
                TrapIndicator(
                    category=TrapCategory.BUSINESS_DETERIORATION,
                    name="Operating Margin",
                    value=stock.operating_margin,
                    risk_score=risk,
                    description=desc,
                    is_warning=risk >= 50,
                )
            )
            scores.append(risk)

        # FCF check
        if stock.fcf < 0:
            indicators.append(
                TrapIndicator(
                    category=TrapCategory.BUSINESS_DETERIORATION,
                    name="Free Cash Flow",
                    value=stock.fcf,
                    risk_score=75,
                    description=f"Negative FCF: {stock.fcf/1e9:.2f}B",
                    is_warning=True,
                    is_critical=True,
                )
            )
            scores.append(75)

        # Average score
        avg_score = sum(scores) / len(scores) if scores else 30
        return avg_score, indicators

    def _check_moat_erosion(self, stock) -> tuple:
        """Check for competitive moat erosion."""
        indicators: List[TrapIndicator] = []
        scores = []

        # ROE level check
        if stock.roe > 0:
            if stock.roe < self.low_roe_threshold:
                risk = 70
                desc = f"Low ROE: {stock.roe:.1f}% (below {self.low_roe_threshold}%)"
                is_warning = True
            elif stock.roe < 15:
                risk = 40
                desc = f"Moderate ROE: {stock.roe:.1f}%"
                is_warning = False
            else:
                risk = 15
                desc = f"Strong ROE: {stock.roe:.1f}%"
                is_warning = False

            indicators.append(
                TrapIndicator(
                    category=TrapCategory.MOAT_EROSION,
                    name="ROE Level",
                    value=stock.roe,
                    risk_score=risk,
                    description=desc,
                    is_warning=is_warning,
                )
            )
            scores.append(risk)

        # ROE trend check
        if self.roe_trend:
            if self.roe_trend == "declining":
                risk = 80
                desc = "ROE is declining over time"
                is_critical = True
            elif self.roe_trend == "stable":
                risk = 30
                desc = "ROE is stable"
                is_critical = False
            else:
                risk = 10
                desc = "ROE is improving"
                is_critical = False

            indicators.append(
                TrapIndicator(
                    category=TrapCategory.MOAT_EROSION,
                    name="ROE Trend",
                    value=0,
                    risk_score=risk,
                    description=desc,
                    is_warning=risk >= 50,
                    is_critical=is_critical,
                )
            )
            scores.append(risk)

        # Market share trend
        if self.market_share_trend:
            if self.market_share_trend == "declining":
                risk = 85
                desc = "Market share is declining"
            elif self.market_share_trend == "stable":
                risk = 30
                desc = "Market share is stable"
            else:
                risk = 10
                desc = "Market share is growing"

            indicators.append(
                TrapIndicator(
                    category=TrapCategory.MOAT_EROSION,
                    name="Market Share",
                    value=0,
                    risk_score=risk,
                    description=desc,
                    is_warning=risk >= 50,
                    is_critical=risk >= 80,
                )
            )
            scores.append(risk)

        # P/E vs growth check (PEG-like)
        if stock.pe_ratio > 0 and stock.growth_rate > 0:
            peg = stock.pe_ratio / stock.growth_rate
            if peg > 2.0 and stock.pe_ratio < 15:
                # Low P/E but high PEG suggests value trap
                risk = 65
                desc = f"Low P/E ({stock.pe_ratio:.1f}) but PEG {peg:.1f} suggests deteriorating fundamentals"
                indicators.append(
                    TrapIndicator(
                        category=TrapCategory.MOAT_EROSION,
                        name="P/E vs Growth",
                        value=peg,
                        risk_score=risk,
                        description=desc,
                        is_warning=True,
                    )
                )
                scores.append(risk)

        avg_score = sum(scores) / len(scores) if scores else 25
        return avg_score, indicators

    def _check_ai_vulnerability(self, stock) -> tuple:
        """Check vulnerability to AI disruption."""
        indicators: List[TrapIndicator] = []

        # Use override if provided
        if self.ai_vulnerability_override is not None:
            ai_score = self.ai_vulnerability_override * 100
            indicators.append(
                TrapIndicator(
                    category=TrapCategory.AI_VULNERABILITY,
                    name="AI Vulnerability (Manual)",
                    value=self.ai_vulnerability_override,
                    risk_score=ai_score,
                    description=f"Manual AI vulnerability assessment: {self.ai_vulnerability_override:.0%}",
                    is_warning=ai_score >= 60,
                    is_critical=ai_score >= 80,
                )
            )
            return ai_score, indicators

        # Determine industry
        industry = self.industry
        if not industry and hasattr(stock, "sectors") and stock.sectors:
            industry = stock.sectors[0] if stock.sectors else None
        if not industry:
            industry = self.sector

        if not industry:
            # No industry info - moderate uncertainty
            indicators.append(
                TrapIndicator(
                    category=TrapCategory.AI_VULNERABILITY,
                    name="AI Vulnerability",
                    value=0,
                    risk_score=30,
                    description="Industry classification not available - unable to assess AI risk",
                    is_warning=False,
                )
            )
            return 30, indicators

        # Normalize industry name
        industry_lower = industry.lower().replace(" ", "_").replace("-", "_")

        # Find matching industry
        ai_vuln = 0.3  # Default moderate
        matched_industry = None

        for ind_pattern, vuln in self.AI_VULNERABLE_INDUSTRIES.items():
            if ind_pattern in industry_lower or industry_lower in ind_pattern:
                ai_vuln = vuln
                matched_industry = ind_pattern
                break

        ai_score = ai_vuln * 100

        # Determine description
        if ai_score >= 80:
            desc = f"Industry '{industry}' is HIGHLY vulnerable to AI disruption"
            is_critical = True
        elif ai_score >= 60:
            desc = f"Industry '{industry}' has significant AI disruption risk"
            is_critical = False
        elif ai_score >= 40:
            desc = f"Industry '{industry}' has moderate AI exposure"
            is_critical = False
        else:
            desc = f"Industry '{industry}' has low AI disruption risk"
            is_critical = False

        indicators.append(
            TrapIndicator(
                category=TrapCategory.AI_VULNERABILITY,
                name="AI Disruption Risk",
                value=ai_vuln,
                risk_score=ai_score,
                description=desc,
                is_warning=ai_score >= 50,
                is_critical=is_critical,
            )
        )

        return ai_score, indicators

    def _check_dividend_signal(self, stock) -> tuple:
        """Check dividend sustainability signals."""
        indicators: List[TrapIndicator] = []

        # No dividend - neutral for this check
        if stock.dividend_yield <= 0:
            indicators.append(
                TrapIndicator(
                    category=TrapCategory.DIVIDEND_SIGNAL,
                    name="Dividend Status",
                    value=0,
                    risk_score=0,
                    description="No dividend - not applicable for dividend trap analysis",
                )
            )
            return 0, indicators

        scores = []

        # Payout ratio check
        payout = stock.payout_ratio
        if payout > 100:
            risk = 90
            desc = f"Payout ratio {payout:.0f}% exceeds 100% - dividend at risk"
            is_critical = True
        elif payout > self.high_payout_threshold:
            risk = 70
            desc = f"High payout ratio: {payout:.0f}% (above {self.high_payout_threshold}%)"
            is_critical = False
        elif payout > 60:
            risk = 40
            desc = f"Moderate payout ratio: {payout:.0f}%"
            is_critical = False
        else:
            risk = 15
            desc = f"Healthy payout ratio: {payout:.0f}%"
            is_critical = False

        indicators.append(
            TrapIndicator(
                category=TrapCategory.DIVIDEND_SIGNAL,
                name="Payout Ratio",
                value=payout,
                risk_score=risk,
                description=desc,
                is_warning=risk >= 50,
                is_critical=is_critical,
            )
        )
        scores.append(risk)

        # FCF coverage check
        if stock.fcf > 0 and stock.dividend_per_share > 0:
            total_dividend = stock.dividend_per_share * stock.shares_outstanding
            fcf_coverage = stock.fcf / total_dividend if total_dividend > 0 else 0

            if fcf_coverage < 1.0:
                risk = 85
                desc = f"FCF cannot cover dividend (coverage: {fcf_coverage:.1f}x)"
                is_critical = True
            elif fcf_coverage < 1.5:
                risk = 50
                desc = f"Low FCF coverage: {fcf_coverage:.1f}x"
                is_critical = False
            else:
                risk = 15
                desc = f"Healthy FCF coverage: {fcf_coverage:.1f}x"
                is_critical = False

            indicators.append(
                TrapIndicator(
                    category=TrapCategory.DIVIDEND_SIGNAL,
                    name="FCF Coverage",
                    value=fcf_coverage,
                    risk_score=risk,
                    description=desc,
                    is_warning=risk >= 50,
                    is_critical=is_critical,
                )
            )
            scores.append(risk)

        # Dividend growth trend
        if stock.dividend_growth_rate < 0:
            risk = 80
            desc = f"Dividend cut or frozen (growth: {stock.dividend_growth_rate:.1f}%)"
            is_critical = True
        elif stock.dividend_growth_rate < 2:
            risk = 45
            desc = f"Dividend growth stagnating: {stock.dividend_growth_rate:.1f}%"
            is_critical = False
        else:
            risk = 15
            desc = f"Dividend growing: {stock.dividend_growth_rate:.1f}%"
            is_critical = False

        indicators.append(
            TrapIndicator(
                category=TrapCategory.DIVIDEND_SIGNAL,
                name="Dividend Growth",
                value=stock.dividend_growth_rate,
                risk_score=risk,
                description=desc,
                is_warning=risk >= 40,
                is_critical=is_critical,
            )
        )
        scores.append(risk)

        avg_score = sum(scores) / len(scores) if scores else 0
        return avg_score, indicators

    def _generate_analysis(
        self,
        stock,
        trap_score: float,
        overall_risk: TrapRiskLevel,
        financial_score: float,
        biz_score: float,
        moat_score: float,
        ai_score: float,
        div_score: float,
    ) -> List[str]:
        """Generate analysis text."""
        analysis = []

        # Overall assessment
        analysis.append(f"=== Value Trap Analysis: {stock.ticker} ===")
        analysis.append(f"Overall Trap Score: {trap_score:.0f}/100 ({overall_risk.value.upper()})")
        analysis.append("")

        # Category breakdown
        analysis.append("Risk by Category:")
        analysis.append(f"  Financial Health:    {financial_score:.0f}/100")
        analysis.append(f"  Business Deterioration: {biz_score:.0f}/100")
        analysis.append(f"  Moat Erosion:        {moat_score:.0f}/100")
        analysis.append(f"  AI Vulnerability:    {ai_score:.0f}/100")
        if stock.dividend_yield > 0:
            analysis.append(f"  Dividend Signal:     {div_score:.0f}/100")
        analysis.append("")

        # Interpretation
        if trap_score >= 75:
            analysis.append("CRITICAL: This stock shows multiple severe value trap indicators.")
            analysis.append("Recommendation: AVOID - High probability of permanent capital loss.")
        elif trap_score >= 55:
            analysis.append("WARNING: Significant value trap risk detected.")
            analysis.append("Recommendation: Deep due diligence required before investing.")
        elif trap_score >= 35:
            analysis.append("CAUTION: Some value trap indicators present.")
            analysis.append("Recommendation: Monitor closely and verify business fundamentals.")
        else:
            analysis.append("LOW RISK: No significant value trap indicators detected.")
            analysis.append("Recommendation: Standard valuation analysis appropriate.")

        return analysis

    def _generate_recommendation(self, risk: TrapRiskLevel, critical_issues: List[str]) -> str:
        """Generate investment recommendation."""
        if risk == TrapRiskLevel.CRITICAL:
            return "AVOID - Multiple critical risk factors. This appears to be a value trap."
        elif risk == TrapRiskLevel.HIGH:
            return "HIGH RISK - Significant concerns. Only invest with deep understanding of turnaround potential."
        elif risk == TrapRiskLevel.MODERATE:
            return "CAUTION - Some warning signs. Investigate thoroughly before investing."
        else:
            return "LOW RISK - No major value trap indicators. Proceed with standard due diligence."


def detect_value_trap(
    stock,
    revenue_cagr_5y: Optional[float] = None,
    margin_trend: Optional[str] = None,
    roe_trend: Optional[str] = None,
    industry: Optional[str] = None,
) -> ValueTrapResult:
    """
    Convenience function for quick value trap detection.

    Args:
        stock: Stock object to analyze
        revenue_cagr_5y: 5-year revenue CAGR (optional)
        margin_trend: "expanding", "stable", or "compressing"
        roe_trend: "improving", "stable", or "declining"
        industry: Industry classification for AI risk

    Returns:
        ValueTrapResult with detailed analysis

    Example:
        result = detect_value_trap(
            stock,
            revenue_cagr_5y=-3.2,  # Declining revenue
            margin_trend="compressing",
            industry="education"
        )

        if result.is_trap:
            print("WARNING: Value trap detected!")
    """
    detector = ValueTrapDetector(
        revenue_cagr_5y=revenue_cagr_5y,
        margin_trend=margin_trend,
        roe_trend=roe_trend,
        industry=industry,
    )
    return detector.detect(stock)
