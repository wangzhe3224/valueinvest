from .base import BaseValuation, ValuationResult


class MagicFormula(BaseValuation):
    """
    Joel Greenblatt's Magic Formula - ranks stocks by two criteria:
    1. Earnings Yield (EY): EBIT / Enterprise Value
    2. Return on Capital (ROC): EBIT / (Net Fixed Assets + Net Working Capital)
    """
    method_name = "Magic Formula"
    
    def __init__(self, required_ey: float = 10.0, benchmark_roc: float = 25.0):
        self.required_ey = required_ey
        self.benchmark_roc = benchmark_roc
    
    def calculate(self, stock) -> ValuationResult:
        ebit = stock.ebit
        if ebit <= 0 and stock.operating_margin > 0 and stock.revenue > 0:
            ebit = stock.revenue * (stock.operating_margin / 100)
        
        if ebit <= 0:
            return ValuationResult(
                method=self.method_name,
                fair_value=0,
                current_price=stock.current_price,
                premium_discount=0,
                assessment="N/A - Cannot calculate EBIT",
                analysis=["EBIT is zero or negative, Magic Formula not applicable"]
            )
        
        ev = stock.enterprise_value
        if ev <= 0:
            return ValuationResult(
                method=self.method_name,
                fair_value=0,
                current_price=stock.current_price,
                premium_discount=0,
                assessment="N/A - Invalid Enterprise Value",
                analysis=["Enterprise Value is zero or negative"]
            )
        
        invested_capital = stock.net_fixed_assets + stock.net_working_capital
        if invested_capital <= 0:
            return ValuationResult(
                method=self.method_name,
                fair_value=0,
                current_price=stock.current_price,
                premium_discount=0,
                assessment="N/A - Invalid Invested Capital",
                analysis=["Invested Capital (Net Fixed Assets + NWC) is zero or negative"]
            )
        
        earnings_yield = (ebit / ev) * 100
        return_on_capital = (ebit / invested_capital) * 100
        
        fair_ev = ebit / (self.required_ey / 100)
        fair_price = (fair_ev - stock.net_debt) / stock.shares_outstanding if stock.shares_outstanding > 0 else 0
        
        if fair_price <= 0:
            return ValuationResult(
                method=self.method_name,
                fair_value=0,
                current_price=stock.current_price,
                premium_discount=0,
                assessment="N/A - Fair price calculation failed",
                analysis=[f"EY: {earnings_yield:.1f}%, ROC: {return_on_capital:.1f}%"]
            )
        
        premium_discount = ((fair_price - stock.current_price) / stock.current_price) * 100
        
        ey_pass = earnings_yield >= self.required_ey
        roc_pass = return_on_capital >= self.benchmark_roc
        
        if ey_pass and roc_pass:
            quality = "High Quality & Cheap"
        elif ey_pass:
            quality = "Cheap but Average Quality"
        elif roc_pass:
            quality = "Good Quality but Expensive"
        else:
            quality = "Low Quality & Expensive"
        
        assessment = self._assess(fair_price, stock.current_price)
        
        return ValuationResult(
            method=self.method_name,
            fair_value=round(fair_price, 2),
            current_price=stock.current_price,
            premium_discount=round(premium_discount, 1),
            assessment=assessment,
            details={
                "earnings_yield": round(earnings_yield, 2),
                "return_on_capital": round(return_on_capital, 2),
                "ebit": ebit,
                "enterprise_value": ev,
                "invested_capital": invested_capital,
            },
            components={
                "earnings_yield_pct": round(earnings_yield, 2),
                "roc_pct": round(return_on_capital, 2),
            },
            analysis=[
                f"Earnings Yield: {earnings_yield:.2f}% (Required: {self.required_ey}%) - {'PASS' if ey_pass else 'FAIL'}",
                f"Return on Capital: {return_on_capital:.2f}% (Benchmark: {self.benchmark_roc}%) - {'PASS' if roc_pass else 'FAIL'}",
                f"Quality Assessment: {quality}",
                f"Fair EV (at {self.required_ey}% EY): ${fair_ev/1e9:.2f}B",
            ]
        )
