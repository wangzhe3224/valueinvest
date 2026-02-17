"""
Valuation Engine - Unified interface for all valuation methods.
"""
from typing import List, Dict, Any, Optional
from .base import ValuationResult
from .graham import GrahamNumber, GrahamFormula, NCAV
from .dcf import DCF, ReverseDCF
from .epv import EPV
from .ddm import DDM, TwoStageDDM
from .growth import PEG, GARP, RuleOf40
from .bank import PBValuation, ResidualIncome
from .magic_formula import MagicFormula


class ValuationEngine:
    DEFAULT_METHODS = [
        "graham_number",
        "graham_formula", 
        "ncav",
        "dcf",
        "epv",
        "ddm",
        "two_stage_ddm",
        "peg",
        "garp",
        "magic_formula",
    ]
    
    BANK_METHODS = [
        "graham_number",
        "graham_formula",
        "dcf",
        "epv",
        "ddm",
        "two_stage_ddm",
        "pb",
        "residual_income",
    ]
    
    DIVIDEND_METHODS = [
        "ddm",
        "two_stage_ddm",
        "graham_number",
        "graham_formula",
        "epv",
    ]
    
    GROWTH_METHODS = [
        "dcf",
        "reverse_dcf",
        "peg",
        "garp",
        "rule_of_40",
        "graham_formula",
        "magic_formula",
    ]
    
    def __init__(self):
        self._methods = {
            "graham_number": GrahamNumber(),
            "graham_formula": GrahamFormula(),
            "ncav": NCAV(),
            "dcf": DCF(),
            "reverse_dcf": ReverseDCF(),
            "epv": EPV(),
            "ddm": DDM(),
            "two_stage_ddm": TwoStageDDM(),
            "peg": PEG(),
            "garp": GARP(),
            "rule_of_40": RuleOf40(),
            "pb": PBValuation(),
            "residual_income": ResidualIncome(),
            "magic_formula": MagicFormula(),
        }
    
    def run_single(self, stock, method: str, **kwargs) -> ValuationResult:
        if method not in self._methods:
            raise ValueError(f"Unknown method: {method}. Available: {list(self._methods.keys())}")
        
        valuator = self._methods[method]
        
        if kwargs:
            if method == "dcf":
                valuator = DCF(
                    growth_1_5=kwargs.get("growth_1_5"),
                    growth_6_10=kwargs.get("growth_6_10"),
                    terminal_growth=kwargs.get("terminal_growth"),
                    discount_rate=kwargs.get("discount_rate"),
                )
            elif method == "ddm":
                valuator = DDM(required_return=kwargs.get("required_return"))
            elif method == "two_stage_ddm":
                valuator = TwoStageDDM(
                    growth_stage1=kwargs.get("growth_stage1", 5.0),
                    stage1_years=kwargs.get("stage1_years", 5),
                    growth_stage2=kwargs.get("growth_stage2", 2.0),
                    required_return=kwargs.get("required_return"),
                )
            elif method == "pb":
                valuator = PBValuation(
                    cost_of_equity=kwargs.get("cost_of_equity", 10.0),
                    sustainable_growth=kwargs.get("sustainable_growth", 2.0),
                )
            elif method == "residual_income":
                valuator = ResidualIncome(
                    cost_of_equity=kwargs.get("cost_of_equity", 10.0),
                    years=kwargs.get("years", 10),
                    terminal_roe=kwargs.get("terminal_roe", 8.0),
                )
        
        return valuator.calculate(stock)
    
    def run_multiple(self, stock, methods: List[str] = None, **kwargs) -> List[ValuationResult]:
        if methods is None:
            methods = self.DEFAULT_METHODS
        
        results = []
        for method in methods:
            try:
                result = self.run_single(stock, method, **kwargs)
                results.append(result)
            except Exception as e:
                results.append(ValuationResult(
                    method=method,
                    fair_value=0,
                    current_price=stock.current_price,
                    premium_discount=0,
                    assessment=f"Error: {str(e)}",
                ))
        
        return results
    
    def run_bank(self, stock, **kwargs) -> List[ValuationResult]:
        return self.run_multiple(stock, self.BANK_METHODS, **kwargs)
    
    def run_dividend(self, stock, **kwargs) -> List[ValuationResult]:
        return self.run_multiple(stock, self.DIVIDEND_METHODS, **kwargs)
    
    def run_growth(self, stock, **kwargs) -> List[ValuationResult]:
        return self.run_multiple(stock, self.GROWTH_METHODS, **kwargs)
    
    def run_all(self, stock, **kwargs) -> List[ValuationResult]:
        return self.run_multiple(stock, list(self._methods.keys()), **kwargs)
    
    def summary(self, results: List[ValuationResult]) -> Dict[str, Any]:
        valid_results = [r for r in results if r.fair_value > 0]
        
        if not valid_results:
            return {
                "average_value": 0,
                "median_value": 0,
                "min_value": 0,
                "max_value": 0,
                "undervalued_count": 0,
                "overvalued_count": 0,
                "fair_count": 0,
            }
        
        values = [r.fair_value for r in valid_results]
        current_price = results[0].current_price if results else 0
        
        undervalued = sum(1 for r in valid_results if r.premium_discount > 15)
        overvalued = sum(1 for r in valid_results if r.premium_discount < -15)
        fair = len(valid_results) - undervalued - overvalued
        
        return {
            "average_value": sum(values) / len(values),
            "median_value": sorted(values)[len(values) // 2],
            "min_value": min(values),
            "max_value": max(values),
            "undervalued_count": undervalued,
            "overvalued_count": overvalued,
            "fair_count": fair,
            "current_price": current_price,
            "average_premium_discount": sum(r.premium_discount for r in valid_results) / len(valid_results),
        }
    
    def get_available_methods(self) -> List[str]:
        return list(self._methods.keys())
