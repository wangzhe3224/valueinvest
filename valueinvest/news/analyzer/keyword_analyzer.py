"""
Keyword-based sentiment analyzer.

Analyzes sentiment using predefined positive/negative word lists.
Supports both Chinese and English.
"""
import re
from typing import List, Set, Dict
from collections import Counter

from .base import BaseSentimentAnalyzer
from ..base import NewsItem, NewsAnalysisResult, Sentiment, NewsCategory


POSITIVE_CN: Set[str] = {
    "增长", "上升", "突破", "创新高", "超预期", "利好", "中标",
    "回购", "增持", "分红", "利润增长", "营收增长", "盈利",
    "扩张", "并购", "合作", "签约", "订单", "市场份额提升",
    "扭亏", "业绩向好", "强劲", "看好", "上调", "买入",
    "龙头", "领先", "竞争力", "成长", "机会", "乐观",
    "复苏", "回暖", "改善", "优化", "升级", "创新",
}

NEGATIVE_CN: Set[str] = {
    "下降", "下跌", "亏损", "减持", "减持", "利空", "下修",
    "诉讼", "调查", "处罚", "风险", "下滑", "下滑", "裁员",
    "关停", "违约", "债务", "破产", "退市", "跌停", "暴跌",
    "不及预期", "下调", "卖出", "看空", "悲观", "萎缩",
    "恶化", "受损", "冲击", "压力", "下滑", "减少",
    "竞争加剧", "成本上升", "毛利下降", "资金链", "质押",
}

POSITIVE_EN: Set[str] = {
    "growth", "surge", "jump", "rise", "gain", "profit", "beat",
    "upgrade", "buyback", "dividend", "acquire", "expand", "win",
    "record", "high", "strong", "bullish", "outperform", "overweight",
    "positive", "optimistic", "growth", "opportunity", "breakthrough",
    "increase", "improve", "exceed", "milestone", "partnership",
}

NEGATIVE_EN: Set[str] = {
    "decline", "drop", "fall", "loss", "downgrade", "sell", "lawsuit",
    "investigation", "fine", "penalty", "bankrupt", "delist", "crash",
    "miss", "bearish", "underperform", "underweight", "negative",
    "pessimistic", "risk", "threat", "challenge", "concern", "worst",
    "decrease", "reduce", "cut", "layoff", "shutdown", "default",
}

RISK_KEYWORDS_CN: Set[str] = {
    "风险", "诉讼", "调查", "处罚", "违约", "质押", "减持",
    "竞争加剧", "成本上升", "下滑", "压力", "不确定性",
}

RISK_KEYWORDS_EN: Set[str] = {
    "risk", "lawsuit", "investigation", "fine", "penalty", "default",
    "competition", "pressure", "uncertainty", "concern", "threat",
}

CATALYST_KEYWORDS_CN: Set[str] = {
    "订单", "中标", "签约", "并购", "回购", "新产品",
    "扩张", "增长", "创新高", "超预期", "利好",
}

CATALYST_KEYWORDS_EN: Set[str] = {
    "order", "contract", "acquisition", "buyback", "new product",
    "expansion", "growth", "record", "beat", "positive",
}

CATEGORY_PATTERNS: Dict[NewsCategory, List[str]] = {
    NewsCategory.EARNINGS: [
        r"业绩", r"利润", r"营收", r"盈利", r"亏损", r"财报",
        r"earnings", r"profit", r"revenue", r"loss", r"quarter",
    ],
    NewsCategory.DIVIDEND: [
        r"分红", r"股息", r"派息",
        r"dividend", r"payout",
    ],
    NewsCategory.GUIDANCE: [
        r"指引", r"预期", r"展望", r"预测",
        r"guidance", r"forecast", r"outlook", r"estimate",
    ],
    NewsCategory.INDUSTRY: [
        r"行业", r"市场", r"竞争", r"份额",
        r"industry", r"market", r"sector", r"competition",
    ],
    NewsCategory.MACRO: [
        r"宏观", r"政策", r"经济", r"利率", r"央行",
        r"macro", r"policy", r"economy", r"rate", r"federal",
    ],
    NewsCategory.GOVERNANCE: [
        r"治理", r"股东", r"管理层", r"董事",
        r"governance", r"shareholder", r"management", r"board",
    ],
}


class KeywordSentimentAnalyzer(BaseSentimentAnalyzer):
    """Analyze sentiment using keyword matching."""
    
    analyzer_type = "keyword"
    
    def __init__(
        self,
        positive_words: Set[str] = None,
        negative_words: Set[str] = None,
    ):
        self.positive_words = positive_words or (POSITIVE_CN | POSITIVE_EN)
        self.negative_words = negative_words or (NEGATIVE_CN | NEGATIVE_EN)
    
    def analyze_single(self, item: NewsItem) -> NewsItem:
        text = f"{item.title} {item.content}"
        
        positive_count = sum(1 for word in self.positive_words if word in text)
        negative_count = sum(1 for word in self.negative_words if word in text)
        
        total = positive_count + negative_count
        
        if total == 0:
            item.sentiment = Sentiment.NEUTRAL
            item.confidence = 0.3
            item.impact_score = 0.0
        else:
            positive_ratio = positive_count / total
            
            if positive_ratio > 0.6:
                item.sentiment = Sentiment.POSITIVE
                item.confidence = min(0.9, 0.5 + positive_ratio * 0.4)
                item.impact_score = positive_ratio
            elif positive_ratio < 0.4:
                item.sentiment = Sentiment.NEGATIVE
                item.confidence = min(0.9, 0.5 + (1 - positive_ratio) * 0.4)
                item.impact_score = -(1 - positive_ratio)
            else:
                item.sentiment = Sentiment.NEUTRAL
                item.confidence = 0.4
                item.impact_score = positive_ratio - 0.5
        
        item.keywords = self._extract_keywords(text)
        item.category = self._classify_category(text)
        
        return item
    
    def analyze_batch(
        self, 
        news: List[NewsItem],
        ticker: str,
    ) -> NewsAnalysisResult:
        analyzed_news = [self.analyze_single(item) for item in news]
        
        result = self.aggregate_results(analyzed_news, ticker)
        result.risks = self._extract_risks(analyzed_news)
        result.catalysts = self._extract_catalysts(analyzed_news)
        
        return result
    
    def _extract_keywords(self, text: str) -> List[str]:
        all_keywords = self.positive_words | self.negative_words
        found = [word for word in all_keywords if word in text]
        return list(set(found))[:10]
    
    def _classify_category(self, text: str) -> NewsCategory:
        for category, patterns in CATEGORY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return category
        return NewsCategory.COMPANY
    
    def _extract_risks(self, news: List[NewsItem]) -> List[str]:
        risks = []
        risk_words = RISK_KEYWORDS_CN | RISK_KEYWORDS_EN
        
        for item in news:
            text = f"{item.title} {item.content}"
            for word in risk_words:
                if word in text and word not in risks:
                    risks.append(word)
        
        return risks[:5]
    
    def _extract_catalysts(self, news: List[NewsItem]) -> List[str]:
        catalysts = []
        catalyst_words = CATALYST_KEYWORDS_CN | CATALYST_KEYWORDS_EN
        
        for item in news:
            if item.is_positive:
                text = f"{item.title} {item.content}"
                for word in catalyst_words:
                    if word in text and word not in catalysts:
                        catalysts.append(word)
        
        return catalysts[:5]
