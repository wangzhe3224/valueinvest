from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from .base import BaseFetcher, FetchResult, HistoryResult


class YFinanceFetcher(BaseFetcher):

    def __init__(self) -> None:
        self._ticker: Optional[str] = None
        self._info: Optional[Dict[str, Any]] = None

    @property
    def source_name(self) -> str:
        return "yfinance"

    def _get_ticker_obj(self, ticker: str) -> Any:
        try:
            import yfinance as yf

            return yf.Ticker(ticker)
        except ImportError as e:
            raise ImportError(
                "yfinance is required for US stock data. "
                "Install with: pip install valueinvest[us] or pip install yfinance"
            ) from e

    def fetch_quote(self, ticker: str) -> FetchResult:
        try:
            stock = self._get_ticker_obj(ticker)
            info = stock.info

            if not info:
                return FetchResult(
                    success=False,
                    data={},
                    source=self.source_name,
                    errors=[f"No data found for ticker: {ticker}"],
                    missing_fields=[],
                )

            shares = info.get("sharesOutstanding", 0) or info.get(
                "impliedSharesOutstanding", 0
            )

            data = {
                "ticker": ticker,
                "name": info.get("longName", info.get("shortName", "")),
                "current_price": info.get("currentPrice", info.get("regularMarketPrice", 0)),
                "shares_outstanding": float(shares) if shares else 0.0,
                "market_cap": info.get("marketCap", 0),
                "pe_ratio": info.get("trailingPE", 0) or 0,
                "pb_ratio": info.get("priceToBook", 0) or 0,
                "dividend_yield": (info.get("dividendYield", 0) or 0) * 100,
                "currency": info.get("currency", "USD"),
                "exchange": info.get("exchange", ""),
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
            }

            missing = [k for k, v in data.items() if v is None or v == 0]

            return FetchResult(
                success=True,
                data=data,
                source=self.source_name,
                errors=[],
                missing_fields=missing,
            )

        except Exception as e:
            return FetchResult(
                success=False,
                data={},
                source=self.source_name,
                errors=[str(e)],
                missing_fields=[],
            )

    def fetch_fundamentals(self, ticker: str) -> FetchResult:
        try:
            stock = self._get_ticker_obj(ticker)
            info = stock.info

            if not info:
                return FetchResult(
                    success=False,
                    data={},
                    source=self.source_name,
                    errors=[f"No fundamental data for ticker: {ticker}"],
                    missing_fields=[],
                )

            financials = stock.financials
            balance_sheet = stock.balance_sheet
            cashflow = stock.cashflow

            data: Dict[str, Any] = {
                "eps": info.get("trailingEps", 0) or 0,
                "bvps": info.get("bookValue", 0) or 0,
                "revenue": info.get("totalRevenue", 0) or 0,
                "net_income": info.get("netIncomeToCommon", 0) or 0,
                "ebit": info.get("ebit", 0) or 0,
                "roe": (info.get("returnOnEquity", 0) or 0) * 100,
                "operating_margin": (info.get("operatingMargins", 0) or 0) * 100,
                "total_assets": info.get("totalAssets", 0) or 0,
                "current_assets": 0,
                "total_liabilities": info.get("totalDebt", 0) or 0,
                "net_debt": info.get("netDebt", 0) or 0,
                "fcf": 0,
                "depreciation": 0,
                "capex": 0,
                "dividend_per_share": info.get("trailingAnnualDividendRate", 0) or 0,
                "dividend_growth_rate": 0,
                "growth_rate": 0,
            }

            try:
                if not financials.empty:
                    if "Total Revenue" in financials.index:
                        data["revenue"] = float(financials.loc["Total Revenue"].iloc[0])
                    if "Net Income" in financials.index:
                        data["net_income"] = float(financials.loc["Net Income"].iloc[0])
                    if "EBIT" in financials.index:
                        data["ebit"] = float(financials.loc["EBIT"].iloc[0])
                    if "Depreciation" in financials.index:
                        data["depreciation"] = float(financials.loc["Depreciation"].iloc[0])
            except (KeyError, IndexError, TypeError):
                pass

            try:
                if not balance_sheet.empty:
                    if "Total Assets" in balance_sheet.index:
                        data["total_assets"] = float(balance_sheet.loc["Total Assets"].iloc[0])
                    if "Current Assets" in balance_sheet.index:
                        data["current_assets"] = float(
                            balance_sheet.loc["Current Assets"].iloc[0]
                        )
                    if "Total Liabilities Net Minority Interest" in balance_sheet.index:
                        data["total_liabilities"] = float(
                            balance_sheet.loc["Total Liabilities Net Minority Interest"].iloc[0]
                        )
            except (KeyError, IndexError, TypeError):
                pass

            try:
                if not cashflow.empty:
                    if "Free Cash Flow" in cashflow.index:
                        data["fcf"] = float(cashflow.loc["Free Cash Flow"].iloc[0])
                    if "Capital Expenditure" in cashflow.index:
                        data["capex"] = float(cashflow.loc["Capital Expenditure"].iloc[0])
                    if "Depreciation And Amortization" in cashflow.index:
                        data["depreciation"] = float(
                            cashflow.loc["Depreciation And Amortization"].iloc[0]
                        )
                    # SBC data
                    if "Stock Based Compensation" in cashflow.index:
                        data["sbc"] = float(cashflow.loc["Stock Based Compensation"].iloc[0])
                    # Share issuance/repurchase (financing activities)
                    if "Issuance Of Stock" in cashflow.index:
                        data["shares_issued"] = abs(float(cashflow.loc["Issuance Of Stock"].iloc[0]))
                    if "Repurchase Of Stock" in cashflow.index:
                        data["shares_repurchased"] = abs(float(cashflow.loc["Repurchase Of Stock"].iloc[0]))
            except (KeyError, IndexError, TypeError):
                pass

            missing = [k for k, v in data.items() if v is None or v == 0]

            return FetchResult(
                success=True,
                data=data,
                source=self.source_name,
                errors=[],
                missing_fields=missing,
            )

        except Exception as e:
            return FetchResult(
                success=False,
                data={},
                source=self.source_name,
                errors=[str(e)],
                missing_fields=[],
            )

    def fetch_all(self, ticker: str) -> FetchResult:
        quote = self.fetch_quote(ticker)
        fundamentals = self.fetch_fundamentals(ticker)

        combined = {**fundamentals.data, **quote.data}
        missing = [k for k, v in combined.items() if v is None or v == 0]

        return FetchResult(
            success=quote.success or fundamentals.success,
            data=combined,
            source=self.source_name,
            errors=quote.errors + fundamentals.errors,
            missing_fields=missing,
        )

    def fetch_history(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "5y",
        adjust: str = "qfq",
    ) -> HistoryResult:
        try:
            stock = self._get_ticker_obj(ticker)

            if start_date and end_date:
                df = stock.history(start=start_date, end=end_date)
            else:
                period_map = {
                    "1y": "1y",
                    "2y": "2y",
                    "3y": "3y",
                    "5y": "5y",
                    "10y": "10y",
                    "max": "max",
                }
                yf_period = period_map.get(period.lower(), "5y")
                df = stock.history(period=yf_period)

            if df is None or df.empty:
                return HistoryResult(
                    success=False,
                    ticker=ticker,
                    source=self.source_name,
                    errors=[f"No historical data for {ticker}"],
                )

            df = df.rename(columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            })
            df = df[["open", "high", "low", "close", "volume"]]
            df = df.sort_index()

            dates = df.index.tolist()
            start_dt = dates[0].date() if dates else None
            end_dt = dates[-1].date() if dates else None

            return HistoryResult(
                success=True,
                ticker=ticker,
                source=self.source_name,
                df=df,
                start_date=start_dt,
                end_date=end_dt,
            )

        except Exception as e:
            return HistoryResult(
                success=False,
                ticker=ticker,
                source=self.source_name,
                errors=[str(e)],
            )
