"""Base data classes for ROIC vs WACC analysis."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ROICResult:
    """Result of ROIC calculation."""

    nopat: float
    invested_capital: float
    roic: float  # percentage
    components: Dict[str, float] = field(default_factory=dict)
    method: str = "ROIC"
    confidence: str = "Medium"

    def to_summary(self) -> str:
        lines = [
            f"ROIC: {self.roic:.2f}%",
            f"NOPAT: {self.nopat:,.0f}",
            f"Invested Capital: {self.invested_capital:,.0f}",
            f"Method: {self.method}",
            f"Confidence: {self.confidence}",
        ]
        return "\n".join(lines)


@dataclass
class WACCResult:
    """Result of WACC calculation."""

    cost_of_equity: float  # percentage
    cost_of_debt: float  # percentage
    equity_weight: float  # fraction (e.g., 0.7)
    debt_weight: float  # fraction (e.g., 0.3)
    wacc: float  # percentage
    beta_used: Optional[float] = None
    risk_free_rate: Optional[float] = None
    equity_risk_premium: Optional[float] = None
    tax_rate_used: Optional[float] = None
    method: str = "WACC"
    confidence: str = "Medium"

    def to_summary(self) -> str:
        lines = [
            f"WACC: {self.wacc:.2f}%",
            f"Cost of Equity: {self.cost_of_equity:.2f}%",
            f"Cost of Debt: {self.cost_of_debt:.2f}%",
            f"Equity Weight: {self.equity_weight:.1%}",
            f"Debt Weight: {self.debt_weight:.1%}",
            f"Method: {self.method}",
            f"Confidence: {self.confidence}",
        ]
        if self.beta_used is not None:
            lines.append(f"Beta: {self.beta_used:.2f}")
        if self.risk_free_rate is not None:
            lines.append(f"Risk-Free Rate: {self.risk_free_rate:.2f}%")
        return "\n".join(lines)


@dataclass
class EconomicProfitResult:
    """Result of economic profit analysis (ROIC vs WACC)."""

    ticker: str
    roic_result: ROICResult
    wacc_result: WACCResult
    roic_wacc_spread: float  # percentage points (ROIC - WACC)
    economic_profit: float  # absolute value (invested_capital * (ROIC - WACC) / 100)
    economic_profit_margin: float  # percentage
    value_created: bool
    years_to_double: Optional[float]  # years for invested capital to double at spread rate
    analysis: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_summary(self) -> str:
        lines = [
            f"=== {self.ticker} Economic Profit Analysis ===",
            f"ROIC: {self.roic_result.roic:.2f}%",
            f"WACC: {self.wacc_result.wacc:.2f}%",
            f"Spread: {self.roic_wacc_spread:+.2f}pp",
            f"Economic Profit: {self.economic_profit:,.0f}",
            f"Value Created: {self.value_created}",
        ]
        if self.years_to_double is not None:
            lines.append(f"Years to Double IC: {self.years_to_double:.1f}")
        if self.warnings:
            lines.append(f"Warnings: {'; '.join(self.warnings)}")
        return "\n".join(lines)

    def __str__(self) -> str:
        verdict = "Value Creator" if self.value_created else "Value Destroyer"
        parts = [
            f"{self.ticker}: {verdict}",
            f"ROIC={self.roic_result.roic:.2f}%, WACC={self.wacc_result.wacc:.2f}%, "
            f"Spread={self.roic_wacc_spread:+.2f}pp",
        ]
        if self.years_to_double is not None:
            parts.append(f"Years to Double IC: {self.years_to_double:.1f}")
        return " | ".join(parts)
