"""
Base classes for valuation methods.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod


@dataclass
class ValuationResult:
    method: str
    fair_value: float
    current_price: float
    premium_discount: float
    assessment: str
    details: Dict[str, Any] = field(default_factory=dict)
    components: Dict[str, float] = field(default_factory=dict)
    analysis: List[str] = field(default_factory=list)
    
    @property
    def margin_of_safety(self) -> float:
        return ((self.fair_value - self.current_price) / self.fair_value) * 100 if self.fair_value > 0 else 0


class BaseValuation(ABC):
    method_name: str = "Base"
    
    @abstractmethod
    def calculate(self, stock) -> ValuationResult:
        pass
    
    def _assess(self, fair_value: float, current_price: float, threshold_high: float = 0.15, threshold_low: float = -0.15) -> str:
        if fair_value <= 0:
            return "N/A"
        premium = ((fair_value - current_price) / current_price) * 100
        if premium > threshold_high:
            return "Undervalued"
        elif premium < threshold_low:
            return "Overvalued"
        else:
            return "Fair"
