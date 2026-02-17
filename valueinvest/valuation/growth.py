"""
Growth Company Valuation Methods
"""
from .base import BaseValuation, ValuationResult


class PEG(BaseValuation):
    method_name = "PEG Ratio"
    
    def calculate(self, stock) -> ValuationResult:
        pe_ratio = stock.pe_ratio
        growth_rate = stock.growth_rate
        
        if growth_rate <= 0:
            return ValuationResult(
                method=self.method_name,
                fair_value=0,
                current_price=stock.current_price,
                premium_discount=0,
                assessment="N/A - Non-positive growth rate"
            )
        
        peg_ratio = pe_ratio / growth_rate
        
        fair_pe = growth_rate * 1.0
        fair_price = stock.eps * fair_pe
        
        premium_discount = ((fair_price - stock.current_price) / stock.current_price) * 100
        
        if peg_ratio < 1.0:
            assessment = "Undervalued"
        elif peg_ratio < 1.5:
            assessment = "Fair"
        else:
            assessment = "Overvalued"
        
        return ValuationResult(
            method=self.method_name,
            fair_value=round(fair_price, 2),
            current_price=stock.current_price,
            premium_discount=round(premium_discount, 1),
            assessment=assessment,
            details={"peg_ratio": round(peg_ratio, 2), "pe_ratio": round(pe_ratio, 2), "growth_rate": growth_rate},
            analysis=[f"PEG: {peg_ratio:.2f} (< 1.0 = undervalued, > 1.5 = overvalued)"]
        )


class GARP(BaseValuation):
    method_name = "GARP"
    
    def __init__(self, target_pe: float = 18, years: int = 5, required_return: float = 12.0):
        self.target_pe = target_pe
        self.years = years
        self.required_return = required_return
    
    def calculate(self, stock) -> ValuationResult:
        eps = stock.eps
        g = stock.growth_rate / 100
        r = self.required_return / 100
        
        future_eps = eps * ((1 + g) ** self.years)
        future_price = future_eps * self.target_pe
        present_value = future_price / ((1 + r) ** self.years)
        
        premium_discount = ((present_value - stock.current_price) / stock.current_price) * 100
        
        upside = ((present_value - stock.current_price) / stock.current_price) * 100
        
        return ValuationResult(
            method=self.method_name,
            fair_value=round(present_value, 2),
            current_price=stock.current_price,
            premium_discount=round(premium_discount, 1),
            assessment=self._assess(present_value, stock.current_price),
            details={
                "target_pe": self.target_pe,
                "years": self.years,
                "required_return": r * 100,
            },
            components={
                "current_eps": eps,
                "future_eps": future_eps,
                "future_price": future_price,
            },
            analysis=[f"Projects EPS to ¥{future_eps:.2f} in {self.years} years at {g*100:.1f}% growth"]
        )


class RuleOf40(BaseValuation):
    method_name = "Rule of 40"
    
    def calculate(self, stock) -> ValuationResult:
        revenue_growth = stock.growth_rate
        fcf_margin = (stock.fcf / stock.revenue) * 100 if stock.revenue > 0 else 0
        
        score = revenue_growth + fcf_margin
        passes = score >= 40
        
        if score >= 40:
            assessment = "Healthy"
        elif score >= 30:
            assessment = "Acceptable"
        else:
            assessment = "Weak"
        
        return ValuationResult(
            method=self.method_name,
            fair_value=stock.current_price,
            current_price=stock.current_price,
            premium_discount=0,
            assessment=assessment,
            details={"score": round(score, 1), "growth": revenue_growth, "fcf_margin": round(fcf_margin, 1)},
            components={"revenue_growth": revenue_growth, "fcf_margin": fcf_margin},
            analysis=[f"Score: {score:.1f} (Growth {revenue_growth:.1f}% + FCF Margin {fcf_margin:.1f}%)", 
                      f"Passes Rule of 40: {'Yes' if passes else 'No'}"]
        )
