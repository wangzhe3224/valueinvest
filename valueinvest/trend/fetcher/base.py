"""Base class for quarterly trend data fetchers."""
from abc import ABC, abstractmethod

from ..base import TrendFetchResult, Market


class BaseTrendFetcher(ABC):
    """Abstract base class for quarterly trend data fetchers.

    A trend fetcher returns a :class:`TrendSeries` of single-quarter
    :class:`TrendRecord` objects covering revenue, margins, FCF and CCC inputs.
    """

    @property
    @abstractmethod
    def market(self) -> Market:
        """Market this fetcher handles."""
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Name of the data source."""
        ...

    @abstractmethod
    def fetch_trends(self, ticker: str, years: int = 5) -> TrendFetchResult:
        """Fetch quarterly trend data for a ticker.

        Args:
            ticker: Stock ticker symbol.
            years: Number of years of historical quarterly data to return.

        Returns:
            TrendFetchResult with a TrendSeries of single-quarter records.
        """
        ...
