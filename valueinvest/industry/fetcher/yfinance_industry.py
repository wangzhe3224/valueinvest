"""
yfinance-based industry data fetcher for US stocks.

Note: yfinance has limited industry data. It can provide sector/industry names
but does not have peer company lists or fund flow data.
"""
from typing import ClassVar, List

from ..base import (
    IndustryFetchResult,
    IndustrySummary,
    IndustryMetrics,
    PeerCompany,
    IndustryTrend,
)
from ..registry import Market
from .base import BaseIndustryFetcher


class YFinanceIndustryFetcher(BaseIndustryFetcher):
    """Industry data fetcher using yfinance for US stocks."""

    market: ClassVar[str] = Market.US

    @property
    def source_name(self) -> str:
        return "yfinance"

    def fetch_industry_data(
        self,
        ticker: str,
        include_peers_count: int = 20,
        include_fund_flow: bool = True,
    ) -> IndustryFetchResult:
        """Fetch industry data for US stock."""
        errors = []

        try:
            industry_name = self.get_industry_name(ticker)
            sector = self._get_sector(ticker)
        except Exception as e:
            return IndustryFetchResult(
                success=False,
                ticker=ticker,
                market=self.market,
                source=self.source_name,
                errors=[f"Cannot get industry info: {e}"],
            )

        peers: List[PeerCompany] = []
        ticker_rank = 0

        summary = IndustrySummary(
            industry_name=industry_name,
            trend=IndustryTrend.NEUTRAL,
        )

        if not peers:
            errors.append("yfinance does not provide peer company data")

        return IndustryFetchResult(
            success=len(errors) <= 1,
            ticker=ticker,
            market=self.market,
            source=self.source_name,
            industry_name=industry_name,
            sector=sector,
            summary=summary,
            peers=peers,
            ticker_rank_in_peers=ticker_rank,
            errors=errors,
        )

    def get_industry_name(self, ticker: str) -> str:
        """Get industry name from yfinance."""
        import yfinance as yf

        stock = yf.Ticker(ticker)
        info = stock.info
        return info.get("industry", "")

    def _get_sector(self, ticker: str) -> str:
        """Get sector name from yfinance."""
        import yfinance as yf

        stock = yf.Ticker(ticker)
        info = stock.info
        return info.get("sector", "")

    def get_peer_companies(
        self,
        industry_name: str,
        limit: int = 20,
    ) -> List[PeerCompany]:
        """yfinance does not provide peer company lists."""
        return []
