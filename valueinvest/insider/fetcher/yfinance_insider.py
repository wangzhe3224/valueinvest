"""
US stock insider trading fetcher using yfinance.

Fetches per-trade Form 4 insider transactions from Yahoo Finance
(`Ticker.insider_transactions`, ~2 years of history).
"""
import re
from datetime import datetime, date
from typing import List, Optional

from .base import BaseInsiderFetcher
from ..base import InsiderTrade, InsiderFetchResult, InsiderSummary, TradeType, InsiderTitle
from valueinvest.news.base import Market

# "Sale at price 310.95 per share." / "Stock Gift at price 0.00 per share."
_PRICE_RE = re.compile(r"at price ([\d,.]+) per share")


class YFinanceInsiderFetcher(BaseInsiderFetcher):
    market = Market.US

    @property
    def source_name(self) -> str:
        return "yfinance"

    def fetch_insider_trades(
        self,
        ticker: str,
        days: int = 90,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> InsiderFetchResult:
        import yfinance as yf

        start_dt, end_dt = self._get_date_range(days, start_date, end_date)
        start_only = start_dt.date() if hasattr(start_dt, "date") else start_dt
        end_only = end_dt.date() if hasattr(end_dt, "date") else end_dt

        trades: List[InsiderTrade] = []
        errors = []

        try:
            tx = yf.Ticker(ticker).insider_transactions
            if tx is None or tx.empty:
                errors.append(f"no insider transactions returned for {ticker}")
            else:
                for _, row in tx.iterrows():
                    trade_date = self._parse_date(row.get("Start Date"))
                    if trade_date is None:
                        continue
                    if not (start_only <= trade_date <= end_only):
                        continue

                    shares = self._to_float(row.get("Shares"))
                    text = str(row.get("Text") or "")
                    price = self._parse_price(text)
                    value = self._to_float(row.get("Value"))
                    if value is None:
                        value = shares * price
                    elif price == 0.0 and value > 0 and shares > 0:
                        # Text lacks price (e.g. automatic sales): back it out
                        price = value / shares

                    trades.append(
                        InsiderTrade(
                            ticker=ticker,
                            insider_name=str(row.get("Insider") or "Unknown"),
                            title=self._parse_title(row.get("Position") or ""),
                            trade_type=self._parse_type(text),
                            trade_date=trade_date,
                            shares=abs(shares),
                            price=price,
                            value=abs(value),
                            market=Market.US,
                            filing_date=None,  # Yahoo returns trade date only
                            source="yfinance",
                            url=str(row.get("URL") or ""),
                            raw_data=row.to_dict() if hasattr(row, "to_dict") else {},
                        )
                    )
        except Exception as e:
            errors.append(f"yfinance insider fetch failed: {e}")

        trades.sort(key=lambda t: t.trade_date, reverse=True)

        summary = None
        if trades:
            summary = self._calculate_summary(trades, ticker, Market.US, days)

        return InsiderFetchResult(
            success=len(errors) == 0 or len(trades) > 0,
            ticker=ticker,
            market=Market.US,
            source=self.source_name,
            trades=trades,
            summary=summary,
            errors=errors,
        )

    @staticmethod
    def _to_float(value) -> Optional[float]:
        if value is None:
            return None
        try:
            f = float(value)
        except (TypeError, ValueError):
            return None
        if f != f:  # NaN
            return None
        return f

    @staticmethod
    def _parse_price(text: str) -> float:
        m = _PRICE_RE.search(text or "")
        if not m:
            return 0.0
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            return 0.0

    @staticmethod
    def _parse_type(text: str) -> TradeType:
        t = (text or "").lower()
        if "gift" in t:
            return TradeType.GIFT
        if "exercise" in t:
            return TradeType.EXERCISE
        if "sale" in t or "sell" in t:
            return TradeType.SELL
        if "buy" in t or "purchase" in t:
            return TradeType.BUY
        # Empty text = grant/award or other non-open-market transaction
        return TradeType.OTHER

    def _parse_date(self, value) -> Optional[date]:
        if value is None:
            return None
        if hasattr(value, "date"):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y"]:
                try:
                    return datetime.strptime(value[:19], fmt).date()
                except ValueError:
                    continue
        return None

    @staticmethod
    def _parse_title(title_str: str) -> InsiderTitle:
        if not title_str:
            return InsiderTitle.UNKNOWN

        title_lower = str(title_str).lower()

        if "ceo" in title_lower or "chief executive" in title_lower:
            return InsiderTitle.CEO
        if "cfo" in title_lower or "chief financial" in title_lower:
            return InsiderTitle.CFO
        if "coo" in title_lower or "chief operating" in title_lower:
            return InsiderTitle.COO
        if "chairman" in title_lower or "chair" in title_lower:
            return InsiderTitle.CHAIRMAN
        if "director" in title_lower:
            return InsiderTitle.DIRECTOR
        if "officer" in title_lower:
            return InsiderTitle.OFFICER
        if "vp" in title_lower or "vice president" in title_lower:
            return InsiderTitle.VP

        return InsiderTitle.OTHER
