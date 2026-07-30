"""
Core data structures for financial trend & growth-signal analysis.

Provides **quarterly** time-series for 5 metrics and a growth-signal result
layer that mirrors the redflags engine.

Five tracked metrics (all derived as @property on TrendRecord):
    - revenue        (top-line growth)
    - gross_margin   (unit economics / cost structure)
    - net_margin     (profitability that sticks)
    - fcf_yield      (free cash flow / market cap -- real cash, not accounting)
    - ccc            (cash conversion cycle = DIO + DSO - DPO, operating efficiency)

Key concepts:
    - TrendRecord: one quarter of raw + derived data. Income/cashflow items are
      single-quarter period FLOWS (de-YTD'd for yfinance); balance-sheet items
      are quarter-end point-in-time STOCKS.
    - TrendSeries: chronological records + rolling TTM + per-metric extraction.
    - TrendSignal / TrendSignalResult: growth-signal analysis output.

Note on CCC day counts: the quarterly variant uses a 90-day denominator
(single-quarter flows), which differs deliberately from the annual 365-day
variant used elsewhere in the library.
"""
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional
from enum import Enum

from valueinvest.news.base import Market


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #
class TrendMetric(Enum):
    """The five metrics tracked across the quarterly time-series."""

    REVENUE = "revenue"
    GROSS_MARGIN = "gross_margin"
    NET_MARGIN = "net_margin"
    FCF_YIELD = "fcf_yield"
    CCC = "ccc"


class TrendSignalCategory(Enum):
    """Category a trend signal belongs to (used for score grouping)."""

    GROWTH = "growth"  # revenue
    MARGIN = "margin"  # gross + net
    CASH_FLOW = "cash_flow"  # fcf yield
    EFFICIENCY = "efficiency"  # ccc


class TrendDirection(Enum):
    """Qualitative direction of a single signal (severity analog)."""

    STRONG_POSITIVE = "strong_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    STRONG_NEGATIVE = "strong_negative"
    INSUFFICIENT_DATA = "insufficient_data"


class TrendRating(Enum):
    """Overall trend quality rating derived from the composite score."""

    ACCELERATING = "accelerating"  # >= 75
    IMPROVING = "improving"  # 60..75
    STABLE = "stable"  # 40..60
    DETERIORATING = "deteriorating"  # 25..40
    DECLINING = "declining"  # < 25


# Which category each metric rolls up into.
METRIC_CATEGORY = {
    TrendMetric.REVENUE: TrendSignalCategory.GROWTH,
    TrendMetric.GROSS_MARGIN: TrendSignalCategory.MARGIN,
    TrendMetric.NET_MARGIN: TrendSignalCategory.MARGIN,
    TrendMetric.FCF_YIELD: TrendSignalCategory.CASH_FLOW,
    TrendMetric.CCC: TrendSignalCategory.EFFICIENCY,
}


def metric_value(rec: "TrendRecord", metric: TrendMetric) -> float:
    """Extract a metric's value from a record (works for both single-q and TTM)."""
    if metric == TrendMetric.REVENUE:
        return rec.revenue
    if metric == TrendMetric.GROSS_MARGIN:
        return rec.gross_margin
    if metric == TrendMetric.NET_MARGIN:
        return rec.net_margin
    if metric == TrendMetric.FCF_YIELD:
        return rec.fcf_yield
    if metric == TrendMetric.CCC:
        return rec.ccc
    return 0.0


# --------------------------------------------------------------------------- #
# Data layer
# --------------------------------------------------------------------------- #
@dataclass
class TrendRecord:
    """One quarter of trend data.

    Income/cashflow items are single-quarter period FLOWS (de-YTD'd for
    yfinance quarterly_cashflow, which is often year-to-date cumulative).
    Balance-sheet items are quarter-end point-in-time STOCKS (not
    de-accumulated -- they are snapshots, not flows).
    """

    # identity
    ticker: str
    market: Market
    quarter_end: date
    fiscal_year: int
    fiscal_quarter: int  # 1..4

    # P&L -- single-quarter FLOWS
    revenue: float = 0.0
    gross_profit: float = 0.0  # yfinance "Gross Profit"; tushare revenue - oper_cost
    net_income: float = 0.0

    # Cash flow -- single-quarter FLOWS (de-YTD'd)
    operating_cash_flow: float = 0.0
    capex: float = 0.0  # source sign preserved (yfinance negative); see free_cash_flow
    free_cash_flow: float = 0.0  # final FCF (OCF - capital spending), sign = cash direction

    # Balance sheet -- quarter-end STOCKS (point-in-time snapshot)
    inventory: float = 0.0
    accounts_receivable: float = 0.0
    accounts_payable: float = 0.0

    # Share/price -- for approximated historical FCF yield
    shares_outstanding: float = 0.0
    close_price: float = 0.0  # close on (or nearest to) quarter_end

    source: str = ""

    # ---- derived (read-only) ----
    @property
    def cogs(self) -> float:
        """Cost of goods sold. Never read directly from yfinance; derived."""
        return self.revenue - self.gross_profit

    @property
    def gross_margin(self) -> float:  # %
        return (self.gross_profit / self.revenue * 100) if self.revenue > 0 else 0.0

    @property
    def net_margin(self) -> float:  # %
        return (self.net_income / self.revenue * 100) if self.revenue > 0 else 0.0

    # CCC components -- 90-day denominator for single-quarter flows.
    @property
    def dio(self) -> float:  # Days Inventory Outstanding
        return (self.inventory / self.cogs * 90) if self.cogs > 0 else 0.0

    @property
    def dso(self) -> float:  # Days Sales Outstanding
        return (self.accounts_receivable / self.revenue * 90) if self.revenue > 0 else 0.0

    @property
    def dpo(self) -> float:  # Days Payable Outstanding
        return (self.accounts_payable / self.cogs * 90) if self.cogs > 0 else 0.0

    @property
    def ccc(self) -> float:  # Cash Conversion Cycle (days)
        return self.dio + self.dso - self.dpo

    @property
    def market_cap_approx(self) -> float:
        """APPROXIMATION: close_price x shares (ignores dilution)."""
        return self.close_price * self.shares_outstanding

    @property
    def fcf_yield(self) -> float:  # %, APPROXIMATED (see market_cap_approx)
        return (
            (self.free_cash_flow / self.market_cap_approx * 100)
            if self.market_cap_approx > 0
            else 0.0
        )


@dataclass
class TrendSeries:
    """Chronological quarterly records + rolling TTM + per-metric extraction."""

    ticker: str
    market: Market
    source: str
    records: List[TrendRecord] = field(default_factory=list)  # old -> new

    @property
    def n_quarters(self) -> int:
        return len(self.records)

    @property
    def latest(self) -> Optional[TrendRecord]:
        return self.records[-1] if self.records else None

    def quarter_ends(self) -> List[date]:
        return [r.quarter_end for r in self.records]

    def values(self, metric: TrendMetric) -> List[float]:
        """Single-quarter values for a metric (one per record)."""
        return [metric_value(r, metric) for r in self.records]

    def ttm_records(self) -> List[TrendRecord]:
        """Rolling TTM records, one per quarter where >= 4 quarters exist.

        Flows (revenue/gross_profit/net_income/ocf/capex/fcf) = sum of the last
        4 single-quarter flows; stocks (inventory/ar/ap) + shares + close_price
        = that quarter-end's snapshot. Margins/ccc/fcf_yield are then recomputed
        by the TrendRecord @property from this TTM flow + snapshot mix.
        """
        out: List[TrendRecord] = []
        recs = self.records
        for i in range(3, len(recs)):  # need 4 quarters: i-3..i
            window = recs[i - 3 : i + 1]
            snap = recs[i]
            out.append(
                TrendRecord(
                    ticker=snap.ticker,
                    market=snap.market,
                    quarter_end=snap.quarter_end,
                    fiscal_year=snap.fiscal_year,
                    fiscal_quarter=snap.fiscal_quarter,
                    revenue=sum(w.revenue for w in window),
                    gross_profit=sum(w.gross_profit for w in window),
                    net_income=sum(w.net_income for w in window),
                    operating_cash_flow=sum(w.operating_cash_flow for w in window),
                    capex=sum(w.capex for w in window),
                    free_cash_flow=sum(w.free_cash_flow for w in window),
                    inventory=snap.inventory,
                    accounts_receivable=snap.accounts_receivable,
                    accounts_payable=snap.accounts_payable,
                    shares_outstanding=snap.shares_outstanding,
                    close_price=snap.close_price,
                    source=snap.source,
                )
            )
        return out

    @property
    def latest_ttm(self) -> Optional[TrendRecord]:
        ttms = self.ttm_records()
        return ttms[-1] if ttms else None

    def ttm_values(self, metric: TrendMetric) -> List[float]:
        """TTM values for a metric (one per quarter with >= 4 quarters history)."""
        return [metric_value(r, metric) for r in self.ttm_records()]


@dataclass
class TrendFetchResult:
    """Result from a trend data fetch operation."""

    success: bool
    ticker: str
    market: Market
    source: str
    series: Optional[TrendSeries] = None
    current_market_cap: Optional[float] = None  # reference point from info
    current_shares: Optional[float] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def has_data(self) -> bool:
        return self.series is not None and self.series.n_quarters > 0


# --------------------------------------------------------------------------- #
# Signal layer
# --------------------------------------------------------------------------- #
@dataclass
class TrendSignal:
    """A single computed growth signal (mirrors RedFlagSignal)."""

    name: str
    metric: TrendMetric
    category: TrendSignalCategory
    value: float
    score: float  # 0-100, higher = better trend quality
    direction: TrendDirection
    description: str = ""
    is_available: bool = True


@dataclass
class TrendSignalResult:
    """Aggregated growth-signal assessment (mirrors RedFlagResult)."""

    ticker: str
    market: Market
    composite_score: float  # 0-100
    rating: TrendRating

    growth_score: float = 0.0  # REVENUE category average
    margin_score: float = 0.0  # avg(GROSS_MARGIN, NET_MARGIN)
    cash_flow_score: float = 0.0  # FCF_YIELD
    efficiency_score: float = 0.0  # CCC (0 when not applicable)

    signals: List[TrendSignal] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    analysis: List[str] = field(default_factory=list)

    ccc_applicable: bool = True
    period_quarters: int = 0

    @property
    def available_signal_count(self) -> int:
        return sum(1 for s in self.signals if s.is_available)

    def to_summary(self) -> str:
        return (
            f"Trend({self.ticker}): Score={self.composite_score:.0f}/100 | "
            f"Rating={self.rating.value.upper()} | "
            f"Quarters={self.period_quarters}"
        )

    def __str__(self) -> str:
        lines = [self.to_summary()]
        lines.append(
            f"  Growth: {self.growth_score:.0f} | "
            f"Margin: {self.margin_score:.0f} | "
            f"CashFlow: {self.cash_flow_score:.0f} | "
            f"Efficiency: {self.efficiency_score:.0f}"
        )
        for s in self.signals:
            avail = "" if s.is_available else " [N/A]"
            lines.append(
                f"  [{s.metric.value}] {s.name}: "
                f"{s.score:.0f}/100 ({s.direction.value}){avail}"
            )
        for w in self.warnings:
            lines.append(f"  [!] {w}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.to_summary()


# --------------------------------------------------------------------------- #
# Score -> enum thresholds
# --------------------------------------------------------------------------- #
def score_to_trend_rating(score: float) -> TrendRating:
    if score >= 75:
        return TrendRating.ACCELERATING
    if score >= 60:
        return TrendRating.IMPROVING
    if score >= 40:
        return TrendRating.STABLE
    if score >= 25:
        return TrendRating.DETERIORATING
    return TrendRating.DECLINING


def score_to_direction(score: float) -> TrendDirection:
    if score >= 80:
        return TrendDirection.STRONG_POSITIVE
    if score >= 60:
        return TrendDirection.POSITIVE
    if score >= 40:
        return TrendDirection.NEUTRAL
    if score >= 20:
        return TrendDirection.NEGATIVE
    return TrendDirection.STRONG_NEGATIVE
