import re
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List

import pandas as pd

from .base import BaseFetcher, FetchResult, HistoryResult


class AKShareFetcher(BaseFetcher):

    def __init__(self, ticker: str) -> None:
        self._ticker = self._normalize_ticker(ticker)

    @property
    def source_name(self) -> str:
        return "akshare"

    def _normalize_ticker(self, ticker: str) -> str:
        return re.sub(r"\.(SH|SZ|BJ)$", "", ticker)

    def _detect_exchange(self) -> str:
        if self._ticker.startswith("6"):
            return "SH"
        elif self._ticker.startswith(("0", "3")):
            return "SZ"
        elif self._ticker.startswith(("4", "8")):
            return "BJ"
        return "SH"

    def _get_akshare(self) -> Any:
        try:
            import akshare as ak
            return ak
        except ImportError as e:
            raise ImportError(
                "akshare is required for A-share data. "
                "Install with: pip install valueinvest[ashare] or pip install akshare"
            ) from e

    def _parse_value(self, value: Any) -> float:
        if value is None:
            return 0.0
        try:
            s = str(value).strip()
            if not s or s == "--" or s == "-":
                return 0.0
            return float(s.replace(",", ""))
        except (ValueError, AttributeError):
            return 0.0

    def fetch_quote(self, ticker: str) -> FetchResult:
        try:
            ak = self._get_akshare()

            info = ak.stock_individual_info_em(symbol=self._ticker)
            info_dict = dict(zip(info['item'], info['value']))

            current_price = self._parse_value(info_dict.get('最新', 0))
            shares_str = info_dict.get('总股本', '0')
            shares = self._parse_value(shares_str) if shares_str else 0.0
            market_cap = self._parse_value(info_dict.get('总市值', 0))

            data = {
                "ticker": self._ticker,
                "name": str(info_dict.get('股票简称', '')),
                "current_price": current_price,
                "market_cap": market_cap,
                "shares_outstanding": shares,
                "currency": "CNY",
                "exchange": self._detect_exchange(),
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
            ak = self._get_akshare()

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
                "ebit": 0,
                "operating_margin": 0,
                "tax_rate": 0,
                "depreciation": 0,
                "capex": 0,
                "net_working_capital": 0,
                "net_fixed_assets": 0,
                "dividend_per_share": 0,
                "dividend_yield": 0,
                "dividend_growth_rate": 0,
                "growth_rate": 0,
                "pe_ratio": 0,
                "pb_ratio": 0,
                "shareholder_equity": 0,
            }

            try:
                balance = ak.stock_financial_report_sina(stock=self._ticker, symbol="资产负债表")
                if balance is not None and not balance.empty:
                    latest = balance.iloc[0]
                    for col in balance.columns:
                        col_str = str(col)
                        if '资产总计' in col_str or '资产合计' in col_str:
                            data["total_assets"] = self._parse_value(latest.get(col, 0))
                        elif '流动资产合计' in col_str or ('流动资产' in col_str and '合计' in col_str):
                            data["current_assets"] = self._parse_value(latest.get(col, 0))
                        elif '流动负债合计' in col_str or ('流动负债' in col_str and '合计' in col_str):
                            current_liabilities = self._parse_value(latest.get(col, 0))
                            data["net_working_capital"] = data.get("current_assets", 0) - current_liabilities
                        elif '负债合计' in col_str or '负债总计' in col_str:
                            data["total_liabilities"] = self._parse_value(latest.get(col, 0))
                        elif '归属于母公司股东' in col_str and '权益' in col_str:
                            data["shareholder_equity"] = self._parse_value(latest.get(col, 0))
                        elif '固定资产' in col_str and '净' in col_str:
                            data["net_fixed_assets"] = self._parse_value(latest.get(col, 0))
                        elif '固定资产' in col_str and '合计' in col_str:
                            if data["net_fixed_assets"] == 0:
                                data["net_fixed_assets"] = self._parse_value(latest.get(col, 0))
            except Exception:
                pass

            try:
                income = ak.stock_financial_report_sina(stock=self._ticker, symbol="利润表")
                if income is not None and not income.empty:
                    latest = income.iloc[0]
                    for col in income.columns:
                        col_str = str(col)
                        if '营业收入' in col_str and '净' not in col_str:
                            data["revenue"] = self._parse_value(latest.get(col, 0))
                        elif col_str == '净利润' or ('净利润' in col_str and '归属' in col_str):
                            data["net_income"] = self._parse_value(latest.get(col, 0))
                        elif '基本每股收益' in col_str:
                            data["eps"] = self._parse_value(latest.get(col, 0))
                        elif '营业利润' in col_str:
                            data["ebit"] = self._parse_value(latest.get(col, 0))
                        elif '利润总额' in col_str or '所得税' in col_str:
                            profit_before_tax = self._parse_value(latest.get(col, 0)) if '利润总额' in col_str else 0
                            income_tax = 0
                            if '所得税费用' in col_str:
                                income_tax = self._parse_value(latest.get(col, 0))
                            if profit_before_tax > 0 and income_tax >= 0:
                                data["tax_rate"] = (income_tax / profit_before_tax) * 100
            except Exception:
                pass

            try:
                cashflow = ak.stock_financial_report_sina(stock=self._ticker, symbol="现金流量表")
                if cashflow is not None and not cashflow.empty:
                    latest = cashflow.iloc[0]
                    operating_cf = 0
                    capex_val = 0
                    
                    for col in cashflow.columns:
                        col_str = str(col)
                        if '经营活动产生的现金流量净额' in col_str:
                            operating_cf = self._parse_value(latest.get(col, 0))
                        elif '购建固定资产' in col_str or '资本支出' in col_str:
                            capex_val = abs(self._parse_value(latest.get(col, 0)))
                            data["capex"] = capex_val
                        elif '固定资产折旧' in col_str or '折旧' in col_str:
                            data["depreciation"] = abs(self._parse_value(latest.get(col, 0)))
                    
                    if operating_cf > 0 and capex_val > 0:
                        data["fcf"] = operating_cf - capex_val
                    elif operating_cf > 0:
                        data["fcf"] = operating_cf
            except Exception:
                pass

            if data["revenue"] > 0 and data["ebit"] > 0:
                data["operating_margin"] = (data["ebit"] / data["revenue"]) * 100

            try:
                df_dividend = ak.stock_dividend_cn(symbol=self._ticker)
                if df_dividend is not None and not df_dividend.empty:
                    recent_dividends = df_dividend.head(5)
                    if len(recent_dividends) > 0:
                        latest_div = self._parse_value(recent_dividends.iloc[0].get('分红金额', 0) if '分红金额' in recent_dividends.columns else 0)
                        data["dividend_per_share"] = latest_div / 10 if latest_div > 0 else 0
                        
                        if len(recent_dividends) >= 3:
                            dividends = []
                            for _, row in recent_dividends.iterrows():
                                div_val = self._parse_value(row.get('分红金额', 0))
                                if div_val > 0:
                                    dividends.append(div_val)
                            
                            if len(dividends) >= 2:
                                older_div = dividends[-1]
                                newer_div = dividends[0]
                                if older_div > 0:
                                    years = len(dividends) - 1
                                    growth = ((newer_div / older_div) ** (1/years) - 1) * 100
                                    data["dividend_growth_rate"] = growth
            except Exception:
                pass

            try:
                df_historic = ak.stock_financial_analysis_indicator(symbol=self._ticker)
                if df_historic is not None and not df_historic.empty:
                    roe_values = []
                    for _, row in df_historic.head(5).iterrows():
                        roe_val = self._parse_value(row.get('净资产收益率', 0))
                        if roe_val > 0:
                            roe_values.append(roe_val)
                    if roe_values:
                        data["roe"] = sum(roe_values) / len(roe_values)
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
        
        shares = combined.get("shares_outstanding", 0)
        if shares > 0 and combined.get("shareholder_equity", 0) > 0:
            combined["bvps"] = combined["shareholder_equity"] / shares
        
        if combined.get("eps", 0) > 0 and combined.get("current_price", 0) > 0:
            combined["pe_ratio"] = combined["current_price"] / combined["eps"]
        if combined.get("bvps", 0) > 0 and combined.get("current_price", 0) > 0:
            combined["pb_ratio"] = combined["current_price"] / combined["bvps"]
        
        if combined.get("current_price", 0) > 0 and combined.get("dividend_per_share", 0) > 0:
            combined["dividend_yield"] = (combined["dividend_per_share"] / combined["current_price"]) * 100
        
        if combined.get("market_cap", 0) > 0:
            combined["net_debt"] = combined.get("total_liabilities", 0) - combined.get("current_assets", 0) * 0.5
            combined["enterprise_value"] = combined["market_cap"] + combined["net_debt"]
        
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
            ak = self._get_akshare()

            if end_date is None:
                end_dt = datetime.now()
            else:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")

            if start_date is None:
                years = int(period.replace("y", "").replace("Y", ""))
                start_dt = end_dt - timedelta(days=years * 365)
            else:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")

            df = ak.stock_zh_a_hist(
                symbol=self._ticker,
                period="daily",
                start_date=start_dt.strftime("%Y%m%d"),
                end_date=end_dt.strftime("%Y%m%d"),
                adjust=adjust,
            )

            if df is None or df.empty:
                return HistoryResult(
                    success=False,
                    ticker=self._ticker,
                    source=self.source_name,
                    errors=[f"No historical data for {self._ticker}"],
                )

            df = df.rename(columns={"日期": "date", "收盘": "close", "开盘": "open", "最高": "high", "最低": "low", "成交量": "volume"})
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
            df = df.sort_index()

            return HistoryResult(
                success=True,
                ticker=self._ticker,
                source=self.source_name,
                df=df[["open", "high", "low", "close", "volume"]],
                start_date=start_dt.date(),
                end_date=end_dt.date(),
            )

        except Exception as e:
            return HistoryResult(
                success=False,
                ticker=self._ticker,
                source=self.source_name,
                errors=[str(e)],
            )
