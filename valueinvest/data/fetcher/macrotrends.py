"""Standalone fundamentals fetcher for macrotrends.net financial statements.

macrotrends.net publishes ~15 years of annual and ~59 quarters of quarterly
financial statements (income / balance-sheet / cash-flow) -- far longer
history than stockanalysis.com (~5y). The catch: the site sits behind a
Cloudflare managed challenge that blocks every plain-HTTP client, so this
fetcher drives a local headed Chrome via :mod:`.cdp_chrome` (CDP over
websocket) and extracts the ``var originalData = [...]`` JSON embedded in
each statement page.

Values arrive as strings in millions of USD and are scaled to absolute;
``""`` (not reported) becomes NaN, never 0.0. EPS rows are per-share dollars
and are NOT scaled. Cash-flow frames get two post-processing steps: capex
normalized to negative (``-abs()``, matching the stockanalysis fetcher
convention) and a computed ``free_cash_flow = operating_cash_flow + capex``
(macrotrends embeds no FCF row).

This fetcher is deliberately STANDALONE: it is not registered in
:data:`valueinvest.data.fetcher.get_fetcher` nor in any trend registry --
call it directly::

    from valueinvest.data.fetcher.macrotrends import MacrotrendsFetcher

    f = MacrotrendsFetcher()
    df = f.fetch_statement("NKE", "cash_flow", freq="quarterly")

Disk cache (parsed rows, 12h TTL, under /tmp) keeps repeat calls off the
wire. Requires a local Chrome (see :mod:`.cdp_chrome`); first cold use may
require completing a Cloudflare check in the visible Chrome window.
"""
from __future__ import annotations

import html as _html
import json
import math
import re
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from .cdp_chrome import CDPTab, ChromeDebuggerError

__all__ = [
    "DEFAULT_TTL_SECONDS",
    "MacrotrendsData",
    "MacrotrendsFetcher",
]

# --------------------------------------------------------------------------- #
# Site constants (all verified against live pages)
# --------------------------------------------------------------------------- #
_STATEMENT_SLUGS: dict[str, str] = {
    "income": "income-statement",
    "balance_sheet": "balance-sheet",
    "cash_flow": "cash-flow-statement",
}
_FREQ_PARAM: dict[str, str] = {"annual": "", "quarterly": "?freq=Q"}
_BASE_URL = "https://www.macrotrends.net/stocks/charts"

DEFAULT_TTL_SECONDS = 12 * 3600
_CACHE_DIR = Path("/tmp/valueinvest_macrotrends_cache")

# Browser-cache trap: fetching "<page>?freq=Q" in-page can serve the cached
# ANNUAL body for the same path unless the cache is bypassed. Verified live.
_FETCH_DELAY_S = 1.5  # macrotrends rate-limits rapid in-page fetches (429)
_RATE_LIMIT_RETRIES = 2
_RATE_LIMIT_WAIT_S = 8.0

_ISO_KEY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SLUG_RE = re.compile(r"s:\s*'([a-z0-9\-]+)'")
_TAG_RE = re.compile(r"<[^>]+>")

# --------------------------------------------------------------------------- #
# Alias maps: canonical name <- {display labels AND canonical slugs}.
# Labels were dumped from live NKE pages (2026-10); slugs are the stable
# fallback (labels drift more than slugs). Unknown rows are silently skipped
# into raw_rows, so a site redesign degrades to missing columns, not a crash.
# --------------------------------------------------------------------------- #
_INCOME_MAP: dict[str, set[str]] = {
    "revenue": {"Revenue", "revenue"},
    "cogs": {"Cost Of Goods Sold", "cost-goods-sold"},
    "gross_profit": {"Gross Profit", "gross-profit"},
    "rnd": {"Research And Development Expenses", "research-and-development-expenses"},
    "sga": {"SG&A Expenses", "sga-expenses"},
    "other_operating": {"Other Operating Income Or Expenses",
                        "other-operating-income-or-expenses"},
    "operating_expenses": {"Operating Expenses", "operating-expenses"},
    "operating_income": {"Operating Income", "operating-income"},
    "non_operating_total": {"Total Non-Operating Income/Expense",
                            "total-non-operating-income-expense"},
    "pretax_income": {"Pre-Tax Income", "pre-tax-income"},
    "income_tax": {"Income Taxes", "total-provision-income-taxes"},
    "income_after_taxes": {"Income After Taxes", "income-after-taxes"},
    "income_continuous": {"Income From Continuous Operations",
                          "income-from-continuous-operations"},
    "income_discontinued": {"Income From Discontinued Operations",
                            "income-from-discontinued-operations"},
    "net_income": {"Net Income", "net-income"},
    "ebitda": {"EBITDA", "ebitda"},
    "ebit": {"EBIT", "ebit"},
    "shares_basic": {"Basic Shares Outstanding", "basic-shares-outstanding"},
    "shares_diluted": {"Shares Outstanding", "shares-outstanding"},
    "eps_basic": {"Basic EPS", "eps-basic-net-earnings-per-share"},
    "eps_diluted": {"EPS - Earnings Per Share", "eps-earnings-per-share-diluted"},
}

# Per-share dollar fields: reported in dollars, NOT millions -- never x1e6.
_PS_DOLLAR_FIELDS = {"eps_basic", "eps_diluted"}

_BALANCE_MAP: dict[str, set[str]] = {
    "cash": {"Cash On Hand", "cash-on-hand"},
    "receivables": {"Receivables", "receivables-total"},
    "inventory": {"Inventory", "inventory"},
    "prepaid_expenses": {"Pre-Paid Expenses", "pre-paid-expenses"},
    "other_current_assets": {"Other Current Assets"},
    "total_current_assets": {"Total Current Assets", "total-current-assets"},
    "ppe": {"Property, Plant, And Equipment", "net-property-plant-equipment"},
    "long_term_investments": {"Long-Term Investments"},
    "goodwill_intangibles": {"Goodwill And Intangible Assets",
                             "goodwill-intangible-assets-total"},
    "other_long_term_assets": {"Other Long-Term Assets"},
    "total_long_term_assets": {"Total Long-Term Assets", "total-long-term-assets"},
    "total_assets": {"Total Assets", "total-assets"},
    "total_current_liabilities": {"Total Current Liabilities", "total-current-liabilities"},
    # no standalone AP row for NKE (folded into total_current_liabilities);
    # kept as candidate -- companies that do report it surface automatically
    "payables": {"Accounts Payable", "accounts-payable"},
    "short_term_debt": {"Short Term Debt", "Current Portion Of Long Term Debt",
                        "short-term-debt"},
    "long_term_debt": {"Long Term Debt", "long-term-debt"},
    "other_non_current_liabilities": {"Other Non-Current Liabilities"},
    "total_long_term_liabilities": {"Total Long Term Liabilities",
                                    "total-long-term-liabilities"},
    "total_liabilities": {"Total Liabilities", "total-liabilities"},
    "common_stock_net": {"Common Stock Net"},
    "retained_earnings": {"Retained Earnings (Accumulated Deficit)",
                          "retained-earnings-accumulated-deficit"},
    "comprehensive_income": {"Comprehensive Income"},
    "other_equity": {"Other Share Holders Equity"},
    "total_equity": {"Share Holder Equity", "Total Stockholders Equity",
                     "total-share-holder-equity", "total-equity"},
    "total_liab_and_equity": {"Total Liabilities And Share Holders Equity",
                              "total-liabilities-share-holders-equity"},
}

_CASHFLOW_MAP: dict[str, set[str]] = {
    # no FCF row on the site; free_cash_flow is COMPUTED in post-processing
    "net_income": {"Net Income/Loss", "net-income-loss"},
    "depreciation_amortization": {"Total Depreciation And Amortization - Cash Flow",
                                  "depreciation-amortization"},
    "other_non_cash": {"Other Non-Cash Items"},
    "total_non_cash": {"Total Non-Cash Items"},
    "change_receivables": {"Change In Accounts Receivable"},
    "change_inventory": {"Change In Inventories"},
    "change_payables": {"Change In Accounts Payable"},
    "change_other": {"Change In Assets/Liabilities"},
    "total_change_other": {"Total Change In Assets/Liabilities"},
    "operating_cash_flow": {"Cash Flow From Operating Activities",
                            "cash-flow-from-operating-activities"},
    "capex": {"Net Change In Property, Plant, And Equipment",
              "net-change-in-property-plant-equipment"},
    "change_intangibles": {"Net Change In Intangible Assets"},
    "acquisitions": {"Net Acquisitions/Divestitures"},
    "change_st_investments": {"Net Change In Short-term Investments"},
    "change_lt_investments": {"Net Change In Long-Term Investments"},
    "change_investments": {"Net Change In Investments - Total"},
    "investing_other": {"Investing Activities - Other"},
    "investing_cash_flow": {"Cash Flow From Investing Activities",
                            "cash-flow-from-investing-activities"},
    "net_lt_debt": {"Net Long-Term Debt"},
    "net_current_debt": {"Net Current Debt"},
    "net_debt_total": {"Debt Issuance/Retirement Net - Total"},
    "net_equity_issued": {"Net Common Equity Issued/Repurchased"},
    "net_equity_total": {"Net Total Equity Issued/Repurchased"},
    "dividends_paid": {"Total Common And Preferred Stock Dividends Paid"},
    "financing_other": {"Financial Activities - Other"},
    "financing_cash_flow": {"Cash Flow From Financial Activities",
                            "cash-flow-from-financing-activities"},
    "net_change_cash": {"Net Cash Flow"},
    "stock_based_compensation": {"Stock-Based Compensation"},
    "common_dividends_paid": {"Common Stock Dividends Paid"},
}
_ALIAS_MAPS: dict[str, dict[str, set[str]]] = {
    "income": _INCOME_MAP,
    "balance_sheet": _BALANCE_MAP,
    "cash_flow": _CASHFLOW_MAP,
}

# In-page extraction: resolve the canonical ticker/slug with one fetch (a
# placeholder-slug redirect DROPS the ?freq=Q query -> wrong data), then
# fetch each requested statement at its canonical URL. Every fetch bypasses
# the browser cache (see _FETCH_DELAY_S comment) and bracket-depth-scans out
# the originalData JSON (string/escape aware; the trailing ";\n" terminator
# is unreliable). The scan runs IN the page so N x ~70KB HTML never crosses
# CDP. Output is keyed by STATEMENT KEY: {key: {data, finalUrl} | {error}}.
_IN_PAGE_JS_TEMPLATE = """
(async () => {
  const MARKER = 'var originalData = ';
  const BASE = '__BASE__';
  const EXTRACT = (html) => {
    const i = html.indexOf(MARKER);
    if (i < 0) return null;
    const s = i + MARKER.length;
    let depth = 0, inStr = false, esc = false, end = -1;
    for (let j = s; j < html.length; j++) {
      const c = html[j];
      if (esc) { esc = false; continue; }
      if (c === '\\\\') { esc = true; continue; }
      if (c === '"') { inStr = !inStr; continue; }
      if (inStr) continue;
      if (c === '[' || c === '{') depth++;
      else if (c === ']' || c === '}') {
        depth--;
        if (depth === 0) { end = j + 1; break; }
      }
    }
    return end > 0 ? html.slice(s, end) : null;
  };
  const fetchOne = async (u) => {
    for (let attempt = 0; attempt <= __RETRIES__; attempt++) {
      try {
        const r = await fetch(u, { credentials: 'include', redirect: 'follow',
                                   cache: 'no-store' });
        if (r.status === 429 && attempt < __RETRIES__) {
          await new Promise(res => setTimeout(res, __RL_WAIT__ * 1000));
          continue;
        }
        return r.ok ? { data: EXTRACT(await r.text()), finalUrl: r.url }
                    : { error: 'HTTP ' + r.status };
      } catch (e) { return { error: String(e) }; }
    }
    return { error: 'rate limited (429) after ' + __RETRIES__ + ' retries' };
  };
  const out = {};
  const sleep = (ms) => new Promise(res => setTimeout(res, ms));

  // phase 1: resolve canonical ticker + slug via the income-statement page
  let tick = null, slug = null, resolved = null;
  await sleep(2000);  // settle after page load; the nav already hit this path
  const r0 = await fetchOne(BASE + '/__TICKER_LC__/__TICKER_LC__/income-statement');
  await sleep(__DELAY__ * 1000);
  if (r0 && r0.finalUrl) {
    const m = r0.finalUrl.match(/\\/charts\\/([^\\/]+)\\/([^\\/]+)\\//);
    if (m) {
      tick = m[1].toLowerCase();
      slug = m[2];
      resolved = r0;
    }
  }
  if (!tick) {
    return JSON.stringify({ __resolve__: { error: 'could not resolve canonical '
        + 'slug from ' + ((r0 && r0.finalUrl) || 'no response') } });
  }

  // phase 2: fetch each requested task at its canonical URL
  for (const task of __TASKS__) {
    const [key, stSlug, freqParam] = task;
    if (freqParam === '' && stSlug === 'income-statement') {
      out[key] = resolved;  // the resolve fetch already produced this body
      continue;
    }
    const u = BASE + '/' + tick + '/' + slug + '/' + stSlug + freqParam;
    out[key] = await fetchOne(u);
    await sleep(__DELAY__ * 1000);
  }
  return JSON.stringify({ __resolve__: { tick: tick, slug: slug }, ...out });
})()
"""


def _statement_url(canonical_ticker: str, slug: str, statement: str,
                   freq: str) -> str:
    """Build a canonical statement URL (no redirect expected: the redirect
    for a placeholder slug drops the ``?freq=Q`` query, silently returning
    the ANNUAL body -- verified live; hence slugs must be resolved first)."""
    return (f"{_BASE_URL}/{canonical_ticker.lower()}/{slug}"
            f"/{_STATEMENT_SLUGS[statement]}{_FREQ_PARAM[freq]}")


def _strip_label(field_name: str) -> str:
    """``"<a ...>SG&amp;A Expenses</a>"`` -> ``"SG&A Expenses"``."""
    return _html.unescape(_TAG_RE.sub("", field_name)).strip()


def _row_slug(popup_icon: str) -> str | None:
    """Extract the canonical row slug from the popup chart spec."""
    m = _SLUG_RE.search(popup_icon or "")
    return m.group(1) if m else None


def _extract_original_data_json(html: str) -> str | None:
    """Python mirror of the in-page bracket scanner (used by tests and as a
    fallback for already-fetched HTML). Returns the JSON array substring."""
    marker = "var originalData = "
    i = html.find(marker)
    if i < 0:
        return None
    s = i + len(marker)
    depth, in_str, esc, end = 0, False, False, -1
    for j in range(s, len(html)):
        c = html[j]
        if esc:
            esc = False
            continue
        if c == "\\":
            esc = True
            continue
        if c == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if c in "[{":
            depth += 1
        elif c in "]}":
            depth -= 1
            if depth == 0:
                end = j + 1
                break
    return html[s:end] if end > 0 else None


class MacrotrendsFetcher:
    """Standalone macrotrends.net fundamentals fetcher (Chrome CDP transport)."""

    source_name = "macrotrends"

    def __init__(self, cdp_port: int | None = None,
                 ttl_seconds: float = DEFAULT_TTL_SECONDS,
                 cache_dir: Path | None = None) -> None:
        self.cdp_port = cdp_port
        self.ttl_seconds = ttl_seconds
        self.cache_dir = Path(cache_dir) if cache_dir else _CACHE_DIR

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #
    def fetch(self, ticker: str,
              statements: Sequence[str] = ("income", "balance_sheet", "cash_flow"),
              freq: str = "annual", refresh: bool = False) -> MacrotrendsData:
        """Fetch one or more statements (annual or quarterly) for a ticker.

        One Chrome tab serves all requested URLs: the first uncached URL is
        navigated to (solving any Cloudflare challenge), the rest are fetched
        in-page. Data-level problems land in ``MacrotrendsData.errors``;
        only transport failures (no Chrome, challenge unsolved) raise.
        """
        ticker = ticker.strip().upper()
        for s in statements:
            if s not in _STATEMENT_SLUGS:
                raise ValueError(f"Unknown statement {s!r}; "
                                 f"expected one of {sorted(_STATEMENT_SLUGS)}")
        if freq not in _FREQ_PARAM:
            raise ValueError(f"Unknown freq {freq!r}; expected 'annual' or 'quarterly'")

        result = MacrotrendsData(ticker=ticker, canonical_ticker=ticker, freq=freq)
        tasks: list[tuple] = []
        for s in statements:
            cached = None if refresh else self._cache_read(ticker, s, freq)
            if cached is not None:
                result.canonical_ticker = cached.get("canonical_ticker",
                                                     result.canonical_ticker)
                result.raw_rows[s] = cached["rows"]
            else:
                tasks.append((s, _STATEMENT_SLUGS[s], _FREQ_PARAM[freq]))
        if not tasks:
            self._build_frames(result, statements)
            return result

        # navigate to the (placeholder-slug) income page: real Chrome follows
        # the redirect and passes any Cloudflare challenge; all data is then
        # fetched in-page at canonical URLs (no query-dropping redirects).
        nav_url = f"{_BASE_URL}/{ticker.lower()}/{ticker.lower()}/income-statement"
        ready_js = "typeof originalData !== 'undefined'"
        try:
            with CDPTab(port=self.cdp_port) as tab:
                tab.navigate_and_wait(nav_url, ready_js, timeout=90.0)
                js = (_IN_PAGE_JS_TEMPLATE
                      .replace("__BASE__", _BASE_URL)
                      .replace("__TICKER_LC__", ticker.lower())
                      .replace("__TASKS__", json.dumps([list(t) for t in tasks]))
                      .replace("__RETRIES__", str(_RATE_LIMIT_RETRIES))
                      .replace("__RL_WAIT__", str(_RATE_LIMIT_WAIT_S))
                      .replace("__DELAY__", str(_FETCH_DELAY_S)))
                payload = json.loads(tab.evaluate(js, timeout=300.0))
        except ChromeDebuggerError:
            raise  # transport-level: caller must see it

        resolve = payload.pop("__resolve__", None) or {}
        if resolve.get("tick"):
            result.canonical_ticker = str(resolve["tick"]).upper()
        if resolve.get("error"):
            result.errors.append(f"slug resolve: {resolve['error']}")

        for s, res in payload.items():
            if not isinstance(res, dict) or "data" not in res or not res["data"]:
                detail = (res or {}).get("error", "no originalData found")
                result.errors.append(f"{s}: {detail}")
                continue
            try:
                rows = json.loads(res["data"])
            except ValueError:
                result.errors.append(f"{s}: originalData is not valid JSON")
                continue
            result.raw_rows[s] = rows
            self._cache_write(ticker, s, freq, rows, result.canonical_ticker)

        self._build_frames(result, statements)
        return result

    def fetch_statement(self, ticker: str, statement: str, freq: str = "annual",
                        refresh: bool = False) -> pd.DataFrame:
        """Convenience: one statement as a DataFrame (empty on data failure)."""
        result = self.fetch(ticker, (statement,), freq=freq, refresh=refresh)
        return result.statements.get(statement, pd.DataFrame())

    def fetch_raw(self, ticker: str, statement: str, freq: str = "annual",
                  refresh: bool = False) -> list[dict[str, Any]]:
        """Raw originalData rows for a statement (unmapped, all labels)."""
        return self.fetch(ticker, (statement,), freq=freq, refresh=refresh) \
            .raw_rows.get(statement, [])

    # ------------------------------------------------------------------ #
    # parsing
    # ------------------------------------------------------------------ #
    @staticmethod
    def _parse_num(value: Any, per_share: bool = False) -> float:
        """Millions -> absolute float; '' / garbage -> NaN (never 0:
        macrotrends uses '' for 'not reported', and 0 would fake margins and
        growth). Per-share fields stay in dollars, unscaled. Cells arrive as
        STRINGS for older periods but as bare JSON NUMBERS for recent ones
        (verified live: {'2025-11-30': 579, '2025-08-31': '727.00000'}) --
        both are millions and must scale the same way."""
        if value is None or isinstance(value, bool):
            return math.nan
        if isinstance(value, (int, float)):
            v = float(value)
        else:
            s = str(value).strip()
            if not s:
                return math.nan
            try:
                v = float(s)
            except ValueError:
                return math.nan
        if math.isnan(v):
            return v
        return v if per_share else v * 1e6

    @classmethod
    def _rows_to_frame(cls, rows: list[dict[str, Any]],
                       alias_map: dict[str, set[str]]) -> pd.DataFrame:
        """Map originalData rows to a frame indexed by period-end (ascending),
        columns = canonical names, values absolute. Unmapped rows drop."""
        cells: dict[pd.Timestamp, dict[str, float]] = {}
        for row in rows:
            label = _strip_label(row.get("field_name", ""))
            slug = _row_slug(row.get("popup_icon", "") or "")
            canon = next(
                (k for k, aliases in alias_map.items() if label in aliases
                 or (slug is not None and slug in aliases)),
                None,
            )
            if canon is None:
                continue
            per_share = canon in _PS_DOLLAR_FIELDS
            for key, value in row.items():
                if not _ISO_KEY_RE.match(key):
                    continue
                v = cls._parse_num(value, per_share=per_share)
                cells.setdefault(pd.Timestamp(key), {})[canon] = v
        if not cells:
            return pd.DataFrame()
        return pd.DataFrame.from_dict(cells, orient="index").sort_index().astype(float)

    @classmethod
    def _postprocess_cash_flow(cls, df: pd.DataFrame) -> pd.DataFrame:
        """capex <- -abs(); compute free_cash_flow (NaN-aware)."""
        if df.empty:
            return df
        if "capex" in df.columns:
            df["capex"] = -df["capex"].abs()
        if {"operating_cash_flow", "capex"}.issubset(df.columns):
            # any missing side -> NaN (pandas sum with min_count propagates)
            df["free_cash_flow"] = df[["operating_cash_flow", "capex"]].sum(
                axis=1, min_count=2)
        return df

    def _build_frames(self, result: MacrotrendsData,
                      statements: Sequence[str]) -> None:
        for s in statements:
            rows = result.raw_rows.get(s, [])
            if not rows:
                result.statements[s] = pd.DataFrame()
                continue
            df = self._rows_to_frame(rows, _ALIAS_MAPS[s])
            if df.empty:
                result.errors.append(
                    f"{s}: no rows matched the alias map -- site format may have changed")
            if s == "cash_flow":
                df = self._postprocess_cash_flow(df)
            result.statements[s] = df

    # ------------------------------------------------------------------ #
    # disk cache (parsed rows JSON, TTL)
    # ------------------------------------------------------------------ #
    def _cache_path(self, ticker: str, statement: str, freq: str) -> Path:
        return self.cache_dir / f"{ticker}_{statement}_{freq}.json"

    def _cache_read(self, ticker: str, statement: str,
                    freq: str) -> dict[str, Any] | None:
        path = self._cache_path(ticker, statement, freq)
        try:
            record: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            age = time.time() - float(record["fetched_at"])
            if age <= self.ttl_seconds:
                return record
        except (OSError, ValueError, KeyError, TypeError):
            return None  # absent / corrupt -> miss; overwritten on write
        return None

    def _cache_write(self, ticker: str, statement: str, freq: str,
                     rows: list[dict[str, Any]], canonical_ticker: str) -> None:
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            record = {
                "fetched_at": time.time(),
                "ticker": ticker,
                "statement": statement,
                "freq": freq,
                "canonical_ticker": canonical_ticker,
                "rows": rows,
            }
            self._cache_path(ticker, statement, freq).write_text(
                json.dumps(record), encoding="utf-8")
        except OSError:
            pass  # cache is best-effort


@dataclass
class MacrotrendsData:
    """Result bundle for a :meth:`MacrotrendsFetcher.fetch` call."""

    ticker: str
    canonical_ticker: str
    freq: str
    statements: dict[str, pd.DataFrame] = field(default_factory=dict)
    raw_rows: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def has_data(self) -> bool:
        return any(not df.empty for df in self.statements.values())
