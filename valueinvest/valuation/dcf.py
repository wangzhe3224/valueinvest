"""
Discounted Cash Flow Valuation
"""
from .base import BaseValuation, ValuationResult


class DCF(BaseValuation):
    method_name = "DCF (10-Year)"
    
    def __init__(self, growth_1_5: float = None, growth_6_10: float = None, 
                 terminal_growth: float = None, discount_rate: float = None):
        self.growth_1_5 = growth_1_5
        self.growth_6_10 = growth_6_10
        self.terminal_growth = terminal_growth
        self.discount_rate = discount_rate
    
    def calculate(self, stock) -> ValuationResult:
        fcf = stock.fcf
        shares = stock.shares_outstanding
        net_debt = stock.net_debt
        
        g1 = (self.growth_1_5 or stock.growth_rate_1_5) / 100
        g2 = (self.growth_6_10 or stock.growth_rate_6_10) / 100
        g_term = (self.terminal_growth or stock.terminal_growth) / 100
        r = (self.discount_rate or stock.discount_rate) / 100
        
        if r <= g_term:
            return ValuationResult(
                method=self.method_name,
                fair_value=0,
                current_price=stock.current_price,
                premium_discount=0,
                assessment="N/A - Discount rate <= terminal growth"
            )
        
        projected_fcf = fcf
        total_pv = 0
        cash_flows = []
        
        for year in range(1, 11):
            if year <= 5:
                projected_fcf *= (1 + g1)
            else:
                projected_fcf *= (1 + g2)
            
            pv = projected_fcf / ((1 + r) ** year)
            total_pv += pv
            cash_flows.append({"year": year, "fcf": projected_fcf, "pv": pv})
        
        fcf_year_10 = projected_fcf
        terminal_value = (fcf_year_10 * (1 + g_term)) / (r - g_term)
        pv_terminal = terminal_value / ((1 + r) ** 10)
        
        enterprise_value = total_pv + pv_terminal
        equity_value = enterprise_value - net_debt
        intrinsic_value = equity_value / shares
        
        premium_discount = ((intrinsic_value - stock.current_price) / stock.current_price) * 100
        
        return ValuationResult(
            method=self.method_name,
            fair_value=round(intrinsic_value, 2),
            current_price=stock.current_price,
            premium_discount=round(premium_discount, 1),
            assessment=self._assess(intrinsic_value, stock.current_price),
            details={
                "growth_1_5": g1 * 100,
                "growth_6_10": g2 * 100,
                "terminal_growth": g_term * 100,
                "discount_rate": r * 100,
            },
            components={
                "pv_fcf": total_pv,
                "pv_terminal": pv_terminal,
                "enterprise_value": enterprise_value,
                "equity_value": equity_value,
            },
            analysis=[f"Best for: Growth companies with predictable FCF"]
        )


class ReverseDCF(BaseValuation):
    method_name = "Reverse DCF"
    
    def calculate(self, stock) -> ValuationResult:
        current_price = stock.current_price
        fcf = stock.fcf
        shares = stock.shares_outstanding
        g_term = stock.terminal_growth / 100
        r = stock.discount_rate / 100
        
        target_equity_value = current_price * shares
        
        low, high = 0.0, 50.0
        
        for _ in range(100):
            mid = (low + high) / 2
            g1 = mid / 100
            g2 = g1 * 0.5
            
            projected_fcf = fcf
            total_pv = 0
            
            for year in range(1, 11):
                if year <= 5:
                    projected_fcf *= (1 + g1)
                else:
                    projected_fcf *= (1 + g2)
                total_pv += projected_fcf / ((1 + r) ** year)
            
            fcf_year_10 = projected_fcf
            terminal_value = (fcf_year_10 * (1 + g_term)) / (r - g_term)
            pv_terminal = terminal_value / ((1 + r) ** 10)
            
            implied_equity = total_pv + pv_terminal
            
            if abs(implied_equity - target_equity_value) < target_equity_value * 0.001:
                break
            if implied_equity < target_equity_value:
                low = mid
            else:
                high = mid
        
        return ValuationResult(
            method=self.method_name,
            fair_value=current_price,
            current_price=current_price,
            premium_discount=0,
            assessment="Priced in growth",
            details={
                "implied_growth_1_5": round(mid, 1),
                "implied_growth_6_10": round(mid * 0.5, 1),
            },
            analysis=[f"Market prices in {mid:.1f}% annual growth for years 1-5"]
        )
