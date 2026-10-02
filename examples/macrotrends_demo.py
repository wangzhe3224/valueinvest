"""Demo: macrotrends.net long-history fundamentals via the standalone fetcher.

macrotrends.net serves ~15 years of annual statements and ~59 quarterly
periods -- roughly 3x the history of stockanalysis.com. The catch: it sits
behind a Cloudflare managed challenge, so this fetcher drives a local HEADED
Chrome via CDP (a visible Chrome window is normal; the first cold run may
ask you to click a verification check in that window).

Usage:
    python examples/macrotrends_demo.py          # NKE + SPCX showcase
    python examples/macrotrends_demo.py AAPL     # any ticker
"""
from __future__ import annotations

import sys

sys.path.insert(0, __file__.rsplit("/valueinvest/", 1)[0])

import pandas as pd  # noqa: E402

from valueinvest.data.fetcher.macrotrends import MacrotrendsFetcher  # noqa: E402

pd.set_option("display.width", 160)


def show_m(df: pd.DataFrame, cols: list, rows: int = 15) -> None:
    """Print dollar columns in $M (they are stored absolute)."""
    sub = df[cols].tail(rows) / 1e6
    print(sub.round(0).to_string())


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n  {title}\n{'=' * 70}")


def main() -> None:
    tickers = sys.argv[1:] or ["NKE", "SPCX"]
    f = MacrotrendsFetcher()

    for ticker in tickers:
        section(f"{ticker}: annual income statement (long history)")
        r = f.fetch(ticker, ("income", "cash_flow"), freq="annual")
        if r.errors:
            print("errors:", r.errors)
        inc = r.statements.get("income")
        cf = r.statements.get("cash_flow")
        if inc is not None and not inc.empty:
            cols = [c for c in ("revenue", "gross_profit", "operating_income",
                                "net_income") if c in inc.columns]
            print(f"{len(inc)} fiscal years, {inc.index[0].date()} -> {inc.index[-1].date()}")
            show_m(inc, cols)
            if "eps_diluted" in inc.columns:
                print("\ndiluted EPS ($):")
                print(inc["eps_diluted"].tail(15).round(2).to_string())
        if cf is not None and not cf.empty:
            cols = [c for c in ("operating_cash_flow", "capex", "free_cash_flow",
                                "stock_based_compensation") if c in cf.columns]
            print(f"\ncash flow ({len(cf)} years), $M:")
            show_m(cf, cols)

        section(f"{ticker}: last 8 quarters")
        q = f.fetch(ticker, ("income",), freq="quarterly")
        df = q.statements.get("income")
        if df is not None and not df.empty:
            print("$M:")
            show_m(df, ["revenue", "net_income"], rows=8)

    section("cache demo: second call hits the 12h disk cache")
    import time

    t0 = time.time()
    f.fetch("NKE", ("income", "cash_flow"), freq="annual")
    print(f"cached fetch: {time.time() - t0:.2f}s")
    t0 = time.time()
    f.fetch("NKE", ("income", "cash_flow"), freq="annual", refresh=True)
    print(f"refresh=True (live): {time.time() - t0:.2f}s")


if __name__ == "__main__":
    main()
