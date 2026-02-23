from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass
class FetchResult:
    success: bool
    data: Dict[str, Any]
    source: str
    errors: List[str] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)


@dataclass
class HistoryResult:
    success: bool
    ticker: str
    source: str
    df: Optional[pd.DataFrame] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    errors: List[str] = field(default_factory=list)

    @property
    def prices(self) -> List[float]:
        if self.df is None or self.df.empty:
            return []
        return self.df["close"].tolist()

    @property
    def dates(self) -> List[date]:
        if self.df is None or self.df.empty:
            return []
        return [d.date() if hasattr(d, "date") else d for d in self.df.index.tolist()]

    def calculate_cagr(self, years: int = 5) -> float:
        if self.df is None or len(self.df) < 2:
            return 0.0
        start_price = float(self.df["close"].iloc[0])
        end_price = float(self.df["close"].iloc[-1])
        if start_price <= 0:
            return 0.0
        actual_years = len(self.df) / 252
        if actual_years <= 0:
            return 0.0
        cagr = (end_price / start_price) ** (1 / actual_years) - 1
        return cagr * 100

    def calculate_volatility(self) -> float:
        if self.df is None or len(self.df) < 2:
            return 0.0
        returns = self.df["close"].pct_change().dropna()
        if returns.empty:
            return 0.0
        return float(returns.std() * (252**0.5) * 100)

    def calculate_max_drawdown(self) -> float:
        if self.df is None or self.df.empty:
            return 0.0
        prices = self.df["close"]
        rolling_max = prices.cummax()
        drawdown = (prices - rolling_max) / rolling_max
        return float(drawdown.min() * 100)


class BaseFetcher(ABC):

    @property
    @abstractmethod
    def source_name(self) -> str:
        pass

    @abstractmethod
    def fetch_quote(self, ticker: str) -> FetchResult:
        pass

    @abstractmethod
    def fetch_fundamentals(self, ticker: str) -> FetchResult:
        pass

    @abstractmethod
    def fetch_all(self, ticker: str) -> FetchResult:
        pass

    @abstractmethod
    def fetch_history(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "5y",
        adjust: str = "qfq",
    ) -> HistoryResult:
        pass
