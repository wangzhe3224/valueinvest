"""
Registry for market-specific buyback data fetchers.

Enables extensibility for new markets by registering custom fetchers.

Usage:
    from valueinvest.buyback.registry import BuybackRegistry
    from valueinvest.news.base import Market
    
    # Register a new market fetcher
    BuybackRegistry.register_fetcher(Market.HK, HKBuybackFetcher)
    
    # Get appropriate fetcher for ticker
    fetcher = BuybackRegistry.get_fetcher("00700")
"""
from typing import Dict, Type, Callable, List, Optional
from valueinvest.news.base import Market


class BuybackRegistry:
    _fetchers: Dict[Market, Type] = {}
    _market_detectors: List[Callable[[str], Optional[Market]]] = []
    _initialized: bool = False

    @classmethod
    def register_fetcher(cls, market: Market, fetcher_class: Type) -> None:
        cls._fetchers[market] = fetcher_class

    @classmethod
    def register_detector(cls, detector: Callable[[str], Optional[Market]]) -> None:
        cls._market_detectors.append(detector)

    @classmethod
    def detect_market(cls, ticker: str) -> Market:
        cls._ensure_initialized()

        ticker = ticker.strip().upper()

        for detector in cls._market_detectors:
            result = detector(ticker)
            if result is not None:
                return result

        raise ValueError(f"Cannot detect market for ticker: {ticker}")

    @classmethod
    def get_fetcher(cls, ticker: str, **kwargs):
        cls._ensure_initialized()

        market = cls.detect_market(ticker)
        fetcher_class = cls._fetchers.get(market)

        if fetcher_class is None:
            raise ValueError(f"No buyback fetcher registered for market: {market}")

        return fetcher_class(**kwargs)

    @classmethod
    def get_supported_markets(cls) -> List[Market]:
        cls._ensure_initialized()
        return list(cls._fetchers.keys())

    @classmethod
    def is_market_supported(cls, market: Market) -> bool:
        cls._ensure_initialized()
        return market in cls._fetchers

    @classmethod
    def _ensure_initialized(cls) -> None:
        if cls._initialized:
            return

        cls._setup_defaults()
        cls._initialized = True

    @classmethod
    def _setup_defaults(cls) -> None:
        try:
            from .fetcher.akshare_buyback import AKShareBuybackFetcher

            cls.register_fetcher(Market.A_SHARE, AKShareBuybackFetcher)
        except ImportError:
            pass

        try:
            from .fetcher.yfinance_buyback import YFinanceBuybackFetcher

            cls.register_fetcher(Market.US, YFinanceBuybackFetcher)
        except ImportError:
            pass

        def detect_ashare(ticker: str) -> Optional[Market]:
            if ticker.isdigit() and len(ticker) == 6:
                first = ticker[0]
                if first in ("0", "3", "6"):
                    return Market.A_SHARE
            return None

        def detect_us(ticker: str) -> Optional[Market]:
            if ticker.isalpha() and 1 <= len(ticker) <= 5:
                return Market.US
            return None

        def detect_hk(ticker: str) -> Optional[Market]:
            if ticker.isdigit() and len(ticker) == 5:
                return Market.HK
            return None

        cls.register_detector(detect_ashare)
        cls.register_detector(detect_us)
        cls.register_detector(detect_hk)

    @classmethod
    def reset(cls) -> None:
        cls._fetchers = {}
        cls._market_detectors = []
        cls._initialized = False
