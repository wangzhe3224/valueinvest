"""
A-share news fetcher using AKShare.

Fetches news from East Money (东方财富) via AKShare library.
"""
from datetime import datetime
from typing import List, Optional

from .base import BaseNewsFetcher
from ..base import Market, NewsItem, Guidance


class AKShareNewsFetcher(BaseNewsFetcher):
    """Fetch news for A-share stocks using AKShare."""
    
    market = Market.A_SHARE
    
    @property
    def source_name(self) -> str:
        return "akshare"
    
    def fetch_news(
        self,
        ticker: str,
        days: int = 30,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[NewsItem]:
        import akshare as ak
        
        start_dt, end_dt = self._get_date_range(days, start_date, end_date)
        news_items = []
        
        try:
            df = ak.stock_news_em(symbol=ticker)
            
            if df is None or df.empty:
                return news_items
            
            for _, row in df.iterrows():
                pub_date = self._parse_date(row.get("发布时间", ""))
                
                if pub_date and start_dt <= pub_date <= end_dt:
                    item = NewsItem(
                        ticker=ticker,
                        title=str(row.get("新闻标题", "")),
                        content=str(row.get("新闻内容", "")),
                        source="eastmoney",
                        publish_date=pub_date,
                        market=Market.A_SHARE,
                        url=str(row.get("新闻链接", "")),
                    )
                    news_items.append(item)
            
        except Exception as e:
            raise RuntimeError(f"AKShare news fetch failed: {e}") from e
        
        return news_items
    
    def fetch_guidance(self, ticker: str) -> List[Guidance]:
        return []
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        if not date_str:
            return None
        
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%Y年%m月%d日 %H:%M",
            "%Y年%m月%d日",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(str(date_str).strip(), fmt)
            except ValueError:
                continue
        
        return None
