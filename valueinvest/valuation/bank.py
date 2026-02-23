"""
Bank-Specific Valuation Methods
"""
from typing import Optional
from .base import BaseValuation, ValuationResult, ValuationRange, FieldRequirement


class PBValuation(BaseValuation):
    method_name = "P/B Valuation"
    
    required_fields = [
        FieldRequirement("bvps", "Book Value Per Share", is_critical=True, min_value=0.01),
        FieldRequirement("roe", "Return on Equity %", is_critical=True),
        FieldRequirement("current_price", "Current Stock Price", is_critical=True, min_value=0.01),
    ]
    
    best_for = ["Banks", "Insurance companies", "Financial institutions"]
    not_for = ["Asset-light businesses", "Technology companies", "Companies with negative book value"]
    
    def __init__(self, cost_of_equity: float = 10.0, sustainable_growth: float = 2.0):
        self.cost_of_equity = cost_of_equity
        self.sustainable_growth = sustainable_growth
    
    def calculate(self, stock) -> ValuationResult:
        is_valid, missing, warnings = self.validate_data(stock)
        if not is_valid:
            return self._create_error_result(stock, f"Missing required data: {', '.join(missing)}", missing)
        
        bvps = stock.bvps
        roe = stock.roe / 100
        coe = self.cost_of_equity / 100
        g = self.sustainable_growth / 100
        
        current_pb = stock.current_price / bvps if bvps > 0 else 0
        
        if coe <= g:
            return self._create_error_result(
                stock,
                f"Cost of equity ({coe*100:.1f}%) must exceed growth rate ({g*100:.1f}%)",
                []
            )
        
        if roe <= g:
            fair_pb = 0
            fair_price = 0
            analysis_text = "ROE <= growth: company destroys value, P/B should be below book"
            applicability = "Limited"
        else:
            fair_pb = (roe - g) / (coe - g)
            fair_price = bvps * fair_pb
            analysis_text = f"Fair P/B of {fair_pb:.2f}x implies ROE of {roe*100:.1f}% justifies premium to book"
            applicability = "Applicable"
        
        if fair_pb <= 0:
            analysis_text = f"ROE ({roe*100:.1f}%) below cost of equity ({coe*100:.1f}%) - value destructive"
            fair_pb = max(0, (roe - g) / (coe - g)) if roe > 0 else 0
            fair_price = bvps * fair_pb
        
        premium_discount = ((fair_price - stock.current_price) / stock.current_price) * 100 if fair_price > 0 else -100
        
        pb_low = bvps * max(0, ((roe - 0.02) - g) / (coe + 0.02 - g)) if roe > 0.02 else 0
        pb_high = bvps * ((roe + 0.02) - g) / (coe - 0.02 - g) if roe + 0.02 > g else bvps
        
        analysis = [
            f"Current P/B: {current_pb:.2f}x vs Fair P/B: {fair_pb:.2f}x",
            analysis_text,
            f"ROE: {roe*100:.1f}%, Cost of Equity: {coe*100:.1f}%, Growth: {g*100:.1f}%",
        ]
        
        if current_pb < fair_pb * 0.8:
            analysis.append("Potentially undervalued - trading at significant discount to fair P/B")
        elif current_pb > fair_pb * 1.2:
            analysis.append("Potentially overvalued - trading at premium to justified P/B")
        
        if warnings:
            analysis.extend([f"Note: {w}" for w in warnings])
        
        confidence = "High" if roe > coe else ("Medium" if roe > coe * 0.8 else "Low")
        
        return ValuationResult(
            method=self.method_name,
            fair_value=round(fair_price, 2),
            current_price=stock.current_price,
            premium_discount=round(premium_discount, 1),
            assessment=self._assess(fair_price, stock.current_price),
            details={
                "formula": "Fair P/B = (ROE - g) / (COE - g)",
                "current_pb": round(current_pb, 2),
                "fair_pb": round(fair_pb, 2),
                "roe": roe * 100,
                "cost_of_equity": coe * 100,
                "sustainable_growth": g * 100,
            },
            components={"current_pb": current_pb, "fair_pb": fair_pb, "book_value": bvps},
            analysis=analysis,
            confidence=confidence,
            fair_value_range=ValuationRange(
                low=round(pb_low, 2),
                base=round(fair_price, 2),
                high=round(pb_high, 2)
            ),
            applicability=applicability,
        )


class ResidualIncome(BaseValuation):
    method_name = "Residual Income"
    
    required_fields = [
        FieldRequirement("bvps", "Book Value Per Share", is_critical=True, min_value=0.01),
        FieldRequirement("roe", "Return on Equity %", is_critical=True),
        FieldRequirement("current_price", "Current Stock Price", is_critical=True, min_value=0.01),
    ]
    
    best_for = ["Banks", "Insurance companies", "Stable dividend payers"]
    not_for = ["High-growth companies", "Companies with volatile ROE", "Negative book value"]
    
    def __init__(
        self,
        cost_of_equity: float = 10.0,
        years: int = 10,
        terminal_roe: float = 8.0,
        payout_ratio: float = 0.6,
    ):
        self.cost_of_equity = cost_of_equity
        self.years = years
        self.terminal_roe = terminal_roe
        self.payout_ratio = payout_ratio
    
    def calculate(self, stock) -> ValuationResult:
        is_valid, missing, warnings = self.validate_data(stock)
        if not is_valid:
            return self._create_error_result(stock, f"Missing required data: {', '.join(missing)}", missing)
        
        bvps = stock.bvps
        roe = stock.roe / 100
        coe = self.cost_of_equity / 100
        terminal_roe = self.terminal_roe / 100
        retention_ratio = 1 - self.payout_ratio
        sustainable_growth = roe * retention_ratio
        
        book_value = bvps
        total_residual_income = 0
        residual_incomes = []
        
        for year in range(1, self.years + 1):
            residual_income = book_value * (roe - coe)
            pv_residual = residual_income / ((1 + coe) ** year)
            total_residual_income += pv_residual
            residual_incomes.append({
                "year": year,
                "book_value": book_value,
                "residual_income": residual_income,
                "pv": pv_residual,
            })
            book_value *= (1 + sustainable_growth)
        
        terminal_residual = book_value * (terminal_roe - coe)
        
        if terminal_residual <= 0:
            terminal_value = 0
            terminal_analysis = f"Terminal ROE ({terminal_roe*100:.1f}%) <= COE ({coe*100:.1f}%) - no terminal value"
        else:
            terminal_value = terminal_residual / (coe * ((1 + coe) ** self.years))
            terminal_analysis = f"Terminal value based on ROE converging to {terminal_roe*100:.1f}%"
        
        intrinsic_value = bvps + total_residual_income + terminal_value
        
        premium_discount = ((intrinsic_value - stock.current_price) / stock.current_price) * 100
        
        ri_low = self._calculate_ri_sensitivity(stock, coe + 0.02, roe - 0.02)
        ri_high = self._calculate_ri_sensitivity(stock, coe - 0.02, roe + 0.02)
        
        value_from_book = bvps
        value_from_ri = total_residual_income
        value_from_terminal = terminal_value
        
        analysis = [
            f"Book Value: ¥{bvps:.2f}",
            f"PV of Residual Income (Years 1-{self.years}): ¥{total_residual_income:.2f}",
            f"PV of Terminal Value: ¥{terminal_value:.2f}",
            terminal_analysis,
        ]
        
        if roe < coe:
            analysis.append(f"Warning: Current ROE ({roe*100:.1f}%) < Cost of Equity ({coe*100:.1f}%) - value destructive")
        
        if terminal_roe < coe:
            analysis.append(f"Terminal ROE below COE - assuming ROE decays to cost of capital")
        
        book_pct = (value_from_book / intrinsic_value * 100) if intrinsic_value > 0 else 0
        if book_pct > 80:
            analysis.append(f"Most value ({book_pct:.0f}%) from book value - limited earnings power")
        
        if warnings:
            analysis.extend([f"Note: {w}" for w in warnings])
        
        confidence = "High" if roe > coe and terminal_roe >= coe * 0.9 else ("Medium" if roe > coe * 0.8 else "Low")
        
        return ValuationResult(
            method=self.method_name,
            fair_value=round(intrinsic_value, 2),
            current_price=stock.current_price,
            premium_discount=round(premium_discount, 1),
            assessment=self._assess(intrinsic_value, stock.current_price),
            details={
                "formula": "Value = Book Value + PV(Residual Income)",
                "years": self.years,
                "terminal_roe": terminal_roe * 100,
                "sustainable_growth": sustainable_growth * 100,
            },
            components={
                "book_value": bvps,
                "residual_income_pv": total_residual_income,
                "terminal_value_pv": terminal_value,
            },
            analysis=analysis,
            confidence=confidence,
            fair_value_range=ValuationRange(
                low=round(ri_low, 2),
                base=round(intrinsic_value, 2),
                high=round(ri_high, 2)
            ),
            applicability="Applicable" if roe > 0 and bvps > 0 else "Limited",
        )
    
    def _calculate_ri_sensitivity(self, stock, coe, roe):
        bvps = stock.bvps
        retention_ratio = 1 - self.payout_ratio
        sustainable_growth = roe * retention_ratio
        
        book_value = bvps
        total_residual_income = 0
        
        for year in range(1, self.years + 1):
            residual_income = book_value * (roe - coe)
            pv_residual = residual_income / ((1 + coe) ** year)
            total_residual_income += pv_residual
            book_value *= (1 + sustainable_growth)
        
        terminal_residual = book_value * (self.terminal_roe / 100 - coe)
        terminal_value = terminal_residual / (coe * ((1 + coe) ** self.years)) if terminal_residual > 0 else 0
        
        return bvps + total_residual_income + terminal_value


def analyze_bank_health(
    npl_ratio: float,
    provision_coverage: float,
    capital_adequacy_ratio: float,
    roe: float
) -> dict:
    assessment = []
    score = 0
    
    if npl_ratio < 1.0:
        assessment.append(("NPL Ratio", npl_ratio, "Excellent", 3))
        score += 3
    elif npl_ratio < 1.5:
        assessment.append(("NPL Ratio", npl_ratio, "Good", 2.5))
        score += 2.5
    elif npl_ratio < 2.0:
        assessment.append(("NPL Ratio", npl_ratio, "Acceptable", 2))
        score += 2
    elif npl_ratio < 3.0:
        assessment.append(("NPL Ratio", npl_ratio, "Concern", 1))
        score += 1
    else:
        assessment.append(("NPL Ratio", npl_ratio, "High Risk", 0))
    
    if provision_coverage > 250:
        assessment.append(("Provision Coverage", provision_coverage, "Excellent", 3))
        score += 3
    elif provision_coverage > 200:
        assessment.append(("Provision Coverage", provision_coverage, "Good", 2.5))
        score += 2.5
    elif provision_coverage > 150:
        assessment.append(("Provision Coverage", provision_coverage, "Acceptable", 2))
        score += 2
    elif provision_coverage > 100:
        assessment.append(("Provision Coverage", provision_coverage, "Low", 1))
        score += 1
    else:
        assessment.append(("Provision Coverage", provision_coverage, "Insufficient", 0))
    
    if capital_adequacy_ratio > 16:
        assessment.append(("Capital Adequacy", capital_adequacy_ratio, "Excellent", 3))
        score += 3
    elif capital_adequacy_ratio > 14:
        assessment.append(("Capital Adequacy", capital_adequacy_ratio, "Good", 2.5))
        score += 2.5
    elif capital_adequacy_ratio > 12:
        assessment.append(("Capital Adequacy", capital_adequacy_ratio, "Acceptable", 2))
        score += 2
    elif capital_adequacy_ratio > 10.5:
        assessment.append(("Capital Adequacy", capital_adequacy_ratio, "Adequate", 1))
        score += 1
    else:
        assessment.append(("Capital Adequacy", capital_adequacy_ratio, "Below Minimum", 0))
    
    if roe > 15:
        assessment.append(("ROE", roe, "Excellent", 3))
        score += 3
    elif roe > 12:
        assessment.append(("ROE", roe, "Good", 2.5))
        score += 2.5
    elif roe > 10:
        assessment.append(("ROE", roe, "Acceptable", 2))
        score += 2
    elif roe > 8:
        assessment.append(("ROE", roe, "Below Average", 1))
        score += 1
    else:
        assessment.append(("ROE", roe, "Poor", 0.5))
        score += 0.5
    
    max_score = 12
    if score >= 10:
        overall = "Excellent"
    elif score >= 8:
        overall = "Good"
    elif score >= 6:
        overall = "Average"
    elif score >= 4:
        overall = "Below Average"
    else:
        overall = "Concern"
    
    return {
        "indicators": assessment,
        "total_score": score,
        "max_score": max_score,
        "overall_rating": overall,
        "score_pct": (score / max_score) * 100,
    }
