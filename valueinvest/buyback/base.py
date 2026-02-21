"""
Core data structures for buyback/repurchase information.

This module provides dataclasses for:
- BuybackRecord: Individual buyback transaction/announcement
- BuybackSummary: Aggregated summary over a period
- BuybackFetchResult: Result container for fetch operations

For US stocks, buyback data comes from cash flow statement (Repurchase of Capital Stock).
For A-shares, buyback data comes from akshare's stock_repurchase_em API.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional, Dict
from enum import Enum

# Re-use Market from news module
from valueinvest.news.base import Market


class BuybackStatus(Enum):
    """Status of a buyback program."""

    ANNOUNCED = "announced"  # 计划中/已公告
    IN_PROGRESS = "in_progress"  # 实施中
    COMPLETED = "completed"  # 完成实施
    CANCELLED = "cancelled"  # 取消
    UNKNOWN = "unknown"


class BuybackSentiment(Enum):
    """Sentiment classification for buyback activity."""

    AGGRESSIVE = "aggressive"  # 激进回购 (>3% buyback yield)
    MODERATE = "moderate"  # 适度回购 (1-3%)
    MINIMAL = "minimal"  # 少量回购 (<1%)
    NONE = "none"  # 无回购


@dataclass
class BuybackRecord:
    """Single buyback record (announcement or execution)."""

    ticker: str
    market: Market

    # Core data
    announce_date: Optional[date] = None  # 公告日期
    execution_date: Optional[date] = None  # 执行日期 (for US stocks, fiscal year end)

    # Amounts
    shares_repurchased: float = 0.0  # 已回购股数
    amount: float = 0.0  # 已回购金额 (in local currency)
    avg_price: float = 0.0  # 回购均价

    # Plan data (mainly for A-shares)
    planned_shares_low: Optional[float] = None  # 计划回购股数下限
    planned_shares_high: Optional[float] = None  # 计划回购股数上限
    planned_amount_low: Optional[float] = None  # 计划回购金额下限
    planned_amount_high: Optional[float] = None  # 计划回购金额上限

    # Status
    status: BuybackStatus = BuybackStatus.UNKNOWN

    # Price range
    price_low: Optional[float] = None  # 回购价格区间下限
    price_high: Optional[float] = None  # 回购价格区间上限

    # Metadata
    source: str = ""
    raw_data: dict = field(default_factory=dict)

    @property
    def is_completed(self) -> bool:
        """Check if buyback is completed."""
        return self.status == BuybackStatus.COMPLETED

    @property
    def is_active(self) -> bool:
        """Check if buyback is ongoing."""
        return self.status in (BuybackStatus.ANNOUNCED, BuybackStatus.IN_PROGRESS)

    @property
    def completion_rate(self) -> Optional[float]:
        """Calculate completion rate if plan data available."""
        if self.planned_amount_high and self.planned_amount_high > 0:
            return min(self.amount / self.planned_amount_high, 1.0)
        if self.planned_shares_high and self.planned_shares_high > 0:
            return min(self.shares_repurchased / self.planned_shares_high, 1.0)
        return None


@dataclass
class BuybackSummary:
    """Aggregated summary of buyback activity."""

    ticker: str
    market: Market
    period_days: int

    # Execution data
    total_amount: float = 0.0  # 总回购金额
    total_shares: float = 0.0  # 总回购股数

    # Key metrics
    buyback_yield: float = 0.0  # 回购收益率 = 年回购金额 / 市值
    shares_reduction_rate: float = 0.0  # 股份减少率 (年度)

    # Comparison with dividends
    dividend_yield: float = 0.0  # 股息率
    total_shareholder_yield: float = 0.0  # 总股东收益率 = 回购收益率 + 股息率

    # Multi-year data (for trend analysis)
    yearly_amounts: Dict[int, float] = field(default_factory=dict)  # 年度回购金额

    # Count
    record_count: int = 0  # 记录数
    active_programs: int = 0  # 进行中的回购计划

    # Sentiment
    sentiment: BuybackSentiment = BuybackSentiment.NONE

    @property
    def has_buyback(self) -> bool:
        """Check if there is any buyback activity."""
        return self.total_amount > 0 or self.total_shares > 0

    @property
    def is_aggressive(self) -> bool:
        """Check if buyback is aggressive (>3% yield)."""
        return self.buyback_yield > 3.0

    @property
    def exceeds_dividend(self) -> bool:
        """Check if buyback yield exceeds dividend yield."""
        return self.buyback_yield > self.dividend_yield

    @property
    def avg_annual_amount(self) -> float:
        """Calculate average annual buyback amount."""
        if not self.yearly_amounts:
            return self.total_amount
        return sum(self.yearly_amounts.values()) / max(len(self.yearly_amounts), 1)


@dataclass
class BuybackFetchResult:
    """Result from buyback data fetch operation."""

    success: bool
    ticker: str
    market: Market
    source: str

    records: List[BuybackRecord] = field(default_factory=list)
    summary: Optional[BuybackSummary] = None
    errors: List[str] = field(default_factory=list)

    # Additional context
    market_cap: Optional[float] = None  # 市值 (for yield calculation)
    shares_outstanding: Optional[float] = None  # 当前股数

    @property
    def has_records(self) -> bool:
        """Check if any records were fetched."""
        return len(self.records) > 0

    @property
    def recent_records(self) -> List[BuybackRecord]:
        """Get records from the last 90 days."""
        cutoff = date.today()
        from datetime import timedelta

        cutoff = cutoff - timedelta(days=90)
        return [r for r in self.records if r.announce_date and r.announce_date >= cutoff]

    @property
    def active_records(self) -> List[BuybackRecord]:
        """Get active (non-completed) buyback programs."""
        return [r for r in self.records if r.is_active]
