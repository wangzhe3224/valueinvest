"""
Growth Company Valuation Methods
"""
from typing import Optional
from .base import BaseValuation, ValuationResult, ValuationRange, FieldRequirement


class PEG(BaseValuation):
    method_name = "PEG Ratio"
    
    required_fields = [
        FieldRequirement("eps", "Earnings Per Share", is_critical=True, min_value=0.01),
        FieldRequirement("current_price", "Current Stock Price", is_critical=True, min_value=0.01),
        FieldRequirement("growth_rate", "Expected Growth Rate %", is_critical=True),
    ]
    
    best_for = ["Growth companies with positive earnings", "Consistent growers"]
    not_for = ["Negative earnings", "Cyclical companies", "Turnaround situations"]
    
    MIN_GROWTH = 5.0
    MAX_GROWTH = 50.0
    
    def __init__(self, fair_peg: float = 1.0):
        self.fair_peg = fair_peg
    
    def calculate(self, stock) -> ValuationResult:
        is_valid, missing, warnings = self.validate_data(stock)
        if not is_valid:
            return self._create_error_result(stock, f"Missing required data: {', '.join(missing)}", missing)
        
        pe_ratio = stock.pe_ratio
        growth_rate = stock.growth_rate
        
        if growth_rate <= 0:
            return self._create_error_result(stock, f"Growth rate must be positive (got {growth_rate:.1f}%)", [])
        
        original_growth = growth_rate
        if growth_rate < self.MIN_GROWTH:
            warnings.append(f"Low growth ({growth_rate:.1f}%) - PEG less reliable")
        elif growth_rate > self.MAX_GROWTH:
            warnings.append(f"High growth ({growth_rate:.1f}%) - sustainability uncertain")
        
        peg_ratio = pe_ratio / growth_rate if growth_rate > 0 else float('inf')
        
        fair_pe = growth_rate * self.fair_peg
        fair_price = stock.eps * fair_pe if stock.eps > 0 else 0
        
        premium_discount = ((fair_price - stock.current_price) / stock.current_price) * 100 if fair_price > 0 else 0
        
        if peg_ratio < 1.0:
            assessment = "Undervalued"
            peg_analysis = "PEG < 1.0 suggests undervaluation"
        elif peg_ratio < 1.5:
            assessment = "Fair"
            peg_analysis = "PEG 1.0-1.5 suggests fair value"
        elif peg_ratio < 2.0:
            assessment = "Slightly Overvalued"
            peg_analysis = "PEG 1.5-2.0 suggests mild overvaluation"
        else:
            assessment = "Overvalued"
            peg_analysis = "PEG > 2.0 suggests overvaluation"
        
        price_low = stock.eps * (growth_rate * 0.8)
        price_high = stock.eps * (growth_rate * 1.2)
        
        analysis = [
            f"PEG: {peg_ratio:.2f} (P/E {pe_ratio:.1f} ÷ Growth {growth_rate:.1f}%)",
            peg_analysis,
            f"Fair P/E at PEG={self.fair_peg}: {fair_pe:.1f}x",
        ]
        if warnings:
            analysis.extend([f"Note: {w}" for w in warnings])
        
        confidence = "High" if 5 <= growth_rate <= 25 else ("Medium" if growth_rate <= 40 else "Low")
        
        return ValuationResult(
            method=self.method_name,
            fair_value=round(fair_price, 2),
            current_price=stock.current_price,
            premium_discount=round(premium_discount, 1),
            assessment=assessment,
            details={
                "peg_ratio": round(peg_ratio, 2),
                "pe_ratio": round(pe_ratio, 2),
                "growth_rate": growth_rate,
                "fair_peg": self.fair_peg,
            },
            components={"pe_ratio": pe_ratio, "growth_rate": growth_rate},
            analysis=analysis,
            confidence=confidence,
            fair_value_range=ValuationRange(
                low=round(price_low, 2),
                base=round(fair_price, 2),
                high=round(price_high, 2)
            ),
            applicability="Applicable" if 5 <= growth_rate <= 50 else "Limited",
        )


class GARP(BaseValuation):
    method_name = "GARP"
    
    required_fields = [
        FieldRequirement("eps", "Earnings Per Share", is_critical=True, min_value=0.01),
        FieldRequirement("current_price", "Current Stock Price", is_critical=True, min_value=0.01),
        FieldRequirement("growth_rate", "Expected Growth Rate %", is_critical=True),
    ]
    
    best_for = ["Growth at reasonable price", "Quality growth stocks"]
    not_for = ["Value traps", "Speculative growth", "Negative earnings"]
    
    def __init__(self, target_pe: float = 18, years: int = 5, required_return: float = 12.0):
        self.target_pe = target_pe
        self.years = years
        self.required_return = required_return
    
    def calculate(self, stock) -> ValuationResult:
        is_valid, missing, warnings = self.validate_data(stock)
        if not is_valid:
            return self._create_error_result(stock, f"Missing required data: {', '.join(missing)}", missing)
        
        eps = stock.eps
        g = stock.growth_rate / 100
        r = self.required_return / 100
        
        if g <= 0:
            return self._create_error_result(stock, f"Growth rate must be positive for GARP", [])
        
        future_eps = eps * ((1 + g) ** self.years)
        future_price = future_eps * self.target_pe
        present_value = future_price / ((1 + r) ** self.years)
        
        premium_discount = ((present_value - stock.current_price) / stock.current_price) * 100
        
        implied_pe = stock.current_price / eps if eps > 0 else 0
        peg_implied = implied_pe / (g * 100) if g > 0 else float('inf')
        
        pv_low = eps * ((1 + g * 0.8) ** self.years) * self.target_pe * 0.9 / ((1 + r) ** self.years)
        pv_high = eps * ((1 + g * 1.2) ** self.years) * self.target_pe * 1.1 / ((1 + r) ** self.years)
        
        analysis = [
            f"Projects EPS to ¥{future_eps:.2f} in {self.years} years at {g*100:.1f}% growth",
            f"Target exit P/E: {self.target_pe}x → Future price: ¥{future_price:.2f}",
            f"Present value at {r*100:.0f}% required return: ¥{present_value:.2f}",
            f"Implied PEG: {peg_implied:.2f}",
        ]
        if warnings:
            analysis.extend([f"Note: {w}" for w in warnings])
        
        upside = ((present_value - stock.current_price) / stock.current_price) * 100
        confidence = "High" if 0 < g <= 0.25 and upside > 15 else ("Medium" if upside > 0 else "Low")
        
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
                "future_eps": round(future_eps, 2),
                "future_price": round(future_price, 2),
            },
            components={
                "current_eps": eps,
                "future_eps": future_eps,
                "future_price": future_price,
            },
            analysis=analysis,
            confidence=confidence,
            fair_value_range=ValuationRange(
                low=round(pv_low, 2),
                base=round(present_value, 2),
                high=round(pv_high, 2)
            ),
            applicability="Applicable" if g > 0 and eps > 0 else "Limited",
        )


class RuleOf40(BaseValuation):
    method_name = "Rule of 40"
    
    required_fields = [
        FieldRequirement("growth_rate", "Revenue Growth Rate %", is_critical=True),
        FieldRequirement("fcf", "Free Cash Flow", is_critical=True),
        FieldRequirement("revenue", "Revenue", is_critical=True, min_value=0.01),
    ]
    
    best_for = ["SaaS companies", "Subscription businesses", "Software companies"]
    not_for = ["Traditional businesses", "Low-margin industries", "Hardware companies"]
    
    def __init__(self, min_score: float = 40.0):
        self.min_score = min_score
    
    def calculate(self, stock) -> ValuationResult:
        is_valid, missing, warnings = self.validate_data(stock)
        if not is_valid:
            return self._create_error_result(stock, f"Missing required data: {', '.join(missing)}", missing)
        
        revenue_growth = stock.growth_rate
        fcf_margin = (stock.fcf / stock.revenue) * 100 if stock.revenue > 0 else 0
        
        score = revenue_growth + fcf_margin
        passes = score >= self.min_score
        
        if score >= 50:
            assessment = "Excellent"
            quality_analysis = "Exceptional: Growth + FCF margin > 50%"
        elif score >= 40:
            assessment = "Healthy"
            quality_analysis = "Passes Rule of 40: Sustainable growth profile"
        elif score >= 30:
            assessment = "Acceptable"
            quality_analysis = "Near Rule of 40: Monitor for improvement"
        elif score >= 20:
            assessment = "Weak"
            quality_analysis = "Below Rule of 40: Growth or profitability concerns"
        else:
            assessment = "Poor"
            quality_analysis = "Fails Rule of 40: Significant issues"
        
        fair_value = stock.current_price
        
        analysis = [
            f"Score: {score:.1f} = Growth {revenue_growth:.1f}% + FCF Margin {fcf_margin:.1f}%",
            quality_analysis,
            f"Passes Rule of {self.min_score:.0f}: {'Yes' if passes else 'No'}",
        ]
        
        if revenue_growth > 50 and fcf_margin < 0:
            analysis.append("High growth but negative FCF - ensure path to profitability")
        elif revenue_growth < 10 and fcf_margin > 30:
            analysis.append("Mature business with strong FCF - consider dividend/buyback potential")
        
        if warnings:
            analysis.extend([f"Note: {w}" for w in warnings])
        
        confidence = "High" if stock.fcf > 0 and revenue_growth > 0 else "Medium"
        
        return ValuationResult(
            method=self.method_name,
            fair_value=fair_value,
            current_price=stock.current_price,
            premium_discount=0,
            assessment=assessment,
            details={
                "score": round(score, 1),
                "growth": revenue_growth,
                "fcf_margin": round(fcf_margin, 1),
                "passes": passes,
            },
            components={"revenue_growth": revenue_growth, "fcf_margin": fcf_margin},
            analysis=analysis,
            confidence=confidence,
            fair_value_range=None,
            applicability="Applicable" if stock.revenue > 0 else "Limited",
        )
