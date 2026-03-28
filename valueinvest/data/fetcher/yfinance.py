import math
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
                "dividend_yield": info.get("dividendYield", 0) or 0,
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
                "net_working_capital": 0,
                "net_fixed_assets": 0,
                "fcf": 0,
                "depreciation": 0,
                "capex": 0,
                "dividend_per_share": info.get("trailingAnnualDividendRate", 0) or 0,
                "dividend_growth_rate": 0,  # Will be calculated below
                "growth_rate": (info.get("revenueGrowth", 0) or 0) * 100,
                # New fields from info
                "ebitda": float(info.get("ebitda", 0) or 0),
                "earnings_growth": (info.get("earningsGrowth", 0) or 0) * 100,
                "revenue_growth": (info.get("revenueGrowth", 0) or 0) * 100,
                "operating_cash_flow": float(info.get("operatingCashflow", 0) or 0),
                "total_debt": float(info.get("totalDebt", 0) or 0),
                "cash_and_equivalents": float(info.get("totalCash", 0) or 0),
            }

            # Calculate dividend growth rate from dividend history
            try:
                dividends = stock.dividends
                if dividends is not None and len(dividends) >= 2:
                    # Get annual dividends by year
                    div_by_year = dividends.groupby(dividends.index.year).sum()
                    if len(div_by_year) >= 2:
                        years = len(div_by_year) - 1
                        older_div = float(div_by_year.iloc[0])
                        newer_div = float(div_by_year.iloc[-1])
                        if older_div > 0:
                            growth = ((newer_div / older_div) ** (1 / years) - 1) * 100
                            data["dividend_growth_rate"] = round(growth, 2)
            except Exception:
                pass

            # Income statement data (override info with financials where available)
            try:
                if not financials.empty:
                    if "Total Revenue" in financials.index:
                        data["revenue"] = float(financials.loc["Total Revenue"].iloc[0])
                    if "Net Income" in financials.index:
                        data["net_income"] = float(financials.loc["Net Income"].iloc[0])
                    if "EBIT" in financials.index:
                        data["ebit"] = float(financials.loc["EBIT"].iloc[0])
                    if "EBITDA" in financials.index:
                        data["ebitda"] = float(financials.loc["EBITDA"].iloc[0])
                    if "Depreciation" in financials.index:
                        data["depreciation"] = float(financials.loc["Depreciation"].iloc[0])
                    if "Gross Profit" in financials.index:
                        data["gross_profit"] = float(financials.loc["Gross Profit"].iloc[0])
            except (KeyError, IndexError, TypeError):
                pass

            # Balance sheet data
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
                    if "Total Debt" in balance_sheet.index:
                        data["total_debt"] = float(balance_sheet.loc["Total Debt"].iloc[0])
                    if "Long Term Debt" in balance_sheet.index:
                        data["long_term_debt"] = float(balance_sheet.loc["Long Term Debt"].iloc[0])
                    if "Current Debt" in balance_sheet.index:
                        data["short_term_debt"] = float(balance_sheet.loc["Current Debt"].iloc[0])
                    if "Cash And Cash Equivalents" in balance_sheet.index:
                        data["cash_and_equivalents"] = float(
                            balance_sheet.loc["Cash And Cash Equivalents"].iloc[0]
                        )
                    if "Inventory" in balance_sheet.index:
                        data["inventory"] = float(balance_sheet.loc["Inventory"].iloc[0])
                    if "Accounts Receivable" in balance_sheet.index:
                        data["accounts_receivable"] = float(
                            balance_sheet.loc["Accounts Receivable"].iloc[0]
                        )
                    if "Accounts Payable" in balance_sheet.index:
                        data["accounts_payable"] = float(
                            balance_sheet.loc["Accounts Payable"].iloc[0]
                        )
                    if "Retained Earnings" in balance_sheet.index:
                        data["retained_earnings"] = float(
                            balance_sheet.loc["Retained Earnings"].iloc[0]
                        )
                    if "Current Liabilities" in balance_sheet.index:
                        data["current_liabilities"] = float(
                            balance_sheet.loc["Current Liabilities"].iloc[0]
                        )
                    # Populate net_working_capital and net_fixed_assets
                    if "Working Capital" in balance_sheet.index:
                        data["net_working_capital"] = float(
                            balance_sheet.loc["Working Capital"].iloc[0]
                        )
                    if "Net PPE" in balance_sheet.index:
                        data["net_fixed_assets"] = float(
                            balance_sheet.loc["Net PPE"].iloc[0]
                        )
            except (KeyError, IndexError, TypeError):
                pass

            # Cash flow data
            try:
                if not cashflow.empty:
                    if "Operating Cash Flow" in cashflow.index:
                        data["operating_cash_flow"] = float(
                            cashflow.loc["Operating Cash Flow"].iloc[0]
                        )
                    if "Free Cash Flow" in cashflow.index:
                        data["fcf"] = float(cashflow.loc["Free Cash Flow"].iloc[0])
                    if "Capital Expenditure" in cashflow.index:
                        # Store as positive value representing expenditure
                        raw_capex = float(cashflow.loc["Capital Expenditure"].iloc[0])
                        data["capex"] = abs(raw_capex)
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

            # Compute gross margin
            if "gross_profit" in data and data.get("revenue", 0) > 0:
                data["_gross_margin"] = (data["gross_profit"] / data["revenue"]) * 100

            # Compute current year ratios for prior_* comparison
            try:
                if data.get("total_assets", 0) > 0 and data.get("net_income", 0) > 0:
                    data["_roa"] = (data["net_income"] / data["total_assets"]) * 100
                if data.get("total_assets", 0) > 0 and data.get("total_liabilities", 0) > 0:
                    data["_debt_ratio"] = (data["total_liabilities"] / data["total_assets"]) * 100
                if data.get("current_liabilities", 0) > 0 and data.get("current_assets", 0) > 0:
                    data["_current_ratio"] = data["current_assets"] / data["current_liabilities"]
                if data.get("total_assets", 0) > 0 and data.get("revenue", 0) > 0:
                    data["_asset_turnover"] = data["revenue"] / data["total_assets"]
            except (TypeError, ZeroDivisionError):
                pass

            # Prior year data (second column, index 1) for F-Score and trend analysis
            try:
                if not financials.empty and len(financials.columns) >= 2:
                    prior_net_income = 0.0
                    prior_revenue = 0.0
                    prior_gross_profit = 0.0
                    prior_total_assets = 0.0
                    prior_total_liabilities = 0.0
                    prior_current_assets = 0.0
                    prior_current_liabilities = 0.0
                    prior_shares = 0.0

                    if "Net Income" in financials.index:
                        prior_net_income = float(financials.loc["Net Income"].iloc[1])
                    if "Total Revenue" in financials.index:
                        prior_revenue = float(financials.loc["Total Revenue"].iloc[1])
                    if "Gross Profit" in financials.index:
                        prior_gross_profit = float(financials.loc["Gross Profit"].iloc[1])
                    if "Diluted Average Shares" in financials.index:
                        prior_shares = float(financials.loc["Diluted Average Shares"].iloc[1])

                    # Prior balance sheet
                    if not balance_sheet.empty and len(balance_sheet.columns) >= 2:
                        if "Total Assets" in balance_sheet.index:
                            prior_total_assets = float(balance_sheet.loc["Total Assets"].iloc[1])
                        if "Total Liabilities Net Minority Interest" in balance_sheet.index:
                            prior_total_liabilities = float(
                                balance_sheet.loc["Total Liabilities Net Minority Interest"].iloc[1]
                            )
                        if "Current Assets" in balance_sheet.index:
                            prior_current_assets = float(
                                balance_sheet.loc["Current Assets"].iloc[1]
                            )
                        if "Current Liabilities" in balance_sheet.index:
                            prior_current_liabilities = float(
                                balance_sheet.loc["Current Liabilities"].iloc[1]
                            )

                    # Compute prior ROA
                    if prior_total_assets > 0 and prior_net_income != 0:
                        data["prior_roa"] = (prior_net_income / prior_total_assets) * 100

                    # Compute prior debt ratio
                    if prior_total_assets > 0 and prior_total_liabilities != 0:
                        data["prior_debt_ratio"] = (
                            prior_total_liabilities / prior_total_assets
                        ) * 100

                    # Compute prior current ratio
                    if prior_current_liabilities > 0 and prior_current_assets != 0:
                        data["prior_current_ratio"] = prior_current_assets / prior_current_liabilities

                    # Prior shares outstanding
                    if prior_shares > 0:
                        data["prior_shares_outstanding"] = prior_shares

                    # Prior gross margin
                    if prior_revenue > 0 and prior_gross_profit != 0:
                        data["prior_gross_margin"] = (prior_gross_profit / prior_revenue) * 100

                    # Prior asset turnover
                    if prior_total_assets > 0 and prior_revenue != 0:
                        data["prior_asset_turnover"] = prior_revenue / prior_total_assets
            except (KeyError, IndexError, TypeError):
                pass

            # 5-year CAGR calculations (use valid non-NaN values)
            try:
                if not financials.empty and len(financials.columns) >= 2:
                    revenues = financials.loc["Total Revenue"].values
                    net_incomes = financials.loc["Net Income"].values

                    # Drop NaN values, keep only valid positive numbers
                    valid_revenues = [v for v in revenues if not math.isnan(v) and v > 0]
                    valid_incomes = [v for v in net_incomes if not math.isnan(v) and v > 0]

                    # Revenue CAGR (use up to 5 years of data)
                    if len(valid_revenues) >= 2:
                        years = len(valid_revenues) - 1
                        r_cagr = (valid_revenues[0] / valid_revenues[-1]) ** (1 / years) - 1
                        data["revenue_cagr_5y"] = round(r_cagr * 100, 2)

                    # Earnings CAGR (use up to 5 years of data)
                    if len(valid_incomes) >= 2:
                        years = len(valid_incomes) - 1
                        e_cagr = (valid_incomes[0] / valid_incomes[-1]) ** (1 / years) - 1
                        data["earnings_cagr_5y"] = round(e_cagr * 100, 2)
            except (KeyError, IndexError, TypeError, ZeroDivisionError):
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
