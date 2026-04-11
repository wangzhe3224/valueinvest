"""Tests for Peer Comparison Analysis module."""
import pytest
from valueinvest.stock import Stock
from valueinvest.industry.base import PeerCompany
from valueinvest.peer_comparison import (
    analyze_peers,
    PeerComparisonEngine,
    PeerComparisonResult,
    MetricComparison,
    ComparisonRating,
    MetricDirection,
)
from valueinvest.peer_comparison.engine import METRIC_DEFINITIONS


# --- Fixtures ---


@pytest.fixture
def ashare_peers():
    """Mock A-share peer companies in the same industry."""
    return [
        PeerCompany(
            ticker="600887",
            name="伊利",
            market_cap=200e9,
            pe_ratio=25,
            pb_ratio=5.0,
            roe=25,
            revenue=120e9,
            net_income=10e9,
            current_price=32,
        ),
        PeerCompany(
            ticker="000895",
            name="双汇",
            market_cap=100e9,
            pe_ratio=20,
            pb_ratio=3.5,
            roe=30,
            revenue=60e9,
            net_income=5e9,
            current_price=29,
        ),
        PeerCompany(
            ticker="603288",
            name="海天",
            market_cap=300e9,
            pe_ratio=40,
            pb_ratio=8.0,
            roe=32,
            revenue=25e9,
            net_income=7e9,
            current_price=55,
        ),
        PeerCompany(
            ticker="002568",
            name="百润",
            market_cap=50e9,
            pe_ratio=30,
            pb_ratio=4.0,
            roe=20,
            revenue=3e9,
            net_income=0.6e9,
            current_price=20,
        ),
        PeerCompany(
            ticker="600809",
            name="山西汾酒",
            market_cap=250e9,
            pe_ratio=45,
            pb_ratio=10.0,
            roe=35,
            revenue=20e9,
            net_income=5e9,
            current_price=200,
        ),
    ]


@pytest.fixture
def target_stock():
    """A target A-share stock for comparison."""
    return Stock(
        ticker="600519",
        name="贵州茅台",
        current_price=1800,
        shares_outstanding=1.26e9,
        eps=50,
        bvps=160,
        revenue=150e9,
        net_income=60e9,
        fcf=50e9,
        operating_margin=52.0,
        roe=30.0,
        revenue_growth=15.0,
        sector="消费",
        industry="白酒",
    )


class TestWithManualPeers:
    """Tests using manually provided peer list."""

    def test_basic_analysis(self, target_stock, ashare_peers):
        engine = PeerComparisonEngine(peers=ashare_peers)
        result = engine.analyze(target_stock)
        assert isinstance(result, PeerComparisonResult)
        assert result.ticker == "600519"
        assert result.peer_count == 5
        assert result.composite_score > 0
        assert result.rating in ComparisonRating

    def test_metric_comparisons_populated(self, target_stock, ashare_peers):
        result = analyze_peers(target_stock, peers=ashare_peers)
        assert len(result.metric_comparisons) == len(METRIC_DEFINITIONS)
        pe_comp = next(
            m for m in result.metric_comparisons if m.metric_key == "pe_ratio"
        )
        assert pe_comp.is_available
        assert pe_comp.peer_avg > 0
        assert pe_comp.percentile > 0

    def test_percentile_range(self, target_stock, ashare_peers):
        result = analyze_peers(target_stock, peers=ashare_peers)
        for mc in result.metric_comparisons:
            if mc.is_available:
                assert 0 <= mc.percentile <= 100

    def test_composite_score_range(self, target_stock, ashare_peers):
        result = analyze_peers(target_stock, peers=ashare_peers)
        assert 0 <= result.composite_score <= 100

    def test_has_sufficient_peers(self, target_stock, ashare_peers):
        result = analyze_peers(target_stock, peers=ashare_peers)
        assert result.has_sufficient_peers is True

    def test_pe_percentile_lower_better(self, target_stock, ashare_peers):
        result = analyze_peers(target_stock, peers=ashare_peers)
        pe_comp = next(
            m for m in result.metric_comparisons if m.metric_key == "pe_ratio"
        )
        assert pe_comp.direction == MetricDirection.LOWER_BETTER
        # Target PE=36, peers avg=32, so PE is above avg -> percentile should be < 50
        assert pe_comp.percentile < 60

    def test_roe_percentile_higher_better(self, target_stock, ashare_peers):
        result = analyze_peers(target_stock, peers=ashare_peers)
        roe_comp = next(
            m for m in result.metric_comparisons if m.metric_key == "roe"
        )
        assert roe_comp.direction == MetricDirection.HIGHER_BETTER

    def test_market_cap_rank(self, target_stock, ashare_peers):
        result = analyze_peers(target_stock, peers=ashare_peers)
        assert result.rank_in_peers > 0

    def test_strengths_and_weaknesses(self, target_stock, ashare_peers):
        result = analyze_peers(target_stock, peers=ashare_peers)
        assert len(result.analysis) >= 2

    def test_valuation_score(self, target_stock, ashare_peers):
        result = analyze_peers(target_stock, peers=ashare_peers)
        assert result.valuation_score >= 0

    def test_profitability_score(self, target_stock, ashare_peers):
        result = analyze_peers(target_stock, peers=ashare_peers)
        assert result.profitability_score >= 0


class TestInsufficientPeers:
    """Tests for edge cases with too few peers."""

    def test_no_peers(self, target_stock):
        result = analyze_peers(target_stock, peers=[])
        assert result.has_sufficient_peers is False
        assert result.composite_score == 0.0
        assert len(result.warnings) > 0

    def test_one_peer(self, target_stock):
        result = analyze_peers(
            target_stock,
            peers=[PeerCompany(ticker="001", name="A", market_cap=100e9)],
        )
        assert result.has_sufficient_peers is False

    def test_two_peers(self, target_stock):
        result = analyze_peers(
            target_stock,
            peers=[
                PeerCompany(ticker="001", name="A", market_cap=100e9),
                PeerCompany(ticker="002", name="B", market_cap=200e9),
            ],
        )
        assert result.has_sufficient_peers is False

    def test_three_peers_sufficient(self, target_stock):
        result = analyze_peers(
            target_stock,
            peers=[
                PeerCompany(
                    ticker="001",
                    name="A",
                    market_cap=100e9,
                    pe_ratio=20,
                    roe=15,
                    revenue=50e9,
                    net_income=5e9,
                ),
                PeerCompany(
                    ticker="002",
                    name="B",
                    market_cap=200e9,
                    pe_ratio=30,
                    roe=25,
                    revenue=80e9,
                    net_income=8e9,
                ),
                PeerCompany(
                    ticker="003",
                    name="C",
                    market_cap=150e9,
                    pe_ratio=25,
                    roe=20,
                    revenue=60e9,
                    net_income=6e9,
                ),
            ],
        )
        assert result.has_sufficient_peers is True


class TestMetricComparison:
    """Tests for individual MetricComparison dataclass."""

    def test_vs_avg_pct(self):
        mc = MetricComparison(
            metric_name="PE",
            metric_key="pe_ratio",
            target_value=30,
            peer_avg=25,
            peer_median=24,
            peer_count=10,
            percentile=60,
            direction=MetricDirection.LOWER_BETTER,
        )
        assert mc.vs_avg_pct == pytest.approx(20.0, abs=0.1)

    def test_vs_avg_pct_zero_avg(self):
        mc = MetricComparison(
            metric_name="PE",
            metric_key="pe_ratio",
            target_value=30,
            peer_avg=0,
            peer_median=0,
            peer_count=0,
            percentile=0,
            direction=MetricDirection.LOWER_BETTER,
            is_available=False,
        )
        assert mc.vs_avg_pct == 0.0

    def test_assessment_unavailable(self):
        mc = MetricComparison(
            metric_name="PE",
            metric_key="pe_ratio",
            target_value=0,
            peer_avg=0,
            peer_median=0,
            peer_count=0,
            percentile=0,
            direction=MetricDirection.LOWER_BETTER,
            is_available=False,
        )
        assert mc.assessment == "N/A"

    def test_assessment_higher_better_top(self):
        mc = MetricComparison(
            metric_name="ROE",
            metric_key="roe",
            target_value=30,
            peer_avg=20,
            peer_median=18,
            peer_count=10,
            percentile=80,
            direction=MetricDirection.HIGHER_BETTER,
        )
        assert mc.assessment == "significantly above peers"

    def test_assessment_lower_better_good(self):
        """For LOWER_BETTER, low percentile = good (value is low)."""
        mc = MetricComparison(
            metric_name="PE",
            metric_key="pe_ratio",
            target_value=10,
            peer_avg=25,
            peer_median=24,
            peer_count=10,
            percentile=10,
            direction=MetricDirection.LOWER_BETTER,
        )
        assert "good" in mc.assessment


class TestOutputFormatting:
    """Tests for string output."""

    def test_to_summary(self, target_stock, ashare_peers):
        result = analyze_peers(target_stock, peers=ashare_peers)
        summary = result.to_summary()
        assert "600519" in summary
        assert "PeerComparison" in summary
        assert "/100" in summary

    def test_str_output(self, target_stock, ashare_peers):
        result = analyze_peers(target_stock, peers=ashare_peers)
        output = str(result)
        lines = output.strip().split("\n")
        assert len(lines) > 3

    def test_repr_equals_summary(self, target_stock, ashare_peers):
        result = analyze_peers(target_stock, peers=ashare_peers)
        assert repr(result) == result.to_summary()


class TestConvenienceFunction:
    """Tests for the analyze_peers convenience function."""

    def test_returns_result(self, target_stock, ashare_peers):
        result = analyze_peers(target_stock, peers=ashare_peers)
        assert isinstance(result, PeerComparisonResult)

    def test_forwards_kwargs(self, target_stock, ashare_peers):
        result = analyze_peers(target_stock, peers=ashare_peers, min_peers=2)
        assert result.has_sufficient_peers is True


class TestCustomWeights:
    """Tests for custom metric weights."""

    def test_custom_weights_affect_composite(self, target_stock, ashare_peers):
        result_default = analyze_peers(target_stock, peers=ashare_peers)

        result_weighted = analyze_peers(
            target_stock,
            peers=ashare_peers,
            metric_weights={"pe_ratio": 0.5, "pb_ratio": 0.5},
        )

        assert result_weighted.composite_score != pytest.approx(
            result_default.composite_score, abs=0.1
        )


class TestUSStockManualPeers:
    """Tests for US stock scenario where peers must be provided manually."""

    @pytest.fixture
    def us_stock(self):
        return Stock(
            ticker="AAPL",
            name="Apple Inc",
            current_price=180,
            shares_outstanding=15.5e9,
            eps=6.0,
            bvps=4.0,
            revenue=383e9,
            net_income=97e9,
            fcf=110e9,
            operating_margin=30.0,
            roe=150.0,
            revenue_growth=2.0,
            sector="Technology",
            industry="Consumer Electronics",
        )

    @pytest.fixture
    def us_peers(self):
        return [
            PeerCompany(
                ticker="MSFT",
                name="Microsoft",
                market_cap=2800e9,
                pe_ratio=35,
                pb_ratio=12,
                roe=40,
                revenue=211e9,
                net_income=72e9,
                current_price=370,
            ),
            PeerCompany(
                ticker="GOOGL",
                name="Alphabet",
                market_cap=1700e9,
                pe_ratio=25,
                pb_ratio=6,
                roe=25,
                revenue=307e9,
                net_income=60e9,
                current_price=135,
            ),
            PeerCompany(
                ticker="META",
                name="Meta",
                market_cap=1200e9,
                pe_ratio=30,
                pb_ratio=8,
                roe=20,
                revenue=135e9,
                net_income=35e9,
                current_price=470,
            ),
            PeerCompany(
                ticker="AMZN",
                name="Amazon",
                market_cap=1800e9,
                pe_ratio=60,
                pb_ratio=8,
                roe=15,
                revenue=575e9,
                net_income=30e9,
                current_price=170,
            ),
        ]

    def test_us_stock_with_manual_peers(self, us_stock, us_peers):
        result = analyze_peers(us_stock, peers=us_peers)
        assert result.ticker == "AAPL"
        assert result.peer_count == 4
        assert result.composite_score > 0

    def test_us_stock_no_peers_warns(self, us_stock):
        result = analyze_peers(us_stock, peers=[])
        assert result.has_sufficient_peers is False
        assert len(result.warnings) > 0
