"""Quarterly trend data fetcher for US stocks using yfinance.

This is the first place in the library that touches yfinance's
``quarterly_financials`` / ``quarterly_balance_sheet`` / ``quarterly_cashflow``
statements. It:

- de-YTDs cumulative cash-flow figures (yfinance quarterly_cashflow is often
  year-to-date cumulative within a fiscal year),
- derives COGS as ``Total Revenue - Gross Profit`` (never read directly),
- approximates historical FCF yield via ``close_price x current shares``
  (the library has no historical market-cap source).
"""
from datetime import date
from typing import Any, Dict, List, Optional

from .base import BaseTrendFetcher
from ..base import TrendFetchResult, TrendRecord, TrendSeries, Market


class YFinanceTrendFetcher(BaseTrendFetcher):
    """Fetch quarterly trend data for US stocks via yfinance."""

    def __init__(self) -> None:
        self._ticker_obj: Any = None
        self._info: Optional[Dict[str, Any]] = None

    @property
    def market(self) -> Market:
        return Market.US

    @property
    def source_name(self) -> str:
        return "yfinance"

    # ------------------------------------------------------------------ #
    # yfinance access (mirrors cashflow/fetcher/yfinance_cashflow.py)
    # ------------------------------------------------------------------ #
    def _get_ticker_obj(self, ticker: str) -> Any:
        if self._ticker_obj is None or getattr(self._ticker_obj, "ticker", None) != ticker:
            try:
                import yfinance as yf

                self._ticker_obj = yf.Ticker(ticker)
                self._info = None
            except ImportError as e:
                raise ImportError(
                    "yfinance is required for US stock trend data. "
                    "Install with: pip install valueinvest[us]"
                ) from e
        return self._ticker_obj

    def _get_info(self, ticker: str) -> Dict[str, Any]:
        if self._info is None:
            stock = self._get_ticker_obj(ticker)
            self._info = stock.info or {}
        return self._info

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _get_value(row_name: str, df: Any, col: Any) -> float:
        """Safely read a (row, col) cell from a yfinance statement DataFrame."""
        try:
            if df is not None and row_name in df.index:
                val = df.loc[row_name, col]
                if val is not None and str(val) != "nan":
                    return float(val)
        except (KeyError, TypeError, ValueError):
            pass
        return 0.0

    @staticmethod
    def _col_to_date(col: Any) -> date:
        if hasattr(col, "date"):
            return col.date()
        if hasattr(col, "year"):
            return date(col.year, col.month, col.day)
        s = str(col)
        return date(int(s[:4]), int(s[5:7]), int(s[8:10]))

    @staticmethod
    def _fiscal_quarter(qend: date) -> int:
        return (qend.month - 1) // 3 + 1

    def _quarterly_close_prices(self, quarters: List[Any]) -> Dict[Any, float]:
        """Close price on/nearest-before each quarter-end (for approx FCF yield)."""
        prices: Dict[Any, float] = {col: 0.0 for col in quarters}
        try:
            stock = self._ticker_obj
            hist = stock.history(period="5y") if stock is not None else None
        except Exception:
            hist = None
        if hist is None or getattr(hist, "empty", True):
            return prices
        try:
            closes = hist["Close"]
        except Exception:
            return prices
        # (date, close) pairs sorted ascending
        pairs: List[tuple] = []
        for ts, val in closes.items():
            d = ts.date() if hasattr(ts, "date") else ts
            try:
                pairs.append((d, float(val)))
            except (TypeError, ValueError):
                continue
        pairs.sort(key=lambda p: p[0])
        if not pairs:
            return prices
        for col in quarters:
            qd = self._col_to_date(col)
            chosen = 0.0
            for d, v in pairs:
                if d <= qd:
                    chosen = v
                else:
                    break
            prices[col] = chosen
        return prices

    def _de_ytd(
        self, raw: Dict[Any, float], quarters: List[Any]
    ) -> tuple[Dict[Any, float], bool]:
        """De-accumulate YTD figures within each fiscal year.

        yfinance quarterly cash-flow columns are frequently year-to-date
        cumulative within a fiscal year. If values within a fiscal year are
        monotonically non-decreasing, treat them as cumulative and difference;
        otherwise keep as-is. Resets at each fiscal-year boundary.
        """
        result: Dict[Any, float] = {}
        was_de_ytd = False
        by_fy: Dict[int, List[Any]] = {}
        for col in quarters:
            fy = self._col_to_date(col).year
            by_fy.setdefault(fy, []).append(col)
        for cols in by_fy.values():
            vals = [raw.get(c, 0.0) for c in cols]
            monotonic = all(vals[i] >= vals[i - 1] - 1e-6 for i in range(1, len(vals)))
            if monotonic and len(vals) >= 2:
                was_de_ytd = True
                for i, c in enumerate(cols):
                    result[c] = vals[i] if i == 0 else vals[i] - vals[i - 1]
            else:
                for i, c in enumerate(cols):
                    result[c] = vals[i]
        return result, was_de_ytd

    # ------------------------------------------------------------------ #
    # main
    # ------------------------------------------------------------------ #
    def fetch_trends(self, ticker: str, years: int = 5) -> TrendFetchResult:
        try:
            stock = self._get_ticker_obj(ticker)
            info = self._get_info(ticker)
            if not info:
                return TrendFetchResult(
                    success=False,
                    ticker=ticker,
                    market=self.market,
                    source=self.source_name,
                    errors=[f"No data found for ticker: {ticker}"],
                )

            shares = (
                info.get("sharesOutstanding", 0)
                or info.get("impliedSharesOutstanding", 0)
                or 0
            )
            current_market_cap = info.get("marketCap", 0) or 0

            qf = getattr(stock, "quarterly_financials", None)
            qbs = getattr(stock, "quarterly_balance_sheet", None)
            qcf = getattr(stock, "quarterly_cashflow", None)

            if qcf is None or getattr(qcf, "empty", True):
                return TrendFetchResult(
                    success=False,
                    ticker=ticker,
                    market=self.market,
                    source=self.source_name,
                    errors=["No quarterly cash flow data available"],
                    current_market_cap=current_market_cap,
                    current_shares=shares,
                )

            # Quarter columns come from cashflow (FCF is essential); chronological asc.
            quarters = sorted(qcf.columns, key=self._col_to_date)[-(years * 4 + 4):]

            warnings: List[str] = []

            # OCF / capex: raw read then de-YTD within each fiscal year.
            raw_ocf = {
                col: self._get_value("Operating Cash Flow", qcf, col)
                or self._get_value(
                    "Cash Flow From Continuing Operating Activities", qcf, col
                )
                for col in quarters
            }
            raw_capex = {
                col: self._get_value("Capital Expenditure", qcf, col) for col in quarters
            }
            single_ocf, de_ytd_ocf = self._de_ytd(raw_ocf, quarters)
            single_capex, _ = self._de_ytd(raw_capex, quarters)
            if de_ytd_ocf:
                warnings.append(
                    "Operating cash flow / capex de-YTD'd from quarterly_cashflow"
                )

            close_prices = self._quarterly_close_prices(quarters)
            warnings.append(
                "historical fcf_yield approximated by price x current shares "
                "(ignores dilution)"
            )

            records: List[TrendRecord] = []
            for col in quarters:
                qend = self._col_to_date(col)
                revenue = self._get_value("Total Revenue", qf, col)
                gross_profit = self._get_value("Gross Profit", qf, col)
                net_income = self._get_value("Net Income", qf, col) or self._get_value(
                    "Net Income Common Stockholders", qf, col
                )
                ocf = single_ocf.get(col, 0.0)
                capex = single_capex.get(col, 0.0)
                fcf = ocf + capex  # capex is negative in yfinance convention
                inventory = self._get_value("Inventory", qbs, col)
                ar = self._get_value("Accounts Receivable", qbs, col)
                ap = self._get_value("Accounts Payable", qbs, col)
                close = close_prices.get(col, 0.0)

                # Skip quarters with no meaningful activity.
                if revenue == 0 and ocf == 0:
                    continue

                records.append(
                    TrendRecord(
                        ticker=ticker,
                        market=self.market,
                        quarter_end=qend,
                        fiscal_year=qend.year,
                        fiscal_quarter=self._fiscal_quarter(qend),
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
                    current_market_cap=current_market_cap,
                    current_shares=shares,
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
                current_market_cap=current_market_cap,
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
