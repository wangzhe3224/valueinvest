"""
Core data structures for industry analysis.

This module provides dataclasses for:
- PeerCompany: Individual peer company data
- IndustryMetrics: Industry average metrics
- IndustryFundFlow: Industry fund flow data
- IndustrySummary: Aggregated industry analysis
- IndustryFetchResult: Complete fetch result
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum


class IndustryTrend(Enum):
    """Industry trend classification."""

    STRONG_UP = "strong_up"  # Strong uptrend (>3% avg change)
    UP = "up"  # Uptrend (1-3% avg change)
    NEUTRAL = "neutral"  # Sideways (-1% to 1%)
    DOWN = "down"  # Downtrend (-3% to -1%)
    STRONG_DOWN = "strong_down"  # Strong downtrend (<-3%)


class FundFlowSentiment(Enum):
    """Fund flow sentiment classification."""

    INFLOW = "inflow"  # Net capital inflow
    OUTFLOW = "outflow"  # Net capital outflow
    BALANCED = "balanced"  # Balanced flow


@dataclass
class PeerCompany:
    """Single peer company in the same industry."""

    ticker: str
    name: str
    market_cap: float = 0.0
    pe_ratio: float = 0.0
    pb_ratio: float = 0.0
    roe: float = 0.0
    revenue: float = 0.0
    net_income: float = 0.0
    current_price: float = 0.0
    change_pct: float = 0.0
    rank_in_industry: int = 0
    source: str = ""

    @property
    def is_profitable(self) -> bool:
        """Check if company is profitable."""
        return self.net_income > 0

    @property
    def valuation_quality(self) -> str:
        """Simple valuation quality indicator."""
        if self.pe_ratio <= 0:
            return "unprofitable"
        elif self.pe_ratio < 15:
            return "undervalued"
        elif self.pe_ratio < 30:
            return "fair"
        else:
            return "expensive"


@dataclass
class IndustryMetrics:
    """Industry average metrics calculated from peers."""

    avg_pe: float = 0.0
    avg_pb: float = 0.0
    avg_roe: float = 0.0
    median_pe: float = 0.0
    median_pb: float = 0.0
    total_market_cap: float = 0.0
    company_count: int = 0
    avg_change_pct: float = 0.0

    # Additional metrics
    avg_revenue: float = 0.0
    avg_net_income: float = 0.0
    profitable_count: int = 0
    profitable_ratio: float = 0.0

    @property
    def has_data(self) -> bool:
        """Check if metrics contain valid data."""
        return self.company_count > 0


@dataclass
class IndustryFundFlow:
    """Industry fund flow data."""

    net_inflow: float = 0.0  # Net inflow amount
    main_inflow: float = 0.0  # Main force inflow
    main_outflow: float = 0.0  # Main force outflow
    retail_inflow: float = 0.0  # Retail inflow
    retail_outflow: float = 0.0  # Retail outflow
    sentiment: FundFlowSentiment = FundFlowSentiment.BALANCED
    rank: int = 0  # Fund flow ranking among all industries
    period: str = "今日"  # Period (今日, 5日, 10日)

    @property
    def net_main_flow(self) -> float:
        """Net main force flow."""
        return self.main_inflow - self.main_outflow

    @property
    def net_retail_flow(self) -> float:
        """Net retail flow."""
        return self.retail_inflow - self.retail_outflow


@dataclass
class IndustrySummary:
    """Aggregated industry analysis summary."""

    industry_name: str  # Industry name
    industry_code: str = ""  # Industry code (if available)
    trend: IndustryTrend = IndustryTrend.NEUTRAL
    metrics: Optional[IndustryMetrics] = None
    fund_flow: Optional[IndustryFundFlow] = None
    leading_stock: str = ""  # Top gainer ticker
    leading_stock_name: str = ""  # Top gainer name
    lagging_stock: str = ""  # Top loser ticker
    lagging_stock_name: str = ""  # Top loser name
    period_days: int = 30

    @property
    def has_metrics(self) -> bool:
        """Check if metrics are available."""
        return self.metrics is not None and self.metrics.has_data

    @property
    def has_fund_flow(self) -> bool:
        """Check if fund flow data is available."""
        return self.fund_flow is not None


@dataclass
class IndustryFetchResult:
    """Complete industry data fetch result."""

    success: bool
    ticker: str
    market: str
    source: str

    # Core data
    industry_name: str = ""
    industry_code: str = ""
    sector: str = ""  # Broader sector (for US stocks)
    summary: Optional[IndustrySummary] = None
    peers: List[PeerCompany] = field(default_factory=list)

    # Comparison analysis
    ticker_rank_in_peers: int = 0  # Target stock rank among peers
    ticker_percentile: float = 0.0  # Target stock percentile

    # Metadata
    fetched_at: datetime = field(default_factory=datetime.now)
    errors: List[str] = field(default_factory=list)

    @property
    def has_data(self) -> bool:
        """Check if any industry data was fetched."""
        return bool(self.industry_name)

    @property
    def peer_count(self) -> int:
        """Number of peer companies."""
        return len(self.peers)

    @property
    def has_peers(self) -> bool:
        """Check if peer data is available."""
        return len(self.peers) > 0

    @property
    def has_comparison(self) -> bool:
        """Check if comparison data is available."""
        return self.ticker_rank_in_peers > 0

    def get_top_peers(self, n: int = 5) -> List[PeerCompany]:
        """Get top N peers by market cap."""
        sorted_peers = sorted(self.peers, key=lambda x: x.market_cap, reverse=True)
        return sorted_peers[:n]

    def get_similar_sized_peers(
        self, market_cap: float, tolerance: float = 0.3
    ) -> List[PeerCompany]:
        """Get peers with similar market cap within tolerance."""
        if tolerance <= 0:
            return []
        lower = market_cap * (1 - tolerance)
        upper = market_cap * (1 + tolerance)
        return [p for p in self.peers if lower <= p.market_cap <= upper]
