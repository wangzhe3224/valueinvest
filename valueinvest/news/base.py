"""
Core data structures for news and guidance information.

This module provides dataclasses for:
- NewsItem: Individual news article
- Guidance: Company guidance and analyst expectations
- NewsAnalysisResult: Aggregated analysis result
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum


class Market(Enum):
    """Supported markets for news fetching."""
    A_SHARE = "cn"       # China A-shares
    US = "us"            # US stocks
    HK = "hk"            # Hong Kong (reserved)
    EU = "eu"            # Europe (reserved)


class Sentiment(Enum):
    """Sentiment classification for news."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class NewsCategory(Enum):
    """News category classification."""
    EARNINGS = "earnings"           # 业绩相关
    INDUSTRY = "industry"           # 行业动态
    MACRO = "macro"                 # 宏观经济
    COMPANY = "company"             # 公司新闻
    GOVERNANCE = "governance"       # 公司治理
    DIVIDEND = "dividend"           # 分红相关
    GUIDANCE = "guidance"           # 业绩指引
    UNKNOWN = "unknown"


class AnalystRating(Enum):
    """Analyst rating classification."""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


@dataclass
class NewsItem:
    """Single news item with sentiment analysis."""
    ticker: str
    title: str
    content: str
    source: str
    publish_date: datetime
    market: Market
    
    url: str = ""
    sentiment: Sentiment = Sentiment.NEUTRAL
    confidence: float = 0.0           # Analysis confidence 0-1
    keywords: List[str] = field(default_factory=list)
    category: NewsCategory = NewsCategory.UNKNOWN
    impact_score: float = 0.0         # Price impact estimate -1 to 1
    rationale: str = ""               # Explanation for sentiment (LLM mode)
    
    @property
    def is_positive(self) -> bool:
        return self.sentiment == Sentiment.POSITIVE
    
    @property
    def is_negative(self) -> bool:
        return self.sentiment == Sentiment.NEGATIVE
    
    @property
    def age_days(self) -> int:
        """Days since publication."""
        return (datetime.now() - self.publish_date).days


@dataclass
class Guidance:
    """Company guidance and analyst expectations."""
    ticker: str
    market: Market
    fiscal_year: int
    quarter: Optional[int] = None    # None = annual guidance
    
    # Company guidance (management forecast)
    company_revenue_low: Optional[float] = None
    company_revenue_high: Optional[float] = None
    company_eps_low: Optional[float] = None
    company_eps_high: Optional[float] = None
    company_remarks: str = ""
    
    # Analyst expectations
    analyst_count: int = 0
    analyst_revenue_mean: Optional[float] = None
    analyst_revenue_low: Optional[float] = None
    analyst_revenue_high: Optional[float] = None
    analyst_eps_mean: Optional[float] = None
    analyst_eps_low: Optional[float] = None
    analyst_eps_high: Optional[float] = None
    analyst_rating: AnalystRating = AnalystRating.HOLD
    analyst_rating_distribution: dict = field(default_factory=dict)  # {buy: 5, hold: 3, sell: 1}
    
    # Price targets
    price_target_mean: Optional[float] = None
    price_target_low: Optional[float] = None
    price_target_high: Optional[float] = None
    
    source: str = ""
    updated_date: Optional[datetime] = None
    
    @property
    def has_company_guidance(self) -> bool:
        """Check if company provided guidance."""
        return any([
            self.company_revenue_low is not None,
            self.company_revenue_high is not None,
            self.company_eps_low is not None,
            self.company_eps_high is not None,
        ])
    
    @property
    def has_analyst_data(self) -> bool:
        """Check if analyst data is available."""
        return self.analyst_count > 0
    
    @property
    def guidance_vs_consensus(self) -> str:
        """Compare company guidance to analyst consensus."""
        if not self.has_company_guidance or not self.has_analyst_data:
            return "insufficient_data"
        
        # Compare EPS guidance mid to analyst mean
        if self.company_eps_low and self.company_eps_high and self.analyst_eps_mean:
            guidance_mid = (self.company_eps_low + self.company_eps_high) / 2
            if guidance_mid > self.analyst_eps_mean * 1.05:
                return "above_consensus"
            elif guidance_mid < self.analyst_eps_mean * 0.95:
                return "below_consensus"
            else:
                return "in_line"
        
        return "insufficient_data"


@dataclass
class NewsAnalysisResult:
    """Aggregated news analysis result."""
    ticker: str
    market: Market
    news: List[NewsItem] = field(default_factory=list)
    guidance: List[Guidance] = field(default_factory=list)
    
    # Aggregated sentiment metrics
    sentiment_score: float = 0.0          # -1 to 1
    sentiment_trend: str = "stable"       # improving/deteriorating/stable
    confidence: float = 0.0               # Overall confidence in analysis
    
    # News counts
    news_count_7d: int = 0
    news_count_30d: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    
    # Key findings
    key_themes: List[str] = field(default_factory=list)      # Main topics
    risks: List[str] = field(default_factory=list)           # Risk factors identified
    catalysts: List[str] = field(default_factory=list)       # Potential catalysts
    
    # Valuation implications
    growth_sentiment: str = "neutral"     # Impact on growth expectations
    dividend_safety: str = "stable"       # Dividend sustainability outlook
    
    # Analyzer metadata
    analyzer_type: str = "keyword"        # keyword/llm/agent
    analyzed_at: datetime = field(default_factory=datetime.now)
    errors: List[str] = field(default_factory=list)
    agent_prompt: str = ""                # Prompt for agent-based analysis
    agent_response: dict = field(default_factory=dict)  # Response from agent
    
    @property
    def sentiment_label(self) -> str:
        """Human-readable sentiment label."""
        if self.sentiment_score > 0.3:
            return "positive"
        elif self.sentiment_score < -0.3:
            return "negative"
        elif self.sentiment_score > 0.1:
            return "slightly_positive"
        elif self.sentiment_score < -0.1:
            return "slightly_negative"
        else:
            return "neutral"
    
    @property
    def has_guidance(self) -> bool:
        """Check if any guidance is available."""
        return len(self.guidance) > 0 and any(g.has_analyst_data or g.has_company_guidance for g in self.guidance)
    
    @property
    def latest_guidance(self) -> Optional[Guidance]:
        """Get the most recent guidance."""
        if not self.guidance:
            return None
        return max(self.guidance, key=lambda g: g.updated_date or datetime.min)


@dataclass
class NewsFetchResult:
    """Result from news fetching operation."""
    success: bool
    ticker: str
    market: Market
    source: str
    news: List[NewsItem] = field(default_factory=list)
    guidance: List[Guidance] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
