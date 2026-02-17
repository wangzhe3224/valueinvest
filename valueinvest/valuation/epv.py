"""
Earnings Power Value
"""
from .base import BaseValuation, ValuationResult


class EPV(BaseValuation):
    method_name = "EPV (Zero Growth)"
    
    def calculate(self, stock) -> ValuationResult:
        revenue = stock.revenue
        operating_margin = stock.operating_margin / 100
        tax_rate = stock.tax_rate / 100
        depreciation = stock.depreciation
        capex = stock.capex
        net_working_capital = stock.net_working_capital
        cost_of_capital = stock.cost_of_capital / 100
        shares = stock.shares_outstanding
        net_debt = stock.net_debt
        maintenance_capex_pct = 0.7
        
        ebit = revenue * operating_margin
        nopat = ebit * (1 - tax_rate)
        gross_cash_flow = nopat + depreciation
        maintenance_capex = capex * maintenance_capex_pct
        working_capital_charge = net_working_capital * cost_of_capital
        distributable_cash_flow = gross_cash_flow - maintenance_capex - working_capital_charge
        
        epv_operating = distributable_cash_flow / cost_of_capital
        enterprise_value = epv_operating
        equity_value = enterprise_value - net_debt
        epv_per_share = equity_value / shares
        
        premium_discount = ((epv_per_share - stock.current_price) / stock.current_price) * 100
        
        implied_pe = epv_per_share / (nopat / shares) if nopat > 0 else 0
        
        growth_priced_in = ((stock.current_price / epv_per_share) - 1) * 100 if epv_per_share > 0 else 0
        
        analysis = [
            f"Value assuming ZERO future growth",
            f"Market prices in {growth_priced_in:.1f}% growth above this floor"
        ]
        
        return ValuationResult(
            method=self.method_name,
            fair_value=round(epv_per_share, 2),
            current_price=stock.current_price,
            premium_discount=round(premium_discount, 1),
            assessment=self._assess(epv_per_share, stock.current_price),
            details={"implied_pe": round(implied_pe, 2)},
            components={
                "ebit": ebit,
                "nopat": nopat,
                "distributable_cash_flow": distributable_cash_flow,
                "epv_operating": epv_operating,
            },
            analysis=analysis
        )
