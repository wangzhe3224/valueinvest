"""
Core data structures for insider trading information.

This module provides dataclasses for:
- InsiderTrade: Individual insider transaction
- InsiderSummary: Aggregated summary over a period
- InsiderFetchResult: Result container for fetch operations
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional
from enum import Enum

# Re-use Market from news module
from valueinvest.news.base import Market


class TradeType(Enum):
    """Type of insider transaction."""
    BUY = "buy"
    SELL = "sell"
    GRANT = "grant"          # Stock/option grant
    EXERCISE = "exercise"    # Option exercise
    GIFT = "gift"            # Gift transfer
    OTHER = "other"


class InsiderTitle(Enum):
    """Insider's position/title in the company."""
    CEO = "CEO"
    CFO = "CFO"
    COO = "COO"
    CHAIRMAN = "Chairman"
    DIRECTOR = "Director"
    OFFICER = "Officer"
    VP = "VP"
    OTHER = "Other"
    UNKNOWN = "Unknown"


@dataclass
class InsiderTrade:
    """Single insider transaction record."""
    ticker: str
    insider_name: str
    title: InsiderTitle
    trade_type: TradeType
    trade_date: date
    shares: float                  # Number of shares traded
    price: float                   # Price per share
    value: float                   # Total value (shares × price)
    market: Market
    
    # Optional fields
    shares_owned_after: Optional[float] = None  # Holdings after trade
    filing_date: Optional[date] = None          # SEC filing date (may differ from trade date)
    source: str = ""                            # Data source identifier
    url: str = ""                               # Link to filing/source
    raw_data: dict = field(default_factory=dict)  # Original data for reference
    
    @property
    def is_buy(self) -> bool:
        """Check if this is a buy transaction."""
        return self.trade_type == TradeType.BUY
    
    @property
    def is_sell(self) -> bool:
        """Check if this is a sell transaction."""
        return self.trade_type == TradeType.SELL
    
    @property
    def is_key_insider(self) -> bool:
        """Check if trade is by CEO, CFO, or Chairman."""
        return self.title in (InsiderTitle.CEO, InsiderTitle.CFO, InsiderTitle.CHAIRMAN)
    
    @property
    def age_days(self) -> int:
        """Days since trade date."""
        return (date.today() - self.trade_date).days


@dataclass
class InsiderSummary:
    """Aggregated summary of insider trading activity."""
    ticker: str
    market: Market
    period_days: int
    
    # Trade counts
    total_trades: int = 0
    buy_count: int = 0
    sell_count: int = 0
    other_count: int = 0
    
    # Share volume
    buy_shares: float = 0.0
    sell_shares: float = 0.0
    net_shares: float = 0.0
    
    # Value volume
    buy_value: float = 0.0
    sell_value: float = 0.0
    net_value: float = 0.0
    
    # Insider participation
    unique_insiders: int = 0
    key_insider_trades: int = 0  # CEO/CFO/Chairman trades
    
    # Sentiment indicator
    sentiment: str = "neutral"  # bullish/bearish/neutral
    
    @property
    def buy_ratio(self) -> float:
        """Ratio of buy value to total value."""
        total = self.buy_value + self.sell_value
        if total == 0:
            return 0.0
        return self.buy_value / total
    
    @property
    def has_activity(self) -> bool:
        """Check if there was any insider activity."""
        return self.total_trades > 0
    
    @property
    def is_bullish(self) -> bool:
        """Check if insider activity is bullish (more buying than selling)."""
        return self.net_shares > 0 or self.net_value > 0
    
    @property
    def is_bearish(self) -> bool:
        """Check if insider activity is bearish (more selling than buying)."""
        return self.net_shares < 0 or self.net_value < 0


@dataclass
class InsiderFetchResult:
    """Result from insider trading fetch operation."""
    success: bool
    ticker: str
    market: Market
    source: str
    trades: List[InsiderTrade] = field(default_factory=list)
    summary: Optional[InsiderSummary] = None
    errors: List[str] = field(default_factory=list)
    
    @property
    def has_trades(self) -> bool:
        """Check if any trades were fetched."""
        return len(self.trades) > 0
    
    @property
    def recent_trades(self) -> List[InsiderTrade]:
        """Get trades from the last 30 days."""
        cutoff = date.today()
        from datetime import timedelta
        cutoff = cutoff - timedelta(days=30)
        return [t for t in self.trades if t.trade_date >= cutoff]
    
    @property
    def key_insider_trades(self) -> List[InsiderTrade]:
        """Get trades by key insiders (CEO/CFO/Chairman)."""
        return [t for t in self.trades if t.is_key_insider]
