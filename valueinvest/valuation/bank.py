"""
Bank-Specific Valuation Methods
"""
from .base import BaseValuation, ValuationResult


class PBValuation(BaseValuation):
    method_name = "P/B Valuation"
    
    def __init__(self, cost_of_equity: float = 10.0, sustainable_growth: float = 2.0):
        self.cost_of_equity = cost_of_equity
        self.sustainable_growth = sustainable_growth
    
    def calculate(self, stock) -> ValuationResult:
        bvps = stock.bvps
        roe = stock.roe / 100
        coe = self.cost_of_equity / 100
        g = self.sustainable_growth / 100
        
        current_pb = stock.current_price / bvps if bvps > 0 else 0
        
        fair_pb = (roe - g) / (coe - g)
        fair_price = bvps * fair_pb
        
        premium_discount = ((fair_price - stock.current_price) / stock.current_price) * 100
        
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
            },
            components={"current_pb": current_pb, "fair_pb": fair_pb, "book_value": bvps},
            analysis=[f"Current P/B: {current_pb:.2f}x vs Fair P/B: {fair_pb:.2f}x"]
        )


class ResidualIncome(BaseValuation):
    method_name = "Residual Income"
    
    def __init__(self, cost_of_equity: float = 10.0, years: int = 10, terminal_roe: float = 8.0):
        self.cost_of_equity = cost_of_equity
        self.years = years
        self.terminal_roe = terminal_roe
    
    def calculate(self, stock) -> ValuationResult:
        bvps = stock.bvps
        roe = stock.roe / 100
        coe = self.cost_of_equity / 100
        terminal_roe = self.terminal_roe / 100
        
        book_value = bvps
        total_residual_income = 0
        
        for year in range(1, self.years + 1):
            residual_income = book_value * (roe - coe)
            pv_residual = residual_income / ((1 + coe) ** year)
            total_residual_income += pv_residual
            book_value *= (1 + roe * 0.6)
        
        terminal_residual = book_value * (terminal_roe - coe)
        terminal_value = terminal_residual / (coe * ((1 + coe) ** self.years))
        
        intrinsic_value = bvps + total_residual_income + terminal_value
        
        premium_discount = ((intrinsic_value - stock.current_price) / stock.current_price) * 100
        
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
            },
            components={
                "book_value": bvps,
                "residual_income_pv": total_residual_income,
                "terminal_value_pv": terminal_value,
            },
            analysis=[f"Book Value: ¥{bvps:.2f} + Residual Income: ¥{total_residual_income:.2f} + Terminal: ¥{terminal_value:.2f}"]
        )


def analyze_bank_health(npl_ratio: float, provision_coverage: float, 
                        capital_adequacy_ratio: float, roe: float) -> dict:
    assessment = []
    score = 0
    
    if npl_ratio < 1.5:
        assessment.append(("NPL Ratio", npl_ratio, "Excellent", 3))
        score += 3
    elif npl_ratio < 2.0:
        assessment.append(("NPL Ratio", npl_ratio, "Good", 2))
        score += 2
    else:
        assessment.append(("NPL Ratio", npl_ratio, "Concern", 1))
        score += 1
    
    if provision_coverage > 200:
        assessment.append(("Provision Coverage", provision_coverage, "Excellent", 3))
        score += 3
    elif provision_coverage > 150:
        assessment.append(("Provision Coverage", provision_coverage, "Good", 2))
        score += 2
    else:
        assessment.append(("Provision Coverage", provision_coverage, "Low", 1))
        score += 1
    
    if capital_adequacy_ratio > 15:
        assessment.append(("Capital Adequacy", capital_adequacy_ratio, "Excellent", 3))
        score += 3
    elif capital_adequacy_ratio > 12:
        assessment.append(("Capital Adequacy", capital_adequacy_ratio, "Good", 2))
        score += 2
    else:
        assessment.append(("Capital Adequacy", capital_adequacy_ratio, "Low", 1))
        score += 1
    
    if roe > 12:
        assessment.append(("ROE", roe, "Excellent", 3))
        score += 3
    elif roe > 10:
        assessment.append(("ROE", roe, "Good", 2))
        score += 2
    else:
        assessment.append(("ROE", roe, "Average", 1))
        score += 1
    
    if score >= 10:
        overall = "Excellent"
    elif score >= 8:
        overall = "Good"
    elif score >= 6:
        overall = "Average"
    else:
        overall = "Concern"
    
    return {
        "indicators": assessment,
        "total_score": score,
        "max_score": 12,
        "overall_rating": overall
    }
