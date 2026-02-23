"""
Base class for buyback data fetchers.
"""
from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from ..base import BuybackFetchResult, Market


class BaseBuybackFetcher(ABC):
    """Abstract base class for buyback data fetchers."""

    @property
    @abstractmethod
    def market(self) -> Market:
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the data source name."""
        pass

    @abstractmethod
    def fetch_buyback(
        self,
        ticker: str,
        days: int = 365,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> BuybackFetchResult:
        """
        Fetch buyback data for a ticker.

        Args:
            ticker: Stock ticker symbol
            days: Number of days to look back (default 365)
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            BuybackFetchResult with records and summary
        """
        pass
