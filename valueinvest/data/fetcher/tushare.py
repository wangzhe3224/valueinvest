import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import pandas as pd

from .base import BaseFetcher, FetchResult, HistoryResult


class TushareFetcher(BaseFetcher):

    def __init__(self, token: Optional[str] = None, ticker: str = "") -> None:
        self._token = token or os.environ.get("TUSHARE_TOKEN")
        self._ticker = self._normalize_ticker(ticker)
        self._api: Any = None

    @property
    def source_name(self) -> str:
        return "tushare"

    def _normalize_ticker(self, ticker: str) -> str:
        """Ensure ticker has proper suffix for Tushare."""
        if not ticker:
            return ""
        # If already has suffix, keep it
        if re.match(r"^\d{6}\.(SH|SZ|BJ)$", ticker):
            return ticker
        # Add suffix based on code
        code = re.sub(r"\.(SH|SZ|BJ)$", "", ticker)
        if code.startswith("6"):
            return f"{code}.SH"
        elif code.startswith(("0", "3")):
            return f"{code}.SZ"
        elif code.startswith(("4", "8")):
            return f"{code}.BJ"
        return f"{code}.SH"

    def _get_api(self) -> Any:
        """Initialize Tushare API lazily."""
        if self._api is not None:
            return self._api

        try:
            import tushare as ts

            if not self._token:
                raise ValueError(
                    "Tushare token required. Set TUSHARE_TOKEN environment variable "
                    "or pass token parameter. Get token at https://tushare.pro"
                )
            ts.set_token(self._token)
            self._api = ts.pro_api()
            return self._api
        except ImportError as e:
            raise ImportError(
                "tushare is required. "
                "Install with: pip install valueinvest[tushare] or pip install tushare"
            ) from e

    def fetch_quote(self, ticker: str) -> FetchResult:
        """Fetch current price and basic info from Tushare."""
        try:
            api = self._get_api()
            ts_code = self._normalize_ticker(ticker)

            # Get daily data for current price
            df = api.daily(ts_code=ts_code, limit=1)
            if df.empty:
                return FetchResult(
                    success=False,
                    data={},
                    source=self.source_name,
                    errors=[f"No data for {ts_code}"],
                    missing_fields=[],
                )

            row = df.iloc[0]

            # Get basic info
            try:
                info = api.stock_basic(ts_code=ts_code, fields="name,market")
                name = info.iloc[0]["name"] if not info.empty else ""
            except Exception:
                name = ""

            data = {
                "ticker": ts_code,
                "name": name,
                "current_price": float(row.get("close", 0) or 0),
                "shares_outstanding": 0,  # Will be filled from fundamentals
                "currency": "CNY",
                "exchange": ts_code.split(".")[1] if "." in ts_code else "SH",
            }

            return FetchResult(
                success=True,
                data=data,
                source=self.source_name,
                errors=[],
                missing_fields=["shares_outstanding"],
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
        """Fetch financial statements from Tushare."""
        try:
            api = self._get_api()
            ts_code = self._normalize_ticker(ticker)

            data: Dict[str, Any] = {
                "eps": 0,
                "bvps": 0,
                "roe": 0,
                "revenue": 0,
                "net_income": 0,
                "total_assets": 0,
                "current_assets": 0,
                "total_liabilities": 0,
                "net_debt": 0,
                "fcf": 0,
                "shares_outstanding": 0,
                "dividend_per_share": 0,
                "dividend_yield": 0,
                "dividend_growth_rate": 0,
                "growth_rate": 0,
            }

            # Get daily basic info for PE, PB, market cap
            try:
                basic = api.daily_basic(ts_code=ts_code, fields="pe,pb,total_mv,circ_mv", limit=1)
                if not basic.empty:
                    row = basic.iloc[0]
                    data["pe_ratio"] = float(row.get("pe", 0) or 0)
                    data["pb_ratio"] = float(row.get("pb", 0) or 0)
                    data["market_cap"] = float(row.get("total_mv", 0) or 0) * 1e4  # 万 to 元
            except Exception:
                pass

            # Get income statement
            try:
                income = api.income(ts_code=ts_code, fields="revenue,n_income,basic_eps", limit=1)
                if not income.empty:
                    row = income.iloc[0]
                    data["revenue"] = float(row.get("revenue", 0) or 0) * 1e4
                    data["net_income"] = float(row.get("n_income", 0) or 0) * 1e4
                    data["eps"] = float(row.get("basic_eps", 0) or 0)
            except Exception:
                pass

            # Get balance sheet
            try:
                balance = api.balancesheet(
                    ts_code=ts_code,
                    fields="total_assets,total_hldr_eqy_exc_min_int,total_liab,total_cur_assets",
                    limit=1,
                )
                if not balance.empty:
                    row = balance.iloc[0]
                    data["total_assets"] = float(row.get("total_assets", 0) or 0) * 1e4
                    data["bvps"] = 0  # Calculate from equity
                    data["current_assets"] = float(row.get("total_cur_assets", 0) or 0) * 1e4
                    data["total_liabilities"] = float(row.get("total_liab", 0) or 0) * 1e4

                    # Calculate BVPS
                    equity = float(row.get("total_hldr_eqy_exc_min_int", 0) or 0) * 1e4
                    if data["shares_outstanding"] and data["shares_outstanding"] > 0:
                        data["bvps"] = equity / data["shares_outstanding"]
            except Exception:
                pass

            # Get cash flow
            try:
                cashflow = api.cashflow(
                    ts_code=ts_code,
                    fields="n_cashflow_act_act,c_pay_for_acq_const_fi_assets",
                    limit=1,
                )
                if not cashflow.empty:
                    row = cashflow.iloc[0]
                    ocf = float(row.get("n_cashflow_act_act", 0) or 0) * 1e4
                    capex = float(row.get("c_pay_for_acq_const_fi_assets", 0) or 0) * 1e4
                    data["fcf"] = ocf - abs(capex)
            except Exception:
                pass

            # Get dividend info
            try:
                div = api.dividend(ts_code=ts_code, fields="cash_div,div_yield", limit=1)
                if not div.empty:
                    row = div.iloc[0]
                    data["dividend_per_share"] = float(row.get("cash_div", 0) or 0)
                    data["dividend_yield"] = float(row.get("div_yield", 0) or 0)
            except Exception:
                pass

            # Get FinaIndicator for ROE
            try:
                fina = api.fina_indicator(ts_code=ts_code, fields="roe", limit=1)
                if not fina.empty:
                    data["roe"] = float(fina.iloc[0].get("roe", 0) or 0)
            except Exception:
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
            api = self._get_api()
            ts_code = self._normalize_ticker(ticker)

            if end_date is None:
                end_dt = datetime.now()
            else:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")

            if start_date is None:
                years = int(period.replace("y", "").replace("Y", ""))
                start_dt = end_dt - timedelta(days=years * 365)
            else:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")

            df = api.daily(
                ts_code=ts_code,
                start_date=start_dt.strftime("%Y%m%d"),
                end_date=end_dt.strftime("%Y%m%d"),
            )

            if df is None or df.empty:
                return HistoryResult(
                    success=False,
                    ticker=ts_code,
                    source=self.source_name,
                    errors=[f"No historical data for {ts_code}"],
                )

            df = df.rename(columns={
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "vol": "volume",
            })
            df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d")
            df = df.set_index("trade_date")
            df = df.sort_index()
            df = df[["open", "high", "low", "close", "volume"]]

            return HistoryResult(
                success=True,
                ticker=ts_code,
                source=self.source_name,
                df=df,
                start_date=start_dt.date(),
                end_date=end_dt.date(),
            )

        except Exception as e:
            return HistoryResult(
                success=False,
                ticker=ticker,
                source=self.source_name,
                errors=[str(e)],
            )
