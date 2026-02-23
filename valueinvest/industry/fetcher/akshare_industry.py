"""
AKShare-based industry data fetcher for A-share stocks.
"""
from typing import ClassVar, List

import pandas as pd

from ..base import (
    IndustryFetchResult,
    IndustrySummary,
    IndustryMetrics,
    IndustryFundFlow,
    PeerCompany,
    IndustryTrend,
    FundFlowSentiment,
)
from ..registry import Market
from .base import BaseIndustryFetcher


class AKShareIndustryFetcher(BaseIndustryFetcher):
    """Industry data fetcher using AKShare for A-share stocks."""

    market: ClassVar[str] = Market.A_SHARE

    @property
    def source_name(self) -> str:
        return "akshare"

    def fetch_industry_data(
        self,
        ticker: str,
        include_peers_count: int = 20,
        include_fund_flow: bool = True,
    ) -> IndustryFetchResult:
        """Fetch complete industry analysis data."""
        errors = []

        try:
            industry_name = self.get_industry_name(ticker)
        except Exception as e:
            return IndustryFetchResult(
                success=False,
                ticker=ticker,
                market=self.market,
                source=self.source_name,
                errors=[f"Cannot get industry info: {e}"],
            )

        peers: List[PeerCompany] = []
        metrics: IndustryMetrics | None = None
        fund_flow: IndustryFundFlow | None = None
        ticker_rank = 0
        percentile = 0.0

        try:
            peers = self.get_peer_companies(industry_name, include_peers_count)
            for i, p in enumerate(peers):
                if p.ticker == ticker:
                    ticker_rank = i + 1
                    percentile = (1 - ticker_rank / len(peers)) * 100 if peers else 0
                    break
        except Exception as e:
            errors.append(f"Failed to get peer companies: {e}")

        try:
            metrics = self.get_industry_metrics(industry_name)
        except Exception as e:
            errors.append(f"Failed to get industry metrics: {e}")

        if include_fund_flow:
            try:
                fund_flow = self.get_industry_fund_flow(industry_name)
            except Exception as e:
                errors.append(f"Failed to get fund flow: {e}")

        trend = self._determine_trend(peers)
        leading = peers[0] if peers else None
        lagging = peers[-1] if peers else None

        summary = IndustrySummary(
            industry_name=industry_name,
            trend=IndustryTrend(trend),
            metrics=metrics,
            fund_flow=fund_flow,
            leading_stock=leading.ticker if leading else "",
            leading_stock_name=leading.name if leading else "",
            lagging_stock=lagging.ticker if lagging else "",
            lagging_stock_name=lagging.name if lagging else "",
        )

        return IndustryFetchResult(
            success=len(errors) == 0,
            ticker=ticker,
            market=self.market,
            source=self.source_name,
            industry_name=industry_name,
            summary=summary,
            peers=peers,
            ticker_rank_in_peers=ticker_rank,
            ticker_percentile=percentile,
            errors=errors,
        )

    def get_industry_name(self, ticker: str) -> str:
        """Get industry name from real-time quote data."""
        import akshare as ak

        df = ak.stock_zh_a_spot_em()
        row = df[df["代码"] == ticker]
        if row.empty:
            raise ValueError(f"Ticker {ticker} not found")

        industry = row["所属行业"].values[0]
        return str(industry) if pd.notna(industry) else ""

    def get_peer_companies(
        self,
        industry_name: str,
        limit: int = 20,
    ) -> List[PeerCompany]:
        """Get peer companies from industry board constituents."""
        import akshare as ak

        peers: List[PeerCompany] = []

        try:
            cons = ak.stock_board_industry_cons_em(symbol=industry_name)
        except Exception:
            all_stocks = ak.stock_zh_a_spot_em()
            cons = all_stocks[all_stocks["所属行业"] == industry_name]

        for _, row in cons.head(limit).iterrows():
            try:
                pe_val = row.get("市盈率-动态")
                pb_val = row.get("市净率")

                peer = PeerCompany(
                    ticker=str(row.get("代码", "")),
                    name=str(row.get("名称", "")),
                    current_price=self._safe_float(row.get("最新价")),
                    change_pct=self._safe_float(row.get("涨跌幅")),
                    market_cap=self._safe_float(row.get("总市值")),
                    pe_ratio=self._safe_float(pe_val) if pd.notna(pe_val) else 0,
                    pb_ratio=self._safe_float(pb_val) if pd.notna(pb_val) else 0,
                    source=self.source_name,
                )
                peers.append(peer)
            except Exception:
                continue

        peers.sort(key=lambda x: x.market_cap, reverse=True)
        for i, p in enumerate(peers):
            p.rank_in_industry = i + 1

        return peers

    def get_industry_fund_flow(
        self,
        industry_name: str,
        period: str = "今日",
    ) -> IndustryFundFlow | None:
        """Get industry fund flow data."""
        import akshare as ak

        try:
            df = ak.stock_sector_fund_flow_rank(indicator=period, sector_type="行业资金流")
            row = df[df["名称"] == industry_name]
            if row.empty:
                return None

            r = row.iloc[0]
            net_inflow = self._safe_float(r.get("主力净流入-净额", 0))

            if net_inflow > 0:
                sentiment = FundFlowSentiment.INFLOW
            elif net_inflow < 0:
                sentiment = FundFlowSentiment.OUTFLOW
            else:
                sentiment = FundFlowSentiment.BALANCED

            return IndustryFundFlow(
                net_inflow=net_inflow,
                main_inflow=self._safe_float(r.get("今日主力净流入-最大流入", 0)),
                main_outflow=abs(self._safe_float(r.get("今日主力净流入-最大流出", 0))),
                sentiment=sentiment,
                rank=int(r.name) + 1 if r.name is not None else 0,
                period=period,
            )
        except Exception:
            return None

    def _safe_float(self, value) -> float:
        """Safely convert value to float."""
        if value is None:
            return 0.0
        if pd.isna(value):
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
