"""
Quality and Risk Assessment Valuation Methods

Includes:
- Owner Earnings: Warren Buffett's method for calculating true distributable earnings
- Altman Z-Score: Bankruptcy prediction model
"""
from typing import Optional
from .base import BaseValuation, ValuationResult, ValuationRange, FieldRequirement


class OwnerEarnings(BaseValuation):
    """
    Warren Buffett's Owner Earnings calculation.

    Owner Earnings = Net Income + Depreciation & Amortization - CapEx - Change in Working Capital

    This represents the true cash available to shareholders after maintaining
    the competitive position of the business.

    From Buffett's 1986 shareholder letter:
    "Owner earnings... represent(a) reported earnings plus (b) depreciation,
    depletion, amortization, and certain other non-cash charges... less (c) the
    average annual amount of capitalized expenditures for plant and equipment, etc."
    """

    method_name = "Owner Earnings"

    required_fields = [
        FieldRequirement("net_income", "Net Income", is_critical=True),
        FieldRequirement("depreciation", "Depreciation & Amortization", is_critical=False),
        FieldRequirement("capex", "Capital Expenditure", is_critical=False),
        FieldRequirement("net_working_capital", "Net Working Capital", is_critical=False),
        FieldRequirement(
            "shares_outstanding", "Shares Outstanding", is_critical=True, min_value=0.01
        ),
        FieldRequirement("current_price", "Current Stock Price", is_critical=True, min_value=0.01),
        FieldRequirement("cost_of_capital", "Cost of Capital", is_critical=True),
    ]

    best_for = ["Cash flow quality assessment", "Value investing", "Mature companies"]
    not_for = ["High-growth companies with large working capital changes", "Early-stage companies"]

    # Default assumptions when data is missing
    DEFAULT_DEPRECIATION_PCT = 0.05  # 5% of revenue
    DEFAULT_CAPEX_PCT = 0.07  # 7% of revenue (maintenance capex)
    DEFAULT_NWC_CHANGE_PCT = 0.01  # 1% of revenue (assumed stable)

    def __init__(
        self,
        maintenance_capex_pct: Optional[float] = None,
        cost_of_capital: Optional[float] = None,
    ):
        self.maintenance_capex_pct = maintenance_capex_pct
        self.cost_of_capital = cost_of_capital

    def calculate(self, stock) -> ValuationResult:
        is_valid, missing, warnings = self.validate_data(stock)
        if not is_valid:
            return self._create_error_result(
                stock, f"Missing required data: {', '.join(missing)}", missing
            )

        net_income = stock.net_income
        depreciation = stock.depreciation
        capex = stock.capex
        nwc = stock.net_working_capital
        shares = stock.shares_outstanding

        # Use revenue-based estimates if exact values missing
        revenue = stock.revenue if stock.revenue > 0 else net_income * 10  # Fallback estimate

        if depreciation == 0:
            depreciation = revenue * self.DEFAULT_DEPRECIATION_PCT
            warnings.append(
                f"Depreciation estimated at {self.DEFAULT_DEPRECIATION_PCT*100:.0f}% of revenue"
            )

        # For Owner Earnings, we use maintenance capex, not total capex
        # Maintenance capex is typically 60-80% of total capex
        if capex == 0:
            maintenance_capex = revenue * (self.maintenance_capex_pct or self.DEFAULT_CAPEX_PCT)
            warnings.append(
                f"Maintenance CapEx estimated at {(self.maintenance_capex_pct or self.DEFAULT_CAPEX_PCT)*100:.0f}% of revenue"
            )
        else:
            # Assume 70% of capex is maintenance (conservative)
            maintenance_capex = abs(capex) * (self.maintenance_capex_pct or 0.7)

        # Change in working capital - simplified: assume 1% of revenue if not available
        # In practice, you'd need historical NWC to calculate actual change
        if nwc != 0:
            # Use a portion of NWC as proxy for change (conservative estimate)
            nwc_change = abs(nwc) * 0.1  # Assume 10% change
            warnings.append("Using 10% of NWC as proxy for change in working capital")
        else:
            nwc_change = revenue * self.DEFAULT_NWC_CHANGE_PCT

        # Calculate Owner Earnings
        owner_earnings = net_income + depreciation - maintenance_capex - nwc_change

        if owner_earnings <= 0:
            return self._create_error_result(
                stock,
                f"Owner Earnings is negative ({owner_earnings/1e9:.2f}B) - company may be value destructive",
                [],
            )

        owner_earnings_per_share = owner_earnings / shares

        # Valuation using Owner Earnings yield
        cost_of_capital = (
            self.cost_of_capital if self.cost_of_capital is not None else stock.cost_of_capital
        ) / 100

        # Intrinsic value = Owner Earnings / Cost of Capital (zero growth assumption)
        intrinsic_value_zero_growth = owner_earnings_per_share / cost_of_capital

        # With growth (using stock's growth rate)
        growth_rate = stock.growth_rate / 100 if stock.growth_rate else 0
        if cost_of_capital > growth_rate:
            intrinsic_value_with_growth = (
                owner_earnings_per_share * (1 + growth_rate) / (cost_of_capital - growth_rate)
            )
        else:
            intrinsic_value_with_growth = intrinsic_value_zero_growth * 1.5  # Cap at 50% premium

        # Use average of both for fair value
        fair_value = (intrinsic_value_zero_growth + intrinsic_value_with_growth) / 2

        premium_discount = ((fair_value - stock.current_price) / stock.current_price) * 100

        # Compare Owner Earnings to Reported Net Income
        earnings_quality = owner_earnings / net_income if net_income != 0 else 0

        # Calculate implied P/E based on Owner Earnings
        implied_pe = (
            stock.current_price / owner_earnings_per_share if owner_earnings_per_share > 0 else 0
        )

        # Sensitivity range
        value_low = (owner_earnings_per_share * 0.9) / (cost_of_capital + 0.02)
        value_high = (owner_earnings_per_share * 1.1) / max(0.01, cost_of_capital - 0.02)

        analysis = [
            f"Owner Earnings: {owner_earnings/1e9:.2f}B (vs Net Income: {net_income/1e9:.2f}B)",
            f"Owner Earnings/Share: {owner_earnings_per_share:.2f}",
            f"Earnings Quality: {earnings_quality:.1%} ({'Accrual-heavy' if earnings_quality < 0.8 else 'Cash-rich' if earnings_quality > 1.2 else 'Normal'})",
            f"Implied P/E (Owner Earnings): {implied_pe:.1f}x (vs Reported P/E: {stock.pe_ratio:.1f}x)",
            f"Zero-growth value: {intrinsic_value_zero_growth:.2f}",
            f"With {growth_rate*100:.1f}% growth: {intrinsic_value_with_growth:.2f}",
        ]

        if earnings_quality < 0.7:
            analysis.append(
                "Warning: Low earnings quality - reported earnings may not reflect cash reality"
            )
        elif earnings_quality > 1.3:
            analysis.append("Note: High earnings quality - strong cash conversion")

        if warnings:
            analysis.extend([f"Note: {w}" for w in warnings])

        confidence = (
            "High"
            if earnings_quality > 0.8 and len(warnings) == 0
            else ("Medium" if earnings_quality > 0.6 else "Low")
        )

        return ValuationResult(
            method=self.method_name,
            fair_value=round(fair_value, 2),
            current_price=stock.current_price,
            premium_discount=round(premium_discount, 1),
            assessment=self._assess(fair_value, stock.current_price),
            details={
                "owner_earnings": owner_earnings,
                "owner_earnings_per_share": round(owner_earnings_per_share, 2),
                "earnings_quality": round(earnings_quality, 3),
                "implied_pe": round(implied_pe, 1),
                "zero_growth_value": round(intrinsic_value_zero_growth, 2),
                "growth_value": round(intrinsic_value_with_growth, 2),
                "depreciation_used": depreciation,
                "maintenance_capex": maintenance_capex,
                "nwc_change": nwc_change,
            },
            components={
                "net_income": net_income,
                "depreciation": depreciation,
                "maintenance_capex": maintenance_capex,
                "nwc_change": nwc_change,
            },
            analysis=analysis,
            confidence=confidence,
            fair_value_range=ValuationRange(
                low=round(value_low, 2), base=round(fair_value, 2), high=round(value_high, 2)
            ),
            applicability="Applicable" if owner_earnings > 0 else "Limited",
        )


class AltmanZScore(BaseValuation):
    """
    Altman Z-Score for bankruptcy prediction.

    Original formula for public manufacturing companies:
    Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5

    Where:
    X1 = Working Capital / Total Assets
    X2 = Retained Earnings / Total Assets
    X3 = EBIT / Total Assets
    X4 = Market Cap / Total Liabilities
    X5 = Revenue / Total Assets

    Interpretation:
    Z > 2.99: Safe Zone
    1.81 < Z < 2.99: Grey Zone (caution)
    Z < 1.81: Distress Zone (high bankruptcy risk)
    """

    method_name = "Altman Z-Score"

    required_fields = [
        FieldRequirement("current_assets", "Current Assets", is_critical=False),
        FieldRequirement("total_assets", "Total Assets", is_critical=True, min_value=0.01),
        FieldRequirement("total_liabilities", "Total Liabilities", is_critical=True),
        FieldRequirement("retained_earnings", "Retained Earnings", is_critical=False),
        FieldRequirement("ebit", "EBIT", is_critical=False),
        FieldRequirement("revenue", "Revenue", is_critical=False),
        FieldRequirement("current_price", "Current Stock Price", is_critical=True, min_value=0.01),
        FieldRequirement(
            "shares_outstanding", "Shares Outstanding", is_critical=True, min_value=0.01
        ),
    ]

    best_for = ["Bankruptcy risk assessment", "Credit analysis", "Value trap avoidance"]
    not_for = [
        "Banks and financials",
        "Private companies",
        "Non-manufacturing (use modified Z-score)",
    ]

    # Zone thresholds
    SAFE_ZONE = 2.99
    DISTRESS_ZONE = 1.81

    def __init__(self, zone_safe: float = 2.99, zone_distress: float = 1.81):
        self.zone_safe = zone_safe
        self.zone_distress = zone_distress

    def calculate(self, stock) -> ValuationResult:
        is_valid, missing, warnings = self.validate_data(stock)
        if not is_valid:
            return self._create_error_result(
                stock, f"Missing required data: {', '.join(missing)}", missing
            )

        total_assets = stock.total_assets
        if total_assets <= 0:
            return self._create_error_result(
                stock, "Total assets must be positive", ["total_assets"]
            )

        total_liabilities = stock.total_liabilities
        if total_liabilities <= 0:
            total_liabilities = total_assets * 0.5  # Estimate 50% debt ratio
            warnings.append(
                f"Total liabilities estimated at 50% of assets: {total_liabilities/1e9:.2f}B"
            )

        # X1: Working Capital / Total Assets
        # Use current_assets - total_liabilities as approximation if net_working_capital available
        nwc = stock.net_working_capital
        if nwc == 0 and stock.current_assets > 0:
            # Estimate: Current Assets - Current Liabilities (assume CL = 30% of total liabilities)
            nwc = stock.current_assets - (total_liabilities * 0.3)
            warnings.append("Working Capital estimated from current assets")
        x1 = nwc / total_assets if total_assets > 0 else 0

        # X2: Retained Earnings / Total Assets
        retained_earnings = stock.retained_earnings
        if retained_earnings == 0:
            # Estimate: Assume 30% of equity is retained earnings
            equity = total_assets - total_liabilities
            retained_earnings = equity * 0.3
            warnings.append("Retained earnings estimated at 30% of equity")
        x2 = retained_earnings / total_assets if total_assets > 0 else 0

        # X3: EBIT / Total Assets (operating performance)
        ebit = stock.ebit
        if ebit == 0 and stock.operating_margin > 0 and stock.revenue > 0:
            ebit = stock.revenue * (stock.operating_margin / 100)
            warnings.append("EBIT estimated from operating margin")
        elif ebit == 0:
            # Last resort: estimate from net income
            ebit = stock.net_income * 1.3 if stock.net_income > 0 else 0
            if ebit > 0:
                warnings.append("EBIT estimated from net income")
        x3 = ebit / total_assets if total_assets > 0 else 0

        # X4: Market Cap / Total Liabilities
        market_cap = stock.market_cap
        x4 = market_cap / total_liabilities if total_liabilities > 0 else 0

        # X5: Revenue / Total Assets (asset turnover)
        revenue = stock.revenue
        if revenue == 0:
            # Estimate from net income assuming 10% margin
            revenue = stock.net_income * 10 if stock.net_income > 0 else total_assets * 0.8
            warnings.append("Revenue estimated from net income")
        x5 = revenue / total_assets if total_assets > 0 else 0

        # Calculate Z-Score
        z_score = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5

        # Determine zone and assessment
        if z_score >= self.zone_safe:
            zone = "Safe Zone"
            assessment = "Low Bankruptcy Risk"
            risk_level = "Low"
        elif z_score >= self.zone_distress:
            zone = "Grey Zone"
            assessment = "Moderate Bankruptcy Risk"
            risk_level = "Moderate"
        else:
            zone = "Distress Zone"
            assessment = "High Bankruptcy Risk"
            risk_level = "High"

        # Calculate component contributions
        contributions = {
            "X1_WorkingCapital": round(1.2 * x1, 3),
            "X2_RetainedEarnings": round(1.4 * x2, 3),
            "X3_EBIT": round(3.3 * x3, 3),
            "X4_MarketCap_Liabilities": round(0.6 * x4, 3),
            "X5_AssetTurnover": round(1.0 * x5, 3),
        }

        # Find weakest component
        ratios = {"X1": x1, "X2": x2, "X3": x3, "X4": x4, "X5": x5}
        weakest = min(ratios, key=ratios.get)
        weakest_desc = {
            "X1": "Low working capital - liquidity concerns",
            "X2": "Low retained earnings - limited accumulated profits",
            "X3": "Low EBIT - poor operating performance",
            "X4": "High leverage relative to market value",
            "X5": "Low asset turnover - inefficient asset utilization",
        }

        analysis = [
            f"Z-Score: {z_score:.2f} ({zone})",
            f"Safe Zone: >{self.zone_safe} | Grey Zone: {self.zone_distress}-{self.zone_safe} | Distress: <{self.zone_distress}",
            f"Risk Level: {risk_level}",
            f"Weakest factor: {weakest} - {weakest_desc.get(weakest, '')}",
            "",
            "Component Analysis:",
            f"  X1 (WC/Assets): {x1:.3f} → contributes {1.2*x1:.2f}",
            f"  X2 (RE/Assets): {x2:.3f} → contributes {1.4*x2:.2f}",
            f"  X3 (EBIT/Assets): {x3:.3f} → contributes {3.3*x3:.2f}",
            f"  X4 (MC/Liabilities): {x4:.3f} → contributes {0.6*x4:.2f}",
            f"  X5 (Revenue/Assets): {x5:.3f} → contributes {1.0*x5:.2f}",
        ]

        if z_score < 1.0:
            analysis.append("CRITICAL: Extremely high distress - avoid or investigate deeply")
        elif z_score < self.zone_distress:
            analysis.append("WARNING: Company shows significant financial stress")
        elif z_score < self.zone_safe:
            analysis.append("CAUTION: Company in grey zone - monitor closely")

        if warnings:
            analysis.extend(["", "Estimates Used:"] + [f"  - {w}" for w in warnings])

        # For ValuationResult, use current price as "fair value" since this is a risk metric
        # The premium/discount shows how much the market prices in the risk
        confidence = "High" if len(warnings) == 0 else ("Medium" if len(warnings) <= 2 else "Low")

        return ValuationResult(
            method=self.method_name,
            fair_value=stock.current_price,  # This is a risk metric, not valuation
            current_price=stock.current_price,
            premium_discount=0,
            assessment=assessment,
            details={
                "z_score": round(z_score, 2),
                "zone": zone,
                "risk_level": risk_level,
                "x1_working_capital_ratio": round(x1, 3),
                "x2_retained_earnings_ratio": round(x2, 3),
                "x3_ebit_ratio": round(x3, 3),
                "x4_market_cap_liabilities_ratio": round(x4, 3),
                "x5_asset_turnover": round(x5, 3),
                "component_contributions": contributions,
            },
            components=contributions,
            analysis=analysis,
            confidence=confidence,
            fair_value_range=None,  # Not applicable for risk metrics
            applicability="Applicable" if total_assets > 0 else "Limited",
        )
