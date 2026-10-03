"""One-page stock snapshot: 9 core metrics + valuation + price trend.

Data sources (all free, no API key):
  - PRIMARY: stockanalysis.com quarterly statements (income HTML table +
    embedded financialData blobs, ~20 quarters + TTM + 5 fiscal years).
    Freshest: updated within hours of an earnings release.
  - SUPPLEMENT: macrotrends.net via the library's MacrotrendsFetcher
    (~59 quarters + ~15 fiscal years, needs a local headed Chrome for the
    Cloudflare challenge) -- used ONLY when the stockanalysis history is
    missing/thin (<20 quarters) or its fetch fails. On this path ROE /
    ROIC / valuation multiples are COMPUTED from statements + yfinance
    closes (self-calculated basis, noted in the report).
  - yfinance for price history (52w range, MAs, multi-year returns) in
    both paths.

Usage:
    python stock_snapshot.py AAPL            # aligned text summary
    python stock_snapshot.py AAPL --json     # machine-readable
    python stock_snapshot.py AAPL --source macrotrends  # force deep history
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from typing import Any, Dict, List, Optional

sys.path.insert(0, __file__.rsplit("/valueinvest/", 1)[0])

from valueinvest.trend.fetcher.stockanalysis_trend import StockAnalysisTrendFetcher  # noqa: E402

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}


# --------------------------------------------------------------------- #
# embedded financialData blob extraction
# --------------------------------------------------------------------- #
def extract_financial_data(html: str) -> dict[str, list[Any]]:
    """Pull the embedded `financialData:{...}` JS object out of a page.

    Returns {field_name: [values aligned with 'datekey']}, {} if absent.
    """
    i = html.find("financialData:{")
    if i < 0:
        return {}
    start = i + len("financialData")
    depth, instr, esc, end = 0, False, False, None
    for j in range(start, len(html)):
        c = html[j]
        if instr:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                instr = False
            continue
        if c == '"':
            instr = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = j + 1
                break
    if end is None:
        return {}
    blob = html[start + 1 : end - 1]
    out: dict[str, list[Any]] = {}
    for m in re.finditer(r"([A-Za-z_][A-Za-z0-9_]*):\[([^\]]*)\]", blob):
        key, raw = m.group(1), m.group(2)
        if key == "datekey" or '"' in raw:
            vals: list[Any] = [
                v.strip().strip('"') for v in raw.split(",") if v.strip()
            ]
        else:
            vals = []
            for tok in raw.split(","):
                tok = tok.strip()
                if not tok or tok == "null":
                    vals.append(None)
                else:
                    tok = re.sub(r"(?<![\w.\d])\.(?=\d)", "0.", tok)  # .784 -> 0.784
                    try:
                        vals.append(float(tok))
                    except ValueError:
                        vals.append(None)
        out[key] = vals
    return out


def fetch_page(url: str) -> str:
    import requests

    resp = requests.get(url, headers=UA, timeout=30)
    resp.raise_for_status()
    return resp.text


# --------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------- #
def pct_change(new: float | None, old: float | None) -> float | None:
    if new is None or old is None or old == 0:
        return None
    if (new < 0) != (old < 0):  # sign flip (e.g. negative -> positive FCF): % is meaningless
        return None
    if new < 0 and old < 0:
        # Both negative (burn / loss flows): a plain new/old-1 ratio would read
        # as "growth" while the burn actually widened. Report change in burn
        # magnitude instead: positive = burn shrinking, negative = widening.
        return (1 - new / old) * 100
    return (new / old - 1) * 100


def cagr(new: float | None, old: float | None, years: int) -> float | None:
    if new is None or old is None or old <= 0 or new <= 0 or years <= 0:
        return None
    return ((new / old) ** (1 / years) - 1) * 100


def rank_pct(current: float | None, history: list[float]) -> float | None:
    """Percentile of `current` within `history` (0-100, higher = bigger)."""
    if current is None or not history:
        return None
    vals = [v for v in history if v is not None]
    if not vals:
        return None
    below = sum(1 for v in vals if v <= current)
    return below / len(vals) * 100


def fmt(v: float | None, suffix: str = "", pct: bool = False) -> str:
    if v is None:
        return "n/a"
    if pct:
        return f"{v:+.1f}%{suffix}" if suffix else f"{v:+.1f}%"
    return f"{v:,.1f}{suffix}"


def big_number(v: float | None) -> str:
    """Absolute money value -> human units."""
    if v is None:
        return "n/a"
    a = abs(v)
    for div, unit in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if a >= div:
            return f"{v / div:,.2f}{unit}"
    return f"{v:,.0f}"


# --------------------------------------------------------------------- #
# rolling TTM helper (shared by both data-source spines)
# --------------------------------------------------------------------- #
def ttm_sums(dates: list[str], key_map: dict[str, float | None]) -> list[dict[str, Any]]:
    """Rolling 4-quarter sums over an ascending date grid. Quarters missing
    from the map (None) poison their whole window -> None (NaN policy)."""
    rows = []
    for i in range(len(dates)):
        if i < 3:
            continue
        window = dates[i - 3 : i + 1]
        vals = [key_map.get(d) for d in window]
        if any(v is None for v in vals):
            rows.append({"date": dates[i], "value": None})
        else:
            rows.append({"date": dates[i], "value": sum(vals)})  # type: ignore[arg-type]
    return rows


# --------------------------------------------------------------------- #
# macrotrends spine (primary source)
# --------------------------------------------------------------------- #
def _quarterly_closes(ticker: str) -> tuple[dict[str, float], float | None]:
    """Unadjusted (auto_adjust=False) daily closes for ~11y ->
    ({iso_date: close}, last_close). 11y covers the 10-FY annual table so
    computed ROE/ROIC exist for every displayed year; the valuation
    PERCENTILE history is separately capped to the last 20 quarters in
    fetch_snapshot to keep the '5y percentile' semantics.
    Caveat: around stock splits, historical close x as-reported shares can
    glitch (macrotrends restates share counts; yfinance unadjusted closes
    don't) -- affects only pre-split quarters' annual ROE display, not the
    5y percentile window."""
    import yfinance as yf

    hist = yf.Ticker(ticker).history(period="11y", interval="1d", auto_adjust=False)
    closes = hist["Close"].dropna()
    pairs = sorted((ts.date().isoformat(), float(v)) for ts, v in closes.items())
    return dict(pairs), (pairs[-1][1] if pairs else None)


def _mt_spine_from_frames(
    inc: "Any", bs: "Any", cf: "Any", ann_inc: "Any",
    closes: dict[str, float], last_close: float | None,
) -> dict[str, Any]:
    """Build the snapshot data spine from macrotrends statement frames.

    Pure function (no network): inc/bs/cf are the QUARTERLY period-indexed
    frames, ann_inc the ANNUAL income frame (its index dates are fiscal-year
    ends and identify the fiscal calendar), closes map iso date -> close.
    Raises ValueError when the data cannot support a snapshot (caller falls
    back to stockanalysis).
    """
    import pandas as pd

    def col(df: "Any", name: str) -> dict[str, float | None]:
        if df is None or getattr(df, "empty", True) or name not in df.columns:
            return {}
        return {ts.date().isoformat(): (None if pd.isna(v) else float(v))
                for ts, v in df[name].items()}

    m_rev = col(inc, "revenue")
    m_gp = col(inc, "gross_profit")
    m_ni = col(inc, "net_income")
    m_shares = col(inc, "shares_diluted") or col(inc, "shares_basic")

    m_ocf = col(cf, "operating_cash_flow")
    m_capex: dict[str, float | None] = {}
    m_fcf = col(cf, "free_cash_flow")
    m_sbc = col(cf, "stock_based_compensation")
    m_div = col(cf, "common_dividends_paid")
    m_buyback = col(cf, "net_equity_issued")  # NET issuance/repurchase (buy<0)

    m_assets = col(bs, "total_assets")
    m_liab = col(bs, "total_liabilities")
    m_equity = col(bs, "total_equity")
    m_std = col(bs, "short_term_debt")
    m_ltd = col(bs, "long_term_debt")
    m_cash = col(bs, "cash")

    dates = sorted(set(m_rev) | set(m_ocf) | set(m_assets))
    if len(dates) < 12:
        raise ValueError(f"only {len(dates)} quarters of macrotrends data")
    for label, mp in (("revenue", m_rev), ("net_income", m_ni),
                      ("operating_cash_flow", m_ocf), ("total_equity", m_equity),
                      ("shares", m_shares)):
        if all(mp.get(d) is None for d in dates[-4:]):
            raise ValueError(f"macrotrends column missing: {label}")

    # total interest-bearing debt (macrotrends has no single row) and the
    # conservative net-cash reading (cash only -- no short-term investments)
    m_debt = {d: ((m_std.get(d) or 0.0) + (m_ltd.get(d) or 0.0)) or None for d in dates}
    m_netcash = {d: (m_cash.get(d) - m_debt[d])
                 if (m_cash.get(d) is not None and m_debt[d] is not None) else None
                 for d in dates}

    # rolling TTM flows (None poisons the window)
    t_rev = {r["date"]: r["value"] for r in ttm_sums(dates, m_rev)}
    t_ni = {r["date"]: r["value"] for r in ttm_sums(dates, m_ni)}
    t_fcf = {r["date"]: r["value"] for r in ttm_sums(dates, m_fcf)}
    t_div = {r["date"]: r["value"] for r in ttm_sums(dates, m_div)}
    t_buyback = {r["date"]: r["value"] for r in ttm_sums(dates, m_buyback)}
    if not (t_rev.get(dates[-1]) or 0) > 0:
        raise ValueError("latest TTM revenue missing/zero")

    # fiscal calendar from the annual frame index (its dates ARE fiscal
    # year ends); each quarter belongs to the FY of the first FYE >= quarter
    fye_list = sorted(ts.date().isoformat() for ts in ann_inc.index) \
        if ann_inc is not None and not ann_inc.empty else []

    def fy_of(d: str) -> tuple[int | None, None]:
        for fye in fye_list:
            if d <= fye:
                return int(fye[:4]), None
        return (int(fye_list[-1][:4]) + 1, None) if fye_list else (None, None)

    # fiscal-year anchors: annual FYE dates present in the quarterly grid,
    # plus the in-progress FY's latest quarter as the rolling-TTM anchor
    fy_map = {d: fy_of(d) for d in dates}
    anchor_list: list[dict[str, Any]] = [
        {"fy": int(iso[:4]), "date": iso} for iso in fye_list if iso in set(dates)]
    last_fy = anchor_list[-1]["fy"] if anchor_list else None
    if dates and (not anchor_list or anchor_list[-1]["date"] != dates[-1]):
        anchor_list.append({"fy": (last_fy + 1) if last_fy else int(dates[-1][:4]),
                            "date": dates[-1]})
    anchor_list = anchor_list[-11:]  # last 10 full FYs + the TTM anchor

    # per-quarter computed ratios. UNIT CONVENTIONS match the stockanalysis
    # ratio maps so downstream rendering/percentiles are source-agnostic:
    # roe/roic in PERCENT, pe/ps/pb/pfcf as multiples, fcfy/divy/bby and
    # debtequity as FRACTIONS (rendered x100 / raw downstream).
    close_dates = sorted(closes)

    def close_at(iso: str) -> float | None:
        best = None
        for cd in close_dates:
            if cd <= iso:
                best = closes[cd]
            else:
                break
        return best

    r_roe: dict[str, float | None] = dict.fromkeys(dates)
    r_roic: dict[str, float | None] = dict.fromkeys(dates)
    r_pe: dict[str, float | None] = dict.fromkeys(dates)
    r_ps: dict[str, float | None] = dict.fromkeys(dates)
    r_pb: dict[str, float | None] = dict.fromkeys(dates)
    r_pfcf: dict[str, float | None] = dict.fromkeys(dates)
    r_fcfy: dict[str, float | None] = dict.fromkeys(dates)
    r_divy: dict[str, float | None] = dict.fromkeys(dates)
    r_bby: dict[str, float | None] = dict.fromkeys(dates)
    r_de: dict[str, float | None] = dict.fromkeys(dates)
    r_mcap: dict[str, float | None] = dict.fromkeys(dates)
    r_price: dict[str, float | None] = dict.fromkeys(dates)
    for d in dates:
        eq, de, sh = m_equity.get(d), m_debt.get(d), m_shares.get(d)
        px = close_at(d)
        cap = sh * px if (sh is not None and px) else None
        ni, rev, fcf = t_ni.get(d), t_rev.get(d), t_fcf.get(d)
        r_mcap[d], r_price[d] = cap, px
        r_de[d] = de / eq if (de is not None and eq) else None
        if cap is None:
            continue  # ratio maps stay None for this quarter
        # ROE = TTM NI / equity; ROIC = TTM NI / (equity + interest-bearing
        # debt). Both self-calculated (see source_notes).
        r_roe[d] = ni / eq * 100 if (ni is not None and eq) else None
        ic = (eq or 0.0) + (de or 0.0)
        r_roic[d] = ni / ic * 100 if (ni is not None and ic) else None
        r_pe[d] = cap / ni if ni else None
        r_ps[d] = cap / rev if rev else None
        r_pb[d] = cap / eq if eq else None
        r_pfcf[d] = cap / fcf if fcf else None
        r_fcfy[d] = fcf / cap if (fcf is not None and cap) else None
        div, bb = t_div.get(d), t_buyback.get(d)
        r_divy[d] = -div / cap if div else None
        r_bby[d] = -bb / cap if bb else None

    # current-value overrides (the equivalent of stockanalysis's embedded
    # TTM row): latest TTM + latest close x latest shares
    shares_now = next((m_shares[d] for d in reversed(dates)
                       if m_shares.get(d) is not None), None)
    cap_now = shares_now * last_close if (shares_now is not None and last_close) else None

    current: dict[str, float | None] | None = None
    if cap_now:
        eq_now = m_equity.get(dates[-1])
        fcf_now = t_fcf.get(dates[-1])
        current = {
            "pe": (cap_now / t_ni[dates[-1]]) if t_ni.get(dates[-1]) else None,
            "ps": (cap_now / t_rev[dates[-1]]) if t_rev.get(dates[-1]) else None,
            "pb": (cap_now / eq_now) if eq_now else None,
            "pfcf": (cap_now / fcf_now) if fcf_now else None,
            "fcfy": (fcf_now / cap_now) if fcf_now is not None else None,
            "divy": (-t_div[dates[-1]] / cap_now) if t_div.get(dates[-1]) else None,
            "bby": (-t_buyback[dates[-1]] / cap_now) if t_buyback.get(dates[-1]) else None,
            "mcap": cap_now,
            "price": last_close,
        }

    # annual ROE/ROIC at anchors ({int_fy: value}); includes the TTM anchor
    # under its in-progress FY label so ann_newest() reads current ROE/ROIC
    def ann_from(rmap: dict[str, float | None]) -> dict[int, float]:
        out: dict[int, float] = {}
        for a in anchor_list:
            v = rmap.get(a["date"])
            if v is not None:
                out[int(a["fy"])] = v
        return out

    return {
        "dates": dates,
        "maps": {"rev": m_rev, "gp": m_gp, "ni": m_ni, "ocf": m_ocf, "capex": m_capex,
                 "fcf": m_fcf, "sbc": m_sbc, "buyback": m_buyback, "div": m_div,
                 "liab": m_liab, "assets": m_assets, "equity": m_equity,
                 "debt": m_debt, "netcash": m_netcash, "shares": m_shares},
        "ratios": {"roe": r_roe, "roic": r_roic, "pe": r_pe, "ps": r_ps, "pb": r_pb,
                   "pfcf": r_pfcf, "fcfy": r_fcfy, "divy": r_divy, "bby": r_bby,
                   "de": r_de, "mcap": r_mcap, "price": r_price},
        "fy_of": fy_map,
        "anchor_list": anchor_list,
        "ann_roe": ann_from(r_roe),
        "ann_roic": ann_from(r_roic),
        "current": current,
        "pe_forward": None,  # no forward EPS on macrotrends -> WebSearch fills it
        "errors": [],
    }


def _spine_macrotrends(ticker: str) -> dict[str, Any]:
    """Macrotrends snapshot spine (history supplement / stockanalysis
    fallback). Raises on any failure so the caller can decide."""
    from valueinvest.data.fetcher.macrotrends import MacrotrendsFetcher

    f = MacrotrendsFetcher()
    data = f.fetch(ticker, ("income", "balance_sheet", "cash_flow"), freq="quarterly")
    frames = data.statements
    if any(k not in frames or frames[k].empty for k in ("income", "balance_sheet", "cash_flow")):
        raise ValueError(f"macrotrends statements incomplete: {data.errors}")
    ann = f.fetch(ticker, ("income",), freq="annual")
    closes, last_close = _quarterly_closes(ticker)
    spine = _mt_spine_from_frames(
        frames["income"], frames["balance_sheet"], frames["cash_flow"],
        ann.statements.get("income"), closes, last_close)
    spine["source"] = "macrotrends"
    spine["source_notes"] = [
        "本报告使用 macrotrends.net 三大报表（stockanalysis 历史不足时的补充源，"
        "数据可能滞后数天）+ yfinance 价格：ROE = TTM 净利/股东权益，"
        "ROIC = TTM 净利/(股东权益+有息负债)，估值倍数 = 自算市值/TTM（自算口径，"
        "与 stockanalysis 取数口径有差异）",
        "净现金 = 现金 − 有息负债（不含短期投资，较 stockanalysis 口径保守）；"
        "回购 yield 为净额口径（含增发抵减）",
        "Forward PE 在 macrotrends 源下无现成值，需 WebSearch 补充",
    ]
    return spine


def _last_valid_of(key_map: dict[str, float | None]) -> Any | None:
    """Newest non-None value of a map in its own (blob) order."""
    for v in reversed(list(key_map.values())):
        if v is not None:
            return v
    return None


def _spine_stockanalysis(ticker: str) -> dict[str, Any]:
    """Legacy stockanalysis.com spine (verbatim from the pre-1.9 pipeline)."""
    errors: list[str] = []
    f = StockAnalysisTrendFetcher()
    base = f"{f.BASE}/{ticker.lower()}/financials"

    # -- quarterly income table (revenue / gross profit / net income) -----
    try:
        inc_html = f._fetch_html(ticker, "")
        inc = f._parse_table(inc_html, {
            "revenue": {"Revenue", "Total Revenue"},
            "gross_profit": {"Gross Profit", "Gross Income"},
            "net_income": {"Net Income", "Net Income Common Stockholders"},
        })
        if not inc:
            errors.append("no income table rows parsed")
    except Exception as e:  # noqa: BLE001
        inc = {}
        errors.append(f"income fetch failed: {e}")

    # -- embedded blobs ---------------------------------------------------
    blobs: dict[str, dict[str, list[Any]]] = {}
    for section, tag, quarterly in [
        ("", "income", True),
        ("/cash-flow-statement", "cf", True),
        ("/balance-sheet", "bs", True),
        ("/ratios", "ratios", True),
        # annual ratios page: its newest column is TTM. The quarterly ratios
        # page's roe/roic rows are single-quarter (ROIC) / YTD-basis (ROE)
        # numbers, NOT TTM -- never use them for levels or deltas.
        ("/ratios", "ratios_annual", False),
    ]:
        suffix = "/?p=quarterly" if quarterly else ""
        try:
            blobs[tag] = extract_financial_data(fetch_page(f"{base}{section}{suffix}"))
        except Exception as e:  # noqa: BLE001
            blobs[tag] = {}
            errors.append(f"{tag} blob fetch failed: {e}")

    # unify quarterly series on datekey (cf/bs/ratios share dates).
    # stockanalysis emits datekey DESCENDING (newest first) -- force ascending.
    dates: list[str] = list(blobs.get("cf", {}).get("datekey", []))
    if not dates:
        dates = list(blobs.get("bs", {}).get("datekey", []))
    if not dates:
        dates = sorted({d.isoformat() for d in inc.keys()})
    dates = sorted(dates)

    def series(blob_tag: str, field: str) -> dict[str, float | None]:
        data = blobs.get(blob_tag, {})
        keys = data.get("datekey", [])
        vals = data.get(field, [])
        return {k: vals[i] if i < len(vals) else None for i, k in enumerate(keys)}

    # quarterly-aligned maps
    m_rev = {d: (inc.get(_pdate(d), {}) or {}).get("revenue") for d in dates}
    m_gp = {d: (inc.get(_pdate(d), {}) or {}).get("gross_profit") for d in dates}
    m_ni = {d: (inc.get(_pdate(d), {}) or {}).get("net_income") for d in dates}
    # income blob fallback (same fields as CF-style blob on income page)
    if not any(v is not None for v in m_rev.values()):
        b = series("income", "revenue")
        m_rev = {d: b.get(d) for d in dates}
        gp = series("income", "grossProfit")
        ni = series("income", "netIncome")
        m_gp = {d: gp.get(d) for d in dates}
        m_ni = {d: ni.get(d) for d in dates}

    m_ocf = series("cf", "ncfo")
    m_capex = series("cf", "capex")
    m_fcf = series("cf", "fcf")
    m_sbc = series("cf", "sbcomp")
    m_buyback = series("cf", "commonRepurchased")
    m_div = series("cf", "commonDividendCF")

    m_liab = series("bs", "liabilities")
    m_assets = series("bs", "assets")
    m_equity = series("bs", "equity")
    m_debt = series("bs", "debt")
    m_netcash = series("bs", "netcash")
    m_shares = series("bs", "sharesOutTotalCommon")

    # roe/roic come as fractions (1.21 = 121%) -> normalize to % so all
    # delta/pp math and rendering share one unit
    def pct_normalize(m: dict[str, float | None]) -> dict[str, float | None]:
        return {k: (v * 100 if v is not None and abs(v) < 3 else v) for k, v in m.items()}

    r_roe = pct_normalize(series("ratios", "roe"))
    r_roic = pct_normalize(series("ratios", "roic"))
    r_pe = series("ratios", "pe")
    r_ps = series("ratios", "ps")
    r_pb = series("ratios", "pb")
    r_pfcf = series("ratios", "pfcf")
    r_fcfy = series("ratios", "fcfyield")
    r_divy = series("ratios", "dividendyield")
    r_bby = series("ratios", "buybackyield")
    r_de = series("ratios", "debtequity")
    r_mcap = series("ratios", "marketcap")
    r_price = series("ratios", "lastCloseRatios")

    # fiscal year per quarter (from cf blob). NOTE: blob arrays are in their
    # own (descending) datekey order, so index into them via their OWN
    # datekey list, not our ascending one.
    def blob_aligned(blob_tag: str, field: str) -> dict[str, Any]:
        data = blobs.get(blob_tag, {})
        keys = data.get("datekey", [])
        vals = data.get(field, [])
        return {keys[i]: vals[i] if i < len(vals) else None for i in range(len(keys))}

    fy_map = blob_aligned("cf", "fiscalYear")
    fq_map = blob_aligned("cf", "fiscalQuarter")
    fy_of = {d: (fy_map.get(d), fq_map.get(d)) for d in dates}

    # fiscal-year anchors: last quarter of each fiscal year (ascending order)
    anchors: dict[Any, str] = {}
    for d in dates:
        fyv = fy_of.get(d, (None, None))[0]
        if fyv is not None:
            anchors[fyv] = d  # keep iterating: last quarter of the FY wins
    anchor_list: list[dict[str, Any]] = [
        {"fy": fy, "date": anchors[fy]} for fy in sorted(anchors.keys())]

    # ROE/ROIC from the annual ratios page: fiscalYear-keyed, newest column = TTM.
    def annual_ratio(field: str) -> dict[int, float]:
        data = blobs.get("ratios_annual", {})
        out_map: dict[int, float] = {}
        for i, fyv in enumerate(data.get("fiscalYear", [])):
            vals = data.get(field, [])
            v = vals[i] if i < len(vals) else None
            if v is None:
                continue
            v = v * 100 if abs(v) < 3 else v
            try:
                out_map[int(fyv)] = v
            except (TypeError, ValueError):
                continue
        return out_map

    def ttm_entry(blob_tag: str, field: str) -> Any | None:
        """The 'TTM' row of a ratios blob (freshest: latest price + TTM financials)."""
        data = blobs.get(blob_tag, {})
        keys = data.get("datekey", [])
        vals = data.get(field, [])
        if keys and keys[0] == "TTM" and vals:
            return vals[0]
        return None

    return {
        "dates": dates,
        "maps": {"rev": m_rev, "gp": m_gp, "ni": m_ni, "ocf": m_ocf, "capex": m_capex,
                 "fcf": m_fcf, "sbc": m_sbc, "buyback": m_buyback, "div": m_div,
                 "liab": m_liab, "assets": m_assets, "equity": m_equity,
                 "debt": m_debt, "netcash": m_netcash, "shares": m_shares},
        "ratios": {"roe": r_roe, "roic": r_roic, "pe": r_pe, "ps": r_ps, "pb": r_pb,
                   "pfcf": r_pfcf, "fcfy": r_fcfy, "divy": r_divy, "bby": r_bby,
                   "de": r_de, "mcap": r_mcap, "price": r_price},
        "fy_of": fy_of,
        "anchor_list": anchor_list,
        "ann_roe": annual_ratio("roe"),
        "ann_roic": annual_ratio("roic"),
        "current": {
            "pe": ttm_entry("ratios", "pe"),
            "ps": ttm_entry("ratios", "ps"),
            "pb": ttm_entry("ratios", "pb"),
            "pfcf": ttm_entry("ratios", "pfcf"),
            "fcfy": ttm_entry("ratios", "fcfyield"),
            "divy": ttm_entry("ratios", "dividendyield"),
            "bby": ttm_entry("ratios", "buybackyield"),
            "mcap": ttm_entry("ratios", "marketcap"),
            "price": ttm_entry("ratios", "lastCloseRatios"),
        },
        "pe_forward": ttm_entry("ratios", "peForward") or _last_valid_of(series("ratios", "peForward")),
        "source": "stockanalysis",
        "source_notes": [],
        "errors": errors,
    }


# --------------------------------------------------------------------- #
# fetch all pieces
# --------------------------------------------------------------------- #
_SA_NOMINAL_QUARTERS = 20  # stockanalysis's normal depth; below this the
# history is considered incomplete (young company, partial data, site glitch)


def fetch_snapshot(ticker: str, source: str = "auto") -> dict[str, Any]:
    """source: 'auto' = stockanalysis first, macrotrends ONLY when the
    stockanalysis history is missing/thin (<20q) or the fetch fails;
    'stockanalysis' / 'macrotrends' force one source."""
    errors: list[str] = []
    spine: dict[str, Any] | None = None
    if source in ("auto", "stockanalysis"):
        try:
            spine = _spine_stockanalysis(ticker)
        except Exception as e:  # noqa: BLE001
            if source == "stockanalysis":
                raise
            errors.append(f"stockanalysis failed ({e}); trying macrotrends")
    if spine is None:
        # forced macrotrends, or auto after a stockanalysis failure
        spine = _spine_macrotrends(ticker)  # raises on failure
    elif source == "auto" and len(spine["dates"]) < _SA_NOMINAL_QUARTERS:
        # stockanalysis history incomplete -> macrotrends goes deeper when
        # it can (young companies rarely; partial data / glitches often)
        try:
            mt = _spine_macrotrends(ticker)
            if len(mt["dates"]) > len(spine["dates"]):
                errors.append(
                    f"stockanalysis depth {len(spine['dates'])}q < "
                    f"{_SA_NOMINAL_QUARTERS}q; switched to macrotrends "
                    f"({len(mt['dates'])}q)")
                spine = mt
            else:
                errors.append(
                    f"stockanalysis depth {len(spine['dates'])}q thin; "
                    f"macrotrends not deeper ({len(mt['dates'])}q) -- kept")
        except Exception as e:  # noqa: BLE001
            errors.append(f"macrotrends supplement failed ({e}); kept stockanalysis")

    out: dict[str, Any] = {
        "ticker": ticker, "date": str(date.today()),
        "source": spine.get("source"), "source_notes": spine.get("source_notes", []),
        "errors": errors + list(spine.get("errors", [])),
    }

    dates: list[str] = spine["dates"]
    out["n_quarters"] = len(dates)
    _maps = spine["maps"]
    m_rev = _maps["rev"]; m_gp = _maps["gp"]; m_ni = _maps["ni"]
    m_ocf = _maps["ocf"]; m_capex = _maps["capex"]; m_fcf = _maps["fcf"]
    m_sbc = _maps["sbc"]; m_buyback = _maps["buyback"]; m_div = _maps["div"]
    m_liab = _maps["liab"]; m_assets = _maps["assets"]; m_equity = _maps["equity"]
    m_debt = _maps["debt"]; m_netcash = _maps["netcash"]; m_shares = _maps["shares"]
    _rt = spine["ratios"]
    r_roe = _rt["roe"]; r_roic = _rt["roic"]; r_pe = _rt["pe"]; r_ps = _rt["ps"]
    r_pb = _rt["pb"]; r_pfcf = _rt["pfcf"]; r_fcfy = _rt["fcfy"]; r_divy = _rt["divy"]
    r_bby = _rt["bby"]; r_de = _rt["de"]; r_mcap = _rt["mcap"]; r_price = _rt["price"]
    fy_of = spine["fy_of"]
    anchor_list: list[dict[str, Any]] = spine["anchor_list"]
    anchor_dates = [a["date"] for a in anchor_list]
    ann_roe: dict[int, float] = spine["ann_roe"]
    ann_roic: dict[int, float] = spine["ann_roic"]
    cur_vals: dict[str, float | None] | None = spine.get("current")

    def at_anchor(anchor_map: dict[str, float | None]) -> list[float | None]:
        return [anchor_map.get(a["date"]) for a in anchor_list]

    def ttm_at(anchor_sums: dict[str, float]) -> list[float | None]:
        return [anchor_sums.get(a["date"]) for a in anchor_list]

    def ordered(key_map: dict[str, float | None]) -> list[float | None]:
        """Values aligned to ascending `dates` (source maps may differ)."""
        return [key_map.get(d) for d in dates]

    def last_valid(key_map: dict[str, float | None]) -> float | None:
        for d in reversed(dates):  # ascending dates -> newest first
            v = key_map.get(d)
            if v is not None:
                return v
        return None

    def ratio_series(num: dict[str, float | None], den: dict[str, float | None]) -> list[dict[str, Any]]:
        num_ttm = {r["date"]: r["value"] for r in ttm_sums(dates, num)}
        den_ttm = {r["date"]: r["value"] for r in ttm_sums(dates, den)}
        return [
            {"date": d, "value": (num_ttm[d] / den_ttm[d] * 100) if num_ttm.get(d) and den_ttm.get(d) else None}
            for d in dates[3:]
        ]

    def latest(rows: list[dict[str, Any]]) -> float | None:
        for r in reversed(rows):
            if r["value"] is not None:
                return r["value"]
        return None

    # ---- core metric TTM series + growth -------------------------------
    rev_ttm = ttm_sums(dates, m_rev)
    gp_ttm = ttm_sums(dates, m_gp)
    ni_ttm = ttm_sums(dates, m_ni)
    ocf_ttm = ttm_sums(dates, m_ocf)
    fcf_ttm = ttm_sums(dates, m_fcf)
    gm_series = ratio_series(m_gp, m_rev)
    nm_series = ratio_series(m_ni, m_rev)

    rev_a = ttm_at({r["date"]: r["value"] for r in rev_ttm if r["value"] is not None})
    gp_a = ttm_at({r["date"]: r["value"] for r in gp_ttm if r["value"] is not None})
    ni_a = ttm_at({r["date"]: r["value"] for r in ni_ttm if r["value"] is not None})
    ocf_a = ttm_at({r["date"]: r["value"] for r in ocf_ttm if r["value"] is not None})
    fcf_a = ttm_at({r["date"]: r["value"] for r in fcf_ttm if r["value"] is not None})
    gm_a = [next((r["value"] for r in gm_series if r["date"] == a["date"]), None) for a in anchor_list]
    nm_a = [next((r["value"] for r in nm_series if r["date"] == a["date"]), None) for a in anchor_list]
    dr_a = at_anchor({d: (m_liab.get(d) / m_assets.get(d) * 100) if m_assets.get(d) else None for d in dates})

    # ann_roe / ann_roic come from the spine (stockanalysis: annual ratios
    # page, newest column = TTM; macrotrends: computed quarterly values at
    # fiscal anchors incl. the TTM anchor under its in-progress FY label).

    def ann_anchor_series(ann: dict[int, float]) -> list[float | None]:
        return [ann.get(int(a["fy"])) for a in anchor_list]

    def ann_newest(ann: dict[int, float]) -> float | None:
        return ann[max(ann)] if ann else None

    def ann_delta(ann: dict[int, float]) -> dict[str, float | None]:
        """TTM vs prior full FY (yoy) and vs 3 fiscal years back (delta3), in pp."""
        if not ann:
            return {"yoy": None, "delta3": None}
        ys = sorted(ann)
        cur = ann[ys[-1]]
        prev = ann.get(ys[-2]) if len(ys) >= 2 else None
        base3 = ann.get(ys[-1] - 3)
        return {"yoy": cur - prev if prev is not None else None,
                "delta3": cur - base3 if base3 is not None else None}

    roe_a = ann_anchor_series(ann_roe) if ann_roe else at_anchor(r_roe)
    roic_a = ann_anchor_series(ann_roic) if ann_roic else at_anchor(r_roic)
    sh_a = at_anchor(m_shares)

    def metric_block(name: str, annual: list[float | None], kind: str) -> dict[str, Any]:
        cur = annual[-1] if annual else None
        prev = annual[-2] if len(annual) >= 2 else None
        yoy = pct_change(cur, prev)
        n = len(annual)
        base3 = annual[-4] if n >= 4 else None
        c3 = cagr(cur, base3, min(3, n - 1)) if n >= 2 else None
        return {"metric": name, "annual": annual, "fys": [a["fy"] for a in anchor_list],
                "latest": cur, "yoy": yoy, "cagr3": c3, "kind": kind}

    metrics = [
        metric_block("revenue", rev_a, "money"),
        metric_block("gross_margin", gm_a, "pct"),
        metric_block("net_margin", nm_a, "pct"),
        metric_block("ocf", ocf_a, "money"),
        metric_block("fcf", fcf_a, "money"),
        metric_block("roe", roe_a, "pct"),
        metric_block("roic", roic_a, "pct"),
        metric_block("debt_ratio", dr_a, "pct"),
        metric_block("shares", sh_a, "shares"),
    ]

    # TTM current values (not just FY anchors)
    ttm_now = {
        "revenue": latest(rev_ttm), "gross_margin": latest(gm_series),
        "net_margin": latest(nm_series), "ocf": latest(ocf_ttm),
        "roe": ann_newest(ann_roe) if ann_roe else last_valid(r_roe),
        "roic": ann_newest(ann_roic) if ann_roic else last_valid(r_roic),
        "debt_ratio": next(
            (m_liab.get(d) / m_assets.get(d) * 100 for d in reversed(dates) if m_assets.get(d)),
            None),
        "shares": last_valid(m_shares),
        "fcf": latest(fcf_ttm),
        "sbc": latest(ttm_sums(dates, m_sbc)),
        "net_income": latest(ni_ttm),
    }

    def ttm_growth(rows: list[dict[str, Any]]) -> dict[str, float | None]:
        """YoY (vs 4 TTM rows back) and 3y CAGR (vs 12 rows back) on a TTM series."""
        vals = [r["value"] for r in rows if r["value"] is not None]
        yoy = pct_change(vals[-1], vals[-5]) if len(vals) >= 5 else None
        g3 = cagr(vals[-1], vals[-13], 3) if len(vals) >= 13 else None
        return {"yoy": yoy, "cagr3": g3}

    def pp_delta(vals: list[float | None]) -> dict[str, float | None]:
        """Percentage-point deltas for ratio-type series."""
        v = [x for x in vals if x is not None]
        yoy = (v[-1] - v[-5]) if len(v) >= 5 else None
        d3 = (v[-1] - v[-13]) if len(v) >= 13 else None
        return {"yoy": yoy, "delta3": d3}

    ttm_now["revenue_growth"] = ttm_growth(rev_ttm)
    ttm_now["ocf_growth"] = ttm_growth(ocf_ttm)
    ttm_now["fcf_growth"] = ttm_growth(fcf_ttm)
    ttm_now["shares_growth"] = ttm_growth([{"date": d, "value": m_shares.get(d)} for d in dates])
    ttm_now["roe_delta"] = ann_delta(ann_roe) if ann_roe else pp_delta(ordered(r_roe))
    ttm_now["roic_delta"] = ann_delta(ann_roic) if ann_roic else pp_delta(ordered(r_roic))
    ttm_now["gross_margin_delta"] = pp_delta([r["value"] for r in gm_series])
    ttm_now["net_margin_delta"] = pp_delta([r["value"] for r in nm_series])
    ttm_now["debt_ratio_delta"] = pp_delta(
        [m_liab.get(d) / m_assets.get(d) * 100 if m_assets.get(d) else None for d in dates])

    out["metrics"] = metrics
    out["ttm"] = ttm_now

    # ---- valuation ------------------------------------------------------
    def ratio_block(history: list[float | None], cur: float | None = None) -> dict[str, Any]:
        vals = [v for v in history if v is not None]
        if cur is None and vals:
            cur = vals[-1]
        # if `cur` came from the series itself, exclude it from its own history
        hist = vals[:-1] if (cur is not None and vals and vals[-1] == cur) else vals
        return {
            "current": cur,
            "avg": sum(hist) / len(hist) if hist else None,
            "min": min(hist) if hist else None,
            "max": max(hist) if hist else None,
            "percentile": rank_pct(cur, hist),
            "n": len(hist),
        }

    # percentile window: last 20 quarters (~5 years). stockanalysis only
    # ever had ~20; macrotrends computes ratios over ~11y of closes, so cap
    # explicitly to keep the '5y percentile' anchor semantics.
    def pct_series(key: str) -> list[float | None]:
        return ordered(_rt[key])[-20:]

    valuation = {
        "pe": ratio_block(pct_series("pe"), cur=(cur_vals or {}).get("pe")),
        "pe_forward": {"current": spine.get("pe_forward")},
        "ps": ratio_block(pct_series("ps"), cur=(cur_vals or {}).get("ps")),
        "pb": ratio_block(pct_series("pb"), cur=(cur_vals or {}).get("pb")),
        "p_fcf": ratio_block(pct_series("pfcf"), cur=(cur_vals or {}).get("pfcf")),
        "fcf_yield": ratio_block(pct_series("fcfy"), cur=(cur_vals or {}).get("fcfy")),
        "dividend_yield": {"current": (cur_vals or {}).get("divy") or last_valid(r_divy)},
        "buyback_yield": {"current": (cur_vals or {}).get("bby") or last_valid(r_bby)},
        "debt_equity": {"current": last_valid(r_de)},
        "net_cash": last_valid(m_netcash),
        "total_debt": last_valid(m_debt),
        "market_cap": (cur_vals or {}).get("mcap") or last_valid(r_mcap),
        "price": (cur_vals or {}).get("price"),
        "pe_history": [v for v in pct_series("pe") if v is not None],
    }

    # stockanalysis's embedded TTM `pfcf` can be stale/corrupt when FCF is
    # negative (observed KEEL 2026-09-25: -0.6x while its own fcfyield
    # -17.2% implies -5.8x). Cross-validate the two; on >20% relative
    # disagreement trust the yield and recompute the multiple from it.
    pf = valuation["p_fcf"].get("current")
    fy_cur = valuation["fcf_yield"].get("current")
    if pf and fy_cur and abs(fy_cur) > 0:
        if abs(1.0 / pf - fy_cur) / abs(fy_cur) > 0.20:
            valuation["p_fcf"]["current"] = 1.0 / fy_cur

    out["valuation"] = valuation

    # ---- company meta ---------------------------------------------------
    out["company"] = _company_meta(ticker, out["valuation"])

    # ---- price trend ----------------------------------------------------
    out["price_trend"] = _price_trend(ticker, r_price)

    # ---- fundamental x price alignment (four quadrants) -----------------
    def score(parts: list[tuple[str, float | None, float, float]]) -> dict[str, Any]:
        """Sum of -1/0/+1 votes; per-part thresholds: >hi -> +1, <lo -> -1."""
        used = []
        for name, v, hi, lo in parts:
            if v is None:
                continue
            used.append((name, v, 1 if v > hi else (-1 if v < lo else 0)))
        total = sum(s for _, _, s in used)
        return {"parts": used, "score": total,
                "direction": "up" if total > 0 else ("down" if total < 0 else "flat")}

    pt = out["price_trend"]
    fcf_yoy_part = -100.0 if (ttm_now.get("fcf") or 0) < 0 \
        else (ttm_now.get("fcf_growth") or {}).get("yoy")
    fund = score([
        ("revenue_yoy", (ttm_now.get("revenue_growth") or {}).get("yoy"), 10.0, 0.0),
        ("net_margin_dy_pp", (ttm_now.get("net_margin_delta") or {}).get("yoy"), 0.5, -0.5),
        ("roic_dy_pp", (ttm_now.get("roic_delta") or {}).get("yoy"), 0.5, -0.5),
        ("fcf_yoy", fcf_yoy_part, 10.0, -10.0),
    ])
    price = score([
        ("r1y", pt.get("r1y"), 10.0, -10.0),
        ("ma90_dir", {"rising": 10.0, "falling": -10.0}.get(pt.get("ma90_dir")), 0.0, 0.0),
        ("ma200_dir", {"rising": 10.0, "falling": -10.0}.get(pt.get("ma200_dir")), 0.0, 0.0),
    ])
    sf, sp = fund["direction"], price["direction"]
    out["alignment"] = {
        "fund": fund, "price": price,
        "quadrant": {
            ("up", "up"): "confirmed_uptrend",
            ("up", "down"): "positive_divergence",
            ("down", "up"): "negative_divergence",
            ("down", "down"): "confirmed_downtrend",
        }.get((sf, sp), "mixed_or_flat"),
    }

    return out


def _pdate(iso: str):
    from datetime import date as _d

    return _d.fromisoformat(iso)


def _company_meta(ticker: str, valuation: dict[str, Any]) -> dict[str, Any]:
    meta: dict[str, Any] = {"name": None, "sector": None, "currency": "USD", "price": None}
    try:
        import yfinance as yf

        t = yf.Ticker(ticker)
        info = t.get_info()
        meta["name"] = info.get("shortName") or info.get("longName")
        meta["sector"] = info.get("sector")
        meta["currency"] = info.get("currency", "USD")
        meta["price"] = info.get("currentPrice") or info.get("regularMarketPrice")
    except Exception as e:  # noqa: BLE001
        meta["error"] = str(e)
        if valuation.get("market_cap") is None:
            meta["error"] += " (valuation falls back to stockanalysis price)"
    return meta


def _price_trend(ticker: str, r_price: dict[str, float | None]) -> dict[str, Any]:
    res: dict[str, Any] = {}
    try:
        import yfinance as yf

        hist = yf.Ticker(ticker).history(period="5y", interval="1d", auto_adjust=False)
        closes = hist["Close"].dropna()
        if closes.empty:
            raise ValueError("empty price history")
        last = float(closes.iloc[-1])
        res["price"] = last
        res["asof"] = str(closes.index[-1].date())
        w52 = closes.iloc[-252:]
        hi, lo = float(w52.max()), float(w52.min())
        res["w52_high"], res["w52_low"] = hi, lo
        res["w52_position"] = (last - lo) / (hi - lo) * 100 if hi > lo else None
        res["drawdown_from_high"] = (last / hi - 1) * 100
        # MA90 (one trading quarter, aligned with the earnings cycle) + MA200 (~1 year)
        ma90 = float(closes.iloc[-90:].mean())
        ma200 = float(closes.iloc[-200:].mean())
        res["above_ma90"] = last > ma90
        res["above_ma200"] = last > ma200
        res["ma90"], res["ma200"] = ma90, ma200
        res["ma200_dev"] = (last / ma200 - 1) * 100  # extension vs the 1y line

        def ma_direction(span: int, lookback: int) -> tuple[float | None, str | None]:
            """Slope of an N-day MA over `lookback` days -> rising/flat/falling."""
            if len(closes) < span + lookback:
                return None, None
            ma_then = float(closes.iloc[-(span + lookback):-lookback].mean())
            ma_now = float(closes.iloc[-span:].mean())
            slope = (ma_now / ma_then - 1) * 100
            d = "rising" if slope > 0.5 else ("falling" if slope < -0.5 else "flat")
            return slope, d

        for key, span, lb in (("ma90", 90, 20), ("ma200", 200, 40)):
            slope, d = ma_direction(span, lb)
            res[f"{key}_slope"] = slope
            res[f"{key}_dir"] = d
        for label, n in (("r1y", 252), ("r3y", 756), ("r5y", len(closes) - 1)):
            if len(closes) > n:
                res[label] = (last / float(closes.iloc[-n - 1]) - 1) * 100
    except Exception as e:  # noqa: BLE001
        # fallback: stockanalysis period closes (quarterly, coarse)
        vals = [v for v in r_price.values() if v is not None]
        res["error"] = str(e)
        if vals:
            res["price"] = vals[-1]
            if len(vals) >= 5:
                res["r5y_approx_quarterly"] = (vals[-1] / vals[0] - 1) * 100
    return res


# --------------------------------------------------------------------- #
# text rendering
# --------------------------------------------------------------------- #
DELTA_KEYS = {
    "gross_margin": "gross_margin_delta",
    "net_margin": "net_margin_delta",
    "roe": "roe_delta",
    "roic": "roic_delta",
    "debt_ratio": "debt_ratio_delta",
}

QUAD_CN = {
    "confirmed_uptrend": "确认上升", "positive_divergence": "正背离",
    "negative_divergence": "负背离", "confirmed_downtrend": "确认下降",
    "mixed_or_flat": "混合/中性",
}


def collect_quick_notes(s: dict[str, Any]) -> list[str]:
    """Auto red-flag notes shared by text and markdown renderers."""
    ttm = s.get("ttm", {})
    comp = s.get("company", {})
    val = s.get("valuation", {})
    out: list[str] = []
    roe = ttm.get("roe")
    roic = ttm.get("roic")
    if roe is not None:
        rv = roe * 100 if abs(roe) < 3 else roe
        ric = None
        if roic is not None:
            ric = roic * 100 if abs(roic) < 3 else roic
        if rv > 60:
            if ric is not None:
                out.append(
                    f"[!] ROE {rv:.0f}% extreme - buyback-shrunk equity suspected."
                    f" ROIC {ric:.0f}% is the cross-check: BOTH extreme = shrunk capital"
                    f" (ROE alone meaningless); ROIC normal vs ROE high = leverage/non-op distortion"
                )
            else:
                out.append(f"[!] ROE {rv:.0f}% extreme - likely buyback-shrunk equity, verify with ROIC")
    dr = ttm.get("debt_ratio")
    if dr is not None and dr > 70:
        out.append(f"[!] debt ratio {dr:.0f}% > 70% - high leverage (financials: this metric is structural, ignore)")
    if comp.get("sector") and "Financial" in str(comp["sector"]):
        out.append("[i] Financial sector: debt ratio / ROE / DuPont are structural, use PE/PB")
    gm = ttm.get("gross_margin")
    if gm is not None:
        gmv = gm * 100 if abs(gm) < 3 else gm
        if gmv >= 99.5:
            out.append(
                f"[i] gross margin {gmv:.0f}% - vendor P&L has no COGS row (all costs booked"
                f" as opex), GP imputed = revenue (e.g. MA/ICE); use operating/net margin instead"
            )
    sbc = ttm.get("sbc")
    rev = ttm.get("revenue")
    if sbc and rev:
        if sbc / rev > 0.10:
            out.append(f"[!] SBC {sbc / rev * 100:.1f}% of revenue - dilution risk, check shares trend")
    ni = ttm.get("net_income")
    ocf = ttm.get("ocf")
    if ni and ocf and ni > 0 and ocf < ni * 0.7:
        out.append(f"[!] OCF {big_number(ocf)} < 70% of NI {big_number(ni)} - earnings quality flag")
    if roic is not None:
        ric = roic * 100 if abs(roic) < 3 else roic
        if ric < 8 and (ni is None or ni > 0):
            out.append(
                f"[i] ROIC {ric:.0f}% < ~10% typical WACC (conservative total-capital basis,"
                f" incl. goodwill) - verify value creation in deep analysis"
            )
    ocf_yoy = (ttm.get("ocf_growth") or {}).get("yoy")
    if ocf_yoy is not None and abs(ocf_yoy) > 200:
        out.append(f"[!] OCF YoY {ocf_yoy:+.0f}% extreme - one-time items likely distort the base year")
    fcf_yoy = (ttm.get("fcf_growth") or {}).get("yoy")
    if fcf_yoy is not None and abs(fcf_yoy) > 200:
        out.append(f"[!] FCF YoY {fcf_yoy:+.0f}% extreme - capex lumps / one-time items distort the base year")
    fcf_now = ttm.get("fcf")
    if fcf_now is not None and fcf_now < 0:
        out.append(f"[!] FCF negative ({big_number(fcf_now)} TTM) - check cash runway / funding dependence")
    pe_hist = val.get("pe_history", [])
    if pe_hist and min(pe_hist) < 0:
        out.append("[i] PE history includes loss-making periods (negative PE) - range stats polluted, prefer PS")
    pfcf = val.get("p_fcf") or {}
    if pfcf.get("min") is not None and pfcf["min"] < 0:
        out.append("[i] P/FCF history includes negative-FCF years - range stats polluted, interpret with care")
    return out


def render(s: dict[str, Any]) -> str:
    L: list[str] = []
    tk = s["ticker"]
    comp = s.get("company", {})
    val = s.get("valuation", {})
    pt = s.get("price_trend", {})
    ttm = s.get("ttm", {})

    L.append(f"================ STOCK SNAPSHOT: {tk} ================")
    L.append(
        f"name: {comp.get('name') or 'n/a'} | sector: {comp.get('sector') or 'n/a'}"
        f" | price: {fmt(pt.get('price'))} {comp.get('currency', 'USD')}"
        f" | mktcap: {big_number(val.get('market_cap'))} | as of {s['date']}"
    )
    L.append(f"quarterly history depth: {s['n_quarters']} quarters | source: {s.get('source') or 'n/a'}")
    if s["errors"]:
        L.append("WARNINGS: " + "; ".join(s["errors"]))

    L.append("")
    L.append("-- 1. CORE METRICS (annual = TTM at fiscal year end; last col may be a partial FY) --")
    fys = [str(f) + ("*" if i == len(s["metrics"][0]["fys"]) - 1 else "") for i, f in enumerate(s["metrics"][0]["fys"])]
    hdr = f"{'metric':14s}|" + "|".join(f" FY{f:>5s}" for f in fys) + "| latest TTM | YoY/Δpp | 3y/CAGR3"
    L.append(hdr)

    def growth_cell(name: str, m: dict[str, Any]) -> str:
        if m["kind"] in ("pct", "ratio_pct"):
            d = ttm.get(DELTA_KEYS.get(name, ""), {})
            yoy = d.get("yoy")
            return (f"{'+' if yoy is not None and yoy >= 0 else ''}{yoy:.1f}pp"
                    if yoy is not None else "n/a")
        g = ttm.get(f"{name}_growth", {})
        yoy = g.get("yoy")
        return f"{yoy:+.1f}%" if yoy is not None else "n/a"

    def growth3_cell(name: str, m: dict[str, Any]) -> str:
        if m["kind"] in ("pct", "ratio_pct"):
            d = ttm.get(DELTA_KEYS.get(name, ""), {})
            return f"{d['delta3']:+.1f}pp" if d.get("delta3") is not None else "n/a"
        g = ttm.get(f"{name}_growth", {})
        return f"{g['cagr3']:+.1f}%" if g.get("cagr3") is not None else "n/a"

    for m in s["metrics"]:
        cells = []
        for v in m["annual"]:
            if v is None:
                cells.append("  n/a")
            elif m["kind"] == "money":
                cells.append(f"{big_number(v):>6s}")
            elif m["kind"] == "ratio_pct":
                cells.append(f"{v * 100 if abs(v) < 3 else v:5.1f}%")
            elif m["kind"] == "shares":
                cells.append(f"{big_number(v):>6s}")
            else:
                cells.append(f"{v:5.1f}%")
        if m["kind"] == "money":
            latest_c = big_number(ttm.get(m["metric"]))
        elif m["kind"] == "ratio_pct":
            lv = ttm.get(m["metric"])
            latest_c = f"{lv * 100 if lv is not None and abs(lv) < 3 else lv:,.1f}%" if lv is not None else "n/a"
        elif m["kind"] == "shares":
            latest_c = big_number(ttm.get(m["metric"]))
        else:
            latest_c = f"{ttm.get(m['metric']):,.1f}%" if ttm.get(m["metric"]) is not None else "n/a"
        L.append(
            f"{m['metric']:14s}|" + "|".join(cells) + f"| {latest_c:>10s} "
            f"| {growth_cell(m['metric'], m):>7s} "
            f"| {growth3_cell(m['metric'], m):>7s}"
        )

    L.append("")
    L.append("-- 2. VALUATION (vs own history) --")
    rows = [
        ("PE TTM", val.get("pe")),
        ("PS", val.get("ps")),
        ("PB", val.get("pb")),
        ("P/FCF", val.get("p_fcf")),
    ]
    def stat(v: float | None) -> str:
        return f"{v:7.2f}" if v is not None else "     n/a"

    for name, b in rows:
        if not b or b.get("current") is None:
            L.append(f"{name:12s} n/a")
            continue
        pct = b.get("percentile")
        L.append(
            f"{name:12s} cur {stat(b['current'])} | avg {stat(b.get('avg'))} | min {stat(b.get('min'))}"
            f" | max {stat(b.get('max'))} | pct {(f'{pct:5.1f}%' if pct is not None else '  n/a')} | n={b.get('n', 0)}"
        )
    fy = val.get("fcf_yield")
    if fy and fy.get("current") is not None:
        def pct_stat(v: float | None) -> str:
            return f"{v * 100:6.2f}%" if v is not None else "   n/a"

        pct = fy.get("percentile")
        L.append(
            f"{'FCF yield':12s} cur {pct_stat(fy['current'])} | avg {pct_stat(fy.get('avg'))}"
            f" | min {pct_stat(fy.get('min'))} | max {pct_stat(fy.get('max'))}"
            f" | pct {(f'{pct:5.1f}%' if pct is not None else '  n/a')} | n={fy.get('n', 0)}  (high pct = cheap)"
        )
    pf = val.get("pe_forward", {}).get("current")
    L.append(f"{'Fwd PE':12s} cur {fmt(pf)}")
    dy = val.get("dividend_yield", {}).get("current")
    bb = val.get("buyback_yield", {}).get("current")
    sh = (dy + bb) * 100 if dy is not None and bb is not None else None

    def pct_fmt(v: float | None) -> str:
        return f"{v:.1f}%" if v is not None else "n/a"

    L.append(
        f"{'Yields':12s} div {pct_fmt(dy * 100 if dy is not None else None)}"
        f" | buyback {pct_fmt(bb * 100 if bb is not None else None)}"
        f" | shareholder {pct_fmt(sh)}"
    )
    L.append(
        f"{'Debt':12s} D/E {fmt(val.get('debt_equity', {}).get('current'))}"
        f" | total debt {big_number(val.get('total_debt'))}"
        f" | net cash {big_number(val.get('net_cash'))}"
    )

    L.append("")
    L.append("-- 3. PRICE TREND --")
    if pt.get("price"):
        L.append(f"price {fmt(pt['price'])} (as of {pt.get('asof', 'n/a')})")
    if pt.get("w52_high"):
        L.append(
            f"52w range {fmt(pt['w52_low'])} - {fmt(pt['w52_high'])}"
            f" | position in range {fmt(pt.get('w52_position'))}%"
            f" | from high {fmt(pt.get('drawdown_from_high'))}%"
        )
    if pt.get("above_ma90") is not None:
        def ma_cell(key: str, level: float | None, above: bool) -> str:
            d = pt.get(f"{key}_dir")
            slope = pt.get(f"{key}_slope")
            dtxt = f", {d} {slope:+.1f}%" if d else ""
            return f"{key.upper()} {fmt(level)} ({'above' if above else 'BELOW'}{dtxt})"

        L.append(ma_cell("ma90", pt.get("ma90"), pt["above_ma90"]) + " | " + ma_cell("ma200", pt.get("ma200"), pt["above_ma200"]))
        if pt.get("ma200_dev") is not None:
            L.append(f"vs MA200: {pt['ma200_dev']:+.1f}%")
    for lbl in ("r1y", "r3y", "r5y"):
        if pt.get(lbl) is not None:
            L.append(f"{lbl}: {pt[lbl]:+.1f}%")
    if pt.get("error"):
        L.append(f"price trend error: {pt['error']}")

    al = s.get("alignment") or {}
    if al and al.get("fund", {}).get("parts") is not None:
        quad_label = {
            "confirmed_uptrend": "CONFIRMED UPTREND (fund up + price up)",
            "positive_divergence": "POSITIVE DIVERGENCE (fund up + price down) - potential mispricing / valuation compression",
            "negative_divergence": "NEGATIVE DIVERGENCE (fund down + price up) - multiple expansion, risk building",
            "confirmed_downtrend": "CONFIRMED DOWNTREND (fund down + price down) - double squeeze",
            "mixed_or_flat": "MIXED / FLAT - no clear quadrant",
        }.get(al.get("quadrant"), str(al.get("quadrant")))

        def parts_txt(parts: list[tuple[str, float, int]]) -> str:
            return " | ".join(f"{n} {v:+.1f} ({sv:+d})" for n, v, sv in parts) or "n/a"

        L.append("")
        L.append("-- 4. FUNDAMENTAL x PRICE ALIGNMENT (four quadrants) --")
        L.append(
            f"fundamental: {al['fund']['direction']:>4s} (score {al['fund']['score']:+d})  "
            f"{parts_txt(al['fund']['parts'])}"
        )
        L.append(
            f"price:       {al['price']['direction']:>4s} (score {al['price']['score']:+d})  "
            f"{parts_txt(al['price']['parts'])}"
        )
        L.append(f"QUADRANT: {quad_label}")

    L.append("")
    L.append("-- 5. QUICK NOTES --")
    L.extend(collect_quick_notes(s))
    return "\n".join(L)


def render_md(s: dict[str, Any]) -> str:
    """Markdown report skeleton: all tables pre-rendered, judgment slots left
    as 〔占位〕 for the analyst (Claude) to fill after web verification."""
    tk = s["ticker"]
    comp = s.get("company", {})
    val = s.get("valuation", {})
    pt = s.get("price_trend", {})
    ttm = s.get("ttm", {})
    al = s.get("alignment") or {}

    def cn(v: float | None) -> str:
        if v is None:
            return "n/a"
        a = abs(v)
        if a >= 1e12:
            return f"{v / 1e12:.2f}万亿"
        if a >= 1e8:
            return f"{v / 1e8:.1f}亿"
        if a >= 1e4:
            return f"{v / 1e4:,.0f}万"
        return f"{v:,.0f}"

    def pp(v: float | None) -> str:
        return f"{v:+.1f}pp" if v is not None else "n/a"

    def pc(v: float | None) -> str:
        return f"{v:+.1f}%" if v is not None else "n/a"

    def ratio(v: float | None) -> str:
        return f"{v:.1f}%" if v is not None else "n/a"

    L: list[str] = []
    L.append(
        f"本文使用 [ValueInvest](https://github.com/wangzhe3224/valueinvest) 库对 "
        f"{comp.get('name') or tk} ({tk}) 进行一页纸快照分析，时间戳: {s['date']}"
    )
    L.append("（金额单位：美元；* 号财年 = 截至最新已公布季度的 TTM，非完整财年）")
    L.append("")
    L.append(f"## {comp.get('name') or tk} ({tk}) 一句话定位")
    L.append("")
    L.append(f"〔一句话：做什么生意的 + 市值 {cn(val.get('market_cap'))}，现价 {fmt(pt.get('price'))}。 sector: {comp.get('sector') or 'n/a'}〕")
    L.append("")

    # core metrics
    fys = [str(f) + ("*最新TTM" if i == len(s["metrics"][0]["fys"]) - 1 else "")
           for i, f in enumerate(s["metrics"][0]["fys"])]
    L.append(f"## 核心指标（TTM，近 {len(fys)} 财年）")
    L.append("")
    L.append("| 指标 | " + " | ".join(f"FY{f}" for f in fys) + " | YoY | 3年 |")
    L.append("|" + "------|" * (len(fys) + 3))
    cn_names = {"revenue": "营收", "gross_margin": "毛利率", "net_margin": "净利率",
                "ocf": "经营现金流", "fcf": "自由现金流", "roe": "ROE", "roic": "ROIC",
                "debt_ratio": "资产负债率", "shares": "股本"}
    for m in s["metrics"]:
        cells = []
        for v in m["annual"]:
            if v is None:
                cells.append("n/a")
            elif m["kind"] in ("money", "shares"):
                cells.append(cn(v))
            else:
                cells.append(ratio(v))
        if m["kind"] in ("money", "shares"):
            g = ttm.get(f"{m['metric']}_growth", {})
            yoy = pc(g.get("yoy")) if g.get("yoy") is not None else "n/a"
            c3 = f"CAGR {pc(g.get('cagr3'))}" if g.get("cagr3") is not None else "n/a"
        else:
            d = ttm.get(DELTA_KEYS.get(m["metric"], ""), {})
            yoy = pp(d.get("yoy"))
            c3 = pp(d.get("delta3"))
        L.append(f"| {cn_names.get(m['metric'], m['metric'])} | " + " | ".join(cells) + f" | {yoy} | {c3} |")
    L.append("")
    L.append("〔一两句话点出最重要的 1-2 个趋势〕")
    L.append("")

    # valuation
    def fmt_r(v: float | None) -> str:
        return f"{v:.2f}x" if v is not None else "n/a"

    def fmt_p(v: float | None) -> str:
        return f"{v:.2f}%" if v is not None else "n/a"

    def pctile(v: float | None) -> str:
        return f"{v:.0f}%" if v is not None else "n/a"

    L.append("## 估值（相对自身 5 年季度区间）")
    L.append("")
    L.append("| 倍数 | 当前 | 5年均值 | 5年区间 | 分位 |")
    L.append("|------|------|---------|---------|------|")
    pe = val.get("pe") or {}
    pe_cur = pe.get("current")
    pe_disp = fmt_r(pe_cur) if (pe_cur is not None and pe_cur > 0) else "负（GAAP 亏损）"
    L.append(f"| PE TTM | {pe_disp} | {fmt_r(pe.get('avg'))} | {fmt_r(pe.get('min'))}–{fmt_r(pe.get('max'))} | {pctile(pe.get('percentile'))} |")
    L.append(f"| Forward PE | {fmt_r(val.get('pe_forward', {}).get('current'))} | - | - | - |")
    for label, key in (("PS", "ps"), ("PB", "pb"), ("P/FCF", "p_fcf")):
        b = val.get(key) or {}
        rng = f"{fmt_r(b.get('min'))}–{fmt_r(b.get('max'))}" if b.get("min") is not None else "n/a"
        L.append(f"| {label} | {fmt_r(b.get('current'))} | {fmt_r(b.get('avg'))} | {rng} | {pctile(b.get('percentile'))} |")
    fy = val.get("fcf_yield") or {}

    def fmt_py(v: float | None) -> str:
        return f"{v * 100:.2f}%" if v is not None else "n/a"

    rng = f"{fmt_py(fy.get('min'))}–{fmt_py(fy.get('max'))}" if fy.get("min") is not None else "n/a"
    L.append(f"| FCF yield | {fmt_py(fy.get('current'))} | {fmt_py(fy.get('avg'))} | {rng} | {pctile(fy.get('percentile'))}（高分位=便宜）|")
    dy = val.get("dividend_yield", {}).get("current")
    bb = val.get("buyback_yield", {}).get("current")
    div_s = f"{dy * 100:.1f}%" if dy is not None else "无股息"
    bb_s = f"{bb * 100:.1f}%" if bb is not None else "n/a"
    L.append(f"| 股息 + 回购 yield | {div_s}；回购 {bb_s} | - | - | - |")
    L.append("")
    L.append(f"净现金/净债务: {cn(val.get('net_cash'))}；总债务: {cn(val.get('total_debt'))}。")
    L.append("")
    L.append("〔一句话判断：当前估值处于自身历史的高/低分位，与增速相比贵不贵〕")
    L.append("")

    # price trend
    dir_cn = {"rising": "上升", "flat": "盘整", "falling": "下跌"}

    L.append("## 价格趋势")
    L.append("")
    L.append("| 指标 | 数值 |")
    L.append("|------|------|")
    L.append(f"| 现价 | {fmt(pt.get('price'))} |")
    L.append(f"| 52 周区间 | {fmt(pt.get('w52_low'))} – {fmt(pt.get('w52_high'))}（现处 {pctile(pt.get('w52_position'))} 位置）|")
    L.append(f"| 距 52 周高点 | {pc(pt.get('drawdown_from_high'))} |")
    L.append(f"| MA90 | {'上方' if pt.get('above_ma90') else '下方'}，方向 **{dir_cn.get(pt.get('ma90_dir'), 'n/a')}**（{pt.get('ma90_slope') or 0:+.1f}% /20日）|")
    L.append(f"| MA200 | {'上方' if pt.get('above_ma200') else '下方'}，方向 **{dir_cn.get(pt.get('ma200_dir'), 'n/a')}**（{pt.get('ma200_slope') or 0:+.1f}% /40日）|")
    if pt.get("ma200_dev") is not None:
        L.append(f"| 距 MA200 | {pt['ma200_dev']:+.1f}%（扩张/回归标尺）|")
    r1y, r3y, r5y = pt.get("r1y"), pt.get("r3y"), pt.get("r5y")
    L.append(f"| 1Y / 3Y / 5Y 回报 | {pc(r1y)} / {pc(r3y)} / {pc(r5y)} |")
    L.append("")
    L.append("〔一句话：趋势状态〕")
    L.append("")

    # quadrant: 2x2 matrix with the current cell marked
    quad = al.get("quadrant", "mixed_or_flat")
    quad_cn = QUAD_CN.get(quad, quad)

    def cell(name: str) -> str:
        cn = QUAD_CN.get(name, name)
        return f"**{cn} ← 当前**" if quad == name else cn

    L.append("## 基本面 × 价格四象限")
    L.append("")
    L.append("| | 价格↑ | 价格↓ |")
    L.append("|------|------|------|")
    L.append(f"| **基本面↑** | {cell('confirmed_uptrend')} | {cell('positive_divergence')} |")
    L.append(f"| **基本面↓** | {cell('negative_divergence')} | {cell('confirmed_downtrend')} |")
    L.append("")
    fs, ps_ = al.get("fund", {}), al.get("price", {})
    L.append(f"本次象限: **{quad_cn}**（基本面 {fs.get('direction')} {fs.get('score', 0):+d} / 价格 {ps_.get('direction')} {ps_.get('score', 0):+d}）")
    L.append("")
    L.append("〔一两句：象限含义落到这只票上——背离时列出市场在担心什么，确认趋势时说明动量是否过热〕")
    L.append("")

    # KPI + catalysts (require web search; placeholders only)
    L.append("## 核心 KPI（驱动股价的先行指标）")
    L.append("")
    L.append("| KPI | 最新值 | 趋势 | 传导 |")
    L.append("|------|--------|------|------|")
    for i in range(1, 4):
        L.append(f"| 〔KPI {i}〕 | 〔最新值〕 | 〔趋势〕 | 〔一句话传导〕 |")
    L.append("")
    L.append("〔最多一句点评；按需增删行，3-4 个为宜〕")
    L.append("")
    L.append("## 催化剂（未来 1-12 个月）")
    L.append("")
    L.append("| 时间窗 | 事件 | 方向 | 看点（锚定具体数字）|")
    L.append("|--------|------|------|---------------------|")
    for i in range(1, 4):
        L.append(f"| 〔时间〕 | 〔事件 {i}〕 | 〔利好/利空/双向〕 | 〔看点〕 |")
    L.append("")
    L.append("〔最多一句：哪个事件是核心矛盾的验证点〕")
    L.append("")

    # conclusions
    L.append("## 结论")
    L.append("")
    L.append("- **质量**: **〔优/中/差〕** —— 〔证据〕")
    L.append("- **成长**: **〔优/中/差〕** —— 〔证据〕")
    L.append("- **估值**: **〔低估/合理/高估〕** —— 〔证据〕")
    L.append("- **趋势**: **〔向上/盘整/向下〕** —— 〔证据〕")
    L.append(f"- **四象限**: **{quad_cn}** —— 〔一句话〕")
    L.append("")
    L.append("综合: 〔一句话——值不值得列入深度分析清单 / 买点观察价〕")
    L.append("")

    # notes
    L.append("## 注意事项")
    L.append("")
    notes = collect_quick_notes(s)
    if notes:
        for n in notes:
            L.append(f"- 〔翻译+补充背景〕 {n}")
    else:
        L.append("- 〔无自动红旗则写\"无自动红旗\"〕")
    for note in s.get("source_notes", []):
        L.append(f"- 〔数据源口径〕 {note}")
    L.append("")
    L.append("---")
    L.append("")
    if s.get("source") == "macrotrends":
        L.append("数据源: macrotrends.net（三大报表，~10 财年 + 全部可得季度）+ yfinance（价格历史）；"
                 "ROE/ROIC/估值倍数为脚本自算口径；关键数字经 WebSearch 核实（〔日期 + 来源链接〕）")
    else:
        L.append("数据源: stockanalysis.com（季度财务 + 内嵌估值比率）+ yfinance（价格历史）；关键数字经 WebSearch 核实（〔日期 + 来源链接〕）")
    L.append("**作者**: [ValueInvest](https://github.com/wangzhe3224/valueinvest) 快照引擎")
    L.append("")
    L.append("*免责声明：本文仅供学习交流，不构成任何投资建议。股市有风险，投资需谨慎。*")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description="One-page stock snapshot")
    ap.add_argument("ticker")
    ap.add_argument("--json", action="store_true", help="emit raw JSON instead of text")
    ap.add_argument("--md", action="store_true",
                    help="emit markdown report skeleton (tables pre-rendered, judgment slots as 〔占位〕)")
    ap.add_argument("--source", choices=["auto", "macrotrends", "stockanalysis"],
                    default="auto",
                    help="data source: auto = stockanalysis first, macrotrends only "
                         "when stockanalysis history is thin (<20q) or fails (default); "
                         "'macrotrends'/'stockanalysis' force one source")
    args = ap.parse_args()

    snap = fetch_snapshot(args.ticker, source=args.source)
    if args.json:
        print(json.dumps(snap, indent=2, default=str))
    elif args.md:
        print(render_md(snap))
    else:
        print(render(snap))


if __name__ == "__main__":
    main()
