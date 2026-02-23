"""
Agent-based sentiment analyzer.

Uses coding agents (ultrabrain/deep) for high-quality sentiment analysis
without requiring external API keys.
"""
import json
from typing import List, Optional
from datetime import datetime

from .base import BaseSentimentAnalyzer
from ..base import NewsItem, NewsAnalysisResult, Sentiment, NewsCategory


ANALYSIS_PROMPT = """Analyze the following stock news and provide a comprehensive sentiment analysis.

Stock Ticker: {ticker}
Stock Name: {stock_name}
Current Price: {current_price}
Company Type: {company_type}

Recent News ({news_count} articles from the past {days} days):
{news_list}

Provide your analysis in the following JSON format:
{{
  "sentiment_score": -1.0 to 1.0,
  "sentiment_label": "positive" | "negative" | "neutral",
  "sentiment_trend": "improving" | "deteriorating" | "stable",
  "confidence": 0.0 to 1.0,
  "key_themes": ["theme1", "theme2", "theme3"],
  "risks": ["risk1", "risk2"],
  "catalysts": ["catalyst1", "catalyst2"],
  "growth_outlook": "positive" | "negative" | "neutral",
  "dividend_safety": "stable" | "at_risk" | "improving",
  "investment_thesis": "2-3 sentence summary of the investment case",
  "news_analysis": [
    {{
      "title": "original title",
      "sentiment": "positive" | "negative" | "neutral",
      "impact_score": -1.0 to 1.0,
      "rationale": "brief explanation"
    }}
  ]
}}

Guidelines:
- sentiment_score: Overall market sentiment (-1 most bearish, +1 most bullish)
- sentiment_trend: How sentiment is changing compared to prior period
- key_themes: 3-5 main topics from the news (be specific, not generic)
- risks: Concrete risk factors mentioned in news
- catalysts: Potential positive triggers mentioned
- growth_outlook: Impact on future growth expectations
- dividend_safety: For dividend stocks, assess dividend sustainability
- news_analysis: Analyze the 5 most important news items
"""

BATCH_SUMMARY_PROMPT = """Based on the following news analysis, provide investment recommendations.

Stock: {ticker}
Current Sentiment Score: {sentiment_score}
Key Themes: {themes}
Risks: {risks}
Catalysts: {catalysts}

Provide a JSON response:
{{
  "overall_recommendation": "bullish" | "bearish" | "neutral",
  "price_outlook": "likely to rise" | "likely to fall" | "likely sideways",
  "key_watch_items": ["item1", "item2", "item3"],
  "contrarian_opportunity": true | false,
  "contrarian_rationale": "explanation if true",
  "summary": "2-3 sentence actionable summary"
}}
"""


class AgentSentimentAnalyzer(BaseSentimentAnalyzer):
    """Analyze sentiment using coding agents (no external API required)."""
    
    analyzer_type = "agent"
    
    def __init__(
        self,
        stock_name: str = "",
        current_price: float = 0.0,
        company_type: str = "general",
        days: int = 30,
    ):
        self.stock_name = stock_name
        self.current_price = current_price
        self.company_type = company_type
        self.days = days
    
    def analyze_single(self, item: NewsItem) -> NewsItem:
        item.sentiment = Sentiment.NEUTRAL
        item.confidence = 0.5
        return item
    
    def analyze_batch(
        self, 
        news: List[NewsItem],
        ticker: str,
    ) -> NewsAnalysisResult:
        from valueinvest.news.analyzer.keyword_analyzer import KeywordSentimentAnalyzer
        
        keyword_analyzer = KeywordSentimentAnalyzer()
        initial_result = keyword_analyzer.analyze_batch(news, ticker)
        
        return initial_result
    
    def analyze_with_context(
        self,
        news: List[NewsItem],
        ticker: str,
        stock_name: str,
        current_price: float,
        company_type: str,
        days: int = 30,
    ) -> dict:
        """
        Perform deep analysis using coding agent.
        
        Returns a dict with analysis results suitable for enhancing the report.
        """
        news_list = self._format_news_for_agent(news[:20])
        
        prompt = ANALYSIS_PROMPT.format(
            ticker=ticker,
            stock_name=stock_name,
            current_price=current_price,
            company_type=company_type,
            news_count=len(news),
            days=days,
            news_list=news_list,
        )
        
        return {
            "prompt": prompt,
            "news_count": len(news),
            "ticker": ticker,
        }
    
    def _format_news_for_agent(self, news: List[NewsItem]) -> str:
        lines = []
        for i, item in enumerate(news, 1):
            date_str = item.publish_date.strftime("%Y-%m-%d")
            sentiment = item.sentiment.value if item.sentiment else "unknown"
            lines.append(f"{i}. [{date_str}] [{sentiment}] {item.title}")
            if item.content:
                content_preview = item.content[:200].replace('\n', ' ')
                lines.append(f"   Content: {content_preview}...")
        return "\n".join(lines)


def create_agent_analysis_prompt(
    ticker: str,
    stock_name: str,
    current_price: float,
    company_type: str,
    news: List[NewsItem],
    days: int = 30,
) -> str:
    """
    Create a prompt for agent-based news analysis.
    
    This function creates a structured prompt that can be used with
    the task tool and ultrabrain/deep agents.
    """
    analyzer = AgentSentimentAnalyzer()
    return analyzer.analyze_with_context(
        news=news,
        ticker=ticker,
        stock_name=stock_name,
        current_price=current_price,
        company_type=company_type,
        days=days,
    )["prompt"]


def parse_agent_analysis_result(response_text: str) -> dict:
    """
    Parse the JSON response from agent analysis.
    
    Handles various response formats including markdown code blocks.
    """
    try:
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0]
        else:
            json_str = response_text
        
        return json.loads(json_str.strip())
    except (json.JSONDecodeError, IndexError):
        return {}


def enhance_analysis_with_agent_result(
    base_result: NewsAnalysisResult,
    agent_response: dict,
) -> NewsAnalysisResult:
    """
    Enhance keyword-based analysis with agent insights.
    """
    if not agent_response:
        return base_result
    
    if "sentiment_score" in agent_response:
        base_result.sentiment_score = float(agent_response["sentiment_score"])
    
    if "sentiment_trend" in agent_response:
        base_result.sentiment_trend = agent_response["sentiment_trend"]
    
    if "confidence" in agent_response:
        base_result.confidence = float(agent_response["confidence"])
    
    if "key_themes" in agent_response and agent_response["key_themes"]:
        base_result.key_themes = agent_response["key_themes"]
    
    if "risks" in agent_response and agent_response["risks"]:
        base_result.risks = agent_response["risks"]
    
    if "catalysts" in agent_response and agent_response["catalysts"]:
        base_result.catalysts = agent_response["catalysts"]
    
    if "growth_outlook" in agent_response:
        base_result.growth_sentiment = agent_response["growth_outlook"]
    
    if "dividend_safety" in agent_response:
        base_result.dividend_safety = agent_response["dividend_safety"]
    
    if "news_analysis" in agent_response:
        for agent_news in agent_response["news_analysis"]:
            for item in base_result.news:
                if item.title == agent_news.get("title"):
                    if "sentiment" in agent_news:
                        item.sentiment = Sentiment(agent_news["sentiment"])
                    if "impact_score" in agent_news:
                        item.impact_score = float(agent_news["impact_score"])
                    if "rationale" in agent_news:
                        item.rationale = agent_news["rationale"]
    
    base_result.analyzer_type = "agent"
    
    return base_result
