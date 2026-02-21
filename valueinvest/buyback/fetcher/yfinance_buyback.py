"""
Buyback data fetcher for US stocks using yfinance.

Data sources:
- Cash flow statement: Repurchase Of Capital Stock
- Balance sheet: Share Issued (for share reduction calculation)
- Info: marketCap, sharesOutstanding
"""
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any

from .base import BaseBuybackFetcher
from ..base import (
    BuybackFetchResult,
    BuybackRecord,
    BuybackSummary,
    BuybackStatus,
    BuybackSentiment,
    Market,
)


class YFinanceBuybackFetcher(BaseBuybackFetcher):
    """Fetch buyback data for US stocks via yfinance."""

    def __init__(self):
        self._ticker_obj = None
        self._info = None

    @property
    def market(self):
        return Market.US

    @property
    def source_name(self) -> str:
        return "yfinance"

    def _get_ticker_obj(self, ticker: str):
        if self._ticker_obj is None or self._ticker_obj.ticker != ticker:
            try:
                import yfinance as yf

                self._ticker_obj = yf.Ticker(ticker)
                self._info = None
            except ImportError as e:
                raise ImportError(
                    "yfinance is required for US stock buyback data. "
                    "Install with: pip install valueinvest[us]"
                ) from e
        return self._ticker_obj

    def _get_info(self, ticker: str) -> Dict[str, Any]:
        if self._info is None:
            stock = self._get_ticker_obj(ticker)
            self._info = stock.info or {}
        return self._info

    def fetch_buyback(
        self,
        ticker: str,
        days: int = 365,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> BuybackFetchResult:
        try:
            stock = self._get_ticker_obj(ticker)
            info = self._get_info(ticker)

            if not info:
                return BuybackFetchResult(
                    success=False,
                    ticker=ticker,
                    market=self.market,
                    source=self.source_name,
                    errors=[f"No data found for ticker: {ticker}"],
                )

            market_cap = info.get("marketCap", 0)
            shares_outstanding = info.get("sharesOutstanding", 0)
            dividend_yield = info.get("dividendYield", 0) or 0

            cashflow = stock.cashflow
            balance_sheet = stock.balance_sheet

            records = []
            yearly_amounts: Dict[int, float] = {}
            total_amount = 0.0
            shares_data = []

            if cashflow is not None and not cashflow.empty:
                if "Repurchase Of Capital Stock" in cashflow.index:
                    repurchase_row = cashflow.loc["Repurchase Of Capital Stock"]

                    for col_idx, col in enumerate(repurchase_row.index):
                        try:
                            value = repurchase_row[col]
                            if value is None or str(value) == "nan":
                                continue

                            amount = abs(float(value))
                            if amount <= 0:
                                continue

                            col_date = col
                            if hasattr(col, "year"):
                                year = col.year
                            else:
                                year = int(str(col)[:4])

                            fiscal_year_end = (
                                date(year, 12, 31) if hasattr(col, "month") else date(year, 12, 31)
                            )

                            record = BuybackRecord(
                                ticker=ticker,
                                market=self.market,
                                execution_date=fiscal_year_end,
                                amount=amount,
                                status=BuybackStatus.COMPLETED,
                                source=self.source_name,
                                raw_data={"fiscal_year": year, "raw_value": value},
                            )
                            records.append(record)

                            if year not in yearly_amounts:
                                yearly_amounts[year] = 0.0
                            yearly_amounts[year] += amount
                            total_amount += amount

                        except (KeyError, TypeError, ValueError):
                            continue

            if balance_sheet is not None and not balance_sheet.empty:
                if "Share Issued" in balance_sheet.index:
                    shares_row = balance_sheet.loc["Share Issued"]
                    for col in shares_row.index:
                        try:
                            val = shares_row[col]
                            if val is not None and str(val) != "nan":
                                shares_data.append(
                                    {
                                        "date": col,
                                        "shares": float(val),
                                    }
                                )
                        except (KeyError, TypeError, ValueError):
                            continue

            shares_reduction_rate = 0.0
            if len(shares_data) >= 2:
                shares_data.sort(key=lambda x: x["date"], reverse=True)
                latest_shares = shares_data[0]["shares"]
                oldest_shares = shares_data[-1]["shares"]
                if oldest_shares > 0:
                    years_diff = len(shares_data) - 1
                    reduction = (oldest_shares - latest_shares) / oldest_shares
                    if years_diff > 0:
                        shares_reduction_rate = (reduction / years_diff) * 100

            buyback_yield = 0.0
            if market_cap and market_cap > 0 and yearly_amounts:
                latest_year = max(yearly_amounts.keys())
                latest_amount = yearly_amounts.get(latest_year, 0)
                buyback_yield = (latest_amount / market_cap) * 100

            total_shareholder_yield = buyback_yield + dividend_yield

            sentiment = BuybackSentiment.NONE
            if buyback_yield > 3.0:
                sentiment = BuybackSentiment.AGGRESSIVE
            elif buyback_yield > 1.0:
                sentiment = BuybackSentiment.MODERATE
            elif buyback_yield > 0:
                sentiment = BuybackSentiment.MINIMAL

            summary = BuybackSummary(
                ticker=ticker,
                market=self.market,
                period_days=days,
                total_amount=total_amount,
                buyback_yield=buyback_yield,
                shares_reduction_rate=shares_reduction_rate,
                dividend_yield=dividend_yield,
                total_shareholder_yield=total_shareholder_yield,
                yearly_amounts=yearly_amounts,
                record_count=len(records),
                sentiment=sentiment,
            )

            return BuybackFetchResult(
                success=True,
                ticker=ticker,
                market=self.market,
                source=self.source_name,
                records=records,
                summary=summary,
                market_cap=market_cap,
                shares_outstanding=shares_outstanding,
            )

        except Exception as e:
            return BuybackFetchResult(
                success=False,
                ticker=ticker,
                market=self.market,
                source=self.source_name,
                errors=[str(e)],
            )
