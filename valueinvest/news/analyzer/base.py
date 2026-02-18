"""
Base class for sentiment analyzers.

All sentiment analyzers should inherit from BaseSentimentAnalyzer.
"""
from abc import ABC, abstractmethod
from typing import List

from ..base import NewsItem, NewsAnalysisResult


class BaseSentimentAnalyzer(ABC):
    """Abstract base class for sentiment analyzers."""
    
    analyzer_type: str = "base"
    
    @abstractmethod
    def analyze_single(self, item: NewsItem) -> NewsItem:
        """Analyze a single news item and return with sentiment filled."""
        pass
    
    @abstractmethod
    def analyze_batch(
        self, 
        news: List[NewsItem],
        ticker: str,
    ) -> NewsAnalysisResult:
        """Analyze a batch of news and return aggregated result."""
        pass
    
    def aggregate_results(
        self,
        news: List[NewsItem],
        ticker: str,
    ) -> NewsAnalysisResult:
        """Create aggregated result from analyzed news items."""
        if not news:
            return NewsAnalysisResult(
                ticker=ticker,
                market=news[0].market if news else None,
                analyzer_type=self.analyzer_type,
            )
        
        positive = sum(1 for n in news if n.is_positive)
        negative = sum(1 for n in news if n.is_negative)
        neutral = len(news) - positive - negative
        
        sentiment_scores = []
        for n in news:
            if n.sentiment.value == "positive":
                sentiment_scores.append(n.impact_score if n.impact_score else 0.5)
            elif n.sentiment.value == "negative":
                sentiment_scores.append(-(n.impact_score if n.impact_score else 0.5))
            else:
                sentiment_scores.append(0)
        
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        
        from datetime import datetime, timedelta
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        news_7d = [n for n in news if n.publish_date >= week_ago]
        news_30d = [n for n in news if n.publish_date >= month_ago]
        
        return NewsAnalysisResult(
            ticker=ticker,
            market=news[0].market,
            news=news,
            sentiment_score=avg_sentiment,
            confidence=self._calculate_confidence(news),
            news_count_7d=len(news_7d),
            news_count_30d=len(news_30d),
            positive_count=positive,
            negative_count=negative,
            neutral_count=neutral,
            key_themes=self._extract_themes(news),
            risks=self._extract_risks(news),
            catalysts=self._extract_catalysts(news),
            analyzer_type=self.analyzer_type,
        )
    
    def _calculate_confidence(self, news: List[NewsItem]) -> float:
        if not news:
            return 0.0
        
        total_confidence = sum(n.confidence for n in news if n.confidence > 0)
        count = sum(1 for n in news if n.confidence > 0)
        
        return total_confidence / count if count > 0 else 0.5
    
    def _extract_themes(self, news: List[NewsItem]) -> List[str]:
        from collections import Counter
        all_keywords = []
        for n in news:
            all_keywords.extend(n.keywords)
        
        most_common = Counter(all_keywords).most_common(5)
        return [kw for kw, _ in most_common]
    
    def _extract_risks(self, news: List[NewsItem]) -> List[str]:
        return []
    
    def _extract_catalysts(self, news: List[NewsItem]) -> List[str]:
        return []
