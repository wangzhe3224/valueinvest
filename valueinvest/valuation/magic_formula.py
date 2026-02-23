"""
Magic Formula - Joel Greenblatt's Value Investing Strategy
"""
from .base import BaseValuation, ValuationResult, ValuationRange, FieldRequirement


class MagicFormula(BaseValuation):
    method_name = "Magic Formula"
    
    required_fields = [
        FieldRequirement("ebit", "EBIT (Operating Income)", is_critical=False),
        FieldRequirement("operating_margin", "Operating Margin %", is_critical=False),
        FieldRequirement("revenue", "Revenue", is_critical=False),
        FieldRequirement("net_fixed_assets", "Net Fixed Assets", is_critical=False),
        FieldRequirement("net_working_capital", "Net Working Capital", is_critical=False),
        FieldRequirement("market_cap", "Market Cap", is_critical=True, min_value=0.01),
        FieldRequirement("net_debt", "Net Debt", is_critical=False),
        FieldRequirement("shares_outstanding", "Shares Outstanding", is_critical=True, min_value=0.01),
        FieldRequirement("current_price", "Current Stock Price", is_critical=True, min_value=0.01),
    ]
    
    best_for = ["Quality at reasonable price", "Screening for value stocks"]
    not_for = ["Banks and financials", "Negative earnings", "Asset-light businesses with negative working capital"]
    
    def __init__(self, required_ey: float = 10.0, benchmark_roc: float = 25.0):
        self.required_ey = required_ey
        self.benchmark_roc = benchmark_roc
    
    def calculate(self, stock) -> ValuationResult:
        is_valid, missing, warnings = self.validate_data(stock)
        
        ebit = stock.ebit
        if (ebit is None or ebit <= 0) and stock.operating_margin > 0 and stock.revenue > 0:
            ebit = stock.revenue * (stock.operating_margin / 100)
        
        if ebit is None or ebit <= 0:
            return self._create_error_result(
                stock,
                "EBIT must be positive (either directly provided or calculable from revenue × operating margin)",
                ["ebit"]
            )
        
        ev = stock.enterprise_value
        if ev <= 0:
            ev = stock.market_cap + stock.net_debt
        if ev <= 0:
            return self._create_error_result(stock, "Enterprise Value must be positive", ["enterprise_value"])
        
        invested_capital = stock.net_fixed_assets + stock.net_working_capital
        
        if invested_capital <= 0:
            if stock.net_fixed_assets > 0 and stock.net_working_capital >= 0:
                pass
            else:
                return self._create_error_result(
                    stock,
                    f"Invalid Invested Capital: Net Fixed Assets ({stock.net_fixed_assets/1e9:.2f}B) + NWC ({stock.net_working_capital/1e9:.2f}B) = {invested_capital/1e9:.2f}B",
                    ["net_fixed_assets", "net_working_capital"]
                )
        
        earnings_yield = (ebit / ev) * 100 if ev > 0 else 0
        return_on_capital = (ebit / invested_capital) * 100 if invested_capital > 0 else 0
        
        fair_ev = ebit / (self.required_ey / 100)
        fair_equity = fair_ev - stock.net_debt
        fair_price = fair_equity / stock.shares_outstanding if stock.shares_outstanding > 0 and fair_equity > 0 else 0
        
        if fair_price <= 0:
            return ValuationResult(
                method=self.method_name,
                fair_value=0,
                current_price=stock.current_price,
                premium_discount=0,
                assessment="N/A - Fair price calculation failed",
                details={
                    "earnings_yield": round(earnings_yield, 2),
                    "return_on_capital": round(return_on_capital, 2) if invested_capital > 0 else "N/A",
                },
                analysis=[
                    f"Earnings Yield: {earnings_yield:.1f}%",
                    f"Return on Capital: {return_on_capital:.1f}%" if invested_capital > 0 else "ROC: N/A (negative invested capital)",
                    "Cannot calculate fair price - net debt exceeds fair enterprise value",
                ],
                confidence="Low",
                applicability="Limited",
                missing_fields=missing,
            )
        
        premium_discount = ((fair_price - stock.current_price) / stock.current_price) * 100
        
        ey_pass = earnings_yield >= self.required_ey
        roc_pass = invested_capital > 0 and return_on_capital >= self.benchmark_roc
        
        if ey_pass and roc_pass:
            quality = "High Quality & Cheap"
            quality_analysis = "Passes both criteria - potential Magic Formula candidate"
        elif ey_pass:
            quality = "Cheap but Average Quality"
            quality_analysis = f"Good earnings yield but ROC ({return_on_capital:.1f}%) below benchmark"
        elif roc_pass:
            quality = "Good Quality but Expensive"
            quality_analysis = f"Good ROC but earnings yield ({earnings_yield:.1f}%) below requirement"
        else:
            quality = "Below Thresholds"
            quality_analysis = "Below both EY and ROC thresholds - not a Magic Formula candidate"
        
        fair_price_low = (ebit / (self.required_ey / 100 + 0.03) - stock.net_debt) / stock.shares_outstanding
        fair_price_high = (ebit / (self.required_ey / 100 - 0.03) - stock.net_debt) / stock.shares_outstanding
        
        analysis = [
            f"Earnings Yield (EBIT/EV): {earnings_yield:.1f}% (Required: {self.required_ey}%) - {'PASS' if ey_pass else 'FAIL'}",
            f"Return on Capital: {return_on_capital:.1f}% (Benchmark: {self.benchmark_roc}%) - {'PASS' if roc_pass else 'FAIL'}" if invested_capital > 0 else "ROC: N/A",
            f"Quality Assessment: {quality}",
            quality_analysis,
        ]
        
        if invested_capital > 0 and return_on_capital > 50:
            analysis.append(f"Note: Very high ROC ({return_on_capital:.0f}%) - verify capital base")
        
        if earnings_yield > 15:
            analysis.append(f"Note: Very high EY ({earnings_yield:.0f}%) - check for earnings quality issues")
        
        if warnings:
            analysis.extend([f"Note: {w}" for w in warnings])
        
        confidence = "High" if ey_pass and roc_pass else ("Medium" if ey_pass or roc_pass else "Low")
        
        return ValuationResult(
            method=self.method_name,
            fair_value=round(fair_price, 2),
            current_price=stock.current_price,
            premium_discount=round(premium_discount, 1),
            assessment=self._assess(fair_price, stock.current_price),
            details={
                "earnings_yield": round(earnings_yield, 2),
                "return_on_capital": round(return_on_capital, 2) if invested_capital > 0 else 0,
                "ebit": ebit,
                "enterprise_value": ev,
                "invested_capital": invested_capital,
                "quality_rating": quality,
            },
            components={
                "earnings_yield_pct": round(earnings_yield, 2),
                "roc_pct": round(return_on_capital, 2) if invested_capital > 0 else 0,
            },
            analysis=analysis,
            confidence=confidence,
            fair_value_range=ValuationRange(
                low=round(max(0, fair_price_low), 2),
                base=round(fair_price, 2),
                high=round(fair_price_high, 2)
            ),
            applicability="Applicable" if ebit > 0 and invested_capital > 0 else "Limited",
            missing_fields=missing,
        )
