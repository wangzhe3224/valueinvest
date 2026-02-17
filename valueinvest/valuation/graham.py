"""
Graham Valuation Methods
"""
import math
from .base import BaseValuation, ValuationResult


class GrahamNumber(BaseValuation):
    method_name = "Graham Number"
    
    def calculate(self, stock) -> ValuationResult:
        eps = stock.eps
        bvps = stock.bvps
        
        if eps <= 0 or bvps <= 0:
            return ValuationResult(
                method=self.method_name,
                fair_value=0,
                current_price=stock.current_price,
                premium_discount=0,
                assessment="N/A - Negative EPS or BVPS",
                details={"eps": eps, "bvps": bvps},
                analysis=["Cannot calculate: EPS or BVPS is negative or zero"]
            )
        
        graham_number = math.sqrt(22.5 * eps * bvps)
        premium_discount = ((graham_number - stock.current_price) / stock.current_price) * 100
        
        return ValuationResult(
            method=self.method_name,
            fair_value=round(graham_number, 2),
            current_price=stock.current_price,
            premium_discount=round(premium_discount, 1),
            assessment=self._assess(graham_number, stock.current_price),
            details={"formula": "√(22.5 × EPS × BVPS)", "eps": eps, "bvps": bvps},
            components={"eps": eps, "bvps": bvps},
            analysis=[f"Best for: Defensive investors, stable blue-chips"]
        )


class GrahamFormula(BaseValuation):
    method_name = "Graham Formula"
    
    def calculate(self, stock) -> ValuationResult:
        eps = stock.eps
        growth_rate = stock.growth_rate
        aaa_yield = stock.aaa_corporate_yield
        
        if aaa_yield <= 0:
            return ValuationResult(
                method=self.method_name,
                fair_value=0,
                current_price=stock.current_price,
                premium_discount=0,
                assessment="N/A - Invalid AAA yield"
            )
        
        intrinsic_value = (eps * (8.5 + 2 * growth_rate) * 4.4) / aaa_yield
        premium_discount = ((intrinsic_value - stock.current_price) / stock.current_price) * 100
        
        return ValuationResult(
            method=self.method_name,
            fair_value=round(intrinsic_value, 2),
            current_price=stock.current_price,
            premium_discount=round(premium_discount, 1),
            assessment=self._assess(intrinsic_value, stock.current_price),
            details={"formula": "V = (EPS × (8.5 + 2g) × 4.4) / Y", "growth_rate": growth_rate, "aaa_yield": aaa_yield},
            components={"eps": eps, "growth_rate": growth_rate},
            analysis=[f"Best for: Companies with moderate, predictable growth"]
        )


class NCAV(BaseValuation):
    method_name = "NCAV (Net-Net)"
    
    def calculate(self, stock) -> ValuationResult:
        current_assets = stock.current_assets
        total_liabilities = stock.total_liabilities
        shares = stock.shares_outstanding
        
        if shares <= 0:
            return ValuationResult(
                method=self.method_name,
                fair_value=0,
                current_price=stock.current_price,
                premium_discount=0,
                assessment="N/A - Invalid shares outstanding"
            )
        
        ncav_total = current_assets - total_liabilities
        ncav_per_share = ncav_total / shares
        buy_target = ncav_per_share * 0.67
        
        premium_discount = ((ncav_per_share - stock.current_price) / stock.current_price) * 100
        
        analysis = []
        if stock.current_price < buy_target:
            analysis.append("*** Net-Net opportunity! Price below 2/3 NCAV ***")
        elif stock.current_price < ncav_per_share:
            analysis.append("Below NCAV but above 2/3 safety line")
        else:
            analysis.append("Price above NCAV - not a cigar butt opportunity")
        
        return ValuationResult(
            method=self.method_name,
            fair_value=round(ncav_per_share, 2),
            current_price=stock.current_price,
            premium_discount=round(premium_discount, 1),
            assessment=self._assess(ncav_per_share, stock.current_price),
            details={"formula": "(Current Assets - Total Liabilities) / Shares"},
            components={"ncav_per_share": ncav_per_share, "buy_target_2_3": buy_target},
            analysis=analysis
        )
