"""Tests for the standalone Macrotrends fetcher (hand-built fixtures, no mocks).

Parsing tests run on inline HTML fixtures modelled on REAL captured pages
(NKE income-statement, captured 2026-10; trimmed + a few crafted rows for
edge cases). Live tests at the bottom require a local Chrome debug endpoint
and skip silently when it is down -- unlike test_fetcher.py's unguarded live
tests, these cannot run without the browser.
"""
import json
import math
from pathlib import Path

import pandas as pd
import pytest

from valueinvest.data.fetcher.cdp_chrome import is_debugger_alive
from valueinvest.data.fetcher.macrotrends import (
    MacrotrendsFetcher,
    _extract_original_data_json,
    _row_slug,
    _statement_url,
    _strip_label,
)

# --------------------------------------------------------------------------- #
# fixtures (real captured structure; values trimmed to 3 periods)
# --------------------------------------------------------------------------- #
_ROW_REVENUE = """{"field_name":"<a href='/stocks/charts/NKE/nike/revenue'>Revenue</a>",
"popup_icon":"<div class='ajax-chart' data-tipped-options=\\"ajax: {data: { t: 'NKE', s: 'revenue', freq: 'A', statement: 'income-statement' }}\\"><i class='fas fa-chart-bar'></i></div>",
"2024-05-31":"51362.00000","2025-05-31":"46309.00000","2026-05-31":"46398.00000"}"""

_ROW_SGA = """{"field_name":"<span style='color:#337ab7;'>SG&amp;A Expenses</span>",
"popup_icon":"<div class='ajax-chart' data-tipped-options=\\"ajax: {data: { t: 'NKE', s: 'sga-expenses', freq: 'A', statement: 'income-statement' }}\\"><i class='fas fa-chart-bar'></i></div>",
"2024-05-31":"12036.00000","2025-05-31":"11932.00000","2026-05-31":"11582.00000"}"""

_ROW_EPS = """{"field_name":"<a href='/stocks/charts/NKE/nike/eps-earnings-per-share-diluted'>EPS - Earnings Per Share</a>",
"popup_icon":"<div class='ajax-chart' data-tipped-options=\\"ajax: {data: { t: 'NKE', s: 'eps-earnings-per-share-diluted', freq: 'A', statement: 'income-statement' }}\\"><i class='fas fa-chart-bar'></i></div>",
"2024-05-31":"3.73000","2025-05-31":"2.73000","2026-05-31":"2.71000"}"""

_ROW_MIXED = """{"field_name":"<a href='/x'>Cash Flow From Operating Activities</a>",
"popup_icon":"<div class='ajax-chart' data-tipped-options=\\"ajax: {data: { t: 'NKE', s: 'cash-flow-from-operating-activities', freq: 'Q', statement: 'cash-flow-statement' }}\\"><i class='fas fa-chart-bar'></i></div>",
"2024-05-31":"7429.00000","2025-05-31":3698,"2026-05-31":2868}"""

_ROW_CAPEX = """{"field_name":"<a href='/x'>Net Change In Property, Plant, And Equipment</a>",
"popup_icon":"<div class='ajax-chart' data-tipped-options=\\"ajax: {data: { t: 'NKE', s: 'net-change-in-property-plant-equipment', freq: 'Q', statement: 'cash-flow-statement' }}\\"><i class='fas fa-chart-bar'></i></div>",
"2024-05-31":"-900.00000","2025-05-31":-800,"2026-05-31":-700}"""

_ROW_EMPTY = """{"field_name":"<span style='color:#337ab7;'>Research And Development Expenses</span>",
"popup_icon":"","2024-05-31":"","2025-05-31":"","2026-05-31":""}"""

_ROW_BRACKET = """{"field_name":"<a href='/x'>Weird [Label] Row</a>",
"popup_icon":"<div class='ajax-chart' data-tipped-options=\\"ajax: {data: { t: 'T', s: 'weird-label-row', note: 'a ] inside' }}\\"><i class='fas fa-chart-bar'></i></div>",
"2024-05-31":"1.00000"}"""


def _html(rows: str, tail: str = "<h2>Cash Flow</h2><p>footer text</p>") -> str:
    return f"<html><script>\nvar originalData = [{rows}];\n</script>{tail}</html>"


# --------------------------------------------------------------------------- #
# extraction
# --------------------------------------------------------------------------- #
class TestExtract:
    def test_simple(self):
        rows = _extract_original_data_json(_html(_ROW_REVENUE))
        assert rows is not None and '"46398.00000"' in rows

    def test_bracket_inside_string(self):
        rows = _extract_original_data_json(_html(_ROW_BRACKET))
        assert rows is not None
        import json

        parsed = json.loads(rows)
        assert parsed[0]["field_name"].endswith("Weird [Label] Row</a>")

    def test_missing_marker(self):
        assert _extract_original_data_json("<html><p>no data</p></html>") is None

    def test_truncated(self):
        html = "<script>var originalData = [{\"a\": \"1\"</script>"
        assert _extract_original_data_json(html) is None

    def test_trailing_junk_after_array(self):
        # the ";\\n" terminator is unreliable -- text after ] must not break us
        rows = _extract_original_data_json(
            _html(_ROW_REVENUE, tail=");\nvar x = 1; <b>more</b>"))
        assert rows is not None and '"46398.00000"' in rows


# --------------------------------------------------------------------------- #
# labels & slugs
# --------------------------------------------------------------------------- #
class TestLabels:
    def test_strip_anchor(self):
        assert _strip_label("<a href='/x'>Revenue</a>") == "Revenue"
        assert _strip_label("<a href='/x'>Net Income/Loss</a>") == "Net Income/Loss"

    def test_unescape_entity(self):
        assert _strip_label("<span>SG&amp;A Expenses</span>") == "SG&A Expenses"

    def test_slug(self):
        icon = "ajax: {data: { t: 'NKE', s: 'cash-flow-from-operating-activities', freq: 'Q' }}"
        assert _row_slug(icon) == "cash-flow-from-operating-activities"

    def test_slug_empty(self):
        assert _row_slug("") is None
        assert _row_slug("<div>no spec</div>") is None


# --------------------------------------------------------------------------- #
# numbers
# --------------------------------------------------------------------------- #
class TestParseNum:
    parse = staticmethod(MacrotrendsFetcher._parse_num)

    def test_string_millions(self):
        assert self.parse("6794.00000") == 6.794e9

    def test_json_number_also_millions(self):
        # recent quarters arrive as bare numbers, still in millions
        assert self.parse(579) == 5.79e8
        assert self.parse(3698.0) == 3.698e9

    def test_empty_and_none_are_nan(self):
        assert math.isnan(self.parse(""))
        assert math.isnan(self.parse(None))
        assert math.isnan(self.parse("  "))

    def test_bool_is_nan(self):
        assert math.isnan(self.parse(True))

    def test_garbage_is_nan(self):
        assert math.isnan(self.parse("N/A"))

    def test_per_share_not_scaled(self):
        assert self.parse("2.73000", per_share=True) == 2.73
        assert self.parse(2.73, per_share=True) == 2.73


# --------------------------------------------------------------------------- #
# frame building
# --------------------------------------------------------------------------- #
class TestRowsToFrame:
    def _frame(self, rows_html: str) -> pd.DataFrame:
        import json

        rows = json.loads(f"[{rows_html}]")
        from valueinvest.data.fetcher.macrotrends import _INCOME_MAP

        return MacrotrendsFetcher._rows_to_frame(rows, _INCOME_MAP)

    def test_label_and_slug_match(self):
        df = self._frame(f"{_ROW_REVENUE},\n{_ROW_SGA}")
        assert list(df.columns) == ["revenue", "sga"]
        assert df.loc[pd.Timestamp("2026-05-31"), "revenue"] == 4.6398e10

    def test_slug_only_match(self):
        # site renames the display label; slug still resolves the row
        row = _ROW_REVENUE.replace(">Revenue</a>", ">Total Revenue</a>")
        df = self._frame(row)
        assert "revenue" in df.columns

    def test_eps_not_scaled(self):
        df = self._frame(_ROW_EPS)
        assert df.loc[pd.Timestamp("2026-05-31"), "eps_diluted"] == pytest.approx(2.71)

    def test_mixed_string_number_cells(self):
        import json

        rows = json.loads(f"[{_ROW_MIXED}]")
        from valueinvest.data.fetcher.macrotrends import _CASHFLOW_MAP

        df = MacrotrendsFetcher._rows_to_frame(rows, _CASHFLOW_MAP)
        assert df.loc[pd.Timestamp("2025-05-31"), "operating_cash_flow"] == 3.698e9
        assert df.loc[pd.Timestamp("2026-05-31"), "operating_cash_flow"] == 2.868e9

    def test_unmapped_rows_dropped(self):
        unmapped = _ROW_BRACKET.replace(
            "'weird-label-row'", "'totally-unknown-row'")  # label & slug both unmapped
        df = self._frame(f"{_ROW_REVENUE},\n{unmapped}")
        assert list(df.columns) == ["revenue"]

    def test_ascending_index_and_nan_preserved(self):
        import json

        rows = json.loads(f"[{_ROW_REVENUE},\n{_ROW_EMPTY}]")
        from valueinvest.data.fetcher.macrotrends import _INCOME_MAP

        df = MacrotrendsFetcher._rows_to_frame(rows, _INCOME_MAP)
        assert df.index.is_monotonic_increasing
        assert df["rnd"].isna().all()

    def test_non_iso_keys_skipped(self):

        row = _ROW_REVENUE.replace('"2024-05-31":"51362.00000"',
                                   '"TTM":"50000.00000","2024-05-31":"51362.00000"')
        df = self._frame(row)
        assert list(df.index) == [pd.Timestamp("2024-05-31"),
                                  pd.Timestamp("2025-05-31"),
                                  pd.Timestamp("2026-05-31")]


class TestCashFlowPost:
    def test_capex_normalized_and_fcf(self):
        rows = json.loads(f"[{_ROW_MIXED},\n{_ROW_CAPEX}]")
        from valueinvest.data.fetcher.macrotrends import _CASHFLOW_MAP

        df = MacrotrendsFetcher._postprocess_cash_flow(
            MacrotrendsFetcher._rows_to_frame(rows, _CASHFLOW_MAP))
        capex = df.loc[pd.Timestamp("2026-05-31"), "capex"]
        fcf = df.loc[pd.Timestamp("2026-05-31"), "free_cash_flow"]
        assert capex == -7e8  # string "-700.00000" -> abs -> negative
        assert fcf == df.loc[pd.Timestamp("2026-05-31"), "operating_cash_flow"] + capex

    def test_capex_abs_applied_to_positive_too(self):
        df = pd.DataFrame({"operating_cash_flow": [1e9], "capex": [5e8]})
        out = MacrotrendsFetcher._postprocess_cash_flow(df)
        assert out.loc[0, "capex"] == -5e8
        assert out.loc[0, "free_cash_flow"] == 5e8

    def test_nan_capex_propagates_to_fcf(self):
        df = pd.DataFrame({"operating_cash_flow": [1e9], "capex": [float("nan")]})
        out = MacrotrendsFetcher._postprocess_cash_flow(df)
        assert math.isnan(out.loc[0, "free_cash_flow"])

    def test_empty_frame_untouched(self):
        out = MacrotrendsFetcher._postprocess_cash_flow(pd.DataFrame())
        assert out.empty


# --------------------------------------------------------------------------- #
# urls & validation
# --------------------------------------------------------------------------- #
class TestUrls:
    def test_annual(self):
        assert _statement_url("NKE", "nike", "cash_flow", "annual") == (
            "https://www.macrotrends.net/stocks/charts/nke/nike/cash-flow-statement")

    def test_quarterly(self):
        assert _statement_url("SPCX", "space-exploration-technologies", "income",
                              "quarterly") == (
            "https://www.macrotrends.net/stocks/charts/spcx/space-exploration-technologies"
            "/income-statement?freq=Q")

    def test_bad_statement_raises(self):
        f = MacrotrendsFetcher()
        with pytest.raises(ValueError):
            f.fetch("NKE", ("nope",))

    def test_bad_freq_raises(self):
        f = MacrotrendsFetcher()
        with pytest.raises(ValueError):
            f.fetch("NKE", ("income",), freq="monthly")


# --------------------------------------------------------------------------- #
# cache
# --------------------------------------------------------------------------- #
class TestCache:
    def _fetcher(self, tmp_path: Path) -> MacrotrendsFetcher:
        return MacrotrendsFetcher(cache_dir=tmp_path / "cache", ttl_seconds=3600)

    def test_roundtrip(self, tmp_path):
        f = self._fetcher(tmp_path)
        assert f._cache_read("NKE", "income", "annual") is None
        f._cache_write("NKE", "income", "annual", [{"a": 1}], "NKE")
        hit = f._cache_read("NKE", "income", "annual")
        assert hit is not None and hit["rows"] == [{"a": 1}]
        assert hit["canonical_ticker"] == "NKE"

    def test_ttl_expiry(self, tmp_path):
        import time as _time

        f = self._fetcher(tmp_path)
        f._cache_write("NKE", "income", "annual", [{"a": 1}], "NKE")
        path = f._cache_path("NKE", "income", "annual")
        record = json.loads(path.read_text())
        record["fetched_at"] = _time.time() - 3601
        path.write_text(json.dumps(record))
        assert f._cache_read("NKE", "income", "annual") is None

    def test_corrupt_is_miss(self, tmp_path):
        f = self._fetcher(tmp_path)
        f.cache_dir.mkdir(parents=True)
        f._cache_path("NKE", "income", "annual").write_text("{not json")
        assert f._cache_read("NKE", "income", "annual") is None


# --------------------------------------------------------------------------- #
# live tests (need local Chrome on the CDP port; skip when it is down)
# --------------------------------------------------------------------------- #
_CDP_UP = is_debugger_alive()


@pytest.mark.skipif(not _CDP_UP, reason="local Chrome debug endpoint not running")
class TestLiveMacrotrends:
    def test_nke_quarterly_long_history(self):
        f = MacrotrendsFetcher()
        df = f.fetch_statement("NKE", "cash_flow", freq="quarterly")
        assert not df.empty
        assert len(df) >= 50  # ~15 years of quarters
        assert "free_cash_flow" in df.columns
        assert df["operating_cash_flow"].iloc[-1] != 0

    def test_nke_annual_income(self):
        f = MacrotrendsFetcher()
        df = f.fetch_statement("NKE", "income", freq="annual")
        assert not df.empty
        assert len(df) >= 10
        assert df["revenue"].iloc[-1] > 0

    def test_spcx_short_history(self):
        # IPO'd 2026: only ~3 annual periods; exercises the short-history path
        f = MacrotrendsFetcher()
        df = f.fetch_statement("SPCX", "income", freq="annual")
        assert not df.empty
        assert 1 <= len(df) <= 5
        assert df["revenue"].iloc[-1] > 0
