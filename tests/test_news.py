"""
Tests for news module.
"""
import pytest
from datetime import datetime, timedelta

from valueinvest.news.base import (
    Market, Sentiment, NewsCategory, AnalystRating,
    NewsItem, Guidance, NewsAnalysisResult, NewsFetchResult,
)
from valueinvest.news.registry import NewsRegistry
from valueinvest.news.analyzer.keyword_analyzer import KeywordSentimentAnalyzer
from valueinvest.news.analyzer.base import BaseSentimentAnalyzer
from valueinvest.news.fetcher.base import BaseNewsFetcher


class TestNewsBase:
    
    def test_market_enum(self):
        assert Market.A_SHARE.value == "cn"
        assert Market.US.value == "us"
        assert Market.HK.value == "hk"
        assert Market.EU.value == "eu"
    
    def test_sentiment_enum(self):
        assert Sentiment.POSITIVE.value == "positive"
        assert Sentiment.NEGATIVE.value == "negative"
        assert Sentiment.NEUTRAL.value == "neutral"
    
    def test_news_category_enum(self):
        assert NewsCategory.EARNINGS.value == "earnings"
        assert NewsCategory.INDUSTRY.value == "industry"
        assert NewsCategory.MACRO.value == "macro"
        assert NewsCategory.COMPANY.value == "company"
    
    def test_analyst_rating_enum(self):
        assert AnalystRating.STRONG_BUY.value == "strong_buy"
        assert AnalystRating.BUY.value == "buy"
        assert AnalystRating.HOLD.value == "hold"
        assert AnalystRating.SELL.value == "sell"
        assert AnalystRating.STRONG_SELL.value == "strong_sell"
    
    def test_news_item_creation(self):
        item = NewsItem(
            ticker="600887",
            title="伊利股份业绩超预期",
            content="公司发布业绩预告，净利润同比增长20%",
            source="eastmoney",
            publish_date=datetime.now(),
            market=Market.A_SHARE,
        )
        
        assert item.ticker == "600887"
        assert item.sentiment == Sentiment.NEUTRAL
        assert item.is_positive is False
        assert item.is_negative is False
    
    def test_news_item_positive(self):
        item = NewsItem(
            ticker="AAPL",
            title="Apple beats earnings",
            content="Revenue surge 15%",
            source="yahoo",
            publish_date=datetime.now(),
            market=Market.US,
            sentiment=Sentiment.POSITIVE,
        )
        
        assert item.is_positive is True
        assert item.is_negative is False
    
    def test_news_item_negative(self):
        item = NewsItem(
            ticker="600887",
            title="业绩下滑",
            content="净利润下降",
            source="test",
            publish_date=datetime.now(),
            market=Market.A_SHARE,
            sentiment=Sentiment.NEGATIVE,
        )
        
        assert item.is_positive is False
        assert item.is_negative is True
    
    def test_news_item_age_days(self):
        old_date = datetime.now() - timedelta(days=10)
        item = NewsItem(
            ticker="600887",
            title="Test",
            content="Test content",
            source="test",
            publish_date=old_date,
            market=Market.A_SHARE,
        )
        
        assert item.age_days == 10
    
    def test_guidance_creation(self):
        guidance = Guidance(
            ticker="AAPL",
            market=Market.US,
            fiscal_year=2024,
            quarter=1,
            company_eps_low=1.50,
            company_eps_high=1.60,
            analyst_eps_mean=1.55,
            analyst_count=10,
        )
        
        assert guidance.has_company_guidance is True
        assert guidance.has_analyst_data is True
    
    def test_guidance_no_data(self):
        guidance = Guidance(
            ticker="AAPL",
            market=Market.US,
            fiscal_year=2024,
        )
        
        assert guidance.has_company_guidance is False
        assert guidance.has_analyst_data is False
    
    def test_guidance_vs_consensus(self):
        guidance_above = Guidance(
            ticker="AAPL",
            market=Market.US,
            fiscal_year=2024,
            company_eps_low=1.70,
            company_eps_high=1.80,
            analyst_eps_mean=1.55,
            analyst_count=10,
        )
        assert guidance_above.guidance_vs_consensus == "above_consensus"
        
        guidance_below = Guidance(
            ticker="AAPL",
            market=Market.US,
            fiscal_year=2024,
            company_eps_low=1.30,
            company_eps_high=1.40,
            analyst_eps_mean=1.55,
            analyst_count=10,
        )
        assert guidance_below.guidance_vs_consensus == "below_consensus"
        
        guidance_inline = Guidance(
            ticker="AAPL",
            market=Market.US,
            fiscal_year=2024,
            company_eps_low=1.52,
            company_eps_high=1.58,
            analyst_eps_mean=1.55,
            analyst_count=10,
        )
        assert guidance_inline.guidance_vs_consensus == "in_line"
        
        guidance_no_data = Guidance(
            ticker="AAPL",
            market=Market.US,
            fiscal_year=2024,
        )
        assert guidance_no_data.guidance_vs_consensus == "insufficient_data"
    
    def test_news_fetch_result(self):
        result = NewsFetchResult(
            success=True,
            ticker="600887",
            market=Market.A_SHARE,
            source="test",
            news=[],
            guidance=[],
        )
        
        assert result.success is True
        assert result.ticker == "600887"
        assert result.errors == []


class TestNewsRegistry:
    
    def test_detect_ashare_market(self):
        NewsRegistry.reset()
        NewsRegistry._setup_defaults()
        
        assert NewsRegistry.detect_market("600887") == Market.A_SHARE
        assert NewsRegistry.detect_market("000001") == Market.A_SHARE
        assert NewsRegistry.detect_market("300001") == Market.A_SHARE
        assert NewsRegistry.detect_market("601398") == Market.A_SHARE
    
    def test_detect_us_market(self):
        NewsRegistry.reset()
        NewsRegistry._setup_defaults()
        
        assert NewsRegistry.detect_market("AAPL") == Market.US
        assert NewsRegistry.detect_market("MSFT") == Market.US
        assert NewsRegistry.detect_market("GOOGL") == Market.US
        assert NewsRegistry.detect_market("T") == Market.US
    
    def test_detect_unknown_market(self):
        NewsRegistry.reset()
        NewsRegistry._setup_defaults()
        
        with pytest.raises(ValueError):
            NewsRegistry.detect_market("INVALID123")
    
    def test_get_supported_markets(self):
        NewsRegistry.reset()
        NewsRegistry._ensure_initialized()
        
        markets = NewsRegistry.get_supported_markets()
        assert Market.A_SHARE in markets or Market.US in markets
    
    def test_is_market_supported(self):
        NewsRegistry.reset()
        NewsRegistry._ensure_initialized()
        
        assert NewsRegistry.is_market_supported(Market.A_SHARE) is True
        assert NewsRegistry.is_market_supported(Market.US) is True
    
    def test_register_custom_fetcher(self):
        NewsRegistry.reset()
        
        class CustomFetcher(BaseNewsFetcher):
            market = Market.HK
            
            @property
            def source_name(self) -> str:
                return "custom"
            
            def fetch_news(self, ticker, days=30, start_date=None, end_date=None):
                return []
            
            def fetch_guidance(self, ticker):
                return []
        
        NewsRegistry.register_fetcher(Market.HK, CustomFetcher)
        
        assert NewsRegistry.is_market_supported(Market.HK) is True


class TestKeywordAnalyzer:
    
    def test_analyze_positive_news_cn(self):
        analyzer = KeywordSentimentAnalyzer()
        
        item = NewsItem(
            ticker="600887",
            title="伊利股份业绩超预期增长",
            content="公司发布业绩预告，净利润同比增长20%，营收创新高",
            source="test",
            publish_date=datetime.now(),
            market=Market.A_SHARE,
        )
        
        result = analyzer.analyze_single(item)
        
        assert result.sentiment == Sentiment.POSITIVE
        assert result.confidence > 0.5
        assert len(result.keywords) > 0
    
    def test_analyze_negative_news_cn(self):
        analyzer = KeywordSentimentAnalyzer()
        
        item = NewsItem(
            ticker="600887",
            title="伊利股份业绩下滑",
            content="公司业绩不及预期，净利润下降，存在风险",
            source="test",
            publish_date=datetime.now(),
            market=Market.A_SHARE,
        )
        
        result = analyzer.analyze_single(item)
        
        assert result.sentiment == Sentiment.NEGATIVE
    
    def test_analyze_positive_news_en(self):
        analyzer = KeywordSentimentAnalyzer()
        
        item = NewsItem(
            ticker="AAPL",
            title="Apple beats earnings estimates",
            content="Revenue surge 15%, profit growth exceeds expectations",
            source="test",
            publish_date=datetime.now(),
            market=Market.US,
        )
        
        result = analyzer.analyze_single(item)
        
        assert result.sentiment == Sentiment.POSITIVE
    
    def test_analyze_negative_news_en(self):
        analyzer = KeywordSentimentAnalyzer()
        
        item = NewsItem(
            ticker="AAPL",
            title="Apple misses revenue target",
            content="Revenue decline, loss increases, downgrade rating",
            source="test",
            publish_date=datetime.now(),
            market=Market.US,
        )
        
        result = analyzer.analyze_single(item)
        
        assert result.sentiment == Sentiment.NEGATIVE
    
    def test_analyze_neutral_news(self):
        analyzer = KeywordSentimentAnalyzer()
        
        item = NewsItem(
            ticker="AAPL",
            title="Apple announces new product",
            content="The company announced a new product today.",
            source="test",
            publish_date=datetime.now(),
            market=Market.US,
        )
        
        result = analyzer.analyze_single(item)
        
        assert result.sentiment == Sentiment.NEUTRAL
    
    def test_analyze_batch(self):
        analyzer = KeywordSentimentAnalyzer()
        
        news = [
            NewsItem(
                ticker="600887",
                title="业绩增长",
                content="净利润增长20%",
                source="test",
                publish_date=datetime.now() - timedelta(days=i),
                market=Market.A_SHARE,
            )
            for i in range(5)
        ]
        
        result = analyzer.analyze_batch(news, "600887")
        
        assert result.ticker == "600887"
        assert len(result.news) == 5
        assert result.analyzer_type == "keyword"
        assert result.sentiment_score > 0
        assert result.positive_count == 5
    
    def test_analyze_empty_batch(self):
        analyzer = KeywordSentimentAnalyzer()
        
        result = analyzer.analyze_batch([], "600887")
        
        assert result.ticker == "600887"
        assert len(result.news) == 0
        assert result.sentiment_score == 0
    
    def test_extract_risks(self):
        analyzer = KeywordSentimentAnalyzer()
        
        news = [
            NewsItem(
                ticker="600887",
                title="公司面临风险",
                content="市场竞争加剧，存在不确定性风险",
                source="test",
                publish_date=datetime.now(),
                market=Market.A_SHARE,
                sentiment=Sentiment.NEGATIVE,
            ),
        ]
        
        result = analyzer.analyze_batch(news, "600887")
        
        assert len(result.risks) > 0
    
    def test_extract_catalysts(self):
        analyzer = KeywordSentimentAnalyzer()
        
        news = [
            NewsItem(
                ticker="600887",
                title="公司中标重大项目",
                content="公司中标新订单，业绩增长可期",
                source="test",
                publish_date=datetime.now(),
                market=Market.A_SHARE,
                sentiment=Sentiment.POSITIVE,
            ),
        ]
        
        result = analyzer.analyze_batch(news, "600887")
        
        assert len(result.catalysts) > 0
    
    def test_category_classification_earnings(self):
        analyzer = KeywordSentimentAnalyzer()
        
        item = NewsItem(
            ticker="AAPL",
            title="Apple earnings report",
            content="Company announces quarterly profit and revenue",
            source="test",
            publish_date=datetime.now(),
            market=Market.US,
        )
        
        result = analyzer.analyze_single(item)
        
        assert result.category == NewsCategory.EARNINGS
    
    def test_category_classification_dividend(self):
        analyzer = KeywordSentimentAnalyzer()
        
        item = NewsItem(
            ticker="600887",
            title="伊利股份分红公告",
            content="公司宣布派息方案",
            source="test",
            publish_date=datetime.now(),
            market=Market.A_SHARE,
        )
        
        result = analyzer.analyze_single(item)
        
        assert result.category == NewsCategory.DIVIDEND


class TestLLMAnalyzer:
    
    def test_initialization(self):
        from valueinvest.news.analyzer.llm_analyzer import LLMSentimentAnalyzer
        
        analyzer = LLMSentimentAnalyzer(api_key="test-key", model="gpt-4o-mini")
        
        assert analyzer.analyzer_type == "llm"
        assert analyzer.model == "gpt-4o-mini"
    
    def test_initialization_with_base_url(self):
        from valueinvest.news.analyzer.llm_analyzer import LLMSentimentAnalyzer
        
        analyzer = LLMSentimentAnalyzer(
            api_key="test-key",
            base_url="https://api.example.com/v1"
        )
        
        assert analyzer.base_url == "https://api.example.com/v1"
    
    def test_parse_json_response(self):
        from valueinvest.news.analyzer.llm_analyzer import LLMSentimentAnalyzer
        
        analyzer = LLMSentimentAnalyzer(api_key="test-key")
        
        # Test plain JSON
        result = analyzer._parse_json_response('{"sentiment": "positive", "confidence": 0.9}')
        assert result["sentiment"] == "positive"
        assert result["confidence"] == 0.9
        
        # Test JSON in code block
        result = analyzer._parse_json_response('```json\n{"sentiment": "negative"}\n```')
        assert result["sentiment"] == "negative"
        
        # Test invalid JSON
        result = analyzer._parse_json_response('not valid json')
        assert result == {}


class TestNewsAnalysisResult:
    
    def test_sentiment_label_positive(self):
        result = NewsAnalysisResult(
            ticker="600887",
            market=Market.A_SHARE,
            sentiment_score=0.5,
        )
        assert result.sentiment_label == "positive"
        
        result.sentiment_score = 0.31
        assert result.sentiment_label == "positive"
    
    def test_sentiment_label_negative(self):
        result = NewsAnalysisResult(
            ticker="600887",
            market=Market.A_SHARE,
            sentiment_score=-0.5,
        )
        assert result.sentiment_label == "negative"
        
        result.sentiment_score = -0.31
        assert result.sentiment_label == "negative"
    
    def test_sentiment_label_slightly_positive(self):
        result = NewsAnalysisResult(
            ticker="600887",
            market=Market.A_SHARE,
            sentiment_score=0.2,
        )
        assert result.sentiment_label == "slightly_positive"
    
    def test_sentiment_label_slightly_negative(self):
        result = NewsAnalysisResult(
            ticker="600887",
            market=Market.A_SHARE,
            sentiment_score=-0.2,
        )
        assert result.sentiment_label == "slightly_negative"
    
    def test_sentiment_label_neutral(self):
        result = NewsAnalysisResult(
            ticker="600887",
            market=Market.A_SHARE,
            sentiment_score=0.0,
        )
        assert result.sentiment_label == "neutral"
        
        result.sentiment_score = 0.05
        assert result.sentiment_label == "neutral"
    
    def test_has_guidance(self):
        result = NewsAnalysisResult(
            ticker="AAPL",
            market=Market.US,
        )
        assert result.has_guidance is False
        
        result.guidance = [
            Guidance(
                ticker="AAPL",
                market=Market.US,
                fiscal_year=2024,
                analyst_count=10,
            )
        ]
        assert result.has_guidance is True
    
    def test_latest_guidance(self):
        old_guidance = Guidance(
            ticker="AAPL",
            market=Market.US,
            fiscal_year=2023,
            updated_date=datetime.now() - timedelta(days=30),
        )
        new_guidance = Guidance(
            ticker="AAPL",
            market=Market.US,
            fiscal_year=2024,
            updated_date=datetime.now(),
        )
        
        result = NewsAnalysisResult(
            ticker="AAPL",
            market=Market.US,
            guidance=[old_guidance, new_guidance],
        )
        
        assert result.latest_guidance == new_guidance
    
    def test_latest_guidance_empty(self):
        result = NewsAnalysisResult(
            ticker="AAPL",
            market=Market.US,
        )
        
        assert result.latest_guidance is None


class TestEnhancedReporter:
    
    def test_reporter_initialization(self):
        from valueinvest.reports.enhanced_reporter import EnhancedReporter
        
        reporter = EnhancedReporter()
        assert reporter is not None
    
    def test_reporter_render_minimal(self):
        from valueinvest.reports.enhanced_reporter import EnhancedReporter
        from valueinvest.stock import Stock, StockHistory
        from valueinvest.valuation.base import ValuationResult
        
        reporter = EnhancedReporter()
        
        stock = Stock(
            ticker="600887",
            name="伊利股份",
            current_price=26.0,
            eps=1.65,
            bvps=8.9,
        )
        
        history = StockHistory(ticker="600887")
        
        results = [
            ValuationResult(
                method="graham_number",
                fair_value=18.0,
                current_price=26.0,
                premium_discount=-30.8,
                assessment="Overvalued",
            )
        ]
        
        report = reporter.render(
            stock=stock,
            history=history,
            valuation_results=results,
            company_type="value",
        )
        
        assert "伊利股份" in report
        assert "600887" in report
        assert "估值汇总" in report
    
    def test_reporter_render_with_news(self):
        from valueinvest.reports.enhanced_reporter import EnhancedReporter
        from valueinvest.stock import Stock, StockHistory
        from valueinvest.valuation.base import ValuationResult
        
        reporter = EnhancedReporter()
        
        stock = Stock(
            ticker="600887",
            name="伊利股份",
            current_price=26.0,
            eps=1.65,
            bvps=8.9,
        )
        
        history = StockHistory(ticker="600887")
        
        results = [
            ValuationResult(
                method="graham_number",
                fair_value=18.0,
                current_price=26.0,
                premium_discount=-30.8,
                assessment="Overvalued",
            )
        ]
        
        news = [
            NewsItem(
                ticker="600887",
                title="业绩增长20%",
                content="净利润增长20%",
                source="test",
                publish_date=datetime.now(),
                market=Market.A_SHARE,
                sentiment=Sentiment.POSITIVE,
            )
        ]
        
        analysis = NewsAnalysisResult(
            ticker="600887",
            market=Market.A_SHARE,
            news=news,
            sentiment_score=0.5,
            positive_count=1,
            negative_count=0,
            neutral_count=0,
            key_themes=["增长"],
        )
        
        report = reporter.render(
            stock=stock,
            history=history,
            valuation_results=results,
            news_analysis=analysis,
            company_type="value",
        )
        
        assert "新闻情感分析" in report
        assert "业绩增长" in report
    
    def test_get_type_label(self):
        from valueinvest.reports.enhanced_reporter import EnhancedReporter
        
        reporter = EnhancedReporter()
        
        assert reporter._get_type_label("bank") == "银行/金融"
        assert reporter._get_type_label("dividend") == "分红股"
        assert reporter._get_type_label("growth") == "成长股"
        assert reporter._get_type_label("value") == "价值股"
        assert reporter._get_type_label("general") == "一般"
    
    def test_get_rating_label(self):
        from valueinvest.reports.enhanced_reporter import EnhancedReporter
        
        reporter = EnhancedReporter()
        
        assert reporter._get_rating_label(AnalystRating.STRONG_BUY) == "强力买入"
        assert reporter._get_rating_label(AnalystRating.BUY) == "买入"
        assert reporter._get_rating_label(AnalystRating.HOLD) == "持有"
        assert reporter._get_rating_label(AnalystRating.SELL) == "卖出"
        assert reporter._get_rating_label(AnalystRating.STRONG_SELL) == "强力卖出"
    
    def test_format_range(self):
        from valueinvest.reports.enhanced_reporter import EnhancedReporter
        
        reporter = EnhancedReporter()
        
        assert reporter._format_range(1.5, 2.5) == "1.50-2.50"
        assert reporter._format_range(1.5, 1.5) == "1.50"
        assert reporter._format_range(None, 2.5) == "≤2.50"
        assert reporter._format_range(1.5, None) == "≥1.50"
        assert reporter._format_range(None, None) == "-"


class TestAnalyzerBase:
    
    def test_aggregate_results(self):
        from valueinvest.news.analyzer.base import BaseSentimentAnalyzer
        
        class ConcreteAnalyzer(BaseSentimentAnalyzer):
            analyzer_type = "test"
            def analyze_single(self, item): return item
            def analyze_batch(self, news, ticker): 
                return self.aggregate_results(news, ticker)
        
        analyzer = ConcreteAnalyzer()
        
        news = [
            NewsItem(
                ticker="600887",
                title="Test",
                content="Test",
                source="test",
                publish_date=datetime.now(),
                market=Market.A_SHARE,
                sentiment=Sentiment.POSITIVE,
                confidence=0.8,
                impact_score=0.5,
            ),
            NewsItem(
                ticker="600887",
                title="Test2",
                content="Test2",
                source="test",
                publish_date=datetime.now(),
                market=Market.A_SHARE,
                sentiment=Sentiment.NEGATIVE,
                confidence=0.7,
                impact_score=-0.3,
            ),
        ]
        
        result = analyzer.aggregate_results(news, "600887")
        
        assert result.ticker == "600887"
        assert result.positive_count == 1
        assert result.negative_count == 1


class TestAgentAnalyzer:
    
    def test_initialization(self):
        from valueinvest.news.analyzer.agent_analyzer import AgentSentimentAnalyzer
        
        analyzer = AgentSentimentAnalyzer(
            stock_name="伊利股份",
            current_price=26.0,
            company_type="value",
            days=30,
        )
        
        assert analyzer.analyzer_type == "agent"
        assert analyzer.stock_name == "伊利股份"
        assert analyzer.current_price == 26.0
    
    def test_analyze_batch_uses_keyword_fallback(self):
        from valueinvest.news.analyzer.agent_analyzer import AgentSentimentAnalyzer
        
        analyzer = AgentSentimentAnalyzer()
        
        news = [
            NewsItem(
                ticker="600887",
                title="业绩增长超预期",
                content="净利润增长20%",
                source="test",
                publish_date=datetime.now(),
                market=Market.A_SHARE,
            )
        ]
        
        result = analyzer.analyze_batch(news, "600887")
        
        assert result.ticker == "600887"
        assert len(result.news) == 1
        assert result.sentiment_score > 0
    
    def test_create_agent_analysis_prompt(self):
        from valueinvest.news.analyzer.agent_analyzer import create_agent_analysis_prompt
        
        news = [
            NewsItem(
                ticker="600887",
                title="业绩增长",
                content="净利润增长20%",
                source="test",
                publish_date=datetime.now(),
                market=Market.A_SHARE,
            )
        ]
        
        prompt = create_agent_analysis_prompt(
            ticker="600887",
            stock_name="伊利股份",
            current_price=26.0,
            company_type="value",
            news=news,
            days=30,
        )
        
        assert "600887" in prompt
        assert "伊利股份" in prompt
        assert "26" in prompt
        assert "sentiment_score" in prompt
        assert "key_themes" in prompt
    
    def test_parse_agent_analysis_result_json(self):
        from valueinvest.news.analyzer.agent_analyzer import parse_agent_analysis_result
        
        json_response = '{"sentiment_score": 0.5, "key_themes": ["增长", "创新"]}'
        result = parse_agent_analysis_result(json_response)
        
        assert result["sentiment_score"] == 0.5
        assert "增长" in result["key_themes"]
    
    def test_parse_agent_analysis_result_markdown(self):
        from valueinvest.news.analyzer.agent_analyzer import parse_agent_analysis_result
        
        markdown_response = '''
Here is the analysis:
```json
{
  "sentiment_score": -0.3,
  "sentiment_label": "negative",
  "risks": ["竞争加剧"]
}
```
'''
        result = parse_agent_analysis_result(markdown_response)
        
        assert result["sentiment_score"] == -0.3
        assert result["sentiment_label"] == "negative"
    
    def test_parse_agent_analysis_result_invalid(self):
        from valueinvest.news.analyzer.agent_analyzer import parse_agent_analysis_result
        
        result = parse_agent_analysis_result("not valid json at all")
        
        assert result == {}
    
    def test_enhance_analysis_with_agent_result(self):
        from valueinvest.news.analyzer.agent_analyzer import enhance_analysis_with_agent_result
        
        base_result = NewsAnalysisResult(
            ticker="600887",
            market=Market.A_SHARE,
            sentiment_score=0.0,
            key_themes=["default"],
            risks=[],
            catalysts=[],
        )
        
        agent_response = {
            "sentiment_score": 0.6,
            "sentiment_trend": "improving",
            "confidence": 0.85,
            "key_themes": ["增长", "创新", "扩张"],
            "risks": ["竞争"],
            "catalysts": ["新品发布"],
            "growth_outlook": "positive",
            "dividend_safety": "stable",
        }
        
        enhanced = enhance_analysis_with_agent_result(base_result, agent_response)
        
        assert enhanced.sentiment_score == 0.6
        assert enhanced.sentiment_trend == "improving"
        assert enhanced.confidence == 0.85
        assert enhanced.key_themes == ["增长", "创新", "扩张"]
        assert enhanced.risks == ["竞争"]
        assert enhanced.catalysts == ["新品发布"]
        assert enhanced.growth_sentiment == "positive"
        assert enhanced.dividend_safety == "stable"
        assert enhanced.analyzer_type == "agent"
    
    def test_enhance_analysis_empty_response(self):
        from valueinvest.news.analyzer.agent_analyzer import enhance_analysis_with_agent_result
        
        base_result = NewsAnalysisResult(
            ticker="600887",
            market=Market.A_SHARE,
            sentiment_score=0.5,
        )
        
        enhanced = enhance_analysis_with_agent_result(base_result, {})
        
        assert enhanced.sentiment_score == 0.5
        assert enhanced.analyzer_type == "keyword"
