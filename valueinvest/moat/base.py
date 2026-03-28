"""Base dataclasses and enums for Economic Moat analysis."""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class MoatType(Enum):
    """Types of economic moats."""
    NONE = "none"
    NARROW = "narrow"
    WIDE = "wide"
    VERY_WIDE = "very_wide"


class MoatSignalCategory(Enum):
    """Categories of moat signals."""
    PROFITABILITY = "profitability"
    EFFICIENCY = "efficiency"
    GROWTH = "growth"
    MARKET_POSITION = "market_position"
    FINANCIAL_FORTRESS = "financial_fortress"


class SignalStrength(Enum):
    """Strength of a moat signal."""
    NONE = "none"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


@dataclass
class MoatSignal:
    """A single moat indicator with its assessment."""
    name: str
    category: MoatSignalCategory
    value: float
    score: float  # 0-100
    strength: SignalStrength
    weight: float = 1.0
    description: str = ""
    is_available: bool = True


@dataclass
class MoatResult:
    """Complete moat analysis result."""
    ticker: str
    moat_type: MoatType
    moat_score: float  # 0-100 composite score

    # Category sub-scores
    profitability_score: float = 0.0
    efficiency_score: float = 0.0
    growth_score: float = 0.0
    market_position_score: float = 0.0
    financial_fortress_score: float = 0.0

    # Individual signals
    signals: List[MoatSignal] = field(default_factory=list)

    # Evidence
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    analysis: List[str] = field(default_factory=list)

    @property
    def has_moat(self) -> bool:
        return self.moat_type in (MoatType.NARROW, MoatType.WIDE, MoatType.VERY_WIDE)

    @property
    def available_signal_count(self) -> int:
        return sum(1 for s in self.signals if s.is_available)

    @property
    def total_signal_count(self) -> int:
        return len(self.signals)

    def to_summary(self) -> str:
        return (
            f"Moat({self.ticker}): Score={self.moat_score:.0f}/100 | "
            f"Type={self.moat_type.value.upper()} | "
            f"Signals={self.available_signal_count}/{self.total_signal_count}"
        )

    def __str__(self) -> str:
        lines = [self.to_summary()]
        lines.append(f"  Profitability: {self.profitability_score:.0f} | "
                      f"Efficiency: {self.efficiency_score:.0f} | "
                      f"Growth: {self.growth_score:.0f}")
        lines.append(f"  Market Position: {self.market_position_score:.0f} | "
                      f"Financial Fortress: {self.financial_fortress_score:.0f}")
        for s in self.signals:
            if s.is_available:
                avail = ""
            else:
                avail = " [N/A]"
            lines.append(f"  [{s.category.value}] {s.name}: {s.score:.0f}/100 ({s.strength.value}){avail}")
        if self.strengths:
            lines.append("  Strengths: " + "; ".join(self.strengths[:3]))
        if self.weaknesses:
            lines.append("  Weaknesses: " + "; ".join(self.weaknesses[:3]))
        for w in self.warnings:
            lines.append(f"  [!] {w}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.to_summary()


def _score_to_strength(score: float) -> SignalStrength:
    """Convert 0-100 score to SignalStrength."""
    if score >= 80:
        return SignalStrength.VERY_STRONG
    elif score >= 60:
        return SignalStrength.STRONG
    elif score >= 40:
        return SignalStrength.MODERATE
    elif score >= 20:
        return SignalStrength.WEAK
    else:
        return SignalStrength.NONE


def _score_to_moat_type(score: float) -> MoatType:
    """Convert 0-100 composite score to MoatType."""
    if score >= 75:
        return MoatType.VERY_WIDE
    elif score >= 55:
        return MoatType.WIDE
    elif score >= 35:
        return MoatType.NARROW
    else:
        return MoatType.NONE
