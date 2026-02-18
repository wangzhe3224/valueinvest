"""
News module for fetching and analyzing stock-related news.

Usage:
    from valueinvest.news import NewsAnalyzer, NewsRegistry
    
    # Auto-detect market and fetch news
    analyzer = NewsAnalyzer()
    result = analyzer.analyze("600887", days=30)
    
    # Use specific fetcher
    from valueinvest.news import AKShareNewsFetcher
    fetcher = AKShareNewsFetcher()
    news = fetcher.fetch_news("600887")
"""
from .base import (
    Market,
    Sentiment,
    NewsCategory,
    AnalystRating,
    NewsItem,
    Guidance,
    NewsAnalysisResult,
    NewsFetchResult,
)

__all__ = [
    "Market",
    "Sentiment", 
    "NewsCategory",
    "AnalystRating",
    "NewsItem",
    "Guidance",
    "NewsAnalysisResult",
    "NewsFetchResult",
]
