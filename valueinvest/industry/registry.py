"""
Registry for market-specific industry fetchers.

Enables extensibility for new markets by registering custom fetchers.

Usage:
    from valueinvest.industry.registry import IndustryRegistry
    from valueinvest.news.base import Market
    
    # Register a new market fetcher
    IndustryRegistry.register_fetcher(Market.HK, HKIndustryFetcher)
    
    # Get appropriate fetcher for ticker
    fetcher = IndustryRegistry.get_fetcher("00700")
"""
from typing import Dict, Type, Callable, List, Optional


class Market:
    """Supported markets for industry data."""

    A_SHARE = "cn"
    US = "us"
    HK = "hk"


class IndustryRegistry:
    """
    Registry for market-specific industry fetchers.

    Supports automatic market detection and fetcher retrieval.
    """

    _fetchers: Dict[str, Type] = {}
    _market_detectors: List[Callable[[str], Optional[str]]] = []
    _initialized: bool = False

    @classmethod
    def register_fetcher(cls, market: str, fetcher_class: Type) -> None:
        """Register a fetcher class for a specific market."""
        cls._fetchers[market] = fetcher_class

    @classmethod
    def register_detector(cls, detector: Callable[[str], Optional[str]]) -> None:
        """Register a function that detects market from ticker string."""
        cls._market_detectors.append(detector)

    @classmethod
    def detect_market(cls, ticker: str) -> str:
        """Detect which market a ticker belongs to."""
        cls._ensure_initialized()

        ticker = ticker.strip().upper()

        for detector in cls._market_detectors:
            result = detector(ticker)
            if result is not None:
                return result

        raise ValueError(f"Cannot detect market for ticker: {ticker}")

    @classmethod
    def get_fetcher(cls, ticker: str, **kwargs):
        """
        Get appropriate fetcher instance for the given ticker.

        Args:
            ticker: Stock ticker symbol
            **kwargs: Additional arguments passed to fetcher constructor

        Returns:
            Instance of appropriate BaseIndustryFetcher subclass
        """
        cls._ensure_initialized()

        market = cls.detect_market(ticker)
        fetcher_class = cls._fetchers.get(market)

        if fetcher_class is None:
            raise ValueError(f"No industry fetcher registered for market: {market}")

        return fetcher_class(**kwargs)

    @classmethod
    def get_supported_markets(cls) -> List[str]:
        """Return list of markets with registered fetchers."""
        cls._ensure_initialized()
        return list(cls._fetchers.keys())

    @classmethod
    def is_market_supported(cls, market: str) -> bool:
        """Check if a market has a registered fetcher."""
        cls._ensure_initialized()
        return market in cls._fetchers

    @classmethod
    def _ensure_initialized(cls) -> None:
        """Initialize default fetchers if not already done."""
        if cls._initialized:
            return

        cls._setup_defaults()
        cls._initialized = True

    @classmethod
    def _setup_defaults(cls) -> None:
        """Setup default fetchers and detectors."""
        try:
            from .fetcher.akshare_industry import AKShareIndustryFetcher

            cls.register_fetcher(Market.A_SHARE, AKShareIndustryFetcher)
        except ImportError:
            pass

        try:
            from .fetcher.yfinance_industry import YFinanceIndustryFetcher

            cls.register_fetcher(Market.US, YFinanceIndustryFetcher)
        except ImportError:
            pass

        # A-share: 6 digits starting with 0, 3, 6
        def detect_ashare(ticker: str) -> Optional[str]:
            if ticker.isdigit() and len(ticker) == 6:
                first = ticker[0]
                if first in ("0", "3", "6"):
                    return Market.A_SHARE
            return None

        # US: 1-5 uppercase letters
        def detect_us(ticker: str) -> Optional[str]:
            if ticker.isalpha() and 1 <= len(ticker) <= 5:
                return Market.US
            return None

        # HK: 5 digits (reserved for future)
        def detect_hk(ticker: str) -> Optional[str]:
            if ticker.isdigit() and len(ticker) == 5:
                return Market.HK
            return None

        cls.register_detector(detect_ashare)
        cls.register_detector(detect_us)
        cls.register_detector(detect_hk)

    @classmethod
    def reset(cls) -> None:
        """Reset registry to uninitialized state (for testing)."""
        cls._fetchers = {}
        cls._market_detectors = []
        cls._initialized = False
