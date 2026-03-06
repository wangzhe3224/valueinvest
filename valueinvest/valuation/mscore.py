"""
Beneish M-Score: Earnings Manipulation Detection

Developed by Professor Messod D. Beneish (1999), this 8-variable
model detects companies likely manipulating earnings.

Author: ValueInvest Project
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from .base import BaseValuation, ValuationResult, FieldRequirement


@dataclass
class MScoreResult:
    """Result of Beneish M-Score analysis."""

    m_score: float
    manipulation_risk: str  # Low, Medium, High, Very High
    is_manipulator: bool
    red_flags: List[str]
    component_scores: Dict[str, float]


class BeneishMScore(BaseValuation):
    """
    Beneish M-Score: Earnings Manipulation Detection

    Developed by Professor Messod D. Beneish (1999), this 8-variable
    model detects companies likely manipulating earnings.

    The 8 Variables:

    1. DSRI (Days Sales Receivable Index)
       = (Net Receivables_t / Sales_t) / (Net Receivables_t-1 / Sales_t-1)
       High DSRI suggests revenue inflation via loose credit

    2. GMI (Gross Margin Index)
       = Gross Margin_t-1 / Gross Margin_t
       GMI > 1 indicates deteriorating margins (incentive to manipulate)

    3. AQI (Asset Quality Index)
       = (1 - (Current Assets_t + PPE_t) / Total Assets_t) /
         (1 - (Current Assets_t-1 + PPE_t-1) / Total Assets_t-1)
       AQI > 1 indicates increased intangibles/other assets (potential manipulation)

    4. SGI (Sales Growth Index)
       = Sales_t / Sales_t-1
       High growth creates pressure to manipulate

    5. DEPI (Depreciation Index)
       = (Depreciation_t-1 / (Depreciation_t-1 + PPE_t-1)) /
         (Depreciation_t / (Depreciation_t + PPE_t))
       DEPI > 1 suggests aggressive depreciation policy change

    6. SGAI (SG&A Index)
       = (SG&A_t / Sales_t) / (SG&A_t-1 / Sales_t-1)
       SGAI > 1 suggests declining efficiency (incentive to manipulate)

    7. LVGI (Leverage Index)
       = (Total Debt_t / Total Assets_t) / (Total Debt_t-1 / Total Assets_t-1)
       LVGI > 1 indicates increasing leverage (debt covenant pressure)

    8. TATA (Total Accruals to Total Assets)
       = (Income from Continuing Operations_t - Cash from Operations_t) / Total Assets_t
       High accruals indicate low earnings quality

    M-Score Formula:
    M = -4.84 + 0.92*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI +
        0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI

    Interpretation:
    M < -2.22: Non-manipulator (safe)
    M > -2.22: Potential manipulator (investigate)
    M > -1.78: High probability manipulator
    """

    method_name = "Beneish M-Score"

    required_fields = [
        FieldRequirement("revenue", "Revenue (current year)", is_critical=True),
        FieldRequirement("total_assets", "Total Assets", is_critical=True),
        FieldRequirement("current_assets", "Current Assets", is_critical=False),
        FieldRequirement("accounts_receivable", "Accounts Receivable", is_critical=False),
        FieldRequirement("net_income", "Net Income", is_critical=True),
        FieldRequirement("fcf", "Free Cash Flow", is_critical=False),
    ]

    best_for = [
        "Earnings manipulation detection",
        "Fraud risk assessment",
        "Value investing due diligence",
        "Quality screening",
    ]

    not_for = [
        "Financial companies (different accounting)",
        "Companies with major acquisitions (distorted ratios)",
    ]

    # Thresholds
    SAFE_THRESHOLD = -2.22
    HIGH_RISK_THRESHOLD = -1.78

    def __init__(
        self,
        # Prior year data (required for most indices)
        prior_revenue: Optional[float] = None,
        prior_gross_margin: Optional[float] = None,
        prior_total_assets: Optional[float] = None,
        prior_current_assets: Optional[float] = None,
        prior_ppe: Optional[float] = None,
        prior_depreciation: Optional[float] = None,
        prior_sga: Optional[float] = None,
        prior_total_debt: Optional[float] = None,
        prior_accounts_receivable: Optional[float] = None,
    ):
        """
        Initialize Beneish M-Score.

        Args:
            prior_revenue: Prior year revenue
            prior_gross_margin: Prior year gross margin (%)
            prior_total_assets: Prior year total assets
            prior_current_assets: Prior year current assets
            prior_ppe: Prior year property, plant & equipment
            prior_depreciation: Prior year depreciation
            prior_sga: Prior year SG&A expenses
            prior_total_debt: Prior year total debt
            prior_accounts_receivable: Prior year accounts receivable
        """
        self.prior_revenue = prior_revenue
        self.prior_gross_margin = prior_gross_margin
        self.prior_total_assets = prior_total_assets
        self.prior_current_assets = prior_current_assets
        self.prior_ppe = prior_ppe
        self.prior_depreciation = prior_depreciation
        self.prior_sga = prior_sga
        self.prior_total_debt = prior_total_debt
        self.prior_accounts_receivable = prior_accounts_receivable

    def calculate(self, stock) -> ValuationResult:
        """Calculate Beneish M-Score."""
        is_valid, missing, warnings = self.validate_data(stock)
        if not is_valid:
            return self._create_error_result(
                stock, f"Missing required data: {', '.join(missing)}", missing
            )

        # Get prior data from constructor or stock fields
        prior_rev = self.prior_revenue or getattr(stock, "prior_revenue", None)
        prior_gm = self.prior_gross_margin or getattr(stock, "prior_gross_margin", None)
        prior_ta = self.prior_total_assets or getattr(stock, "prior_total_assets", None)
        prior_ca = self.prior_current_assets or getattr(stock, "prior_current_assets", None)
        prior_ppe = self.prior_ppe or getattr(
            stock, "net_fixed_assets", None
        )  # Use current as proxy
        prior_dep = self.prior_depreciation or getattr(stock, "depreciation", None)
        prior_sga = self.prior_sga or getattr(stock, "extra", {}).get("sga", None)
        prior_debt = self.prior_total_debt or getattr(stock, "total_liabilities", None)
        prior_ar = self.prior_accounts_receivable or getattr(stock, "accounts_receivable", None)

        # Current values
        curr_rev = stock.revenue
        curr_ta = stock.total_assets
        curr_ca = stock.current_assets
        curr_ar = stock.accounts_receivable
        curr_ppe = stock.net_fixed_assets
        curr_dep = stock.depreciation
        curr_debt = stock.total_liabilities
        curr_ni = stock.net_income
        curr_fcf = stock.fcf

        # Calculate indices (with safety checks)
        indices = {}

        # 1. DSRI - Days Sales Receivable Index
        if prior_rev and prior_rev > 0 and prior_ar is not None and curr_ar > 0:
            dsri = (curr_ar / curr_rev) / (prior_ar / prior_rev)
            indices["DSRI"] = dsri
        else:
            indices["DSRI"] = 1.0
            warnings.append("DSRI estimated as 1.0 (insufficient prior data)")

        # 2. GMI - Gross Margin Index
        if prior_gm and prior_gm > 0 and stock.operating_margin > 0:
            curr_gm = stock.operating_margin
            gmi = prior_gm / curr_gm
            indices["GMI"] = gmi
        else:
            indices["GMI"] = 1.0
            warnings.append("GMI estimated as 1.0 (insufficient margin data)")

        # 3. AQI - Asset Quality Index
        if prior_ta and prior_ta > 0 and prior_ca is not None and prior_ppe is not None:
            prior_asset_quality = 1 - (prior_ca + prior_ppe) / prior_ta
            curr_aq = 1 - (curr_ca + curr_ppe) / curr_ta if curr_ta > 0 else 0
            if prior_asset_quality > 0 and curr_aq > 0:
                aqi = curr_aq / prior_asset_quality
                indices["AQI"] = aqi
            else:
                indices["AQI"] = 1.0
        else:
            indices["AQI"] = 1.0
            warnings.append("AQI estimated as 1.0 (insufficient asset data)")

        # 4. SGI - Sales Growth Index
        if prior_rev and prior_rev > 0:
            sgi = curr_rev / prior_rev
            indices["SGI"] = sgi
        else:
            indices["SGI"] = 1.0
            warnings.append("SGI estimated as 1.0 (no prior revenue)")

        # 5. DEPI - Depreciation Index
        if (
            prior_dep
            and prior_dep > 0
            and prior_ppe
            and prior_ppe > 0
            and curr_dep > 0
            and curr_ppe > 0
        ):
            prior_dep_rate = prior_dep / (prior_dep + prior_ppe)
            curr_dep_rate = curr_dep / (curr_dep + curr_ppe)
            if curr_dep_rate > 0:
                depi = prior_dep_rate / curr_dep_rate
                indices["DEPI"] = depi
            else:
                indices["DEPI"] = 1.0
        else:
            indices["DEPI"] = 1.0
            warnings.append("DEPI estimated as 1.0 (insufficient depreciation data)")

        # 6. SGAI - SG&A Index
        if prior_sga and prior_sga > 0 and prior_rev > 0 and curr_rev > 0:
            # Current SG&A - estimate if not available
            curr_sga = stock.extra.get("sga", curr_rev * 0.15)  # Estimate 15% of revenue
            sgai = (curr_sga / curr_rev) / (prior_sga / prior_rev)
            indices["SGAI"] = sgai
        else:
            indices["SGAI"] = 1.0
            warnings.append("SGAI estimated as 1.0 (insufficient SG&A data)")

        # 7. LVGI - Leverage Index
        if prior_debt and prior_debt > 0 and prior_ta and prior_ta > 0:
            prior_lev = prior_debt / prior_ta
            curr_lev = curr_debt / curr_ta if curr_ta > 0 else 0
            if prior_lev > 0:
                lvgi = curr_lev / prior_lev
                indices["LVGI"] = lvgi
            else:
                indices["LVGI"] = 1.0
        else:
            indices["LVGI"] = 1.0
            warnings.append("LVGI estimated as 1.0 (insufficient leverage data)")

        # 8. TATA - Total Accruals to Total Assets
        if curr_fcf != 0 and curr_ta > 0:
            # Accruals = Net Income - CFO (using FCF as proxy)
            accruals = curr_ni - curr_fcf
            tata = accruals / curr_ta
            indices["TATA"] = tata
        else:
            # Estimate accruals as 10% of assets if no FCF
            tata = 0.1
            indices["TATA"] = tata
            warnings.append("TATA estimated at 0.1 (no FCF data)")

        # Calculate M-Score
        m_score = (
            -4.84
            + 0.92 * indices.get("DSRI", 1.0)
            + 0.528 * indices.get("GMI", 1.0)
            + 0.404 * indices.get("AQI", 1.0)
            + 0.892 * indices.get("SGI", 1.0)
            + 0.115 * indices.get("DEPI", 1.0)
            - 0.172 * indices.get("SGAI", 1.0)
            + 4.679 * indices.get("TATA", 0.1)
            - 0.327 * indices.get("LVGI", 1.0)
        )

        # Determine risk level
        if m_score < self.SAFE_THRESHOLD:
            manipulation_risk = "Low"
            is_manipulator = False
        elif m_score < self.HIGH_RISK_THRESHOLD:
            manipulation_risk = "Medium"
            is_manipulator = True
        else:
            manipulation_risk = "High"
            is_manipulator = True

        # Identify red flags
        red_flags = []
        if indices.get("DSRI", 1.0) > 1.2:
            red_flags.append(
                f"High DSRI ({indices['DSRI']:.2f}) - receivables growing faster than sales"
            )
        if indices.get("GMI", 1.0) > 1.1:
            red_flags.append(f"Deteriorating gross margins ({indices['GMI']:.2f})")
        if indices.get("AQI", 1.0) > 1.2:
            red_flags.append(f"Declining asset quality ({indices['AQI']:.2f})")
        if indices.get("SGI", 1.0) > 1.5:
            red_flags.append(f"Very high sales growth ({indices['SGI']:.2f})")
        if indices.get("TATA", 0) > 0.1:
            red_flags.append(f"High accruals to assets ({indices['TATA']:.3f})")

        # Build analysis
        analysis = [
            f"=== Beneish M-Score Analysis: {stock.ticker} ===",
            f"M-Score: {m_score:.2f}",
            f"Threshold: < {self.SAFE_THRESHOLD:.2f} (safe), > {self.HIGH_RISK_THRESHOLD:.2f} (high risk)",
            f"Risk Level: {manipulation_risk}",
            f"Is Manipulator: {'YES' if is_manipulator else 'NO'}",
            "",
            "Component Scores:",
        ]

        for name, value in indices.items():
            analysis.append(f"  {name}: {value:.3f}")

        if red_flags:
            analysis.extend(["", "Red Flags:"])
            for flag in red_flags:
                analysis.append(f"  ⚠️  {flag}")

        if is_manipulator:
            analysis.extend(
                ["", "⚠️  WARNING: Company shows signs of potential earnings manipulation."]
            )
            analysis.append("Recommendation: Deep due diligence required before investing.")
        else:
            analysis.extend(["", "✅ Company shows low risk of earnings manipulation."])

        if warnings:
            analysis.extend(["", "Notes:"] + [f"  - {w}" for w in warnings])

        confidence = "High" if len(warnings) == 0 else ("Medium" if len(warnings) <= 2 else "Low")

        return ValuationResult(
            method=self.method_name,
            fair_value=stock.current_price,  # This is risk assessment, not valuation
            current_price=stock.current_price,
            premium_discount=0,
            assessment=f"Manipulation Risk: {manipulation_risk} (M={m_score:.2f})",
            details={
                "m_score": round(m_score, 2),
                "manipulation_risk": manipulation_risk,
                "is_manipulator": is_manipulator,
                "red_flags": red_flags,
                "component_scores": {k: round(v, 3) for k, v in indices.items()},
                "threshold_safe": self.SAFE_THRESHOLD,
                "threshold_high_risk": self.HIGH_RISK_THRESHOLD,
            },
            components=indices,
            analysis=analysis,
            confidence=confidence,
            applicability="Applicable" if prior_rev else "Limited",
        )


# Convenience function
def calculate_m_score(
    stock,
    prior_revenue: Optional[float] = None,
    prior_gross_margin: Optional[float] = None,
    prior_total_assets: Optional[float] = None,
    prior_accounts_receivable: Optional[float] = None,
    prior_total_debt: Optional[float] = None,
) -> MScoreResult:
    """
    Calculate Beneish M-Score for earnings manipulation detection.

    Usage:
        result = calculate_m_score(
            stock,
            prior_revenue=100e9,
            prior_gross_margin=35.0,
            prior_total_assets=50e9,
        )
        print(f"M-Score: {result.m_score:.2f}")
        print(f"Is Manipulator: {result.is_manipulator}")
    """
    scorer = BeneishMScore(
        prior_revenue=prior_revenue,
        prior_gross_margin=prior_gross_margin,
        prior_total_assets=prior_total_assets,
        prior_accounts_receivable=prior_accounts_receivable,
        prior_total_debt=prior_total_debt,
    )
    val_result = scorer.calculate(stock)

    return MScoreResult(
        m_score=round(val_result.details.get("m_score", 0), 2),
        manipulation_risk=val_result.details.get("manipulation_risk", "Unknown"),
        is_manipulator=val_result.details.get("is_manipulator", False),
        red_flags=val_result.details.get("red_flags", []),
        component_scores=val_result.details.get("component_scores", {}),
    )
