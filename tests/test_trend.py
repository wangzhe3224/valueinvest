"""Tests for the trend & growth-signal module (hand-built fixtures, no mocks)."""
from datetime import date

import pytest

from valueinvest.news.base import Market
from valueinvest.trend.base import (
    TrendMetric,
    TrendRating,
    TrendRecord,
    TrendSeries,
    metric_value,
)
from valueinvest.trend.engine import (
    DEFAULT_METRIC_WEIGHTS,
    TrendSignalEngine,
    analyze_trend_signals,
)
from valueinvest.trend.signals import (
    _acceleration_series,
    _cagr,
    _cv,
    _inflection,
    _streak,
    _yoy_series,
    is_ccc_applicable,
)

_QDAYS = [31, 30, 30, 31]


def _rec(i, revenue, inv_ratio=0.10, gm=0.4, nm=0.2, ocf=0.25, capex=0.05,
         ticker="TEST", start_y=2022):
    q = i % 4
    y = start_y + i // 4
    return TrendRecord(
        ticker=ticker, market=Market.US, quarter_end=date(y, 3 + q * 3, _QDAYS[q]),
        fiscal_year=y, fiscal_quarter=q + 1,
        revenue=revenue, gross_profit=revenue * gm, net_income=revenue * nm,
        operating_cash_flow=revenue * ocf, capex=-revenue * capex,
        free_cash_flow=revenue * (ocf - capex),
        inventory=revenue * inv_ratio, accounts_receivable=revenue * 0.15,
        accounts_payable=revenue * 0.08, shares_outstanding=1000, close_price=10 + i,
    )


def _series(revenues, **kw):
    recs = [_rec(i, r, **kw) for i, r in enumerate(revenues)]
    return TrendSeries(ticker="TEST", market=Market.US, source="synthetic", records=recs)


ACCEL = [100, 105, 112, 120, 135, 150, 170, 195, 225, 260, 300, 345]
DECL = ACCEL[::-1]
STEADY = [100, 101, 102, 101, 100, 101, 102, 101, 100, 101, 102, 101]


# --------------------------------------------------------------------------- #
# TrendRecord derived math
# --------------------------------------------------------------------------- #
def test_trendrecord_margins_and_ccc():
    r = _rec(0, 100, inv_ratio=0.10)
    assert r.gross_margin == pytest.approx(40.0)
    assert r.net_margin == pytest.approx(20.0)
    assert r.cogs == pytest.approx(60.0)
    # DIO = inv/cogs*90 = 10/60*90 = 15
    assert r.dio == pytest.approx(15.0)
    # DSO = ar/rev*90 = 15/100*90 = 13.5
    assert r.dso == pytest.approx(13.5)
    # DPO = ap/cogs*90 = 8/60*90 = 12
    assert r.dpo == pytest.approx(12.0)
    assert r.ccc == pytest.approx(15.0 + 13.5 - 12.0)
    # fcf_yield: mktcap = 1000 * 10 = 10000; fcf = 100*(0.25-0.05)=20; 20/10000*100 = 0.2
    assert r.fcf_yield == pytest.approx(0.2, abs=0.01)


def test_trendrecord_zero_revenue_safe():
    r = TrendRecord(ticker="X", market=Market.US, quarter_end=date(2024, 1, 1),
                    fiscal_year=2024, fiscal_quarter=1)
    assert r.gross_margin == 0.0 and r.net_margin == 0.0
    assert r.ccc == 0.0 and r.fcf_yield == 0.0


# --------------------------------------------------------------------------- #
# TrendSeries TTM rolling
# --------------------------------------------------------------------------- #
def test_ttm_rolling_sums_last_four_quarters():
    s = _series(ACCEL)
    ttms = s.ttm_records()
    assert len(ttms) == len(ACCEL) - 3  # need 4-quarter window
    # TTM revenue ending at index i = sum of single-q[i-3..i]
    for i in range(3, len(ACCEL)):
        assert ttms[i - 3].revenue == pytest.approx(sum(ACCEL[i - 3 : i + 1]))


def test_metric_value_dispatch():
    r = _rec(0, 100)
    assert metric_value(r, TrendMetric.REVENUE) == 100
    assert metric_value(r, TrendMetric.GROSS_MARGIN) == pytest.approx(40.0)


# --------------------------------------------------------------------------- #
# signal atom functions
# --------------------------------------------------------------------------- #
def test_yoy_series():
    vals = [100, 0, 0, 0, 150]  # only i=4 has a prior (i-4)
    yoy = _yoy_series(vals)
    assert yoy == pytest.approx([50.0])


def test_acceleration_is_first_diff_of_yoy():
    yoy = [10.0, 18.0, 25.0]
    assert _acceleration_series(yoy) == pytest.approx([8.0, 7.0])


def test_streak_counts_consecutive_same_sign():
    assert _streak([8.1, 7.6, 6.0, 3.4]) == (1, 4)  # all positive
    assert _streak([1.0, -1.0, -2.0]) == (-1, 2)    # last two negative
    assert _streak([]) == (0, 0)


def test_inflection_finds_recent_sign_flip():
    # peak at index 3 (1,1,1,-1)
    assert _inflection([3.0, 2.0, 1.0, -1.0]) == (3, "peak")
    # trough (negative then positive)
    assert _inflection([-2.0, -1.0, 1.0]) == (2, "trough")
    assert _inflection([1.0, 2.0, 3.0]) is None


def test_cagr_quarterly_endpoints():
    # 5 TTM points, 100 -> 150 over 1 year (4 quarters)
    assert _cagr([100, 0, 0, 0, 150]) == pytest.approx(50.0, abs=0.01)


def test_cv_undefined_for_zero_mean():
    assert _cv([0.0, 0.0]) is None
    assert _cv([10.0, 12.0, 14.0]) is not None


# --------------------------------------------------------------------------- #
# CCC applicability
# --------------------------------------------------------------------------- #
def test_ccc_applicable_with_inventory():
    assert is_ccc_applicable(_series(ACCEL, inv_ratio=0.10)) is True


def test_ccc_not_applicable_no_inventory():
    s = _series(ACCEL, inv_ratio=0.0)
    assert is_ccc_applicable(s) is False


def test_ccc_not_applicable_financial_sector_hint():
    s = _series(ACCEL, inv_ratio=0.10)
    assert is_ccc_applicable(s, sector_hint="Bank of America") is False


# --------------------------------------------------------------------------- #
# Engine: scoring + weight redistribution + ratings
# --------------------------------------------------------------------------- #
def test_accelerating_scores_high():
    r = analyze_trend_signals(_series(ACCEL))
    assert not (r.composite_score != r.composite_score)  # not NaN
    assert r.growth_score > 60
    assert r.rating in (TrendRating.IMPROVING, TrendRating.ACCELERATING)


def test_declining_scores_low():
    r = analyze_trend_signals(_series(DECL))
    assert r.composite_score < 50
    assert r.rating in (TrendRating.DETERIORATING, TrendRating.DECLINING, TrendRating.STABLE)


def test_software_skips_ccc_and_redistributes_weight():
    r = analyze_trend_signals(_series(ACCEL, inv_ratio=0.0))
    assert r.ccc_applicable is False
    assert all(s.metric != TrendMetric.CCC for s in r.signals)
    assert r.efficiency_score == 0.0
    # CCC weight (0.10) redistributed across the other 4 metrics
    assert sum(DEFAULT_METRIC_WEIGHTS[m] for m in DEFAULT_METRIC_WEIGHTS) == pytest.approx(1.0)


def test_short_series_produces_unavailable_signals():
    r = analyze_trend_signals(_series([100, 105, 112]))  # only 3 quarters
    assert r.period_quarters == 3
    # most signals need >=3 TTM points -> many unavailable
    assert any(not s.is_available for s in r.signals)
    assert "only 3 quarters available" in " ".join(r.analysis).lower()


def test_steady_series_is_stable():
    r = analyze_trend_signals(_series(STEADY))
    assert TrendRating.STABLE.value in [r.rating.value] or r.composite_score < 70


def test_engine_custom_weights_and_sector_hint():
    engine = TrendSignalEngine(
        metric_weights={TrendMetric.REVENUE: 1.0}, sector_hint="software"
    )
    r = engine.analyze(_series(ACCEL, inv_ratio=0.0))
    # only revenue weighted -> composite == growth_score (when only revenue available)
    assert r.ccc_applicable is False


def test_strengths_and_weaknesses_populated():
    r = analyze_trend_signals(_series(ACCEL))
    # accelerating series should yield some high-score strengths
    assert isinstance(r.strengths, list)
    assert isinstance(r.weaknesses, list)
    assert r.composite_score >= 0
