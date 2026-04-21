"""Base dataclasses and enums for Accounting Red Flags analysis."""

from dataclasses import dataclass, field
from typing import List
from enum import Enum


class RiskLevel(Enum):
    CLEAN = "clean"
    MINOR_CONCERNS = "minor_concerns"
    MODERATE_CONCERNS = "moderate_concerns"
    SIGNIFICANT_FLAGS = "significant_flags"
    SEVERE_FLAGS = "severe_flags"


class RedFlagCategory(Enum):
    EARNINGS_QUALITY = "earnings_quality"
    REVENUE_RECOGNITION = "revenue_recognition"
    ASSET_WORKING_CAPITAL = "asset_working_capital"
    CAPITAL_STRUCTURE = "capital_structure"


class RedFlagSeverity(Enum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RedFlagSignal:
    name: str
    category: RedFlagCategory
    value: float
    score: float  # 0-100, higher = more red flags
    severity: RedFlagSeverity
    description: str = ""
    is_available: bool = True


@dataclass
class RedFlagResult:
    ticker: str
    overall_score: float  # 0-100
    risk_level: RiskLevel

    earnings_quality_score: float = 0.0
    revenue_recognition_score: float = 0.0
    asset_working_capital_score: float = 0.0
    capital_structure_score: float = 0.0

    signals: List[RedFlagSignal] = field(default_factory=list)
    triggered_flags: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    analysis: List[str] = field(default_factory=list)

    @property
    def available_signal_count(self) -> int:
        return sum(1 for s in self.signals if s.is_available)

    @property
    def total_signal_count(self) -> int:
        return len(self.signals)

    @property
    def has_flags(self) -> bool:
        return self.risk_level in (
            RiskLevel.MODERATE_CONCERNS,
            RiskLevel.SIGNIFICANT_FLAGS,
            RiskLevel.SEVERE_FLAGS,
        )

    def to_summary(self) -> str:
        return (
            f"RedFlags({self.ticker}): Score={self.overall_score:.0f}/100 | "
            f"Risk={self.risk_level.value.upper()} | "
            f"Flags={len(self.triggered_flags)}"
        )

    def __str__(self) -> str:
        lines = [self.to_summary()]
        lines.append(
            f"  Earnings Quality: {self.earnings_quality_score:.0f} | "
            f"Revenue Recog: {self.revenue_recognition_score:.0f}"
        )
        lines.append(
            f"  Asset/WC: {self.asset_working_capital_score:.0f} | "
            f"Capital Structure: {self.capital_structure_score:.0f}"
        )
        for s in self.signals:
            avail = "" if s.is_available else " [N/A]"
            lines.append(
                f"  [{s.category.value}] {s.name}: "
                f"{s.score:.0f}/100 ({s.severity.value}){avail}"
            )
        if self.triggered_flags:
            lines.append("  Triggered Flags:")
            for flag in self.triggered_flags[:5]:
                lines.append(f"    [!] {flag}")
        for w in self.warnings:
            lines.append(f"  [N/A] {w}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.to_summary()


def _score_to_severity(score: float) -> RedFlagSeverity:
    if score >= 80:
        return RedFlagSeverity.CRITICAL
    elif score >= 60:
        return RedFlagSeverity.HIGH
    elif score >= 40:
        return RedFlagSeverity.MODERATE
    elif score >= 20:
        return RedFlagSeverity.LOW
    else:
        return RedFlagSeverity.NONE


def _score_to_risk_level(score: float) -> RiskLevel:
    if score >= 80:
        return RiskLevel.SEVERE_FLAGS
    elif score >= 60:
        return RiskLevel.SIGNIFICANT_FLAGS
    elif score >= 40:
        return RiskLevel.MODERATE_CONCERNS
    elif score >= 20:
        return RiskLevel.MINOR_CONCERNS
    else:
        return RiskLevel.CLEAN
