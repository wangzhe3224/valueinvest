"""
Earnings Power Value
"""
from typing import Optional
from .base import BaseValuation, ValuationResult, ValuationRange, FieldRequirement


class EPV(BaseValuation):
    method_name = "EPV (Zero Growth)"
    
    required_fields = [
        FieldRequirement("revenue", "Revenue", is_critical=True, min_value=0.01),
        FieldRequirement("operating_margin", "Operating Margin %", is_critical=True),
        FieldRequirement("tax_rate", "Tax Rate %", is_critical=True),
        FieldRequirement("depreciation", "Depreciation", is_critical=False),
        FieldRequirement("capex", "Capital Expenditure", is_critical=False),
        FieldRequirement("cost_of_capital", "Cost of Capital %", is_critical=True),
        FieldRequirement("shares_outstanding", "Shares Outstanding", is_critical=True, min_value=0.01),
        FieldRequirement("current_price", "Current Stock Price", is_critical=True, min_value=0.01),
    ]
    
    best_for = ["Mature companies", "Stable businesses", "Value investing baseline"]
    not_for = ["High-growth companies", "Turnaround situations", "Cyclical companies at peak"]
    
    DEFAULT_MAINTENANCE_CAPEX_PCT = 0.7
    
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
            return self._create_error_result(stock, f"Missing required data: {', '.join(missing)}", missing)
        
        revenue = stock.revenue
        operating_margin = stock.operating_margin / 100
        tax_rate = stock.tax_rate / 100
        depreciation = stock.depreciation
        capex = stock.capex
        net_working_capital = stock.net_working_capital
        cost_of_capital = (self.cost_of_capital if self.cost_of_capital is not None else stock.cost_of_capital) / 100
        shares = stock.shares_outstanding
        net_debt = stock.net_debt
        
        maintenance_pct = self.maintenance_capex_pct or self.DEFAULT_MAINTENANCE_CAPEX_PCT
        
        if maintenance_pct != self.DEFAULT_MAINTENANCE_CAPEX_PCT:
            warnings.append(f"Using custom maintenance capex %: {maintenance_pct*100:.0f}%")
        
        if operating_margin <= 0:
            return self._create_error_result(stock, f"Operating margin must be positive (got {operating_margin*100:.1f}%)", [])
        
        if cost_of_capital <= 0:
            return self._create_error_result(stock, f"Cost of capital must be positive (got {cost_of_capital*100:.1f}%)", [])
        
        ebit = revenue * operating_margin
        nopat = ebit * (1 - tax_rate)
        
        maintenance_capex = abs(capex) * maintenance_pct if capex != 0 else 0
        
        # Greenwald's EPV: Use excess depreciation (tax-affected at 50% of tax rate)
        # NOT full depreciation add-back, and NO working capital charge (constant size assumption)
        excess_depreciation = depreciation * (0.5 * tax_rate)
        
        # Adjusted earnings per Greenwald's methodology
        distributable_cash_flow = nopat - maintenance_capex + excess_depreciation
        
        if distributable_cash_flow <= 0:
            return self._create_error_result(
                stock, 
                f"Distributable cash flow is negative ({distributable_cash_flow/1e9:.2f}B)",
                []
            )
        
        epv_operating = distributable_cash_flow / cost_of_capital
        enterprise_value = epv_operating
        equity_value = enterprise_value - net_debt
        epv_per_share = equity_value / shares if shares > 0 else 0
        
        premium_discount = ((epv_per_share - stock.current_price) / stock.current_price) * 100
        
        implied_pe = epv_per_share / (nopat / shares) if nopat > 0 and shares > 0 else 0
        
        growth_priced_in = ((stock.current_price / epv_per_share) - 1) * 100 if epv_per_share > 0 else 0
        
        epv_low = self._calculate_epv_sensitivity(
            stock, revenue, operating_margin * 0.95, tax_rate, depreciation, 
            abs(capex), maintenance_pct + 0.1, cost_of_capital + 0.01, shares, net_debt
        )
        epv_high = self._calculate_epv_sensitivity(
            stock, revenue, operating_margin * 1.05, tax_rate, depreciation,
            abs(capex), maintenance_pct - 0.1, cost_of_capital - 0.01, shares, net_debt
        )
        
        analysis = [
            f"Value assuming ZERO future growth",
            f"Market prices in {growth_priced_in:.1f}% growth above this floor",
            f"Distributable CF: {distributable_cash_flow/1e9:.2f}B",
            f"Implied P/E at EPV: {implied_pe:.1f}x",
        ]
        
        if growth_priced_in > 50:
            analysis.append(f"High growth expectations ({growth_priced_in:.0f}%) - verify sustainability")
        elif growth_priced_in < 0:
            analysis.append(f"Trading below zero-growth value - potential value opportunity")
        
        if warnings:
            analysis.extend([f"Note: {w}" for w in warnings])
        
        confidence = "High" if 0 < growth_priced_in < 30 else ("Medium" if 0 < growth_priced_in < 50 else "Low")
        
        return ValuationResult(
            method=self.method_name,
            fair_value=round(epv_per_share, 2),
            current_price=stock.current_price,
            premium_discount=round(premium_discount, 1),
            assessment=self._assess(epv_per_share, stock.current_price),
            details={
                "implied_pe": round(implied_pe, 2),
                "growth_priced_in": round(growth_priced_in, 1),
                "maintenance_capex_pct": maintenance_pct * 100,
            },
            components={
                "ebit": ebit,
                "nopat": nopat,
                "distributable_cash_flow": distributable_cash_flow,
                "epv_operating": epv_operating,
            },
            analysis=analysis,
            confidence=confidence,
            fair_value_range=ValuationRange(
                low=round(epv_low, 2),
                base=round(epv_per_share, 2),
                high=round(epv_high, 2)
            ),
            applicability="Applicable" if distributable_cash_flow > 0 else "Limited",
        )
    
    def _calculate_epv_sensitivity(
        self, stock, revenue, operating_margin, tax_rate, depreciation,
        capex, maintenance_pct, cost_of_capital, shares, net_debt
    ):
        if operating_margin <= 0 or cost_of_capital <= 0:
            return 0
        
        ebit = revenue * operating_margin
        nopat = ebit * (1 - tax_rate)
        excess_depreciation = depreciation * (0.5 * tax_rate)
        maintenance_capex = capex * maintenance_pct
        distributable_cash_flow = nopat - maintenance_capex + excess_depreciation
        
        if distributable_cash_flow <= 0:
            return 0
        
        epv_operating = distributable_cash_flow / cost_of_capital
        equity_value = epv_operating - net_debt
        return equity_value / shares if shares > 0 else 0
