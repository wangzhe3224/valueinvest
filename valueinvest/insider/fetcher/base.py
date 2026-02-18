"""
Base class for insider trading fetchers.

All market-specific fetchers should inherit from BaseInsiderFetcher.
"""
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Optional, ClassVar

from ..base import InsiderTrade, InsiderSummary, InsiderFetchResult
from valueinvest.news.base import Market


class BaseInsiderFetcher(ABC):
    """Abstract base class for market-specific insider trading fetchers."""
    
    market: ClassVar[Market]
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of this data source."""
        pass
    
    @abstractmethod
    def fetch_insider_trades(
        self,
        ticker: str,
        days: int = 90,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> InsiderFetchResult:
        """
        Fetch insider trades for a given ticker.
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days to look back (default 90)
            start_date: Explicit start date (overrides days)
            end_date: Explicit end date (defaults to now)
            
        Returns:
            InsiderFetchResult with trades and summary
        """
        pass
    
    def _get_date_range(
        self,
        days: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> tuple:
        """Calculate start and end dates for query."""
        if end_date is None:
            end_date = datetime.now()
        
        if start_date is None:
            start_date = end_date - timedelta(days=days)
        
        return start_date, end_date
    
    def _calculate_summary(
        self,
        trades: List[InsiderTrade],
        ticker: str,
        market: Market,
        period_days: int,
    ) -> InsiderSummary:
        from ..base import TradeType
        
        buy_count = 0
        sell_count = 0
        other_count = 0
        buy_shares = 0.0
        sell_shares = 0.0
        buy_value = 0.0
        sell_value = 0.0
        key_trades = 0
        insiders = set()
        
        for trade in trades:
            insiders.add(trade.insider_name)
            
            if trade.is_key_insider:
                key_trades += 1
            
            if trade.trade_type == TradeType.BUY:
                buy_count += 1
                buy_shares += trade.shares
                buy_value += trade.value
            elif trade.trade_type == TradeType.SELL:
                sell_count += 1
                sell_shares += trade.shares
                sell_value += trade.value
            elif trade.trade_type == TradeType.GRANT:
                buy_count += 1
                buy_shares += trade.shares
                buy_value += trade.value
            else:
                other_count += 1
        
        net_shares = buy_shares - sell_shares
        net_value = buy_value - sell_value
        
        if net_value > 0:
            sentiment = "bullish"
        elif net_value < 0:
            sentiment = "bearish"
        else:
            sentiment = "neutral"
        
        return InsiderSummary(
            ticker=ticker,
            market=market,
            period_days=period_days,
            total_trades=len(trades),
            buy_count=buy_count,
            sell_count=sell_count,
            other_count=other_count,
            buy_shares=buy_shares,
            sell_shares=sell_shares,
            net_shares=net_shares,
            buy_value=buy_value,
            sell_value=sell_value,
            net_value=net_value,
            unique_insiders=len(insiders),
            key_insider_trades=key_trades,
            sentiment=sentiment,
        )
