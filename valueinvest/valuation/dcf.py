"""
Discounted Cash Flow Valuation
"""
from typing import Optional
from .base import BaseValuation, ValuationResult, ValuationRange, FieldRequirement


class DCF(BaseValuation):
    method_name = "DCF (10-Year)"
    
    required_fields = [
        FieldRequirement("fcf", "Free Cash Flow", is_critical=True),
        FieldRequirement("shares_outstanding", "Shares Outstanding", is_critical=True, min_value=0.01),
        FieldRequirement("current_price", "Current Stock Price", is_critical=True, min_value=0.01),
        FieldRequirement("net_debt", "Net Debt", is_critical=False),
        FieldRequirement("discount_rate", "Discount Rate (WACC)", is_critical=True),
        FieldRequirement("terminal_growth", "Terminal Growth Rate", is_critical=True),
        FieldRequirement("growth_rate_1_5", "Growth Rate Years 1-5", is_critical=True),
        FieldRequirement("growth_rate_6_10", "Growth Rate Years 6-10", is_critical=True),
    ]
    
    best_for = ["Growth companies with predictable FCF", "Mature businesses", "Cash-generative companies"]
    not_for = ["Banks and financials", "Negative FCF companies", "Early-stage startups"]
    
    def __init__(
        self,
        growth_1_5: Optional[float] = None,
        growth_6_10: Optional[float] = None,
        terminal_growth: Optional[float] = None,
        discount_rate: Optional[float] = None,
    ):
        self.growth_1_5 = growth_1_5
        self.growth_6_10 = growth_6_10
        self.terminal_growth = terminal_growth
        self.discount_rate = discount_rate
    
    def calculate(self, stock) -> ValuationResult:
        is_valid, missing, warnings = self.validate_data(stock)
        if not is_valid:
            return self._create_error_result(stock, f"Missing required data: {', '.join(missing)}", missing)
        
        fcf = stock.fcf
        if fcf <= 0:
            return self._create_error_result(stock, "Free Cash Flow must be positive for DCF", ["fcf"])
        
        shares = stock.shares_outstanding
        net_debt = stock.net_debt
        
        g1 = (self.growth_1_5 if self.growth_1_5 is not None else stock.growth_rate_1_5) / 100
        g2 = (self.growth_6_10 if self.growth_6_10 is not None else stock.growth_rate_6_10) / 100
        g_term = (self.terminal_growth if self.terminal_growth is not None else stock.terminal_growth) / 100
        r = (self.discount_rate if self.discount_rate is not None else stock.discount_rate) / 100
        
        if r <= g_term:
            return self._create_error_result(
                stock, 
                f"Discount rate ({r*100:.1f}%) must be greater than terminal growth ({g_term*100:.1f}%)",
                []
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
        
        value_low = self._run_dcf_sensitivity(stock, fcf, shares, net_debt, g1 - 0.02, g2 - 0.01, g_term - 0.005, r + 0.02)
        value_high = self._run_dcf_sensitivity(stock, fcf, shares, net_debt, g1 + 0.02, g2 + 0.01, g_term + 0.005, r - 0.02)
        
        tv_pct = (pv_terminal / enterprise_value) * 100 if enterprise_value > 0 else 0
        
        analysis = [
            f"10-year DCF with terminal value",
            f"Terminal Value represents {tv_pct:.1f}% of total value",
            f"FCF Year 10: {fcf_year_10/1e9:.2f}B",
        ]
        if tv_pct > 60:
            analysis.append("Warning: Terminal value is >60% of total - consider sensitivity to growth assumptions")
        if warnings:
            analysis.extend([f"Note: {w}" for w in warnings])
        
        confidence = "High" if tv_pct < 50 else ("Medium" if tv_pct < 70 else "Low")
        
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
                "terminal_value_pct": tv_pct,
            },
            components={
                "pv_fcf": total_pv,
                "pv_terminal": pv_terminal,
                "enterprise_value": enterprise_value,
                "equity_value": equity_value,
            },
            analysis=analysis,
            confidence=confidence,
            fair_value_range=ValuationRange(
                low=round(value_low, 2),
                base=round(intrinsic_value, 2),
                high=round(value_high, 2)
            ),
            applicability="Applicable" if fcf > 0 and r > g_term else "Limited",
        )
    
    def _run_dcf_sensitivity(self, stock, fcf, shares, net_debt, g1, g2, g_term, r):
        if r <= g_term or g1 < 0 or fcf <= 0:
            return 0
        
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
        
        return (total_pv + pv_terminal - net_debt) / shares


class ReverseDCF(BaseValuation):
    method_name = "Reverse DCF"
    
    required_fields = [
        FieldRequirement("fcf", "Free Cash Flow", is_critical=True),
        FieldRequirement("shares_outstanding", "Shares Outstanding", is_critical=True, min_value=0.01),
        FieldRequirement("current_price", "Current Stock Price", is_critical=True, min_value=0.01),
        FieldRequirement("net_debt", "Net Debt", is_critical=False),
        FieldRequirement("discount_rate", "Discount Rate", is_critical=True),
        FieldRequirement("terminal_growth", "Terminal Growth Rate", is_critical=True),
    ]
    
    best_for = ["Understanding market expectations", "Growth stocks", "Sanity check on valuations"]
    not_for = ["Negative FCF companies", "Banks and financials"]
    
    MAX_ITERATIONS = 200
    GROWTH_MIN = -10.0
    GROWTH_MAX = 100.0
    TOLERANCE = 0.001
    
    def calculate(self, stock) -> ValuationResult:
        is_valid, missing, warnings = self.validate_data(stock)
        if not is_valid:
            return self._create_error_result(stock, f"Missing required data: {', '.join(missing)}", missing)
        
        current_price = stock.current_price
        fcf = stock.fcf
        shares = stock.shares_outstanding
        net_debt = stock.net_debt
        g_term = stock.terminal_growth / 100
        r = stock.discount_rate / 100
        
        if fcf <= 0:
            return self._create_error_result(stock, "Free Cash Flow must be positive", ["fcf"])
        
        if r <= g_term:
            return self._create_error_result(stock, "Discount rate must exceed terminal growth", [])
        
        target_equity_value = current_price * shares
        target_ev = target_equity_value + net_debt
        
        low, high = self.GROWTH_MIN, self.GROWTH_MAX
        mid = 0.0
        converged = False
        iteration = 0
        
        for iteration in range(self.MAX_ITERATIONS):
            mid = (low + high) / 2
            g1 = mid / 100
            g2 = g1 * 0.5
            
            if g1 <= -1:
                low = mid
                continue
            
            implied_ev = self._calculate_ev(fcf, g1, g2, g_term, r)
            
            if implied_ev <= 0:
                low = mid
                continue
            
            relative_error = abs(implied_ev - target_ev) / target_ev
            
            if relative_error < self.TOLERANCE:
                converged = True
                break
            
            if implied_ev < target_ev:
                low = mid
            else:
                high = mid
            
            if high - low < 0.01:
                converged = True
                break
        
        analysis = [
            f"Market prices in {mid:.1f}% annual growth for years 1-5",
            f"Years 6-10 growth implied at {mid*0.5:.1f}%",
        ]
        
        if not converged:
            analysis.append(f"Warning: Calculation did not fully converge after {self.MAX_ITERATIONS} iterations")
        
        if mid < 0:
            analysis.append("Market expects negative growth - potential value trap or distressed situation")
        elif mid > 30:
            analysis.append(f"High implied growth ({mid:.1f}%) - verify if sustainable")
        elif mid < 5:
            analysis.append(f"Low implied growth ({mid:.1f}%) - mature or declining business expected")
        
        if warnings:
            analysis.extend([f"Note: {w}" for w in warnings])
        
        growth_low = mid - 5
        growth_high = mid + 5
        analysis.append(f"Sensitivity range: {max(0, growth_low):.1f}% to {min(50, growth_high):.1f}% growth")
        
        return ValuationResult(
            method=self.method_name,
            fair_value=current_price,
            current_price=current_price,
            premium_discount=0,
            assessment="Priced in growth",
            details={
                "implied_growth_1_5": round(mid, 1),
                "implied_growth_6_10": round(mid * 0.5, 1),
                "converged": converged,
                "iterations": iteration + 1,
            },
            components={
                "target_equity_value": target_equity_value,
                "target_ev": target_ev,
            },
            analysis=analysis,
            confidence="High" if converged and 0 <= mid <= 30 else ("Medium" if converged else "Low"),
            fair_value_range=ValuationRange(
                low=self._price_at_growth(stock, max(growth_low, 0) / 100, g_term, r),
                base=current_price,
                high=self._price_at_growth(stock, min(growth_high, 50) / 100, g_term, r),
            ) if converged else None,
            applicability="Applicable" if fcf > 0 and converged else "Limited",
        )
    
    def _calculate_ev(self, fcf, g1, g2, g_term, r):
        projected_fcf = fcf
        total_pv = 0
        
        for year in range(1, 11):
            if year <= 5:
                projected_fcf *= (1 + g1)
            else:
                projected_fcf *= (1 + g2)
            
            if projected_fcf <= 0:
                return 0
            total_pv += projected_fcf / ((1 + r) ** year)
        
        fcf_year_10 = projected_fcf
        terminal_value = (fcf_year_10 * (1 + g_term)) / (r - g_term)
        pv_terminal = terminal_value / ((1 + r) ** 10)
        
        return total_pv + pv_terminal
    
    def _price_at_growth(self, stock, g1, g_term, r):
        g2 = g1 * 0.5
        implied_ev = self._calculate_ev(stock.fcf, g1, g2, g_term, r)
        implied_equity = implied_ev - stock.net_debt
        return implied_equity / stock.shares_outstanding if implied_equity > 0 else 0
