"""
Valuation Engine - Unified interface for all valuation methods.
"""
from typing import List, Dict, Any, Optional
from .base import ValuationResult
from .graham import GrahamNumber, GrahamFormula, NCAV
from .dcf import DCF, ReverseDCF
from .epv import EPV
from .ddm import DDM, TwoStageDDM
from .growth import PEG, GARP, RuleOf40, EVEBITDA
from .bank import PBValuation, ResidualIncome
from .magic_formula import MagicFormula
from .quality import OwnerEarnings, AltmanZScore


class ValuationEngine:
    DEFAULT_METHODS = [
        "graham_number",
        "graham_formula",
        "ncav",
        "dcf",
        "reverse_dcf",
        "epv",
        "ddm",
        "two_stage_ddm",
        "peg",
        "garp",
        "magic_formula",
        "owner_earnings",
        "ev_ebitda",
        "altman_z",
    ]

    BANK_METHODS = [
        "graham_number",
        "pb",
        "residual_income",
        "ddm",
        "two_stage_ddm",
        "altman_z",
    ]

    DIVIDEND_METHODS = [
        "ddm",
        "two_stage_ddm",
        "graham_number",
        "graham_formula",
        "epv",
        "owner_earnings",
    ]

    GROWTH_METHODS = [
        "dcf",
        "reverse_dcf",
        "peg",
        "garp",
        "rule_of_40",
        "graham_formula",
        "magic_formula",
        "ev_ebitda",
    ]

    VALUE_METHODS = [
        "graham_number",
        "ncav",
        "epv",
        "graham_formula",
        "owner_earnings",
        "altman_z",
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
            "owner_earnings": OwnerEarnings(),
            "ev_ebitda": EVEBITDA(),
            "altman_z": AltmanZScore(),
        }

    def run_single(self, stock, method: str, **kwargs) -> ValuationResult:
        if method not in self._methods:
            raise ValueError(f"Unknown method: {method}. Available: {list(self._methods.keys())}")

        valuator = self._methods[method]

        if kwargs:
            valuator = self._create_custom_valuator(method, kwargs)

        return valuator.calculate(stock)

    def _create_custom_valuator(self, method: str, kwargs: Dict[str, Any]):
        if method == "dcf":
            return DCF(
                growth_1_5=kwargs.get("growth_1_5"),
                growth_6_10=kwargs.get("growth_6_10"),
                terminal_growth=kwargs.get("terminal_growth"),
                discount_rate=kwargs.get("discount_rate"),
            )
        elif method == "ddm":
            return DDM(required_return=kwargs.get("required_return"))
        elif method == "two_stage_ddm":
            return TwoStageDDM(
                growth_stage1=kwargs.get("growth_stage1", 5.0),
                stage1_years=kwargs.get("stage1_years", 5),
                growth_stage2=kwargs.get("growth_stage2", 2.0),
                required_return=kwargs.get("required_return"),
            )
        elif method == "pb":
            return PBValuation(
                cost_of_equity=kwargs.get("cost_of_equity", 10.0),
                sustainable_growth=kwargs.get("sustainable_growth", 2.0),
            )
        elif method == "residual_income":
            return ResidualIncome(
                cost_of_equity=kwargs.get("cost_of_equity", 10.0),
                years=kwargs.get("years", 10),
                terminal_roe=kwargs.get("terminal_roe", 8.0),
            )
        elif method == "epv":
            return EPV(
                maintenance_capex_pct=kwargs.get("maintenance_capex_pct"),
                cost_of_capital=kwargs.get("cost_of_capital"),
            )
        elif method == "garp":
            return GARP(
                target_pe=kwargs.get("target_pe", 18),
                years=kwargs.get("years", 5),
                required_return=kwargs.get("required_return", 12.0),
            )
        elif method == "peg":
            return PEG(fair_peg=kwargs.get("fair_peg", 1.0))
        elif method == "owner_earnings":
            return OwnerEarnings(
                maintenance_capex_pct=kwargs.get("maintenance_capex_pct"),
                cost_of_capital=kwargs.get("cost_of_capital"),
            )
        elif method == "ev_ebitda":
            return EVEBITDA(
                fair_multiple=kwargs.get("fair_multiple"),
                industry=kwargs.get("industry"),
            )
        elif method == "altman_z":
            return AltmanZScore(
                zone_safe=kwargs.get("zone_safe", 2.99),
                zone_distress=kwargs.get("zone_distress", 1.81),
            )
        return self._methods[method]

    def run_multiple(
        self, stock, methods: Optional[List[str]] = None, **kwargs
    ) -> List[ValuationResult]:
        if methods is None:
            methods = self.DEFAULT_METHODS

        results = []
        for method in methods:
            try:
                result = self.run_single(stock, method, **kwargs)
                results.append(result)
            except Exception as e:
                results.append(
                    ValuationResult(
                        method=method,
                        fair_value=0,
                        current_price=stock.current_price,
                        premium_discount=0,
                        assessment=f"Error: {str(e)}",
                        missing_fields=[],
                    )
                )

        return results

    def run_bank(self, stock, **kwargs) -> List[ValuationResult]:
        return self.run_multiple(stock, self.BANK_METHODS, **kwargs)

    def run_dividend(self, stock, **kwargs) -> List[ValuationResult]:
        return self.run_multiple(stock, self.DIVIDEND_METHODS, **kwargs)

    def run_growth(self, stock, **kwargs) -> List[ValuationResult]:
        return self.run_multiple(stock, self.GROWTH_METHODS, **kwargs)

    def run_value(self, stock, **kwargs) -> List[ValuationResult]:
        return self.run_multiple(stock, self.VALUE_METHODS, **kwargs)

    def run_all(self, stock, **kwargs) -> List[ValuationResult]:
        return self.run_multiple(stock, list(self._methods.keys()), **kwargs)

    def get_recommended_methods(self, stock) -> Dict[str, List[str]]:
        recommendations = {
            "primary": [],
            "secondary": [],
            "not_recommended": [],
        }

        has_dividend = stock.dividend_per_share > 0 and stock.dividend_yield > 1.5
        has_fcf = stock.fcf > 0
        has_positive_earnings = stock.eps > 0
        is_growth = stock.growth_rate > 10 if stock.growth_rate else False
        is_bank = hasattr(stock, "sectors") and any(
            s in ["银行", "Bank", "Financial", "Insurance"] for s in (stock.sectors or [])
        )
        is_value = stock.pe_ratio < 15 if stock.pe_ratio else False

        if is_bank:
            recommendations["primary"] = ["pb", "residual_income", "ddm", "altman_z"]
            recommendations["secondary"] = ["graham_number", "two_stage_ddm"]
            recommendations["not_recommended"] = [
                "dcf",
                "reverse_dcf",
                "magic_formula",
                "rule_of_40",
            ]
        elif has_dividend and not is_growth:
            recommendations["primary"] = ["ddm", "two_stage_ddm", "graham_number", "owner_earnings"]
            recommendations["secondary"] = ["epv", "graham_formula"]
            recommendations["not_recommended"] = ["rule_of_40"]
        elif is_growth and has_fcf:
            recommendations["primary"] = ["dcf", "reverse_dcf", "peg", "garp", "ev_ebitda"]
            recommendations["secondary"] = ["graham_formula", "magic_formula"]
            recommendations["not_recommended"] = ["ncav", "ddm"]
        elif is_value and has_positive_earnings:
            recommendations["primary"] = [
                "graham_number",
                "graham_formula",
                "epv",
                "owner_earnings",
            ]
            recommendations["secondary"] = ["ncav", "magic_formula", "altman_z"]
            recommendations["not_recommended"] = ["rule_of_40", "peg"]
        else:
            recommendations["primary"] = ["graham_formula", "epv"]
            recommendations["secondary"] = ["dcf"] if has_fcf else ["graham_number"]
            recommendations["not_recommended"] = []

        return recommendations

    def run_recommended(self, stock, **kwargs) -> List[ValuationResult]:
        recommendations = self.get_recommended_methods(stock)
        methods = recommendations["primary"] + recommendations["secondary"]
        return self.run_multiple(stock, methods, **kwargs)

    def summary(self, results: List[ValuationResult]) -> Dict[str, Any]:
        valid_results = [r for r in results if r.fair_value > 0 and r.is_reliable]

        if not valid_results:
            return {
                "average_value": 0,
                "median_value": 0,
                "min_value": 0,
                "max_value": 0,
                "undervalued_count": 0,
                "overvalued_count": 0,
                "fair_count": 0,
                "reliable_count": 0,
                "total_methods": len(results),
            }

        values = [r.fair_value for r in valid_results]
        current_price = results[0].current_price if results else 0

        undervalued = sum(1 for r in valid_results if r.premium_discount > 15)
        overvalued = sum(1 for r in valid_results if r.premium_discount < -15)
        fair = len(valid_results) - undervalued - overvalued

        sorted_values = sorted(values)
        mid = len(sorted_values) // 2
        median = (
            sorted_values[mid]
            if len(sorted_values) % 2 == 1
            else (sorted_values[mid - 1] + sorted_values[mid]) / 2
        )

        avg_premium = sum(r.premium_discount for r in valid_results) / len(valid_results)

        return {
            "average_value": sum(values) / len(values),
            "median_value": median,
            "min_value": min(values),
            "max_value": max(values),
            "undervalued_count": undervalued,
            "overvalued_count": overvalued,
            "fair_count": fair,
            "reliable_count": len(valid_results),
            "total_methods": len(results),
            "current_price": current_price,
            "average_premium_discount": avg_premium,
        }

    def get_available_methods(self) -> List[str]:
        return list(self._methods.keys())

    def get_method_info(self, method: str) -> Dict[str, Any]:
        if method not in self._methods:
            raise ValueError(f"Unknown method: {method}")

        valuator = self._methods[method]
        return valuator.get_applicability_info()
