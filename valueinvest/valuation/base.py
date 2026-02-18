"""
Base classes for valuation methods.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from abc import ABC, abstractmethod


@dataclass
class ValuationRange:
    """Sensitivity analysis result with low/base/high scenarios."""
    low: float = 0.0
    base: float = 0.0
    high: float = 0.0
    
    @property
    def range_pct(self) -> float:
        """Percentage range from low to high."""
        if self.base == 0:
            return 0.0
        return ((self.high - self.low) / self.base) * 100


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
    confidence: str = "Medium"  # High, Medium, Low, N/A
    fair_value_range: Optional[ValuationRange] = None
    missing_fields: List[str] = field(default_factory=list)
    applicability: str = "Applicable"  # Applicable, Limited, Not Applicable
    
    @property
    def margin_of_safety(self) -> float:
        return ((self.fair_value - self.current_price) / self.fair_value) * 100 if self.fair_value > 0 else 0
    
    @property
    def is_reliable(self) -> bool:
        """Check if the valuation result is reliable (no missing critical fields)."""
        return len(self.missing_fields) == 0 and self.fair_value > 0


@dataclass
class FieldRequirement:
    """Describes a required field for valuation."""
    name: str
    description: str
    is_critical: bool = True  # Critical = valuation fails without it
    min_value: Optional[float] = None
    max_value: Optional[float] = None


class DataValidator:
    """Validates stock data before valuation."""
    
    @staticmethod
    def check_required_fields(stock, requirements: List[FieldRequirement]) -> Tuple[bool, List[str], List[str]]:
        """
        Check if stock has all required fields.
        Returns: (is_valid, missing_fields, warning_fields)
        """
        missing = []
        warnings = []
        
        for req in requirements:
            value = getattr(stock, req.name, None)
            
            if value is None or value == 0:
                if req.is_critical:
                    missing.append(f"{req.name} ({req.description})")
                else:
                    warnings.append(f"{req.name} ({req.description})")
            elif req.min_value is not None and value < req.min_value:
                warnings.append(f"{req.name}={value} < min {req.min_value}")
            elif req.max_value is not None and value > req.max_value:
                warnings.append(f"{req.name}={value} > max {req.max_value}")
        
        return len(missing) == 0, missing, warnings


class BaseValuation(ABC):
    method_name: str = "Base"
    
    # Subclasses should define their requirements
    required_fields: List[FieldRequirement] = []
    
    # Best for / not for descriptions
    best_for: List[str] = []
    not_for: List[str] = []
    
    @abstractmethod
    def calculate(self, stock) -> ValuationResult:
        pass
    
    def validate_data(self, stock) -> Tuple[bool, List[str], List[str]]:
        """Validate stock data against method requirements."""
        if not self.required_fields:
            return True, [], []
        return DataValidator.check_required_fields(stock, self.required_fields)
    
    def _assess(self, fair_value: float, current_price: float, 
                threshold_high: float = 0.15, threshold_low: float = -0.15) -> str:
        if fair_value <= 0 or current_price <= 0:
            return "N/A"
        premium = ((fair_value - current_price) / current_price) * 100
        if premium > threshold_high * 100:
            return "Undervalued"
        elif premium < threshold_low * 100:
            return "Overvalued"
        else:
            return "Fair"
    
    def _create_error_result(self, stock, reason: str, missing_fields: Optional[List[str]] = None) -> ValuationResult:
        """Create a standardized error result."""
        return ValuationResult(
            method=self.method_name,
            fair_value=0,
            current_price=stock.current_price,
            premium_discount=0,
            assessment=f"N/A - {reason}",
            missing_fields=missing_fields or [],
            confidence="N/A",
            applicability="Not Applicable",
            analysis=[f"Cannot calculate: {reason}"]
        )
    
    @classmethod
    def get_applicability_info(cls) -> Dict[str, Any]:
        """Return information about when this method is applicable."""
        return {
            "method": cls.method_name,
            "required_fields": [(f.name, f.description, f.is_critical) for f in cls.required_fields],
            "best_for": cls.best_for,
            "not_for": cls.not_for,
        }
