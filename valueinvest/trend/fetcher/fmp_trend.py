"""Quarterly trend data fetcher via Financial Modeling Prep (FMP).

FMP provides ~30 years of quarterly statements -- far deeper than yfinance's
~5 quarters -- which is what makes real multi-year trend / growth-signal
analysis possible. Requires an FMP API key (free tier available at
https://financialmodelingprep.com) in the ``FMP_KEY`` (or ``FMP_API_KEY``)
environment variable.

Uses FMP's current ``/stable/`` endpoints (the legacy ``/api/v3/`` endpoints
are restricted to pre-2025-08-31 subscribers). Financial data comes from FMP;
closing prices are pulled via yfinance (reliable 5y daily series). FMP quarterly
statements are single-quarter (non-cumulative), so no de-YTD step is needed.
"""
import os
from datetime import date
from typing import Any, Dict, List, Optional

from .base import BaseTrendFetcher
from ..base import TrendFetchResult, TrendRecord, TrendSeries, Market


class FMPTrendFetcher(BaseTrendFetcher):
    """Fetch quarterly trend data via Financial Modeling Prep."""

    BASE = "https://financialmodelingprep.com/stable"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key or os.environ.get("FMP_KEY") or os.environ.get("FMP_API_KEY")

    @property
    def market(self) -> Market:
        return Market.US

    @property
    def source_name(self) -> str:
        return "fmp"

    # ------------------------------------------------------------------ #
    # FMP access
    # ------------------------------------------------------------------ #
    def _get(self, path: str, params: Dict[str, Any]) -> Any:
        if not self._api_key:
            raise ValueError(
                "FMP API key required. Set FMP_KEY environment variable "
                "(free tier: https://financialmodelingprep.com)."
            )
        import requests

        full = {"symbol": "", **params, "apikey": self._api_key}
        resp = requests.get(f"{self.BASE}/{path}", params=full, timeout=30)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _parse_date(s: str) -> date:
        return date(int(s[:4]), int(s[5:7]), int(s[8:10]))

    @staticmethod
    def _fiscal_quarter(qend: date) -> int:
        return (qend.month - 1) // 3 + 1

    def _quarterly_close(self, ticker: str, dates: List[str]) -> Dict[str, float]:
        """Close on/nearest-before each quarter-end via yfinance (reliable 5y daily)."""
        result = {d: 0.0 for d in dates}
        try:
            import yfinance as yf

            hist = yf.Ticker(ticker).history(period="5y")
        except Exception:
            return result
        if hist is None or getattr(hist, "empty", True):
            return result
        try:
            closes = hist["Close"]
        except Exception:
            return result
        pairs: List[tuple] = []
        for ts, val in closes.items():
            d = ts.date() if hasattr(ts, "date") else ts
            try:
                pairs.append((d, float(val)))
            except (TypeError, ValueError):
                continue
        pairs.sort(key=lambda p: p[0])
        if not pairs:
            return result
        for d in dates:
            qd = self._parse_date(d)
            chosen = 0.0
            for pd, v in pairs:
                if pd <= qd:
                    chosen = v
                else:
                    break
            result[d] = chosen
        return result

    @staticmethod
    def _f(row: Optional[Dict[str, Any]], key: str, *aliases: str) -> float:
        """Read a float from a statement row, trying key + aliases."""
        if not row:
            return 0.0
        for k in (key, *aliases):
            if k in row and row[k] is not None:
                try:
                    return float(row[k])
                except (TypeError, ValueError):
                    continue
        return 0.0

    # ------------------------------------------------------------------ #
    # main
    # ------------------------------------------------------------------ #
    def fetch_trends(self, ticker: str, years: int = 5) -> TrendFetchResult:
        try:
            limit = years * 4 + 8
            common = {"period": "quarter", "limit": limit}
            inc = self._get("income-statement", {**common, "symbol": ticker})
            bs = self._get("balance-sheet-statement", {**common, "symbol": ticker})
            cf = self._get("cash-flow-statement", {**common, "symbol": ticker})

            if not isinstance(inc, list) or not inc:
                return TrendFetchResult(
                    success=False,
                    ticker=ticker,
                    market=self.market,
                    source=self.source_name,
                    errors=[f"No FMP income data for {ticker}"],
                )

            inc_map = {r["date"]: r for r in inc if isinstance(r, dict) and "date" in r}
            bs_map = {
                r["date"]: r for r in (bs or []) if isinstance(r, dict) and "date" in r
            }
            cf_map = {
                r["date"]: r for r in (cf or []) if isinstance(r, dict) and "date" in r
            }

            dates = sorted(set(inc_map.keys()) & set(cf_map.keys()))[-(years * 4 + 4):]
            # shares from latest income statement (weighted average shares outstanding)
            shares = self._f(inc[0], "weightedAverageShsOut") if inc else 0.0
            close_map = self._quarterly_close(ticker, dates)
            warnings: List[str] = [
                "historical fcf_yield approximated by price x current shares "
                "(ignores dilution)"
            ]

            records: List[TrendRecord] = []
            for d in dates:
                ir = inc_map[d]
                cr = cf_map[d]
                bsr = bs_map.get(d, {})
                revenue = self._f(ir, "revenue")
                gross_profit = self._f(ir, "grossProfit")
                net_income = self._f(ir, "netIncome")
                ocf = self._f(cr, "operatingCashFlow")
                capex_raw = self._f(cr, "capitalExpenditure", "capitalExpenditures")
                fcf = self._f(cr, "freeCashFlow")
                capex = -abs(capex_raw)  # normalize to negative (cash outflow)
                if fcf == 0:
                    fcf = ocf + capex
                inventory = self._f(bsr, "inventory")
                ar = self._f(bsr, "netReceivables", "accountsReceivables")
                ap = self._f(bsr, "accountPayables", "accountPayable", "accountsPayable")
                qd = self._parse_date(d)
                close = close_map.get(d, 0.0)

                if revenue == 0 and ocf == 0:
                    continue

                records.append(
                    TrendRecord(
                        ticker=ticker,
                        market=self.market,
                        quarter_end=qd,
                        fiscal_year=qd.year,
                        fiscal_quarter=self._fiscal_quarter(qd),
                        revenue=revenue,
                        gross_profit=gross_profit,
                        net_income=net_income,
                        operating_cash_flow=ocf,
                        capex=capex,
                        free_cash_flow=fcf,
                        inventory=inventory,
                        accounts_receivable=ar,
                        accounts_payable=ap,
                        shares_outstanding=shares,
                        close_price=close,
                        source=self.source_name,
                    )
                )

            if not records:
                return TrendFetchResult(
                    success=False,
                    ticker=ticker,
                    market=self.market,
                    source=self.source_name,
                    errors=["Could not extract any quarterly trend records"],
                )

            series = TrendSeries(
                ticker=ticker,
                market=self.market,
                source=self.source_name,
                records=records,
            )
            return TrendFetchResult(
                success=True,
                ticker=ticker,
                market=self.market,
                source=self.source_name,
                series=series,
                current_shares=shares,
                warnings=warnings,
            )
        except Exception as e:
            return TrendFetchResult(
                success=False,
                ticker=ticker,
                market=self.market,
                source=self.source_name,
                errors=[str(e)],
            )
