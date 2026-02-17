"""Tests for data fetcher module."""
import pytest

from valueinvest.data.fetcher import detect_source, get_fetcher, normalize_ashare_ticker
from valueinvest.data.fetcher.base import FetchResult, HistoryResult


class TestSourceDetection:
    def test_detect_us_stock(self):
        assert detect_source("AAPL") == "yfinance"
        assert detect_source("GOOGL") == "yfinance"
        assert detect_source("MSFT") == "yfinance"

    def test_detect_ashare_6digit(self):
        assert detect_source("600000") == "akshare"
        assert detect_source("000001") == "akshare"
        assert detect_source("002594") == "akshare"

    def test_detect_ashare_with_suffix(self):
        assert detect_source("600000.SH") == "akshare"
        assert detect_source("000001.SZ") == "akshare"

    def test_normalize_ashare_ticker(self):
        assert normalize_ashare_ticker("600000.SH") == "600000"
        assert normalize_ashare_ticker("000001.SZ") == "000001"
        assert normalize_ashare_ticker("600000") == "600000"


class TestFetcherCreation:
    def test_create_yfinance_fetcher(self):
        fetcher = get_fetcher("AAPL")
        assert fetcher.source_name == "yfinance"

    def test_create_akshare_fetcher(self):
        fetcher = get_fetcher("600000")
        assert fetcher.source_name == "akshare"


class TestAKShareFetcher:
    @pytest.fixture
    def fetcher(self):
        return get_fetcher("600000")

    def test_fetch_quote(self, fetcher):
        result = fetcher.fetch_quote("600000")
        assert result.success
        assert result.data["ticker"] == "600000"
        assert result.data["name"] != ""
        assert result.data["current_price"] > 0
        assert result.data["shares_outstanding"] > 0

    def test_fetch_fundamentals(self, fetcher):
        result = fetcher.fetch_fundamentals("600000")
        assert result.success
        assert result.data["eps"] > 0 or result.data["revenue"] > 0

    def test_fetch_all(self, fetcher):
        result = fetcher.fetch_all("600000")
        assert result.success
        assert "name" in result.data
        assert "current_price" in result.data

    def test_fetch_history(self, fetcher):
        result = fetcher.fetch_history("600000", period="1y")
        assert result.success
        assert result.df is not None
        assert len(result.df) > 100
        assert "close" in result.df.columns
        assert len(result.prices) > 0


class TestStockFromApi:
    def test_from_api_ashare(self):
        from valueinvest import Stock

        stock = Stock.from_api("600000")
        assert stock.ticker == "600000"
        assert stock.name != ""
        assert stock.current_price > 0
        assert stock.eps > 0

    def test_from_api_with_source(self):
        from valueinvest import Stock

        stock = Stock.from_api("600887", source="akshare")
        assert stock.ticker == "600887"
        assert stock.current_price > 0


class TestStockFromApiWithHistory:
    def test_from_api_separate_history(self):
        from valueinvest import Stock, StockHistory

        stock = Stock.from_api("600000")
        history = Stock.fetch_price_history("600000", period="1y")
        
        assert stock.ticker == "600000"
        assert stock.current_price > 0
        assert isinstance(history, StockHistory)
        assert history.ticker == "600000"
        assert len(history.prices) > 100

    def test_history_calculates_cagr(self):
        from valueinvest import Stock

        history = Stock.fetch_price_history("600000", period="3y")
        assert history.cagr != 0 or history.volatility != 0 or history.max_drawdown != 0


class TestStockHistoryMethods:
    def test_get_recent_prices(self):
        from valueinvest import Stock

        history = Stock.fetch_price_history("600000", period="1y")
        recent = history.get_recent_prices(days=10)
        
        assert len(recent) > 0
        assert "date" in recent[0]
        assert "close" in recent[0]

    def test_get_price_stats(self):
        from valueinvest import Stock

        history = Stock.fetch_price_history("600000", period="1y")
        stats = history.get_price_stats(days=30)
        
        assert stats["high"] >= stats["low"]
        assert stats["latest"] > 0


class TestHistoryResult:
    def test_history_result_properties(self):
        fetcher = get_fetcher("600000")
        result = fetcher.fetch_history("600000", period="1y")
        
        assert result.success
        assert isinstance(result.prices, list)
        assert len(result.prices) > 0
        
    def test_history_calculations(self):
        fetcher = get_fetcher("600000")
        result = fetcher.fetch_history("600000", period="3y")
        
        if result.success and len(result.prices) > 1:
            cagr = result.calculate_cagr()
            volatility = result.calculate_volatility()
            max_dd = result.calculate_max_drawdown()
            
            assert isinstance(cagr, float)
            assert isinstance(volatility, float)
            assert isinstance(max_dd, float)
