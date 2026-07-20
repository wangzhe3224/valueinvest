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

    def _annual_report_filter(self, df: "pd.DataFrame") -> "pd.DataFrame":
        """Filter to keep only annual reports (end_type=4, report_type=1)."""
        import pandas as _pd
        if df is None or df.empty:
            return df
        masks = []
        if "end_type" in df.columns:
            masks.append(df["end_type"] == "4")
        if "report_type" in df.columns:
            masks.append(df["report_type"] == "1")
        if masks:
            combined = masks[0]
            for m in masks[1:]:
                combined = combined & m
            df = df[combined]
        return df

    def _fetch_prior_year_data(self, api: Any, ts_code: str, current_end_date: str) -> Dict[str, Any]:
        """Fetch prior-year annual data for F-Score and M-Score comparison."""
        prior: Dict[str, Any] = {}
        try:
            cur_year = int(current_end_date[:4])
            prior_year = str(cur_year - 1)
            import pandas as _pd

            p_revenue = 0.0
            p_net_income = 0.0
            p_total_assets = 0.0
            p_total_liab = 0.0
            p_cur_assets = 0.0
            p_cur_liab = 0.0

            # Prior year income statement
            try:
                inc = api.income(ts_code=ts_code,
                                 fields="end_date,end_type,report_type,revenue,n_income",
                                 start_date=f"{prior_year}0101", end_date=f"{prior_year}1231", limit=10)
                if inc is not None and not inc.empty:
                    inc = self._annual_report_filter(inc)
                    if not inc.empty:
                        row = inc.sort_values("end_date", ascending=False).iloc[0]
                        p_revenue = float(row.get("revenue", 0) or 0)
                        p_net_income = float(row.get("n_income", 0) or 0)
                        prior["prior_revenue"] = p_revenue
                        prior["prior_net_income"] = p_net_income
            except Exception:
                pass

            # Prior year fina_indicator for gross margin (most reliable)
            try:
                fina = api.fina_indicator(ts_code=ts_code,
                    fields="end_date,grossprofit_margin,roe",
                    start_date=f"{prior_year}0101", end_date=f"{prior_year}1231", limit=10)
                if fina is not None and not fina.empty:
                    fina_annual = fina[fina["end_date"].astype(str).str.endswith("1231")]
                    if not fina_annual.empty:
                        row = fina_annual.iloc[0]
                        prior["prior_gross_margin"] = float(row.get("grossprofit_margin", 0) or 0)
            except Exception:
                pass

            # Prior year balance sheet
            try:
                bal = api.balancesheet(
                    ts_code=ts_code,
                    fields="end_date,end_type,report_type,total_assets,total_hldr_eqy_exc_min_int,total_liab,total_cur_assets,total_cur_liab",
                    start_date=f"{prior_year}0101", end_date=f"{prior_year}1231", limit=10,
                )
                if bal is not None and not bal.empty:
                    bal = self._annual_report_filter(bal)
                    if not bal.empty:
                        row = bal.sort_values("end_date", ascending=False).iloc[0]
                        p_total_assets = float(row.get("total_assets", 0) or 0)
                        p_total_liab = float(row.get("total_liab", 0) or 0)
                        p_cur_assets = float(row.get("total_cur_assets", 0) or 0)
                        p_cur_liab = float(row.get("total_cur_liab", 0) or 0)
                        prior["prior_total_assets"] = p_total_assets
                        prior["prior_total_liabilities"] = p_total_liab
                        prior["prior_current_assets"] = p_cur_assets
                        # F-Score prior fields
                        if p_total_assets > 0:
                            prior["prior_debt_ratio"] = (p_total_liab / p_total_assets) * 100
                            if p_net_income > 0:
                                prior["prior_roa"] = (p_net_income / p_total_assets) * 100
                            if p_revenue > 0:
                                prior["prior_asset_turnover"] = p_revenue / p_total_assets
                        if p_cur_liab > 0:
                            prior["prior_current_ratio"] = p_cur_assets / p_cur_liab
            except Exception:
                pass

            # Prior year cash flow
            try:
                cf = api.cashflow(
                    ts_code=ts_code,
                    fields="end_date,end_type,report_type,n_cashflow_act,free_cashflow",
                    start_date=f"{prior_year}0101", end_date=f"{prior_year}1231", limit=10,
                )
                if cf is not None and not cf.empty:
                    cf = self._annual_report_filter(cf)
                    if not cf.empty:
                        row = cf.sort_values("end_date", ascending=False).iloc[0]
                        prior["prior_ocf"] = float(row.get("n_cashflow_act", 0) or 0)
            except Exception:
                pass

            # Prior shares (approximate from annual market data)
            try:
                basic = api.daily_basic(
                    ts_code=ts_code,
                    fields="trade_date,total_share",
                    start_date=f"{prior_year}1201", end_date=f"{prior_year}1231", limit=5,
                )
                if basic is not None and not basic.empty:
                    ts_val = float(basic.iloc[0].get("total_share", 0) or 0)
                    if ts_val > 0:
                        prior["prior_shares_outstanding"] = ts_val * 1e4
            except Exception:
                pass

        except Exception:
            pass
        return prior

    def fetch_fundamentals(self, ticker: str) -> FetchResult:
        """Fetch financial statements from Tushare."""
        try:
            api = self._get_api()
            ts_code = self._normalize_ticker(ticker)

            data: Dict[str, Any] = {
                # Core financials
                "eps": 0, "bvps": 0, "roe": 0, "revenue": 0, "net_income": 0,
                "total_assets": 0, "current_assets": 0, "total_liabilities": 0,
                "net_debt": 0, "fcf": 0, "shares_outstanding": 0,
                "dividend_per_share": 0, "dividend_yield": 0,
                "dividend_growth_rate": 0, "growth_rate": 0,
                # Moat / quality fields
                "ebit": 0, "gross_margin": 0, "operating_margin": 0,
                "interest_expense": 0, "depreciation": 0,
                "revenue_cagr_5y": 0, "earnings_cagr_5y": 0,
            }

            # === Daily basic: PE(TTM), PB, market cap, shares ===
            try:
                basic = api.daily_basic(ts_code=ts_code,
                    fields="pe,pb,pe_ttm,total_mv,circ_mv,total_share", limit=1)
                if not basic.empty:
                    row = basic.iloc[0]
                    data["pb_ratio"] = float(row.get("pb", 0) or 0)
                    data["market_cap"] = float(row.get("total_mv", 0) or 0) * 1e4
                    total_share = float(row.get("total_share", 0) or 0)
                    if total_share > 0:
                        data["shares_outstanding"] = total_share * 1e4
                    # Prefer PE_TTM over static PE
                    pe_ttm = float(row.get("pe_ttm", 0) or 0)
                    pe_static = float(row.get("pe", 0) or 0)
                    if pe_ttm > 0:
                        data["pe_ratio"] = pe_ttm
                    elif pe_static > 0:
                        data["pe_ratio"] = pe_static
            except Exception:
                pass

            # === Fina indicator: ROE, gross margin, net margin, EBIT ===
            fina_end_date = ""
            try:
                fina = api.fina_indicator(ts_code=ts_code,
                    fields="end_date,roe,grossprofit_margin,netprofit_margin,ebit,ebitda",
                    limit=1)
                if not fina.empty:
                    row = fina.iloc[0]
                    data["roe"] = float(row.get("roe", 0) or 0)
                    # Tushare: grossprofit_margin is percentage; gross_margin is absolute yuan
                    data["gross_margin"] = float(row.get("grossprofit_margin", 0) or 0)
                    # Also set _gross_margin for Stock.gross_margin property
                    data["_gross_margin"] = data["gross_margin"]
                    data["operating_margin"] = float(row.get("netprofit_margin", 0) or 0)
                    data["ebit"] = float(row.get("ebit", 0) or 0)
                    fina_end_date = str(row.get("end_date", ""))
            except Exception:
                pass

            # === Income statement ===
            cur_end_date = ""
            try:
                income = api.income(ts_code=ts_code,
                    fields="end_date,revenue,n_income,basic_eps,operate_profit,"
                           "fin_exp_int_exp,sell_exp,admin_exp,rd_exp",
                    limit=1)
                if not income.empty:
                    row = income.iloc[0]
                    data["revenue"] = float(row.get("revenue", 0) or 0)
                    data["net_income"] = float(row.get("n_income", 0) or 0)
                    data["eps"] = float(row.get("basic_eps", 0) or 0)
                    # Tushare: fin_exp_int_exp is interest expense within financial expenses
                    data["interest_expense"] = abs(float(row.get("fin_exp_int_exp", 0) or 0))
                    cur_end_date = str(row.get("end_date", ""))
                    # ebit from income if fina didn't have it
                    if data["ebit"] == 0:
                        op = float(row.get("operate_profit", 0) or 0)
                        ie = abs(float(row.get("fin_exp_int_exp", 0) or 0))
                        if op != 0:
                            data["ebit"] = op + ie
            except Exception:
                pass

            # === Balance sheet ===
            try:
                balance = api.balancesheet(
                    ts_code=ts_code,
                    fields="end_date,total_assets,total_hldr_eqy_exc_min_int,"
                           "total_liab,total_cur_assets,total_cur_liab,total_nca",
                    limit=1,
                )
                if not balance.empty:
                    row = balance.iloc[0]
                    data["total_assets"] = float(row.get("total_assets", 0) or 0)
                    data["current_assets"] = float(row.get("total_cur_assets", 0) or 0)
                    data["total_liabilities"] = float(row.get("total_liab", 0) or 0)

                    cur_liab = float(row.get("total_cur_liab", 0) or 0)
                    total_nca = float(row.get("total_nca", 0) or 0)

                    # BVPS
                    equity = float(row.get("total_hldr_eqy_exc_min_int", 0) or 0)
                    if data.get("shares_outstanding") and data["shares_outstanding"] > 0:
                        data["bvps"] = equity / data["shares_outstanding"]

                    # Computed properties for Stock
                    if data["total_assets"] > 0:
                        data["_roa"] = (data["net_income"] / data["total_assets"]) * 100
                        data["_debt_ratio"] = (data["total_liabilities"] / data["total_assets"]) * 100
                        if data["revenue"] > 0:
                            data["_asset_turnover"] = data["revenue"] / data["total_assets"]
                    if cur_liab > 0:
                        data["_current_ratio"] = data["current_assets"] / cur_liab

                    # Net debt
                    if data["total_liabilities"] > 0:
                        data["net_debt"] = data["total_liabilities"] - data["current_assets"]

                    if not cur_end_date:
                        cur_end_date = str(row.get("end_date", ""))
            except Exception:
                pass

            # === Cash flow: use Tushare's pre-computed free_cashflow ===
            try:
                cashflow = api.cashflow(
                    ts_code=ts_code,
                    fields="end_date,n_cashflow_act,free_cashflow,c_pay_acq_const_fiolta",
                    limit=2,
                )
                if not cashflow.empty:
                    # Prefer the report matching fina_indicator's end_date
                    cf_match = cashflow
                    if fina_end_date:
                        matched = cashflow[cashflow["end_date"] == fina_end_date]
                        if not matched.empty:
                            cf_match = matched
                    row = cf_match.iloc[0]
                    fcf_val = float(row.get("free_cashflow", 0) or 0)
                    if fcf_val != 0:
                        data["fcf"] = fcf_val
                    else:
                        # Compute manually
                        ocf = float(row.get("n_cashflow_act", 0) or 0)
                        capex = abs(float(row.get("c_pay_acq_const_fiolta", 0) or 0))
                        data["fcf"] = ocf - capex
            except Exception:
                pass

            # === Dividend ===
            try:
                div = api.dividend(ts_code=ts_code, fields="cash_div,div_yield", limit=1)
                if not div.empty:
                    row = div.iloc[0]
                    data["dividend_per_share"] = float(row.get("cash_div", 0) or 0)
                    data["dividend_yield"] = float(row.get("div_yield", 0) or 0)
            except Exception:
                pass

            # === 5-year CAGR for moat ===
            try:
                cur_year = int(cur_end_date[:4]) if len(cur_end_date) >= 4 else datetime.now().year
                inc_5y = api.income(ts_code=ts_code,
                    fields="end_date,revenue,n_income",
                    start_date=f"{cur_year - 5}0101", end_date=f"{cur_year}1231", limit=20)
                if inc_5y is not None and not inc_5y.empty:
                    inc_annual = self._annual_report_filter(inc_5y)
                    if not inc_annual.empty:
                        rev_vals = inc_annual.sort_values("end_date")["revenue"].values
                        ni_vals = inc_annual.sort_values("end_date")["n_income"].values
                        if len(rev_vals) >= 3:
                            data["revenue_cagr_5y"] = (float(rev_vals[-1]) / float(rev_vals[0])) ** (1 / (len(rev_vals) - 1)) - 1
                        if len(ni_vals) >= 3:
                            data["earnings_cagr_5y"] = (float(ni_vals[-1]) / float(ni_vals[0])) ** (1 / (len(ni_vals) - 1)) - 1
            except Exception:
                pass

            # === Prior year data for F-Score & M-Score ===
            if cur_end_date:
                prior = self._fetch_prior_year_data(api, ts_code, cur_end_date)
                data.update(prior)

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

        # fundamentals last so shares_outstanding from daily_basic wins over quote's 0
        combined = {**quote.data, **fundamentals.data}

        # Derive TTM EPS from PE_TTM (more reliable than single-quarter EPS)
        pe_ttm = combined.get("pe_ratio", 0)  # already set to pe_ttm in daily_basic section
        cur_price = combined.get("current_price", 0)
        if pe_ttm > 0 and cur_price > 0:
            ttm_eps = cur_price / pe_ttm
            single_q_eps = combined.get("eps", 0)
            if ttm_eps > 0 and single_q_eps > 0 and ttm_eps != single_q_eps:
                scale = ttm_eps / single_q_eps
                combined["eps"] = ttm_eps
                combined["revenue"] = combined["revenue"] * scale
                combined["net_income"] = combined["net_income"] * scale

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
