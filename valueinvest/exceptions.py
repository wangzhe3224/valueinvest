"""Custom exceptions for valueinvest library."""


class DataFetchError(Exception):
    """Raised when data fetching fails (network, API limits, etc.)."""
    def __init__(self, ticker: str, message: str, source: str = ""):
        self.ticker = ticker
        self.source = source
        super().__init__(f"[{source}] Failed to fetch {ticker}: {message}" if source else f"Failed to fetch {ticker}: {message}")


class InsufficientDataError(Exception):
    """Raised when required data fields are missing for a calculation."""
    def __init__(self, method: str, missing_fields: list, message: str = ""):
        self.method = method
        self.missing_fields = missing_fields
        msg = message or f"{method} requires missing fields: {', '.join(missing_fields)}"
        super().__init__(msg)


class UnsupportedMarketError(Exception):
    """Raised when a ticker cannot be mapped to a supported market/data source."""
    def __init__(self, ticker: str, message: str = ""):
        self.ticker = ticker
        msg = message or f"Cannot determine data source for ticker: {ticker}"
        super().__init__(msg)
