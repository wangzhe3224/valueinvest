"""One-page stock snapshot: 7 core metrics + valuation + price trend.

Data sources (all free, no API key):
  - stockanalysis.com quarterly statements (income HTML table + embedded
    financialData blobs on cash-flow / balance-sheet / ratios pages, ~20
    quarters + TTM + 5 fiscal years)
  - yfinance for price history (52w range, MAs, multi-year returns)

Usage:
    python stock_snapshot.py AAPL            # aligned text summary
    python stock_snapshot.py AAPL --json     # machine-readable
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
def extract_financial_data(html: str) -> Dict[str, List[Any]]:
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
    out: Dict[str, List[Any]] = {}
    for m in re.finditer(r"([A-Za-z_][A-Za-z0-9_]*):\[([^\]]*)\]", blob):
        key, raw = m.group(1), m.group(2)
        if key == "datekey" or '"' in raw:
            vals: List[Any] = [
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
def pct_change(new: Optional[float], old: Optional[float]) -> Optional[float]:
    if new is None or old is None or old == 0:
        return None
    if (new < 0) != (old < 0):  # sign flip (e.g. negative -> positive FCF): % is meaningless
        return None
    return (new / old - 1) * 100


def cagr(new: Optional[float], old: Optional[float], years: int) -> Optional[float]:
    if new is None or old is None or old <= 0 or new <= 0 or years <= 0:
        return None
    return ((new / old) ** (1 / years) - 1) * 100


def rank_pct(current: Optional[float], history: List[float]) -> Optional[float]:
    """Percentile of `current` within `history` (0-100, higher = bigger)."""
    if current is None or not history:
        return None
    vals = [v for v in history if v is not None]
    if not vals:
        return None
    below = sum(1 for v in vals if v <= current)
    return below / len(vals) * 100


def fmt(v: Optional[float], suffix: str = "", pct: bool = False) -> str:
    if v is None:
        return "n/a"
    if pct:
        return f"{v:+.1f}%{suffix}" if suffix else f"{v:+.1f}%"
    return f"{v:,.1f}{suffix}"


def big_number(v: Optional[float]) -> str:
    """Absolute money value -> human units."""
    if v is None:
        return "n/a"
    a = abs(v)
    for div, unit in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if a >= div:
            return f"{v / div:,.2f}{unit}"
    return f"{v:,.0f}"


# --------------------------------------------------------------------- #
# fetch all pieces
# --------------------------------------------------------------------- #
def fetch_snapshot(ticker: str) -> Dict[str, Any]:
    ticker = ticker.upper()
    f = StockAnalysisTrendFetcher()
    base = f"{f.BASE}/{ticker.lower()}/financials"

    out: Dict[str, Any] = {"ticker": ticker, "date": str(date.today()), "errors": []}

    # -- quarterly income table (revenue / gross profit / net income) -----
    try:
        inc_html = f._fetch_html(ticker, "")
        inc = f._parse_table(inc_html, {
            "revenue": {"Revenue", "Total Revenue"},
            "gross_profit": {"Gross Profit", "Gross Income"},
            "net_income": {"Net Income", "Net Income Common Stockholders"},
        })
        if not inc:
            out["errors"].append("no income table rows parsed")
    except Exception as e:  # noqa: BLE001
        inc = {}
        out["errors"].append(f"income fetch failed: {e}")

    # -- embedded blobs ---------------------------------------------------
    blobs: Dict[str, Dict[str, List[Any]]] = {}
    for section, tag in [
        ("", "income"),
        ("/cash-flow-statement", "cf"),
        ("/balance-sheet", "bs"),
        ("/ratios", "ratios"),
    ]:
        suffix = "/?p=quarterly" if section else "/?p=quarterly"
        try:
            blobs[tag] = extract_financial_data(fetch_page(f"{base}{section}{suffix}"))
        except Exception as e:  # noqa: BLE001
            blobs[tag] = {}
            out["errors"].append(f"{tag} blob fetch failed: {e}")

    # unify quarterly series on datekey (cf/bs/ratios share dates).
    # stockanalysis emits datekey DESCENDING (newest first) -- force ascending.
    dates: List[str] = list(blobs.get("cf", {}).get("datekey", []))
    if not dates:
        dates = list(blobs.get("bs", {}).get("datekey", []))
    if not dates:
        dates = sorted({d.isoformat() for d in inc.keys()})
    dates = sorted(dates)
    out["n_quarters"] = len(dates)

    def series(blob_tag: str, field: str) -> Dict[str, Optional[float]]:
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
    def pct_normalize(m: Dict[str, Optional[float]]) -> Dict[str, Optional[float]]:
        return {k: (v * 100 if v is not None and abs(v) < 3 else v) for k, v in m.items()}

    r_roe = pct_normalize(series("ratios", "roe"))
    r_roic = pct_normalize(series("ratios", "roic"))
    r_pe = series("ratios", "pe")
    r_pef = series("ratios", "peForward")
    r_ps = series("ratios", "ps")
    r_pb = series("ratios", "pb")
    r_pfcf = series("ratios", "pfcf")
    r_fcfy = series("ratios", "fcfyield")
    r_divy = series("ratios", "dividendyield")
    r_bby = series("ratios", "buybackyield")
    r_de = series("ratios", "debtequity")
    r_mcap = series("ratios", "marketcap")
    r_price = series("ratios", "lastCloseRatios")

    # fiscal year per quarter (from cf blob) -> annual anchor dates.
    # NOTE: blob arrays are in their own (descending) datekey order, so index
    # into them via their OWN datekey list, not our ascending one.
    def blob_aligned(blob_tag: str, field: str) -> Dict[str, Any]:
        data = blobs.get(blob_tag, {})
        keys = data.get("datekey", [])
        vals = data.get(field, [])
        return {keys[i]: vals[i] if i < len(vals) else None for i in range(len(keys))}

    fy_map = blob_aligned("cf", "fiscalYear")
    fq_map = blob_aligned("cf", "fiscalQuarter")
    fy_of = {d: (fy_map.get(d), fq_map.get(d)) for d in dates}

    # TTM builder: rolling 4-quarter sums / ratios
    def ttm_sums(key_map: Dict[str, Optional[float]]) -> List[Dict[str, Any]]:
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

    def ratio_series(num: Dict[str, Optional[float]], den: Dict[str, Optional[float]]) -> List[Dict[str, Any]]:
        num_ttm = {r["date"]: r["value"] for r in ttm_sums(num)}
        den_ttm = {r["date"]: r["value"] for r in ttm_sums(den)}
        return [
            {"date": d, "value": (num_ttm[d] / den_ttm[d] * 100) if num_ttm.get(d) and den_ttm.get(d) else None}
            for d in dates[3:]
        ]

    def latest(rows: List[Dict[str, Any]]) -> Optional[float]:
        for r in reversed(rows):
            if r["value"] is not None:
                return r["value"]
        return None

    # ---- core metric TTM series + growth -------------------------------
    rev_ttm = ttm_sums(m_rev)
    gp_ttm = ttm_sums(m_gp)
    ni_ttm = ttm_sums(m_ni)
    ocf_ttm = ttm_sums(m_ocf)
    fcf_ttm = ttm_sums(m_fcf)
    gm_series = ratio_series(m_gp, m_rev)
    nm_series = ratio_series(m_ni, m_rev)

    # annual anchors: last quarter of each fiscal year (ascending order)
    anchors: Dict[str, str] = {}
    for d in dates:
        fyv = fy_of.get(d, (None, None))[0]
        if fyv is not None:
            anchors[fyv] = d  # keep iterating: last quarter of the FY wins
    anchor_list: List[Dict[str, Any]] = [
        {"fy": fy, "date": anchors[fy]} for fy in sorted(anchors.keys())
    ]
    anchor_dates = [a["date"] for a in anchor_list]

    def at_anchor(anchor_map: Dict[str, Optional[float]]) -> List[Optional[float]]:
        return [anchor_map.get(a["date"]) for a in anchor_list]

    def ttm_at(anchor_sums: Dict[str, float]) -> List[Optional[float]]:
        return [anchor_sums.get(a["date"]) for a in anchor_list]

    def ordered(key_map: Dict[str, Optional[float]]) -> List[Optional[float]]:
        """Values aligned to ascending `dates` (blob dicts are descending-ordered)."""
        return [key_map.get(d) for d in dates]

    def last_valid(key_map: Dict[str, Optional[float]]) -> Optional[float]:
        for d in reversed(dates):  # ascending dates -> newest first
            v = key_map.get(d)
            if v is not None:
                return v
        return None

    rev_a = ttm_at({r["date"]: r["value"] for r in rev_ttm if r["value"] is not None})
    gp_a = ttm_at({r["date"]: r["value"] for r in gp_ttm if r["value"] is not None})
    ni_a = ttm_at({r["date"]: r["value"] for r in ni_ttm if r["value"] is not None})
    ocf_a = ttm_at({r["date"]: r["value"] for r in ocf_ttm if r["value"] is not None})
    fcf_a = ttm_at({r["date"]: r["value"] for r in fcf_ttm if r["value"] is not None})
    gm_a = [next((r["value"] for r in gm_series if r["date"] == a["date"]), None) for a in anchor_list]
    nm_a = [next((r["value"] for r in nm_series if r["date"] == a["date"]), None) for a in anchor_list]
    dr_a = at_anchor({d: (m_liab.get(d) / m_assets.get(d) * 100) if m_assets.get(d) else None for d in dates})
    roe_a = at_anchor(r_roe)
    roic_a = at_anchor(r_roic)
    sh_a = at_anchor(m_shares)

    def metric_block(name: str, annual: List[Optional[float]], kind: str) -> Dict[str, Any]:
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
        "roe": last_valid(r_roe),
        "roic": last_valid(r_roic),
        "debt_ratio": next(
            (m_liab.get(d) / m_assets.get(d) * 100 for d in reversed(dates) if m_assets.get(d)),
            None),
        "shares": last_valid(m_shares),
        "fcf": latest(fcf_ttm),
        "sbc": latest(ttm_sums(m_sbc)),
        "net_income": latest(ni_ttm),
    }

    def ttm_growth(rows: List[Dict[str, Any]]) -> Dict[str, Optional[float]]:
        """YoY (vs 4 TTM rows back) and 3y CAGR (vs 12 rows back) on a TTM series."""
        vals = [r["value"] for r in rows if r["value"] is not None]
        yoy = pct_change(vals[-1], vals[-5]) if len(vals) >= 5 else None
        g3 = cagr(vals[-1], vals[-13], 3) if len(vals) >= 13 else None
        return {"yoy": yoy, "cagr3": g3}

    def pp_delta(vals: List[Optional[float]]) -> Dict[str, Optional[float]]:
        """Percentage-point deltas for ratio-type series."""
        v = [x for x in vals if x is not None]
        yoy = (v[-1] - v[-5]) if len(v) >= 5 else None
        d3 = (v[-1] - v[-13]) if len(v) >= 13 else None
        return {"yoy": yoy, "delta3": d3}

    ttm_now["revenue_growth"] = ttm_growth(rev_ttm)
    ttm_now["ocf_growth"] = ttm_growth(ocf_ttm)
    ttm_now["fcf_growth"] = ttm_growth(fcf_ttm)
    ttm_now["shares_growth"] = ttm_growth([{"date": d, "value": m_shares.get(d)} for d in dates])
    ttm_now["roe_delta"] = pp_delta(ordered(r_roe))
    ttm_now["roic_delta"] = pp_delta(ordered(r_roic))
    ttm_now["gross_margin_delta"] = pp_delta([r["value"] for r in gm_series])
    ttm_now["net_margin_delta"] = pp_delta([r["value"] for r in nm_series])
    ttm_now["debt_ratio_delta"] = pp_delta(
        [m_liab.get(d) / m_assets.get(d) * 100 if m_assets.get(d) else None for d in dates])

    out["metrics"] = metrics
    out["ttm"] = ttm_now

    # ---- valuation ------------------------------------------------------
    def ttm_entry(blob_tag: str, field: str) -> Optional[Any]:
        """The 'TTM' row of a ratios blob (freshest: latest price + TTM financials)."""
        data = blobs.get(blob_tag, {})
        keys = data.get("datekey", [])
        vals = data.get(field, [])
        if keys and keys[0] == "TTM" and vals:
            return vals[0]
        return None

    def ratio_block(history: List[Optional[float]], cur: Optional[float] = None) -> Dict[str, Any]:
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

    out["valuation"] = {
        "pe": ratio_block(ordered(r_pe), cur=ttm_entry("ratios", "pe")),
        "pe_forward": {"current": ttm_entry("ratios", "peForward") or last_valid(r_pef)},
        "ps": ratio_block(ordered(r_ps), cur=ttm_entry("ratios", "ps")),
        "pb": ratio_block(ordered(r_pb), cur=ttm_entry("ratios", "pb")),
        "p_fcf": ratio_block(ordered(r_pfcf), cur=ttm_entry("ratios", "pfcf")),
        "fcf_yield": ratio_block(ordered(r_fcfy), cur=ttm_entry("ratios", "fcfyield")),
        "dividend_yield": {"current": ttm_entry("ratios", "dividendyield") or last_valid(r_divy)},
        "buyback_yield": {"current": ttm_entry("ratios", "buybackyield") or last_valid(r_bby)},
        "debt_equity": {"current": last_valid(r_de)},
        "net_cash": last_valid(m_netcash),
        "total_debt": last_valid(m_debt),
        "market_cap": ttm_entry("ratios", "marketcap") or last_valid(r_mcap),
        "price": ttm_entry("ratios", "lastCloseRatios"),
        "pe_history": [v for v in ordered(r_pe) if v is not None],
    }

    # ---- company meta ---------------------------------------------------
    out["company"] = _company_meta(ticker, out["valuation"])

    # ---- price trend ----------------------------------------------------
    out["price_trend"] = _price_trend(ticker, r_price)

    # ---- fundamental x price alignment (four quadrants) -----------------
    def score(parts: List[tuple[str, Optional[float], float, float]]) -> Dict[str, Any]:
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


def _company_meta(ticker: str, valuation: Dict[str, Any]) -> Dict[str, Any]:
    meta: Dict[str, Any] = {"name": None, "sector": None, "currency": "USD", "price": None}
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


def _price_trend(ticker: str, r_price: Dict[str, Optional[float]]) -> Dict[str, Any]:
    res: Dict[str, Any] = {}
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

        def ma_direction(span: int, lookback: int) -> tuple[Optional[float], Optional[str]]:
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


def collect_quick_notes(s: Dict[str, Any]) -> List[str]:
    """Auto red-flag notes shared by text and markdown renderers."""
    ttm = s.get("ttm", {})
    comp = s.get("company", {})
    val = s.get("valuation", {})
    out: List[str] = []
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


def render(s: Dict[str, Any]) -> str:
    L: List[str] = []
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
    L.append(f"quarterly history depth: {s['n_quarters']} quarters")
    if s["errors"]:
        L.append("WARNINGS: " + "; ".join(s["errors"]))

    L.append("")
    L.append("-- 1. CORE METRICS (annual = TTM at fiscal year end; last col may be a partial FY) --")
    fys = [str(f) + ("*" if i == len(s["metrics"][0]["fys"]) - 1 else "") for i, f in enumerate(s["metrics"][0]["fys"])]
    hdr = f"{'metric':14s}|" + "|".join(f" FY{f:>5s}" for f in fys) + "| latest TTM | YoY/Δpp | 3y/CAGR3"
    L.append(hdr)

    def growth_cell(name: str, m: Dict[str, Any]) -> str:
        if m["kind"] in ("pct", "ratio_pct"):
            d = ttm.get(DELTA_KEYS.get(name, ""), {})
            yoy = d.get("yoy")
            return (f"{'+' if yoy is not None and yoy >= 0 else ''}{yoy:.1f}pp"
                    if yoy is not None else "n/a")
        g = ttm.get(f"{name}_growth", {})
        yoy = g.get("yoy")
        return f"{yoy:+.1f}%" if yoy is not None else "n/a"

    def growth3_cell(name: str, m: Dict[str, Any]) -> str:
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
    def stat(v: Optional[float]) -> str:
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
        def pct_stat(v: Optional[float]) -> str:
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

    def pct_fmt(v: Optional[float]) -> str:
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
        def ma_cell(key: str, level: Optional[float], above: bool) -> str:
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

        def parts_txt(parts: List[tuple[str, float, int]]) -> str:
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


def render_md(s: Dict[str, Any]) -> str:
    """Markdown report skeleton: all tables pre-rendered, judgment slots left
    as 〔占位〕 for the analyst (Claude) to fill after web verification."""
    tk = s["ticker"]
    comp = s.get("company", {})
    val = s.get("valuation", {})
    pt = s.get("price_trend", {})
    ttm = s.get("ttm", {})
    al = s.get("alignment") or {}

    def cn(v: Optional[float]) -> str:
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

    def pp(v: Optional[float]) -> str:
        return f"{v:+.1f}pp" if v is not None else "n/a"

    def pc(v: Optional[float]) -> str:
        return f"{v:+.1f}%" if v is not None else "n/a"

    def ratio(v: Optional[float]) -> str:
        return f"{v:.1f}%" if v is not None else "n/a"

    L: List[str] = []
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
    L.append("## 核心指标（TTM，近 5 财年）")
    L.append("")
    fys = [str(f) + ("*最新TTM" if i == len(s["metrics"][0]["fys"]) - 1 else "")
           for i, f in enumerate(s["metrics"][0]["fys"])]
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
    def fmt_r(v: Optional[float]) -> str:
        return f"{v:.2f}x" if v is not None else "n/a"

    def fmt_p(v: Optional[float]) -> str:
        return f"{v:.2f}%" if v is not None else "n/a"

    def pctile(v: Optional[float]) -> str:
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

    def fmt_py(v: Optional[float]) -> str:
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
    L.append("")
    L.append("---")
    L.append("")
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
    args = ap.parse_args()

    snap = fetch_snapshot(args.ticker)
    if args.json:
        print(json.dumps(snap, indent=2, default=str))
    elif args.md:
        print(render_md(snap))
    else:
        print(render(snap))


if __name__ == "__main__":
    main()
