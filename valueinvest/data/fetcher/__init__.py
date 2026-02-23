"""
Data fetcher module with auto-source selection.

Supported sources:
- yfinance: US/International stocks (AAPL, GOOGL, etc.)
- akshare: Chinese A-shares (600000, 000001, etc.) - FREE, no auth
- tushare: Chinese A-shares - requires token
"""
import os
import re
from typing import Optional, TYPE_CHECKING

from .base import BaseFetcher, FetchResult, HistoryResult

if TYPE_CHECKING:
    from .akshare import AKShareFetcher
    from .tushare import TushareFetcher
    from .yfinance import YFinanceFetcher


# Ticker patterns
ASHARE_PATTERN = re.compile(r"^\d{6}$")  # 6 digits only
ASHARE_WITH_SUFFIX = re.compile(r"^(\d{6})\.(SH|SZ|BJ)$")


def detect_source(ticker: str, prefer_tushare: bool = False) -> str:
    """Detect appropriate data source based on ticker format.

    Args:
        ticker: Stock ticker symbol
        prefer_tushare: Prefer Tushare over AKShare for A-shares

    Returns:
        Source name: 'yfinance', 'akshare', or 'tushare'
    """
    # A-share with suffix -> could be Tushare or AKShare
    match = ASHARE_WITH_SUFFIX.match(ticker)
    if match:
        if prefer_tushare and os.environ.get("TUSHARE_TOKEN"):
            return "tushare"
        return "akshare"

    # Pure 6-digit -> AKShare (A-shares)
    if ASHARE_PATTERN.match(ticker):
        return "akshare"

    # Default to yfinance for US/International
    return "yfinance"


def normalize_ashare_ticker(ticker: str) -> str:
    """Convert XXXXXX.SH/SZ/BJ to XXXXXX for AKShare.

    Args:
        ticker: A-share ticker with optional suffix

    Returns:
        6-digit ticker code
    """
    match = ASHARE_WITH_SUFFIX.match(ticker)
    if match:
        return match.group(1)
    return ticker


def get_fetcher(
    ticker: str,
    source: Optional[str] = None,
    tushare_token: Optional[str] = None,
) -> BaseFetcher:
    """Get appropriate fetcher for ticker.

    Auto-selects data source based on ticker format:
    - AAPL, GOOGL -> yfinance
    - 600000, 000001 -> AKShare (free, no auth)
    - 600000.SH -> AKShare or Tushare (if token provided)

    Args:
        ticker: Stock ticker symbol
        source: Force specific source ('yfinance', 'akshare', 'tushare')
        tushare_token: Tushare API token (optional)

    Returns:
        Appropriate fetcher instance

    Raises:
        ImportError: If required package not installed
    """
    detected_source = source or detect_source(ticker, prefer_tushare=bool(tushare_token))

    if detected_source == "akshare":
        from .akshare import AKShareFetcher

        normalized = normalize_ashare_ticker(ticker)
        return AKShareFetcher(normalized)

    if detected_source == "tushare":
        from .tushare import TushareFetcher

        token = tushare_token or os.environ.get("TUSHARE_TOKEN")
        if not token:
            # Fall back to AKShare if no Tushare token
            from .akshare import AKShareFetcher

            normalized = normalize_ashare_ticker(ticker)
            return AKShareFetcher(normalized)
        return TushareFetcher(token, ticker)

    # Default: yfinance
    from .yfinance import YFinanceFetcher

    return YFinanceFetcher()


__all__ = [
    "BaseFetcher",
    "FetchResult",
    "HistoryResult",
    "detect_source",
    "get_fetcher",
    "normalize_ashare_ticker",
]
