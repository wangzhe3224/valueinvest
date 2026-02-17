"""
Graham Valuation Methods
"""
import math
from .base import BaseValuation, ValuationResult, ValuationRange, FieldRequirement


class GrahamNumber(BaseValuation):
    method_name = "Graham Number"
    
    required_fields = [
        FieldRequirement("eps", "Earnings Per Share", is_critical=True, min_value=0.01),
        FieldRequirement("bvps", "Book Value Per Share", is_critical=True, min_value=0.01),
        FieldRequirement("current_price", "Current Stock Price", is_critical=True, min_value=0.01),
    ]
    
    best_for = ["Defensive investors", "Stable blue-chip stocks", "Conservative valuation"]
    not_for = ["Growth stocks", "Negative earnings companies", "Asset-light businesses"]
    
    def calculate(self, stock) -> ValuationResult:
        is_valid, missing, warnings = self.validate_data(stock)
        if not is_valid:
            return self._create_error_result(stock, f"Missing required data: {', '.join(missing)}", missing)
        
        eps = stock.eps
        bvps = stock.bvps
        
        graham_number = math.sqrt(22.5 * eps * bvps)
        premium_discount = ((graham_number - stock.current_price) / stock.current_price) * 100
        
        graham_low = math.sqrt(20.0 * eps * bvps)
        graham_high = math.sqrt(25.0 * eps * bvps)
        
        analysis = [
            f"Graham's formula for defensive investors (P/E × P/B ≤ 22.5)",
            f"Conservative range: ¥{graham_low:.2f} - ¥{graham_high:.2f}",
        ]
        if warnings:
            analysis.extend([f"Warning: {w}" for w in warnings])
        
        return ValuationResult(
            method=self.method_name,
            fair_value=round(graham_number, 2),
            current_price=stock.current_price,
            premium_discount=round(premium_discount, 1),
            assessment=self._assess(graham_number, stock.current_price),
            details={
                "formula": "√(22.5 × EPS × BVPS)",
                "eps": eps,
                "bvps": bvps,
                "pe_pb_product": eps * bvps * (stock.current_price / eps) * (stock.current_price / bvps) / stock.current_price**2 * 22.5,
            },
            components={"eps": eps, "bvps": bvps},
            analysis=analysis,
            confidence="High" if not warnings else "Medium",
            fair_value_range=ValuationRange(low=round(graham_low, 2), base=round(graham_number, 2), high=round(graham_high, 2)),
            applicability="Applicable" if eps > 0 and bvps > 0 else "Limited",
        )


class GrahamFormula(BaseValuation):
    method_name = "Graham Formula"
    
    required_fields = [
        FieldRequirement("eps", "Earnings Per Share", is_critical=True, min_value=0.01),
        FieldRequirement("growth_rate", "Expected Growth Rate", is_critical=False),
        FieldRequirement("aaa_corporate_yield", "AAA Corporate Bond Yield", is_critical=True, min_value=0.01),
        FieldRequirement("current_price", "Current Stock Price", is_critical=True, min_value=0.01),
    ]
    
    best_for = ["Companies with moderate, predictable growth (5-15%)", "Mature businesses"]
    not_for = ["High-growth stocks (>20%)", "Negative earnings", "Cyclical companies at peak earnings"]
    
    MIN_GROWTH = 0.0
    MAX_GROWTH = 20.0
    
    def __init__(self, growth_cap: float = 20.0):
        self.growth_cap = growth_cap
    
    def calculate(self, stock) -> ValuationResult:
        is_valid, missing, warnings = self.validate_data(stock)
        if not is_valid:
            return self._create_error_result(stock, f"Missing required data: {', '.join(missing)}", missing)
        
        eps = stock.eps
        growth_rate = stock.growth_rate
        aaa_yield = stock.aaa_corporate_yield
        
        original_growth = growth_rate
        if growth_rate < self.MIN_GROWTH:
            growth_rate = self.MIN_GROWTH
            warnings.append(f"Growth rate {original_growth}% capped to {self.MIN_GROWTH}% (minimum)")
        elif growth_rate > self.MAX_GROWTH:
            growth_rate = self.MAX_GROWTH
            warnings.append(f"Growth rate {original_growth}% capped to {self.MAX_GROWTH}% (Graham's max)")
        
        base_value = (8.5 + 2 * growth_rate)
        intrinsic_value = (eps * base_value * 4.4) / aaa_yield
        premium_discount = ((intrinsic_value - stock.current_price) / stock.current_price) * 100
        
        value_low = (eps * (8.5 + 2 * max(growth_rate - 5, 0)) * 4.4) / aaa_yield
        value_high = (eps * (8.5 + 2 * min(growth_rate + 5, self.MAX_GROWTH)) * 4.4) / aaa_yield
        
        analysis = [
            f"Original Graham formula: V = (EPS × (8.5 + 2g) × 4.4) / Y",
            f"Growth rate used: {growth_rate}% (original: {original_growth}%)",
            f"Base P/E equivalent: {8.5 + 2 * growth_rate:.1f}x",
        ]
        if warnings:
            analysis.extend([f"Note: {w}" for w in warnings])
        
        confidence = "High"
        if original_growth != growth_rate:
            confidence = "Medium"
        elif stock.eps <= 0:
            confidence = "Low"
        
        return ValuationResult(
            method=self.method_name,
            fair_value=round(intrinsic_value, 2),
            current_price=stock.current_price,
            premium_discount=round(premium_discount, 1),
            assessment=self._assess(intrinsic_value, stock.current_price),
            details={
                "formula": "V = (EPS × (8.5 + 2g) × 4.4) / Y",
                "growth_rate": growth_rate,
                "original_growth": original_growth,
                "aaa_yield": aaa_yield,
                "base_pe": 8.5 + 2 * growth_rate,
            },
            components={"eps": eps, "growth_rate": growth_rate},
            analysis=analysis,
            confidence=confidence,
            fair_value_range=ValuationRange(low=round(value_low, 2), base=round(intrinsic_value, 2), high=round(value_high, 2)),
            applicability="Applicable" if 0 <= growth_rate <= 20 else "Limited",
        )


class NCAV(BaseValuation):
    method_name = "NCAV (Net-Net)"
    
    required_fields = [
        FieldRequirement("current_assets", "Current Assets", is_critical=True, min_value=0.01),
        FieldRequirement("total_liabilities", "Total Liabilities", is_critical=True),
        FieldRequirement("shares_outstanding", "Shares Outstanding", is_critical=True, min_value=0.01),
        FieldRequirement("current_price", "Current Stock Price", is_critical=True, min_value=0.01),
    ]
    
    best_for = ["Deep value investing", "Distressed companies", "Cigar butt opportunities"]
    not_for = ["Growth companies", "Service businesses", "Companies with significant intangibles"]
    
    def __init__(self, preferred_stock: float = 0.0, safety_margin: float = 0.67):
        self.preferred_stock = preferred_stock
        self.safety_margin = safety_margin
    
    def calculate(self, stock) -> ValuationResult:
        is_valid, missing, warnings = self.validate_data(stock)
        if not is_valid:
            return self._create_error_result(stock, f"Missing required data: {', '.join(missing)}", missing)
        
        current_assets = stock.current_assets
        total_liabilities = stock.total_liabilities
        preferred_stock = self.preferred_stock or stock.extra.get("preferred_stock", 0)
        shares = stock.shares_outstanding
        
        ncav_total = current_assets - total_liabilities - preferred_stock
        ncav_per_share = ncav_total / shares if shares > 0 else 0
        buy_target = ncav_per_share * self.safety_margin
        
        premium_discount = ((ncav_per_share - stock.current_price) / stock.current_price) * 100
        
        analysis = []
        if ncav_total <= 0:
            analysis.append("NCAV is negative - company may have solvency concerns")
            analysis.append("Not a Net-Net candidate")
        elif stock.current_price < buy_target:
            analysis.append(f"*** Net-Net opportunity! Price below {self.safety_margin*100:.0f}% of NCAV ***")
            analysis.append(f"Buy Target: ¥{buy_target:.2f} (2/3 of NCAV)")
        elif stock.current_price < ncav_per_share:
            analysis.append(f"Below full NCAV but above {self.safety_margin*100:.0f}% safety margin")
            analysis.append(f"Margin of safety: {((ncav_per_share - stock.current_price) / ncav_per_share * 100):.1f}%")
        else:
            analysis.append("Price above NCAV - not a cigar butt opportunity")
            analysis.append(f"Premium to NCAV: {((stock.current_price - ncav_per_share) / ncav_per_share * 100):.1f}%")
        
        ncav_liquidating = current_assets * 0.85 - total_liabilities - preferred_stock
        ncav_liquidating_per_share = ncav_liquidating / shares if shares > 0 else 0
        
        value_low = ncav_liquidating_per_share
        value_high = ncav_per_share
        
        return ValuationResult(
            method=self.method_name,
            fair_value=round(ncav_per_share, 2),
            current_price=stock.current_price,
            premium_discount=round(premium_discount, 1),
            assessment=self._assess(ncav_per_share, stock.current_price),
            details={
                "formula": "(Current Assets - Total Liabilities - Preferred Stock) / Shares",
                "current_assets": current_assets,
                "total_liabilities": total_liabilities,
                "preferred_stock": preferred_stock,
                "ncav_total": ncav_total,
            },
            components={
                "ncav_per_share": ncav_per_share,
                "buy_target_2_3": buy_target,
                "liquidating_value": ncav_liquidating_per_share,
            },
            analysis=analysis,
            confidence="Medium",
            fair_value_range=ValuationRange(low=round(value_low, 2), base=round(ncav_per_share, 2), high=round(ncav_per_share, 2)),
            applicability="Applicable" if ncav_total > 0 else "Limited",
        )
