"""
LLM-based sentiment analyzer.

Uses OpenAI API for high-quality sentiment analysis.
"""
import json
from typing import List, Optional
from datetime import datetime

from .base import BaseSentimentAnalyzer
from ..base import NewsItem, NewsAnalysisResult, Sentiment, NewsCategory


ANALYSIS_PROMPT = """Analyze the following stock news and return a JSON response.

Stock Ticker: {ticker}
News Title: {title}
News Content: {content}

Return ONLY a valid JSON object with these fields:
{{
  "sentiment": "positive" | "negative" | "neutral",
  "confidence": 0.0-1.0,
  "impact_score": -1.0 to 1.0,
  "category": "earnings" | "industry" | "macro" | "company" | "governance" | "dividend" | "guidance",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "rationale": "Brief explanation in 1-2 sentences"
}}

Guidelines:
- sentiment: Overall tone of the news
- confidence: How certain is your analysis
- impact_score: Potential stock price impact (-1 most negative, +1 most positive)
- keywords: 3-5 most relevant terms
- rationale: Why you assigned this sentiment"""


BATCH_SUMMARY_PROMPT = """Summarize the following analyzed news for stock {ticker}.

News items:
{news_summary}

Return ONLY a valid JSON object:
{{
  "overall_sentiment": -1.0 to 1.0,
  "sentiment_trend": "improving" | "deteriorating" | "stable",
  "key_themes": ["theme1", "theme2", "theme3"],
  "risks": ["risk1", "risk2"],
  "catalysts": ["catalyst1", "catalyst2"],
  "growth_outlook": "positive" | "negative" | "neutral",
  "dividend_safety": "stable" | "at_risk" | "improving",
  "summary": "2-3 sentence investment summary"
}}"""


class LLMSentimentAnalyzer(BaseSentimentAnalyzer):
    """Analyze sentiment using LLM (OpenAI)."""
    
    analyzer_type = "llm"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                kwargs = {"api_key": self.api_key}
                if self.base_url:
                    kwargs["base_url"] = self.base_url
                self._client = OpenAI(**kwargs)
            except ImportError:
                raise ImportError(
                    "openai package required for LLM analyzer. "
                    "Install with: pip install openai"
                )
        return self._client
    
    def analyze_single(self, item: NewsItem) -> NewsItem:
        prompt = ANALYSIS_PROMPT.format(
            ticker=item.ticker,
            title=item.title,
            content=item.content[:2000],
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500,
            )
            
            content = response.choices[0].message.content
            result = self._parse_json_response(content)
            
            item.sentiment = Sentiment(result.get("sentiment", "neutral"))
            item.confidence = float(result.get("confidence", 0.5))
            item.impact_score = float(result.get("impact_score", 0.0))
            item.category = NewsCategory(result.get("category", "unknown"))
            item.keywords = result.get("keywords", [])
            item.rationale = result.get("rationale", "")
            
        except Exception as e:
            item.sentiment = Sentiment.NEUTRAL
            item.confidence = 0.0
            item.rationale = f"LLM analysis failed: {str(e)}"
        
        return item
    
    def analyze_batch(
        self,
        news: List[NewsItem],
        ticker: str,
    ) -> NewsAnalysisResult:
        analyzed_news = []
        for item in news:
            analyzed_news.append(self.analyze_single(item))
        
        result = self.aggregate_results(analyzed_news, ticker)
        
        if len(analyzed_news) > 0:
            batch_summary = self._get_batch_summary(analyzed_news, ticker)
            result.key_themes = batch_summary.get("key_themes", result.key_themes)
            result.risks = batch_summary.get("risks", result.risks)
            result.catalysts = batch_summary.get("catalysts", result.catalysts)
            result.growth_sentiment = batch_summary.get("growth_outlook", "neutral")
            result.dividend_safety = batch_summary.get("dividend_safety", "stable")
            result.sentiment_trend = batch_summary.get("sentiment_trend", "stable")
        
        return result
    
    def _get_batch_summary(
        self,
        news: List[NewsItem],
        ticker: str,
    ) -> dict:
        news_summary = "\n".join([
            f"- [{n.sentiment.value}] {n.title} (impact: {n.impact_score:.2f})"
            for n in news[:20]
        ])
        
        prompt = BATCH_SUMMARY_PROMPT.format(
            ticker=ticker,
            news_summary=news_summary,
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500,
            )
            
            content = response.choices[0].message.content
            return self._parse_json_response(content)
            
        except Exception:
            return {}
    
    def _parse_json_response(self, content: str) -> dict:
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            return json.loads(content.strip())
        except json.JSONDecodeError:
            return {}
