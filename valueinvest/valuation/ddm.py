"""
Dividend Discount Model
"""
from typing import Optional
from .base import BaseValuation, ValuationResult, ValuationRange, FieldRequirement


class DDM(BaseValuation):
    method_name = "DDM (Gordon Growth)"
    
    required_fields = [
        FieldRequirement("dividend_per_share", "Dividend Per Share", is_critical=True, min_value=0.01),
        FieldRequirement("dividend_growth_rate", "Dividend Growth Rate %", is_critical=True),
        FieldRequirement("cost_of_capital", "Cost of Capital %", is_critical=True),
        FieldRequirement("current_price", "Current Stock Price", is_critical=True, min_value=0.01),
    ]
    
    best_for = ["Stable dividend payers", "Utilities", "REITs", "Mature companies"]
    not_for = ["Non-dividend stocks", "High-growth companies", "Companies with volatile dividends"]
    
    MAX_GROWTH_RATE = 15.0
    
    def __init__(self, required_return: Optional[float] = None):
        self.required_return = required_return
    
    def calculate(self, stock) -> ValuationResult:
        is_valid, missing, warnings = self.validate_data(stock)
        if not is_valid:
            return self._create_error_result(stock, f"Missing required data: {', '.join(missing)}", missing)
        
        dividend = stock.dividend_per_share
        g = stock.dividend_growth_rate / 100
        r = (self.required_return if self.required_return is not None else stock.cost_of_capital) / 100
        
        if dividend <= 0:
            return self._create_error_result(stock, "Dividend must be positive for DDM", ["dividend_per_share"])
        
        if g >= r:
            return self._create_error_result(
                stock,
                f"Growth rate ({g*100:.1f}%) must be less than required return ({r*100:.1f}%)",
                []
            )
        
        if g > self.MAX_GROWTH_RATE / 100:
            warnings.append(f"High dividend growth ({g*100:.1f}%) - sustainability uncertain")
        
        next_dividend = dividend * (1 + g)
        intrinsic_value = next_dividend / (r - g)
        
        premium_discount = ((intrinsic_value - stock.current_price) / stock.current_price) * 100
        
        current_yield = (dividend / stock.current_price) * 100
        fair_yield = (next_dividend / intrinsic_value) * 100 if intrinsic_value > 0 else 0
        
        iv_low = next_dividend / (r + 0.02 - max(g - 0.02, 0)) if r + 0.02 > max(g - 0.02, 0) else 0
        iv_high = next_dividend / (r - 0.02 - g) if r - 0.02 > g else intrinsic_value * 1.5
        
        analysis = [
            f"Formula: P = D₁ / (r - g) = {next_dividend:.2f} / ({r*100:.1f}% - {g*100:.1f}%)",
            f"Current yield: {current_yield:.2f}%",
            f"Fair yield: {fair_yield:.2f}%",
        ]
        
        payout_ratio = stock.payout_ratio if hasattr(stock, 'payout_ratio') else 0
        if payout_ratio > 80:
            analysis.append(f"Warning: High payout ratio ({payout_ratio:.0f}%) - dividend growth may be limited")
        
        if current_yield > fair_yield * 1.5:
            analysis.append("Current yield significantly above fair yield - potential undervaluation or dividend cut risk")
        
        if warnings:
            analysis.extend([f"Note: {w}" for w in warnings])
        
        confidence = "High" if 0 < g < 0.08 and payout_ratio < 70 else ("Medium" if g < 0.12 else "Low")
        
        return ValuationResult(
            method=self.method_name,
            fair_value=round(intrinsic_value, 2),
            current_price=stock.current_price,
            premium_discount=round(premium_discount, 1),
            assessment=self._assess(intrinsic_value, stock.current_price),
            details={
                "formula": "P = D / (r - g)",
                "dividend": dividend,
                "next_dividend": next_dividend,
                "growth_rate": g * 100,
                "required_return": r * 100,
                "current_yield": current_yield,
                "fair_yield": fair_yield,
            },
            components={
                "next_dividend": next_dividend,
                "current_yield": current_yield,
                "fair_yield": fair_yield,
            },
            analysis=analysis,
            confidence=confidence,
            fair_value_range=ValuationRange(
                low=round(iv_low, 2),
                base=round(intrinsic_value, 2),
                high=round(iv_high, 2)
            ),
            applicability="Applicable" if dividend > 0 and g < r else "Limited",
        )


class TwoStageDDM(BaseValuation):
    method_name = "Two-Stage DDM"
    
    required_fields = [
        FieldRequirement("dividend_per_share", "Dividend Per Share", is_critical=True, min_value=0.01),
        FieldRequirement("cost_of_capital", "Cost of Capital %", is_critical=True),
        FieldRequirement("current_price", "Current Stock Price", is_critical=True, min_value=0.01),
    ]
    
    best_for = ["Dividend growth stocks", "Transitioning companies", "Moderate growth dividend payers"]
    not_for = ["Non-dividend stocks", "Very high growth companies", "Distressed companies"]
    
    def __init__(
        self,
        growth_stage1: float = 5.0,
        stage1_years: int = 5,
        growth_stage2: float = 2.0,
        required_return: Optional[float] = None,
    ):
        self.growth_stage1 = growth_stage1
        self.stage1_years = stage1_years
        self.growth_stage2 = growth_stage2
        self.required_return = required_return
    
    def calculate(self, stock) -> ValuationResult:
        is_valid, missing, warnings = self.validate_data(stock)
        if not is_valid:
            return self._create_error_result(stock, f"Missing required data: {', '.join(missing)}", missing)
        
        current_dividend = stock.dividend_per_share
        g1 = self.growth_stage1 / 100
        g2 = self.growth_stage2 / 100
        r = (self.required_return if self.required_return is not None else stock.cost_of_capital) / 100
        
        if current_dividend <= 0:
            return self._create_error_result(stock, "Dividend must be positive", ["dividend_per_share"])
        
        if r <= g2:
            return self._create_error_result(
                stock,
                f"Required return ({r*100:.1f}%) must exceed terminal growth ({g2*100:.1f}%)",
                []
            )
        
        if g1 > 0.15:
            warnings.append(f"High stage 1 growth ({g1*100:.1f}%) - verify sustainability")
        
        pv_dividends = 0
        dividend = current_dividend
        dividends = []
        
        for year in range(1, self.stage1_years + 1):
            dividend *= (1 + g1)
            pv = dividend / ((1 + r) ** year)
            pv_dividends += pv
            dividends.append({"year": year, "dividend": dividend, "pv": pv})
        
        terminal_dividend = dividend * (1 + g2)
        terminal_value = terminal_dividend / (r - g2)
        pv_terminal = terminal_value / ((1 + r) ** self.stage1_years)
        
        intrinsic_value = pv_dividends + pv_terminal
        
        premium_discount = ((intrinsic_value - stock.current_price) / stock.current_price) * 100
        
        iv_low = self._calc_two_stage(stock, current_dividend, g1 - 0.02, g2 - 0.01, r + 0.02)
        iv_high = self._calc_two_stage(stock, current_dividend, g1 + 0.02, g2 + 0.01, r - 0.02)
        
        terminal_pct = (pv_terminal / intrinsic_value * 100) if intrinsic_value > 0 else 0
        
        analysis = [
            f"Stage 1: {g1*100:.1f}% growth for {self.stage1_years} years",
            f"Stage 2: {g2*100:.1f}% perpetual growth (terminal)",
            f"PV of Stage 1 dividends: ¥{pv_dividends:.2f}",
            f"PV of Terminal Value: ¥{pv_terminal:.2f} ({terminal_pct:.0f}% of total)",
        ]
        
        if terminal_pct > 70:
            analysis.append("Warning: High terminal value % - sensitive to terminal growth assumption")
        
        if warnings:
            analysis.extend([f"Note: {w}" for w in warnings])
        
        confidence = "High" if terminal_pct < 60 else ("Medium" if terminal_pct < 75 else "Low")
        
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
                "terminal_value_pct": terminal_pct,
            },
            components={
                "pv_dividends_stage1": pv_dividends,
                "pv_terminal": pv_terminal,
            },
            analysis=analysis,
            confidence=confidence,
            fair_value_range=ValuationRange(
                low=round(iv_low, 2),
                base=round(intrinsic_value, 2),
                high=round(iv_high, 2)
            ),
            applicability="Applicable" if current_dividend > 0 and r > g2 else "Limited",
        )
    
    def _calc_two_stage(self, stock, current_div, g1, g2, r):
        if r <= g2 or g1 <= -1:
            return 0
        
        pv_dividends = 0
        dividend = current_div
        
        for year in range(1, self.stage1_years + 1):
            dividend *= (1 + g1)
            if dividend <= 0:
                return 0
            pv_dividends += dividend / ((1 + r) ** year)
        
        terminal_dividend = dividend * (1 + g2)
        terminal_value = terminal_dividend / (r - g2)
        pv_terminal = terminal_value / ((1 + r) ** self.stage1_years)
        
        return pv_dividends + pv_terminal
