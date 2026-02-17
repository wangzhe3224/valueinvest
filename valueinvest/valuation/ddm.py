"""
Dividend Discount Model
"""
from .base import BaseValuation, ValuationResult


class DDM(BaseValuation):
    method_name = "DDM (Gordon Growth)"
    
    def __init__(self, required_return: float = None):
        self.required_return = required_return
    
    def calculate(self, stock) -> ValuationResult:
        dividend = stock.dividend_per_share
        g = stock.dividend_growth_rate / 100
        r = (self.required_return or stock.cost_of_capital) / 100
        
        if r <= g:
            return ValuationResult(
                method=self.method_name,
                fair_value=0,
                current_price=stock.current_price,
                premium_discount=0,
                assessment="N/A - Required return <= growth rate"
            )
        
        next_dividend = dividend * (1 + g)
        intrinsic_value = next_dividend / (r - g)
        
        premium_discount = ((intrinsic_value - stock.current_price) / stock.current_price) * 100
        
        current_yield = (dividend / stock.current_price) * 100
        fair_yield = (next_dividend / intrinsic_value) * 100
        
        return ValuationResult(
            method=self.method_name,
            fair_value=round(intrinsic_value, 2),
            current_price=stock.current_price,
            premium_discount=round(premium_discount, 1),
            assessment=self._assess(intrinsic_value, stock.current_price),
            details={
                "formula": "P = D / (r - g)",
                "dividend": dividend,
                "growth_rate": g * 100,
                "required_return": r * 100,
            },
            components={
                "next_dividend": next_dividend,
                "current_yield": current_yield,
                "fair_yield": fair_yield,
            },
            analysis=[f"Best for: Stable dividend-paying companies"]
        )


class TwoStageDDM(BaseValuation):
    method_name = "Two-Stage DDM"
    
    def __init__(self, growth_stage1: float = 5.0, stage1_years: int = 5, 
                 growth_stage2: float = 2.0, required_return: float = None):
        self.growth_stage1 = growth_stage1
        self.stage1_years = stage1_years
        self.growth_stage2 = growth_stage2
        self.required_return = required_return
    
    def calculate(self, stock) -> ValuationResult:
        current_dividend = stock.dividend_per_share
        g1 = self.growth_stage1 / 100
        g2 = self.growth_stage2 / 100
        r = (self.required_return or stock.cost_of_capital) / 100
        
        if r <= g2:
            return ValuationResult(
                method=self.method_name,
                fair_value=0,
                current_price=stock.current_price,
                premium_discount=0,
                assessment="N/A - Required return <= terminal growth"
            )
        
        pv_dividends = 0
        dividend = current_dividend
        
        for year in range(1, self.stage1_years + 1):
            dividend *= (1 + g1)
            pv_dividends += dividend / ((1 + r) ** year)
        
        terminal_dividend = dividend * (1 + g2)
        terminal_value = terminal_dividend / (r - g2)
        pv_terminal = terminal_value / ((1 + r) ** self.stage1_years)
        
        intrinsic_value = pv_dividends + pv_terminal
        
        premium_discount = ((intrinsic_value - stock.current_price) / stock.current_price) * 100
        
        return ValuationResult(
            method=self.method_name,
            fair_value=round(intrinsic_value, 2),
            current_price=stock.current_price,
            premium_discount=round(premium_discount, 1),
            assessment=self._assess(intrinsic_value, stock.current_price),
            details={
                "stage1_growth": g1 * 100,
                "stage1_years": self.stage1_years,
                "stage2_growth": g2 * 100,
            },
            components={
                "pv_dividends_stage1": pv_dividends,
                "pv_terminal": pv_terminal,
            },
            analysis=[f"Stage 1: {g1*100:.1f}% for {self.stage1_years} years, then {g2*100:.1f}% perpetuity"]
        )
