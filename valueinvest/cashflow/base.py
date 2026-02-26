"""
Core data structures for Free Cash Flow (FCF) analysis.

This module provides dataclasses for:
- CashFlowRecord: Single year FCF data
- CashFlowSummary: Aggregated summary with key metrics
- CashFlowFetchResult: Result container for fetch operations

Key FCF metrics:
- FCF Yield: FCF / Market Cap (similar to earnings yield)
- FCF Margin: FCF / Revenue
- FCF/Net Income: Quality of earnings
- SBC-adjusted FCF: True FCF after stock-based compensation
"""
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional, Dict
from enum import Enum

from valueinvest.news.base import Market


class FCFQuality(Enum):
    """Quality rating for Free Cash Flow."""

    EXCELLENT = "excellent"  # FCF > Net Income, high margins
    GOOD = "good"  # FCF >= 80% of Net Income
    ACCEPTABLE = "acceptable"  # FCF >= 50% of Net Income
    POOR = "poor"  # FCF < 50% of Net Income
    NEGATIVE = "negative"  # Negative FCF


class FCFTrend(Enum):
    """Trend direction for FCF over time."""

    IMPROVING = "improving"  # FCF growing
    STABLE = "stable"  # FCF relatively flat
    DECLINING = "declining"  # FCF shrinking
    VOLATILE = "volatile"  # FCF inconsistent


@dataclass
class CashFlowRecord:
    """Single year cash flow data."""

    ticker: str
    market: Market
    fiscal_year: int

    # Core cash flow data
    operating_cash_flow: float = 0.0  # 经营活动现金流
    capital_expenditure: float = 0.0  # 资本支出 (CapEx)
    free_cash_flow: float = 0.0  # 自由现金流 = OCF - CapEx

    # SBC adjustment
    stock_based_comp: float = 0.0  # 股权激励 (SBC)
    true_fcf: float = 0.0  # SBC调整后FCF = FCF - SBC

    # Income statement data for comparison
    net_income: float = 0.0  # 净利润
    revenue: float = 0.0  # 营业收入
    ebitda: float = 0.0  # EBITDA

    # Other cash flow items
    depreciation: float = 0.0  # 折旧
    amortization: float = 0.0  # 摊销
    interest_paid: float = 0.0  # 利息支出
    taxes_paid: float = 0.0  # 税费支出

    # Share data
    shares_outstanding: float = 0.0  # 股数

    # Metadata
    source: str = ""
    report_date: Optional[date] = None

    @property
    def fcf_per_share(self) -> float:
        """FCF per share."""
        if self.shares_outstanding > 0:
            return self.free_cash_flow / self.shares_outstanding
        return 0.0

    @property
    def true_fcf_per_share(self) -> float:
        """SBC-adjusted FCF per share."""
        if self.shares_outstanding > 0:
            return self.true_fcf / self.shares_outstanding
        return 0.0

    @property
    def fcf_margin(self) -> float:
        """FCF as percentage of revenue."""
        if self.revenue > 0:
            return (self.free_cash_flow / self.revenue) * 100
        return 0.0

    @property
    def true_fcf_margin(self) -> float:
        """SBC-adjusted FCF margin."""
        if self.revenue > 0:
            return (self.true_fcf / self.revenue) * 100
        return 0.0

    @property
    def fcf_to_net_income(self) -> float:
        """FCF / Net Income ratio - quality of earnings indicator."""
        if self.net_income > 0:
            return self.free_cash_flow / self.net_income
        return 0.0

    @property
    def sbc_as_pct_of_fcf(self) -> float:
        """SBC as percentage of FCF."""
        if self.free_cash_flow > 0:
            return (self.stock_based_comp / self.free_cash_flow) * 100
        return 0.0

    @property
    def sbc_as_pct_of_revenue(self) -> float:
        """SBC as percentage of revenue."""
        if self.revenue > 0:
            return (self.stock_based_comp / self.revenue) * 100
        return 0.0

    @property
    def capex_as_pct_of_revenue(self) -> float:
        """CapEx as percentage of revenue."""
        if self.revenue > 0:
            return (abs(self.capital_expenditure) / self.revenue) * 100
        return 0.0


@dataclass
class CashFlowSummary:
    """Aggregated summary of cash flow analysis."""

    ticker: str
    market: Market
    period_years: int

    # Latest year data
    latest_fcf: float = 0.0
    latest_true_fcf: float = 0.0
    latest_revenue: float = 0.0
    latest_net_income: float = 0.0

    # Key metrics
    fcf_yield: float = 0.0  # FCF / Market Cap
    fcf_margin: float = 0.0  # FCF / Revenue
    fcf_per_share: float = 0.0  # FCF per share
    true_fcf_yield: float = 0.0  # SBC-adjusted FCF / Market Cap
    true_fcf_margin: float = 0.0  # SBC-adjusted FCF / Revenue

    # Quality metrics
    fcf_to_net_income: float = 0.0  # FCF / Net Income
    sbc_as_pct_of_fcf: float = 0.0  # SBC / FCF
    sbc_impact_on_fcf: float = 0.0  # How much SBC reduces FCF (%)

    # Trend analysis
    fcf_cagr: float = 0.0  # FCF compound growth rate
    revenue_cagr: float = 0.0  # Revenue CAGR for context
    fcf_trend: FCFTrend = FCFTrend.STABLE
    fcf_quality: FCFQuality = FCFQuality.ACCEPTABLE

    # Multi-year data
    yearly_fcf: Dict[int, float] = field(default_factory=dict)
    yearly_true_fcf: Dict[int, float] = field(default_factory=dict)
    yearly_revenue: Dict[int, float] = field(default_factory=dict)
    yearly_sbc: Dict[int, float] = field(default_factory=dict)
    yearly_capex: Dict[int, float] = field(default_factory=dict)

    # Counts
    record_count: int = 0
    positive_fcf_years: int = 0
    negative_fcf_years: int = 0

    # Market data
    market_cap: float = 0.0
    shares_outstanding: float = 0.0
    current_price: float = 0.0

    @property
    def has_fcf_data(self) -> bool:
        """Check if FCF data is available."""
        return self.latest_fcf != 0 or len(self.yearly_fcf) > 0

    @property
    def is_fcf_positive(self) -> bool:
        """Check if latest FCF is positive."""
        return self.latest_fcf > 0

    @property
    def is_fcf_quality_good(self) -> bool:
        """Check if FCF quality is good or excellent."""
        return self.fcf_quality in (FCFQuality.EXCELLENT, FCFQuality.GOOD)

    @property
    def sbc_is_material(self) -> bool:
        """Check if SBC is material (>10% of FCF)."""
        return self.sbc_as_pct_of_fcf > 10

    @property
    def avg_fcf(self) -> float:
        """Average FCF over the period."""
        if not self.yearly_fcf:
            return self.latest_fcf
        return sum(self.yearly_fcf.values()) / len(self.yearly_fcf)

    @property
    def avg_true_fcf(self) -> float:
        """Average SBC-adjusted FCF over the period."""
        if not self.yearly_true_fcf:
            return self.latest_true_fcf
        return sum(self.yearly_true_fcf.values()) / len(self.yearly_true_fcf)

    @property
    def fcf_consistency(self) -> float:
        """Percentage of years with positive FCF."""
        if self.record_count == 0:
            return 0.0
        return (self.positive_fcf_years / self.record_count) * 100


@dataclass
class CashFlowFetchResult:
    """Result from cash flow data fetch operation."""

    success: bool
    ticker: str
    market: Market
    source: str

    records: List[CashFlowRecord] = field(default_factory=list)
    summary: Optional[CashFlowSummary] = None
    errors: List[str] = field(default_factory=list)

    # Context
    market_cap: Optional[float] = None
    shares_outstanding: Optional[float] = None
    current_price: Optional[float] = None

    @property
    def has_records(self) -> bool:
        """Check if any records were fetched."""
        return len(self.records) > 0

    @property
    def latest_record(self) -> Optional[CashFlowRecord]:
        """Get the most recent cash flow record."""
        if not self.records:
            return None
        return sorted(self.records, key=lambda r: r.fiscal_year, reverse=True)[0]

    @property
    def fcf_trend_records(self) -> List[CashFlowRecord]:
        """Get records sorted by year for trend analysis."""
        return sorted(self.records, key=lambda r: r.fiscal_year)
