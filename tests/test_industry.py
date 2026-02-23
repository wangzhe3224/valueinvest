"""Tests for industry analysis module."""
import pytest
from valueinvest.industry.base import (
    PeerCompany,
    IndustryMetrics,
    IndustryFundFlow,
    IndustrySummary,
    IndustryFetchResult,
    IndustryTrend,
    FundFlowSentiment,
)
from valueinvest.industry.registry import IndustryRegistry, Market


class TestPeerCompany:
    def test_is_profitable(self):
        profitable = PeerCompany(ticker="600887", name="伊利", net_income=100)
        assert profitable.is_profitable is True

        unprofitable = PeerCompany(ticker="600000", name="亏损", net_income=-50)
        assert unprofitable.is_profitable is False

    def test_valuation_quality(self):
        undervalued = PeerCompany(ticker="001", name="A", pe_ratio=10)
        assert undervalued.valuation_quality == "undervalued"

        fair = PeerCompany(ticker="002", name="B", pe_ratio=20)
        assert fair.valuation_quality == "fair"

        expensive = PeerCompany(ticker="003", name="C", pe_ratio=50)
        assert expensive.valuation_quality == "expensive"

        unprofitable = PeerCompany(ticker="004", name="D", pe_ratio=-5)
        assert unprofitable.valuation_quality == "unprofitable"


class TestIndustryMetrics:
    def test_has_data(self):
        metrics = IndustryMetrics(company_count=10)
        assert metrics.has_data is True

        empty = IndustryMetrics()
        assert empty.has_data is False


class TestIndustryFundFlow:
    def test_net_flows(self):
        flow = IndustryFundFlow(
            main_inflow=100,
            main_outflow=30,
            retail_inflow=50,
            retail_outflow=20,
        )
        assert flow.net_main_flow == 70
        assert flow.net_retail_flow == 30


class TestIndustryFetchResult:
    def test_properties(self):
        result = IndustryFetchResult(
            success=True,
            ticker="600887",
            market="cn",
            source="test",
            industry_name="食品饮料",
        )
        assert result.has_data is True
        assert result.peer_count == 0
        assert result.has_peers is False

    def test_with_peers(self):
        peers = [
            PeerCompany(ticker="600887", name="伊利", market_cap=1000),
            PeerCompany(ticker="600873", name="梅花", market_cap=200),
            PeerCompany(ticker="000895", name="双汇", market_cap=800),
        ]
        result = IndustryFetchResult(
            success=True,
            ticker="600887",
            market="cn",
            source="test",
            industry_name="食品饮料",
            peers=peers,
            ticker_rank_in_peers=1,
        )
        assert result.peer_count == 3
        assert result.has_peers is True
        assert result.has_comparison is True

        top = result.get_top_peers(2)
        assert len(top) == 2
        assert top[0].ticker == "600887"

    def test_similar_sized_peers(self):
        peers = [
            PeerCompany(ticker="001", name="A", market_cap=1000),
            PeerCompany(ticker="002", name="B", market_cap=900),
            PeerCompany(ticker="003", name="C", market_cap=500),
            PeerCompany(ticker="004", name="D", market_cap=100),
        ]
        result = IndustryFetchResult(
            success=True,
            ticker="001",
            market="cn",
            source="test",
            peers=peers,
        )
        similar = result.get_similar_sized_peers(1000, tolerance=0.2)
        assert len(similar) == 2  # 1000 and 900 are within 20%


class TestIndustryRegistry:
    def test_detect_market_ashare(self):
        assert IndustryRegistry.detect_market("600887") == Market.A_SHARE
        assert IndustryRegistry.detect_market("000001") == Market.A_SHARE
        assert IndustryRegistry.detect_market("300750") == Market.A_SHARE

    def test_detect_market_us(self):
        assert IndustryRegistry.detect_market("AAPL") == Market.US
        assert IndustryRegistry.detect_market("GOOGL") == Market.US

    def test_get_supported_markets(self):
        markets = IndustryRegistry.get_supported_markets()
        assert Market.A_SHARE in markets
        assert Market.US in markets
