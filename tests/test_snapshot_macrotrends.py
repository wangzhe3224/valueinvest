"""Tests for the stock_snapshot macrotrends spine (hand-built fixtures, no
mocks, no network): builds statement frames directly and exercises the pure
`_mt_spine_from_frames` builder -- FY labeling, TTM NaN poisoning, ratio
units, anchor capping, and the fallback guards."""
import math
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from stock_snapshot import _mt_spine_from_frames  # noqa: E402

Q = pd.bdate_range("2022-03-31", "2026-03-31", freq="QE")  # 17 quarter ends
ISO = [d.date().isoformat() for d in Q]


def _frame(index, **cols):
    n = len(index)
    return pd.DataFrame({k: [v] * n for k, v in cols.items()},
                        index=pd.DatetimeIndex(index))


def _frames(**overrides):
    """17 quarters (2022Q1..2026Q1), Dec FYE; revenue 1e9, gp 0.4e9, ni 0.1e9,
    ocf 0.15e9, fcf 0.1e9, equity 3e9, assets 5e9, liab 2e9, shares 1.2e8."""
    inc = _frame(ISO, revenue=1e9, gross_profit=0.4e9, net_income=0.1e9,
                 shares_diluted=1.2e8)
    bs = _frame(ISO, total_assets=5e9, total_liabilities=2e9, total_equity=3e9,
                long_term_debt=1e9, cash=0.5e9)
    cf = _frame(ISO, operating_cash_flow=0.15e9, capex=-0.05e9, free_cash_flow=0.1e9,
                stock_based_compensation=0.01e9, common_dividends_paid=-0.02e9,
                net_equity_issued=-0.03e9)
    for df, cols in overrides.items():
        for k, v in cols.items():
            df.loc[k[0], k[1]] = v
    ann = _frame([iso for iso in ISO if iso.endswith("12-31")], revenue=4e9)
    return inc, bs, cf, ann


CLOSES_8Q = {iso: 10.0 for iso in ISO[-8:]}  # ~2y of closes


def test_dates_maps_and_units():
    inc, bs, cf, ann = _frames()
    sp = _mt_spine_from_frames(inc, bs, cf, ann, CLOSES_8Q, 10.0)
    assert sp["dates"] == ISO
    assert len(sp["anchor_list"]) == 5  # 4 FYEs + the in-progress TTM anchor
    # ratio units mirror the stockanalysis blob conventions
    last = ISO[-1]
    assert sp["ratios"]["roe"][last] == pytest.approx(0.4e9 / 3e9 * 100)  # percent
    assert sp["ratios"]["fcfy"][last] == pytest.approx(0.4e9 / 1.2e9)  # fraction
    assert sp["ratios"]["de"][last] == pytest.approx(1e9 / 3e9)  # fraction
    assert sp["ratios"]["pe"][last] == pytest.approx(1.2e9 / 0.4e9)


def test_fy_labels_and_ttm_anchor():
    inc, bs, cf, ann = _frames()
    sp = _mt_spine_from_frames(inc, bs, cf, ann, CLOSES_8Q, 10.0)
    fys = [a["fy"] for a in sp["anchor_list"]]
    assert fys == [2022, 2023, 2024, 2025, 2026]  # TTM anchor = in-progress FY2026
    assert sp["anchor_list"][-1]["date"] == "2026-03-31"
    assert sp["anchor_list"][0]["date"] == "2022-12-31"
    # ann_* includes the TTM anchor so ann_newest() reads the current value
    assert sp["ann_roe"][2026] == pytest.approx(0.4e9 / 3e9 * 100)


def test_anchor_cap_at_10_fys():
    inc, bs, cf, ann = _frames()
    # 13 fiscal year ends -> anchor list capped to 10 FYs + TTM = 11
    long_fyes = [f"{y}-12-31" for y in range(2014, 2027)]
    long_ann = _frame([iso for iso in long_fyes if iso in set(ISO)], revenue=4e9)
    # give the annual frame the full FYE list even where quarters are absent:
    # builder intersects FYEs with the quarterly grid, so simulate 13 FYEs by
    # extending the quarterly grid back instead
    early = [f"{y}-{q}" for y in range(2014, 2022) for q in ("03-31", "06-30", "09-30", "12-31")]
    grid = early + ISO
    inc = _frame(grid, revenue=1e9, gross_profit=0.4e9, net_income=0.1e9,
                 shares_diluted=1.2e8)
    bs = _frame(grid, total_assets=5e9, total_liabilities=2e9, total_equity=3e9,
                long_term_debt=1e9, cash=0.5e9)
    cf = _frame(grid, operating_cash_flow=0.15e9, capex=-0.05e9, free_cash_flow=0.1e9,
                stock_based_compensation=0.01e9, common_dividends_paid=-0.02e9,
                net_equity_issued=-0.03e9)
    long_ann = _frame(long_fyes, revenue=4e9)
    sp = _mt_spine_from_frames(inc, bs, cf, long_ann, CLOSES_8Q, 10.0)
    assert len(sp["anchor_list"]) == 11
    assert sp["anchor_list"][0]["fy"] == 2016  # last 10 full FYs + TTM


def test_ratio_window_limited_by_closes():
    inc, bs, cf, ann = _frames()
    sp = _mt_spine_from_frames(inc, bs, cf, ann, CLOSES_8Q, 10.0)
    assert sp["ratios"]["pe"][ISO[0]] is None  # no close that far back
    assert sp["ratios"]["pe"][ISO[-1]] is not None
    # but statements themselves are full-depth
    assert sp["maps"]["rev"][ISO[0]] == 1e9


def test_ttm_nan_poison():
    inc, bs, cf, ann = _frames()
    # poison a quarter inside the closes window but OUTSIDE the latest TTM
    # window: PEs of the 3 following quarters are poisoned; the latest TTM
    # (and the guard) is unaffected. Poisoning the LATEST window instead
    # trips the ValueError guard (see test_guards / the SPCX fallback case).
    inc.loc["2024-06-30", "revenue"] = math.nan
    sp = _mt_spine_from_frames(inc, bs, cf, ann, CLOSES_8Q, 10.0)
    assert sp["maps"]["rev"]["2024-06-30"] is None
    # PS rides TTM revenue -> poisoned for the 3 windows covering the gap;
    # PE rides TTM net income (intact) -> unaffected
    for iso in ("2024-09-30", "2024-12-31", "2025-03-31"):
        assert sp["ratios"]["ps"][iso] is None
        assert sp["ratios"]["pe"][iso] == pytest.approx(3.0)
    assert sp["ratios"]["ps"][ISO[-1]] == pytest.approx(0.3)  # 1.2e9 / (4 x 1e9)
    assert sp["current"]["ps"] is not None  # latest TTM revenue intact


def test_guards_trigger_fallback():
    inc, bs, cf, ann = _frames()
    with pytest.raises(ValueError, match="quarters"):
        _mt_spine_from_frames(inc.iloc[-10:], bs.iloc[-10:], cf.iloc[-10:],
                              ann, CLOSES_8Q, 10.0)
    with pytest.raises(ValueError, match="revenue"):
        inc_no_rev = inc.drop(columns=["revenue"])
        _mt_spine_from_frames(inc_no_rev, bs, cf, ann, CLOSES_8Q, 10.0)
    with pytest.raises(ValueError, match="total_equity"):
        bs_no_eq = bs.drop(columns=["total_equity"])
        _mt_spine_from_frames(inc, bs_no_eq, cf, ann, CLOSES_8Q, 10.0)


def test_current_values():
    inc, bs, cf, ann = _frames()
    sp = _mt_spine_from_frames(inc, bs, cf, ann, CLOSES_8Q, 10.0)
    cur = sp["current"]
    cap_now = 1.2e8 * 10.0
    assert cur["mcap"] == pytest.approx(cap_now)
    assert cur["pe"] == pytest.approx(cap_now / 0.4e9)
    assert cur["fcfy"] == pytest.approx(0.4e9 / cap_now)  # fraction
    assert cur["divy"] == pytest.approx(0.08e9 / cap_now)  # -(-0.02e9*4)/cap
    assert cur["price"] == 10.0


def test_no_closes_means_no_current():
    inc, bs, cf, ann = _frames()
    sp = _mt_spine_from_frames(inc, bs, cf, ann, {}, None)
    assert sp["current"] is None
    assert all(v is None for v in sp["ratios"]["pe"].values())
