"""
Base class for cash flow data fetchers.
"""
from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from ..base import CashFlowFetchResult, Market


class BaseCashFlowFetcher(ABC):
    """Abstract base class for cash flow data fetchers."""

    @property
    @abstractmethod
    def market(self) -> Market:
        """Market this fetcher handles."""
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Name of the data source."""
        pass

    @abstractmethod
    def fetch_cashflow(
        self,
        ticker: str,
        years: int = 5,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> CashFlowFetchResult:
        """
        Fetch cash flow data for a ticker.

        Args:
            ticker: Stock ticker symbol
            years: Number of years of historical data
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            CashFlowFetchResult with records and summary
        """
        pass
