"""
Registry for market-specific news fetchers and sentiment analyzers.

Enables extensibility for new markets by registering custom fetchers.

Usage:
    from valueinvest.news.registry import NewsRegistry, Market
    
    # Register a new market fetcher
    NewsRegistry.register_fetcher(Market.HK, HKNewsFetcher)
    
    # Get appropriate fetcher for ticker
    fetcher = NewsRegistry.get_fetcher("00700")
"""
from typing import Dict, Type, Callable, List, Optional
from .base import Market


class NewsRegistry:
    """
    Registry for market-specific news fetchers.
    
    Supports automatic market detection and fetcher retrieval.
    """
    
    _fetchers: Dict[Market, Type] = {}
    _market_detectors: List[Callable[[str], Optional[Market]]] = []
    _initialized: bool = False
    
    @classmethod
    def register_fetcher(cls, market: Market, fetcher_class: Type) -> None:
        """Register a fetcher class for a specific market."""
        cls._fetchers[market] = fetcher_class
    
    @classmethod
    def register_detector(cls, detector: Callable[[str], Optional[Market]]) -> None:
        """Register a function that detects market from ticker string."""
        cls._market_detectors.append(detector)
    
    @classmethod
    def detect_market(cls, ticker: str) -> Market:
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
            Instance of appropriate BaseNewsFetcher subclass
        """
        cls._ensure_initialized()
        
        market = cls.detect_market(ticker)
        fetcher_class = cls._fetchers.get(market)
        
        if fetcher_class is None:
            raise ValueError(f"No fetcher registered for market: {market}")
        
        return fetcher_class(**kwargs)
    
    @classmethod
    def get_supported_markets(cls) -> List[Market]:
        """Return list of markets with registered fetchers."""
        cls._ensure_initialized()
        return list(cls._fetchers.keys())
    
    @classmethod
    def is_market_supported(cls, market: Market) -> bool:
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
        # Import here to avoid circular imports
        try:
            from .fetcher.akshare_news import AKShareNewsFetcher
            cls.register_fetcher(Market.A_SHARE, AKShareNewsFetcher)
        except ImportError:
            pass
        
        try:
            from .fetcher.yfinance_news import YFinanceNewsFetcher
            cls.register_fetcher(Market.US, YFinanceNewsFetcher)
        except ImportError:
            pass
        
        # Default market detectors (order matters - first match wins)
        
        # A-share: 6 digits starting with 0, 3, 6
        def detect_ashare(ticker: str) -> Optional[Market]:
            if ticker.isdigit() and len(ticker) == 6:
                first = ticker[0]
                if first in ('0', '3', '6'):
                    return Market.A_SHARE
            return None
        
        # US: 1-5 uppercase letters
        def detect_us(ticker: str) -> Optional[Market]:
            if ticker.isalpha() and 1 <= len(ticker) <= 5:
                return Market.US
            return None
        
        # HK: 5 digits (reserved for future)
        def detect_hk(ticker: str) -> Optional[Market]:
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
