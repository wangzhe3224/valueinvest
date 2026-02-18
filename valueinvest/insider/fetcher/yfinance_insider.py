"""
US stock insider trading fetcher using yfinance.

Fetches insider transactions from Yahoo Finance.
"""
from datetime import datetime, date
from typing import List, Optional

from .base import BaseInsiderFetcher
from ..base import InsiderTrade, InsiderFetchResult, InsiderSummary, TradeType, InsiderTitle
from valueinvest.news.base import Market


class YFinanceInsiderFetcher(BaseInsiderFetcher):
    market = Market.US
    
    @property
    def source_name(self) -> str:
        return "yfinance"
    
    def fetch_insider_trades(
        self,
        ticker: str,
        days: int = 90,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> InsiderFetchResult:
        import yfinance as yf
        
        start_dt, end_dt = self._get_date_range(days, start_date, end_date)
        start_date_only = start_dt.date() if hasattr(start_dt, 'date') else start_dt
        end_date_only = end_dt.date() if hasattr(end_dt, 'date') else end_dt
        
        trades: List[InsiderTrade] = []
        errors = []
        
        try:
            stock = yf.Ticker(ticker)
            insider_purchases = stock.insider_purchases
            insider_roster = stock.insider_roster_holders
            
            if insider_purchases is not None and not insider_purchases.empty:
                for _, row in insider_purchases.iterrows():
                    trade_date = self._parse_date(row.get("Start Date"))
                    if trade_date is None:
                        continue
                    
                    if not (start_date_only <= trade_date <= end_date_only):
                        continue
                    
                    insider_name = str(row.get("Insider", "Unknown"))
                    title = self._parse_title(row.get("Position", ""))
                    shares = float(row.get("Shares", 0))
                    price = float(row.get("Cost", 0)) / shares if shares > 0 else 0.0
                    value = float(row.get("Cost", 0))
                    trade_type = TradeType.BUY if value > 0 else TradeType.SELL
                    
                    trade = InsiderTrade(
                        ticker=ticker,
                        insider_name=insider_name,
                        title=title,
                        trade_type=trade_type,
                        trade_date=trade_date,
                        shares=abs(shares),
                        price=abs(price) if price else 0.0,
                        value=abs(value),
                        market=Market.US,
                        source="yfinance",
                        raw_data=row.to_dict() if hasattr(row, 'to_dict') else {},
                    )
                    trades.append(trade)
            
            if insider_roster is not None and not insider_roster.empty:
                for _, row in insider_roster.iterrows():
                    insider_name = str(row.get("Name", "Unknown"))
                    title = self._parse_title(row.get("Position", ""))
                    shares = float(row.get("Shares", 0))
                    
                    if shares > 0:
                        trade = InsiderTrade(
                            ticker=ticker,
                            insider_name=insider_name,
                            title=title,
                            trade_type=TradeType.OTHER,
                            trade_date=date.today(),
                            shares=shares,
                            price=0.0,
                            value=0.0,
                            market=Market.US,
                            source="yfinance_holdings",
                            raw_data=row.to_dict() if hasattr(row, 'to_dict') else {},
                        )
                        trades.append(trade)
            
        except Exception as e:
            errors.append(f"yfinance insider fetch failed: {e}")
        
        trades.sort(key=lambda t: t.trade_date, reverse=True)
        
        summary = None
        if trades:
            summary = self._calculate_summary(trades, ticker, Market.US, days)
        
        return InsiderFetchResult(
            success=len(errors) == 0 or len(trades) > 0,
            ticker=ticker,
            market=Market.US,
            source=self.source_name,
            trades=trades,
            summary=summary,
            errors=errors,
        )
    
    def _parse_date(self, value) -> Optional[date]:
        if value is None:
            return None
        if hasattr(value, 'date'):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y"]:
                try:
                    return datetime.strptime(value[:19], fmt).date()
                except ValueError:
                    continue
        return None
    
    def _parse_title(self, title_str: str) -> InsiderTitle:
        if not title_str:
            return InsiderTitle.UNKNOWN
        
        title_lower = str(title_str).lower()
        
        if "ceo" in title_lower or "chief executive" in title_lower:
            return InsiderTitle.CEO
        if "cfo" in title_lower or "chief financial" in title_lower:
            return InsiderTitle.CFO
        if "coo" in title_lower or "chief operating" in title_lower:
            return InsiderTitle.COO
        if "chairman" in title_lower or "chair" in title_lower:
            return InsiderTitle.CHAIRMAN
        if "director" in title_lower:
            return InsiderTitle.DIRECTOR
        if "officer" in title_lower:
            return InsiderTitle.OFFICER
        if "vp" in title_lower or "vice president" in title_lower:
            return InsiderTitle.VP
        
        return InsiderTitle.OTHER
