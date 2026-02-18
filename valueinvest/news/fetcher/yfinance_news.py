"""
US stock news fetcher using yfinance.

Fetches news and analyst data from Yahoo Finance.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any

from .base import BaseNewsFetcher
from ..base import Market, NewsItem, Guidance, AnalystRating


class YFinanceNewsFetcher(BaseNewsFetcher):
    """Fetch news for US stocks using yfinance."""
    
    market = Market.US
    
    @property
    def source_name(self) -> str:
        return "yfinance"
    
    def fetch_news(
        self,
        ticker: str,
        days: int = 30,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[NewsItem]:
        import yfinance as yf
        
        start_dt, end_dt = self._get_date_range(days, start_date, end_date)
        news_items = []
        
        try:
            stock = yf.Ticker(ticker)
            news_list = stock.news
            
            if not news_list:
                return news_items
            
            for article in news_list:
                pub_timestamp = article.get("content", {}).get("pubDate", 0)
                if pub_timestamp:
                    pub_date = datetime.fromtimestamp(pub_timestamp)
                else:
                    pub_date = datetime.now()
                
                if start_dt <= pub_date <= end_dt:
                    content = article.get("content", {})
                    item = NewsItem(
                        ticker=ticker,
                        title=content.get("title", article.get("title", "")),
                        content=content.get("summary", article.get("summary", "")),
                        source=content.get("provider", {}).get("displayName", "yahoo"),
                        publish_date=pub_date,
                        market=Market.US,
                        url=content.get("canonicalUrl", {}).get("url", ""),
                    )
                    news_items.append(item)
            
        except Exception as e:
            raise RuntimeError(f"yfinance news fetch failed: {e}") from e
        
        return news_items
    
    def fetch_guidance(self, ticker: str) -> List[Guidance]:
        import yfinance as yf
        
        guidance_list = []
        
        try:
            stock = yf.Ticker(ticker)
            
            recommendations = self._fetch_recommendations(stock)
            earnings_trend = self._fetch_earnings_trend(stock)
            
            if recommendations or earnings_trend:
                current_year = datetime.now().year
                
                if earnings_trend:
                    for trend in earnings_trend:
                        period = trend.get("period", "")
                        fiscal_year = current_year
                        
                        if "Q1" in period:
                            quarter = 1
                        elif "Q2" in period:
                            quarter = 2
                        elif "Q3" in period:
                            quarter = 3
                        elif "Q4" in period:
                            quarter = 4
                        else:
                            quarter = None
                        
                        guidance = Guidance(
                            ticker=ticker,
                            market=Market.US,
                            fiscal_year=fiscal_year,
                            quarter=quarter,
                            analyst_eps_mean=trend.get("earningsEstimateAvg"),
                            analyst_eps_low=trend.get("earningsEstimateLow"),
                            analyst_eps_high=trend.get("earningsEstimateHigh"),
                            analyst_revenue_mean=trend.get("revenueEstimateAvg"),
                            analyst_revenue_low=trend.get("revenueEstimateLow"),
                            analyst_revenue_high=trend.get("revenueEstimateHigh"),
                            analyst_count=trend.get("numberOfAnalysts", 0),
                            source="yfinance",
                            updated_date=datetime.now(),
                        )
                        guidance_list.append(guidance)
                
                if recommendations:
                    rating_info = self._parse_recommendations(recommendations)
                    if guidance_list:
                        for g in guidance_list:
                            g.analyst_rating = rating_info.get("rating", AnalystRating.HOLD)
                            g.analyst_rating_distribution = rating_info.get("distribution", {})
                    else:
                        guidance = Guidance(
                            ticker=ticker,
                            market=Market.US,
                            fiscal_year=current_year,
                            analyst_rating=rating_info.get("rating", AnalystRating.HOLD),
                            analyst_rating_distribution=rating_info.get("distribution", {}),
                            source="yfinance",
                            updated_date=datetime.now(),
                        )
                        guidance_list.append(guidance)
            
        except Exception as e:
            raise RuntimeError(f"yfinance guidance fetch failed: {e}") from e
        
        return guidance_list
    
    def _fetch_recommendations(self, stock) -> Optional[List[Dict]]:
        try:
            recs = stock.recommendations
            if recs is not None and not recs.empty:
                return recs.to_dict("records")
        except Exception:
            pass
        return None
    
    def _fetch_earnings_trend(self, stock) -> Optional[List[Dict]]:
        try:
            trend = getattr(stock, "earnings_trend", None)
            if trend is not None:
                if hasattr(trend, "to_dict"):
                    return trend.to_dict("records")
                elif isinstance(trend, list):
                    return trend
        except Exception:
            pass
        return None
    
    def _parse_recommendations(self, recommendations: List[Dict]) -> Dict[str, Any]:
        if not recommendations:
            return {"rating": AnalystRating.HOLD, "distribution": {}}
        
        latest = recommendations[-1] if recommendations else {}
        
        distribution = {
            "strong_buy": latest.get("strongBuy", 0),
            "buy": latest.get("buy", 0),
            "hold": latest.get("hold", 0),
            "sell": latest.get("sell", 0),
            "strong_sell": latest.get("strongSell", 0),
        }
        
        total = sum(distribution.values())
        if total == 0:
            return {"rating": AnalystRating.HOLD, "distribution": distribution}
        
        buy_score = (distribution["strong_buy"] * 2 + distribution["buy"]) / total
        sell_score = (distribution["strong_sell"] * 2 + distribution["sell"]) / total
        
        if buy_score > 0.6:
            rating = AnalystRating.STRONG_BUY if buy_score > 0.8 else AnalystRating.BUY
        elif sell_score > 0.6:
            rating = AnalystRating.STRONG_SELL if sell_score > 0.8 else AnalystRating.SELL
        else:
            rating = AnalystRating.HOLD
        
        return {"rating": rating, "distribution": distribution}
