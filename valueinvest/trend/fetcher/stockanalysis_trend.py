"""Quarterly trend data fetcher via stockanalysis.com (scrape).

stockanalysis.com publishes ~5 years (20 quarters) of quarterly financials as
server-rendered HTML tables -- free, no API key. This fetcher parses those
tables (income / balance-sheet / cash-flow-statement) into TrendRecords.

Trade-off: it couples to the site's HTML structure, so a redesign may require
maintenance. Values are reported in millions and scaled to absolute. Period
dates are read from the table header (accurate quarter-ends, no fiscal-year
guessing). Closing prices come from yfinance.
"""
import re
from datetime import date
from typing import Any, Dict, List, Optional, Set

from bs4 import BeautifulSoup

from .base import BaseTrendFetcher
from ..base import TrendFetchResult, TrendRecord, TrendSeries, Market

_INCOME_MAP: Dict[str, Set[str]] = {
    "revenue": {"Revenue", "Total Revenue"},
    "gross_profit": {"Gross Profit", "Gross Income"},
    "net_income": {"Net Income", "Net Income Common Stockholders"},
    "shares": {"Shares Outstanding", "Diluted Shares Outstanding", "Shares Out"},
}
_BALANCE_MAP: Dict[str, Set[str]] = {
    "inventory": {"Inventory"},
    "ar": {"Receivables", "Total Receivables", "Accounts Receivable", "Net Receivables"},
    "ap": {"Payables", "Accounts Payable", "Total Payables", "Accounts Payables"},
}
_CASHFLOW_MAP: Dict[str, Set[str]] = {
    "ocf": {"Operating Cash Flow", "Net Operating Cash Flow", "Cash from Operations"},
    "capex": {"Capital Expenditures", "Capital Expenditure"},
    "fcf": {"Free Cash Flow"},
}

_MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


class StockAnalysisTrendFetcher(BaseTrendFetcher):
    """Fetch quarterly trend data by scraping stockanalysis.com."""

    BASE = "https://stockanalysis.com/stocks"

    @property
    def market(self) -> Market:
        return Market.US

    @property
    def source_name(self) -> str:
        return "stockanalysis"

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _fetch_html(self, ticker: str, section: str) -> str:
        import requests

        url = f"{self.BASE}/{ticker}/financials{section}/?p=quarterly"
        resp = requests.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
                )
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.text

    @staticmethod
    def _parse_period(cell_text: str) -> Optional[date]:
        m = re.search(r"([A-Z][a-z]{2})\s+(\d{1,2}),\s*(\d{4})", cell_text)
        if not m:
            return None
        mon = _MONTHS.get(m.group(1))
        if not mon:
            return None
        return date(int(m.group(3)), mon, int(m.group(2)))

    @classmethod
    def _thead_dates(cls, table: Any) -> List[date]:
        thead = table.find("thead")
        if not thead:
            return []
        for tr in thead.find_all("tr"):
            cells = [th.get_text(" ", strip=True) for th in tr.find_all("th")]
            if any(re.search(r"\d{1,2},\s*\d{4}", c) for c in cells):
                dates = [cls._parse_period(c) for c in cells[1:]]
                return [d for d in dates if d]
        return []

    @staticmethod
    def _parse_num(s: str) -> float:
        """Parse a displayed value (millions, comma-grouped, parenthesized neg)."""
        s = s.strip().replace(",", "")
        if not s or s in ("N/A", "-", "—", "--"):
            return 0.0
        neg = s.startswith("(") and s.endswith(")")
        s = s.strip("()$%")
        try:
            v = float(s)
        except ValueError:
            return 0.0
        return -v * 1e6 if neg else v * 1e6

    @classmethod
    def _parse_table(
        cls, html: str, alias_map: Dict[str, Set[str]]
    ) -> Dict[date, Dict[str, float]]:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            return {}
        dates = cls._thead_dates(table)
        if not dates:
            return {}
        out: Dict[date, Dict[str, float]] = {d: {} for d in dates}
        body = table.find("tbody") or table
        for tr in body.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 2:
                continue
            strs = list(tds[0].stripped_strings)
            if not strs:
                continue
            label = strs[0]
            canon = None
            for key, aliases in alias_map.items():
                if label in aliases:
                    canon = key
                    break
            if not canon:
                continue
            for i, d in enumerate(dates):
                if i + 1 < len(tds):
                    out[d][canon] = cls._parse_num(tds[i + 1].get_text(strip=True))
        return out

    def _quarterly_close(self, ticker: str, dates: List[date]) -> Dict[date, float]:
        """Close on/nearest-before each quarter-end via yfinance."""
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
            chosen = 0.0
            for pd, v in pairs:
                if pd <= d:
                    chosen = v
                else:
                    break
            result[d] = chosen
        return result

    def _latest_shares(self, ticker: str) -> float:
        """Current shares outstanding via yfinance (single-point; ignores dilution).

        stockanalysis tables expose EPS but not share count, so we source the
        current share count from yfinance for the approximated FCF yield.
        """
        try:
            import yfinance as yf

            info = yf.Ticker(ticker).info or {}
            return (
                info.get("sharesOutstanding", 0)
                or info.get("impliedSharesOutstanding", 0)
                or 0.0
            )
        except Exception:
            return 0.0

    @staticmethod
    def _fiscal_quarter(qend: date) -> int:
        return (qend.month - 1) // 3 + 1

    # ------------------------------------------------------------------ #
    # main
    # ------------------------------------------------------------------ #
    def fetch_trends(self, ticker: str, years: int = 5) -> TrendFetchResult:
        try:
            inc = self._parse_table(self._fetch_html(ticker, ""), _INCOME_MAP)
            bs = self._parse_table(self._fetch_html(ticker, "/balance-sheet"), _BALANCE_MAP)
            cf = self._parse_table(
                self._fetch_html(ticker, "/cash-flow-statement"), _CASHFLOW_MAP
            )

            if not inc:
                return TrendFetchResult(
                    success=False,
                    ticker=ticker,
                    market=self.market,
                    source=self.source_name,
                    errors=[f"No stockanalysis income data for {ticker}"],
                )

            # dates present in both income and cashflow, chronological, capped
            all_dates = sorted(set(inc.keys()) & set(cf.keys()))[-(years * 4 + 4):]

            # stockanalysis tables expose EPS but not share count; pull current
            # shares from yfinance (single-point, ignores dilution).
            shares = self._latest_shares(ticker)

            close_map = self._quarterly_close(ticker, all_dates)
            warnings: List[str] = [
                "historical fcf_yield approximated by price x current shares "
                "(ignores dilution)"
            ]

            records: List[TrendRecord] = []
            for d in all_dates:
                ir = inc.get(d, {})
                bsr = bs.get(d, {})
                cr = cf.get(d, {})
                revenue = ir.get("revenue", 0.0)
                gross_profit = ir.get("gross_profit", 0.0)
                net_income = ir.get("net_income", 0.0)
                ocf = cr.get("ocf", 0.0)
                capex_raw = cr.get("capex", 0.0)
                fcf = cr.get("fcf", 0.0)
                capex = -abs(capex_raw)
                if fcf == 0:
                    fcf = ocf + capex
                inventory = bsr.get("inventory", 0.0)
                ar = bsr.get("ar", 0.0)
                ap = bsr.get("ap", 0.0)

                if revenue == 0 and ocf == 0:
                    continue

                records.append(
                    TrendRecord(
                        ticker=ticker,
                        market=self.market,
                        quarter_end=d,
                        fiscal_year=d.year,
                        fiscal_quarter=self._fiscal_quarter(d),
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
                        close_price=close_map.get(d, 0.0),
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
