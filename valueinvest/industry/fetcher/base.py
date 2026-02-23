"""
Base class for industry data fetchers.
"""
from abc import ABC, abstractmethod
from typing import ClassVar, List

from ..base import (
    IndustryFetchResult,
    PeerCompany,
    IndustryMetrics,
    IndustryFundFlow,
)
from ..registry import Market


class BaseIndustryFetcher(ABC):
    """Abstract base class for industry data fetchers."""

    market: ClassVar[str]

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the data source name."""
        pass

    @abstractmethod
    def fetch_industry_data(
        self,
        ticker: str,
        include_peers_count: int = 20,
        include_fund_flow: bool = True,
    ) -> IndustryFetchResult:
        """
        Fetch complete industry analysis data for a stock.

        Args:
            ticker: Stock ticker symbol
            include_peers_count: Maximum number of peer companies to include
            include_fund_flow: Whether to include fund flow data

        Returns:
            IndustryFetchResult with industry data
        """
        pass

    @abstractmethod
    def get_industry_name(self, ticker: str) -> str:
        """
        Get the industry name for a stock.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Industry name string

        Raises:
            ValueError: If ticker not found
        """
        pass

    @abstractmethod
    def get_peer_companies(
        self,
        industry_name: str,
        limit: int = 20,
    ) -> List[PeerCompany]:
        """
        Get peer companies in the same industry.

        Args:
            industry_name: Industry/sector name
            limit: Maximum number of peers to return

        Returns:
            List of PeerCompany objects
        """
        pass

    def get_industry_metrics(
        self,
        industry_name: str,
    ) -> IndustryMetrics | None:
        """
        Calculate industry average metrics from peers.

        Args:
            industry_name: Industry/sector name

        Returns:
            IndustryMetrics or None if no data available
        """
        peers = self.get_peer_companies(industry_name, limit=50)
        if not peers:
            return None

        valid_pes = [p.pe_ratio for p in peers if p.pe_ratio > 0]
        valid_pbs = [p.pb_ratio for p in peers if p.pb_ratio > 0]
        valid_roes = [p.roe for p in peers if p.roe != 0]
        profitable = [p for p in peers if p.is_profitable]

        def median(values: List[float]) -> float:
            if not values:
                return 0.0
            sorted_vals = sorted(values)
            n = len(sorted_vals)
            mid = n // 2
            if n % 2 == 0:
                return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2
            return sorted_vals[mid]

        return IndustryMetrics(
            avg_pe=sum(valid_pes) / len(valid_pes) if valid_pes else 0,
            avg_pb=sum(valid_pbs) / len(valid_pbs) if valid_pbs else 0,
            avg_roe=sum(valid_roes) / len(valid_roes) if valid_roes else 0,
            median_pe=median(valid_pes),
            median_pb=median(valid_pbs),
            total_market_cap=sum(p.market_cap for p in peers),
            company_count=len(peers),
            avg_change_pct=sum(p.change_pct for p in peers) / len(peers),
            avg_revenue=sum(p.revenue for p in peers) / len(peers) if peers else 0,
            avg_net_income=sum(p.net_income for p in peers) / len(peers) if peers else 0,
            profitable_count=len(profitable),
            profitable_ratio=len(profitable) / len(peers) if peers else 0,
        )

    def get_industry_fund_flow(
        self,
        industry_name: str,
        period: str = "今日",
    ) -> IndustryFundFlow | None:
        """
        Get fund flow data for an industry.

        Args:
            industry_name: Industry/sector name
            period: Time period (今日, 5日, 10日)

        Returns:
            IndustryFundFlow or None if not available
        """
        return None

    def _determine_trend(self, peers: List[PeerCompany]) -> str:
        """Determine industry trend based on peer performance."""
        if not peers:
            return "neutral"

        avg_change = sum(p.change_pct for p in peers) / len(peers)

        if avg_change > 3:
            return "strong_up"
        elif avg_change > 1:
            return "up"
        elif avg_change < -3:
            return "strong_down"
        elif avg_change < -1:
            return "down"
        else:
            return "neutral"
