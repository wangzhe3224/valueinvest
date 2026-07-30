"""Quarterly trend data fetcher for A-shares using tushare.

Unlike the existing ``TushareFetcher`` (which decomposes cumulative -> single
quarter only to fold the last 4 into a TTM scalar, discarding the series),
this fetcher **exposes the single-quarter series** for trend analysis.

Reuses the proven cumulative -> single-quarter decomposition (end_type:
1=Q1 standalone, 2/3/4 = cumulative -> differenced), adds ``oper_cost`` for
COGS, and reads inventory / receivables / payables as quarter-end snapshots.
"""
import os
import re
from datetime import date
from typing import Any, Dict, List, Optional

from .base import BaseTrendFetcher
from ..base import TrendFetchResult, TrendRecord, TrendSeries, Market


class TushareTrendFetcher(BaseTrendFetcher):
    """Fetch quarterly trend data for A-shares via tushare."""

    def __init__(self, token: Optional[str] = None) -> None:
        self._token = token or os.environ.get("TUSHARE_TOKEN")
        self._api: Any = None

    @property
    def market(self) -> Market:
        return Market.A_SHARE

    @property
    def source_name(self) -> str:
        return "tushare"

    # ------------------------------------------------------------------ #
    # tushare access (mirrors data/fetcher/tushare.py)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalize_ticker(ticker: str) -> str:
        if not ticker:
            return ""
        if re.match(r"^\d{6}\.(SH|SZ|BJ)$", ticker):
            return ticker
        code = re.sub(r"\.(SH|SZ|BJ)$", "", ticker)
        if code.startswith("6"):
            return f"{code}.SH"
        elif code.startswith(("0", "3")):
            return f"{code}.SZ"
        elif code.startswith(("4", "8")):
            return f"{code}.BJ"
        return f"{code}.SH"

    def _get_api(self) -> Any:
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
                "tushare is required for A-share trend data. "
                "Install with: pip install valueinvest[tushare]"
            ) from e

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _end_date_to_date(ed: str) -> date:
        return date(int(ed[:4]), int(ed[4:6]), int(ed[6:8]))

    @staticmethod
    def _fiscal_quarter(qend: date) -> int:
        return (qend.month - 1) // 3 + 1

    def _decompose(self, df: Any, value_cols: List[str]) -> Dict[str, Dict[str, float]]:
        """Cumulative -> single-quarter decomposition keyed by end_date.

        Mirrors tushare.py:296-325. end_type 1 = Q1 standalone; 2/3/4 =
        cumulative, differenced against the prior period. ``revenue`` gates
        validity (single-quarter revenue >= 0).
        """
        out: Dict[str, Dict[str, float]] = {}
        if df is None or getattr(df, "empty", True):
            return out
        df = df.drop_duplicates(subset=["end_date"]).sort_values("end_date")
        prev: Optional[Any] = None
        for _, row in df.iterrows():
            etype = str(row.get("end_type", ""))
            ed = str(row.get("end_date", ""))
            if etype == "1":
                rec = {c: float(row.get(c, 0) or 0) for c in value_cols}
                if rec.get("revenue", 0) >= 0:
                    out[ed] = rec
            elif prev is not None and etype in ("2", "3", "4"):
                rec: Dict[str, float] = {}
                for c in value_cols:
                    rec[c] = float(row.get(c, 0) or 0) - float(prev.get(c, 0) or 0)
                if rec.get("revenue", float("inf")) >= 0 or "revenue" not in value_cols:
                    out[ed] = rec
            prev = row
        return out

    def _balance_snapshots(self, df: Any) -> Dict[str, Dict[str, float]]:
        """Quarter-end stock snapshots keyed by end_date."""
        out: Dict[str, Dict[str, float]] = {}
        if df is None or getattr(df, "empty", True):
            return out
        for _, row in df.drop_duplicates(subset=["end_date"]).iterrows():
            ed = str(row.get("end_date", ""))
            out[ed] = {
                "inventories": float(row.get("inventories", 0) or 0),
                "accounts_rec": float(row.get("accounts_rec", 0) or 0),
                "accounts_pay": float(row.get("accounts_pay", 0) or 0),
            }
        return out

    def _latest_shares(self, df: Any) -> float:
        """Latest total_share (tushare unit: 万股) -> share count."""
        if df is None or getattr(df, "empty", True):
            return 0.0
        try:
            latest = df.sort_values("end_date", ascending=False).iloc[0]
            return float(latest.get("total_share", 0) or 0) * 10000  # 万股 -> 股
        except Exception:
            return 0.0

    def _quarterly_close(
        self, api: Any, ts_code: str, end_dates: List[str]
    ) -> Dict[str, float]:
        """Close on/nearest-before each quarter-end via tushare daily."""
        result = {ed: 0.0 for ed in end_dates}
        if not end_dates:
            return result
        cur_year = int(end_dates[-1][:4])
        try:
            daily = api.daily(
                ts_code=ts_code,
                start_date=f"{cur_year - 5}0101",
                end_date=f"{cur_year}1231",
            )
        except Exception:
            return result
        if daily is None or getattr(daily, "empty", True):
            return result
        pairs: List[tuple] = []
        for _, row in daily.iterrows():
            td = str(row.get("trade_date", ""))
            try:
                pairs.append(
                    (self._end_date_to_date(td), float(row.get("close", 0) or 0))
                )
            except (ValueError, TypeError):
                continue
        pairs.sort(key=lambda p: p[0])
        if not pairs:
            return result
        for ed in end_dates:
            qd = self._end_date_to_date(ed)
            chosen = 0.0
            for d, v in pairs:
                if d <= qd:
                    chosen = v
                else:
                    break
            result[ed] = chosen
        return result

    # ------------------------------------------------------------------ #
    # main
    # ------------------------------------------------------------------ #
    def fetch_trends(self, ticker: str, years: int = 5) -> TrendFetchResult:
        try:
            api = self._get_api()
            ts_code = self._normalize_ticker(ticker)
            limit = years * 4 + 8

            income = api.income(
                ts_code=ts_code,
                fields="end_date,end_type,revenue,oper_cost,n_income",
                limit=limit,
            )
            cashflow = api.cashflow(
                ts_code=ts_code,
                fields="end_date,end_type,n_cashflow_act,c_pay_acq_const_fiolta",
                limit=limit,
            )
            balancesheet = api.balancesheet(
                ts_code=ts_code,
                fields="end_date,inventories,accounts_rec,accounts_pay,total_share",
                limit=limit,
            )

            if income is None or getattr(income, "empty", True):
                return TrendFetchResult(
                    success=False,
                    ticker=ticker,
                    market=self.market,
                    source=self.source_name,
                    errors=[f"No income data for {ts_code}"],
                )

            inc_map = self._decompose(income, ["revenue", "oper_cost", "n_income"])
            cf_map = self._decompose(
                cashflow, ["n_cashflow_act", "c_pay_acq_const_fiolta"]
            )
            bs_map = self._balance_snapshots(balancesheet)
            shares = self._latest_shares(balancesheet)

            # chronological end_dates present in BOTH income and cashflow
            end_dates = sorted(set(inc_map.keys()) & set(cf_map.keys()))[
                -(years * 4 + 4):
            ]

            close_map = self._quarterly_close(api, ts_code, end_dates)
            warnings: List[str] = [
                "historical fcf_yield approximated by price x current shares "
                "(ignores dilution)"
            ]

            records: List[TrendRecord] = []
            for ed in end_dates:
                ir = inc_map[ed]
                cr = cf_map[ed]
                bsr = bs_map.get(ed, {})
                revenue = ir["revenue"]
                oper_cost = ir.get("oper_cost", 0.0)
                gross_profit = revenue - oper_cost
                n_income = ir.get("n_income", 0.0)
                ocf = cr.get("n_cashflow_act", 0.0)
                capex = -abs(cr.get("c_pay_acq_const_fiolta", 0.0))  # negative convention
                fcf = ocf + capex
                qd = self._end_date_to_date(ed)

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
                        net_income=n_income,
                        operating_cash_flow=ocf,
                        capex=capex,
                        free_cash_flow=fcf,
                        inventory=bsr.get("inventories", 0.0),
                        accounts_receivable=bsr.get("accounts_rec", 0.0),
                        accounts_payable=bsr.get("accounts_pay", 0.0),
                        shares_outstanding=shares,
                        close_price=close_map.get(ed, 0.0),
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
