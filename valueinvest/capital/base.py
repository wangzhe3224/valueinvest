"""Base dataclasses and enums for Capital Allocation analysis."""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class AllocationRating(Enum):
    """Overall capital allocation rating."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ADEQUATE = "adequate"
    POOR = "poor"
    DESTRUCTIVE = "destructive"


class AllocationCategory(Enum):
    """Categories of capital allocation signals."""
    SHAREHOLDER_RETURN = "shareholder_return"
    REINVESTMENT = "reinvestment"
    BALANCE_SHEET = "balance_sheet"
    DILUTION = "dilution"


class SignalLevel(Enum):
    """Quality level of a capital allocation signal."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ADEQUATE = "adequate"
    POOR = "poor"
    DESTRUCTIVE = "destructive"


@dataclass
class AllocationSignal:
    """A single capital allocation signal."""
    name: str
    category: AllocationCategory
    value: float
    score: float  # 0-100, higher = better allocation
    level: SignalLevel
    description: str = ""
    is_available: bool = True
    benchmark: Optional[float] = None


@dataclass
class CapitalAllocationResult:
    """Complete capital allocation quality result."""
    ticker: str
    overall_score: float  # 0-100
    rating: AllocationRating

    # Category sub-scores
    shareholder_return_score: float = 0.0
    reinvestment_score: float = 0.0
    balance_sheet_score: float = 0.0
    dilution_score: float = 0.0

    # Individual signals
    signals: List[AllocationSignal] = field(default_factory=list)

    # Key metrics summary
    shareholder_yield: float = 0.0
    reinvestment_rate: float = 0.0
    net_dilution_rate: float = 0.0

    # Evidence
    strengths: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    analysis: List[str] = field(default_factory=list)

    @property
    def is_shareholder_friendly(self) -> bool:
        return self.rating in (AllocationRating.EXCELLENT, AllocationRating.GOOD)

    @property
    def available_signal_count(self) -> int:
        return sum(1 for s in self.signals if s.is_available)

    def to_summary(self) -> str:
        return (
            f"CapitalAlloc({self.ticker}): Score={self.overall_score:.0f}/100 | "
            f"Rating={self.rating.value.upper()} | "
            f"ShareholderYield={self.shareholder_yield:.1f}%"
        )

    def __str__(self) -> str:
        lines = [self.to_summary()]
        lines.append(f"  Shareholder Return: {self.shareholder_return_score:.0f} | "
                      f"Reinvestment: {self.reinvestment_score:.0f}")
        lines.append(f"  Balance Sheet: {self.balance_sheet_score:.0f} | "
                      f"Dilution: {self.dilution_score:.0f}")
        for s in self.signals:
            avail = "" if s.is_available else " [N/A]"
            lines.append(f"  [{s.category.value}] {s.name}: {s.score:.0f}/100 ({s.level.value}){avail}")
        if self.strengths:
            lines.append("  Strengths: " + "; ".join(self.strengths[:3]))
        if self.concerns:
            lines.append("  Concerns: " + "; ".join(self.concerns[:3]))
        for w in self.warnings:
            lines.append(f"  [!] {w}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.to_summary()


def _score_to_level(score: float) -> SignalLevel:
    """Convert 0-100 score to SignalLevel."""
    if score >= 80:
        return SignalLevel.EXCELLENT
    elif score >= 60:
        return SignalLevel.GOOD
    elif score >= 40:
        return SignalLevel.ADEQUATE
    elif score >= 20:
        return SignalLevel.POOR
    else:
        return SignalLevel.DESTRUCTIVE


def _score_to_rating(score: float) -> AllocationRating:
    """Convert 0-100 composite score to AllocationRating."""
    if score >= 80:
        return AllocationRating.EXCELLENT
    elif score >= 60:
        return AllocationRating.GOOD
    elif score >= 40:
        return AllocationRating.ADEQUATE
    elif score >= 25:
        return AllocationRating.POOR
    else:
        return AllocationRating.DESTRUCTIVE
