"""
Buyback data fetcher for A-shares using akshare.

Data source: akshare.stock_repurchase_em() - 东方财富回购数据
"""
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any, List

from .base import BaseBuybackFetcher
from ..base import (
    BuybackFetchResult,
    BuybackRecord,
    BuybackSummary,
    BuybackStatus,
    BuybackSentiment,
    Market,
)


class AKShareBuybackFetcher(BaseBuybackFetcher):
    """Fetch buyback data for A-shares via akshare."""

    def __init__(self):
        self._cache = None
        self._cache_time = None

    @property
    def market(self) -> Market:
        return Market.A_SHARE

    @property
    def source_name(self) -> str:
        return "akshare"

    def _get_repurchase_data(self) -> List[Dict[str, Any]]:
        """Fetch all repurchase data from akshare (with caching)."""
        now = datetime.now()
        if (
            self._cache is None
            or self._cache_time is None
            or (now - self._cache_time).total_seconds() > 300
        ):
            try:
                import akshare as ak

                df = ak.stock_repurchase_em()
                self._cache = df.to_dict("records")
                self._cache_time = now
            except ImportError as e:
                raise ImportError(
                    "akshare is required for A-share buyback data. "
                    "Install with: pip install valueinvest[ashare]"
                ) from e
        return self._cache

    def _parse_status(self, status_str: str) -> BuybackStatus:
        """Parse status string to BuybackStatus enum."""
        if not status_str:
            return BuybackStatus.UNKNOWN
        status_str = str(status_str).strip()
        if "完成" in status_str:
            return BuybackStatus.COMPLETED
        elif "实施中" in status_str or "进行" in status_str:
            return BuybackStatus.IN_PROGRESS
        elif "计划" in status_str or "公告" in status_str:
            return BuybackStatus.ANNOUNCED
        elif "取消" in status_str:
            return BuybackStatus.CANCELLED
        return BuybackStatus.UNKNOWN

    def _parse_amount(self, value) -> float:
        """Parse amount value, handling NaN and strings."""
        if value is None:
            return 0.0
        try:
            import math

            f = float(value)
            if math.isnan(f) or math.isinf(f):
                return 0.0
            return f
        except (ValueError, TypeError):
            return 0.0

    def _parse_date(self, value) -> Optional[date]:
        """Parse date string."""
        if value is None or str(value) == "nan":
            return None
        try:
            if isinstance(value, str):
                return datetime.strptime(value, "%Y-%m-%d").date()
            elif hasattr(value, "date"):
                return value.date() if callable(getattr(value, "date")) else value
        except (ValueError, TypeError):
            pass
        return None

    def fetch_buyback(
        self,
        ticker: str,
        days: int = 365,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> BuybackFetchResult:
        try:
            ticker = ticker.zfill(6)
            all_data = self._get_repurchase_data()

            records = []
            total_amount = 0.0
            total_shares = 0.0
            active_programs = 0

            cutoff_date = date.today() - timedelta(days=days)

            for row in all_data:
                row_ticker = str(row.get("股票代码", "")).zfill(6)
                if row_ticker != ticker:
                    continue

                announce_date = self._parse_date(row.get("最新公告日期"))
                if announce_date and announce_date < cutoff_date:
                    continue

                status = self._parse_status(row.get("实施进度", ""))

                shares_repurchased = self._parse_amount(row.get("已回购股份数量", 0))
                amount = self._parse_amount(row.get("已回购金额", 0))

                price_low = self._parse_amount(row.get("已回购股份价格区间-下限"))
                price_high = self._parse_amount(row.get("已回购股份价格区间-上限"))

                planned_shares_low = self._parse_amount(row.get("计划回购数量区间-下限"))
                planned_shares_high = self._parse_amount(row.get("计划回购数量区间-上限"))
                planned_amount_low = self._parse_amount(row.get("计划回购金额区间-下限"))
                planned_amount_high = self._parse_amount(row.get("计划回购金额区间-上限"))

                avg_price = 0.0
                if shares_repurchased > 0 and amount > 0:
                    avg_price = amount / shares_repurchased

                record = BuybackRecord(
                    ticker=ticker,
                    market=self.market,
                    announce_date=announce_date,
                    shares_repurchased=shares_repurchased,
                    amount=amount,
                    avg_price=avg_price,
                    planned_shares_low=planned_shares_low,
                    planned_shares_high=planned_shares_high,
                    planned_amount_low=planned_amount_low,
                    planned_amount_high=planned_amount_high,
                    status=status,
                    price_low=price_low,
                    price_high=price_high,
                    source=self.source_name,
                    raw_data={k: str(v) for k, v in row.items()},
                )
                records.append(record)

                total_amount += amount
                total_shares += shares_repurchased
                if status in (BuybackStatus.ANNOUNCED, BuybackStatus.IN_PROGRESS):
                    active_programs += 1

            market_cap = None
            dividend_yield = 0.0
            try:
                from valueinvest import Stock

                stock = Stock.from_api(ticker)
                if stock.current_price and stock.shares_outstanding:
                    market_cap = stock.current_price * stock.shares_outstanding
                dividend_yield = stock.dividend_yield or 0.0
            except Exception:
                pass

            buyback_yield = 0.0
            if market_cap and market_cap > 0 and total_amount > 0:
                buyback_yield = (total_amount / market_cap) * 100

            total_shareholder_yield = buyback_yield + dividend_yield

            sentiment = BuybackSentiment.NONE
            if buyback_yield > 3.0:
                sentiment = BuybackSentiment.AGGRESSIVE
            elif buyback_yield > 1.0:
                sentiment = BuybackSentiment.MODERATE
            elif buyback_yield > 0:
                sentiment = BuybackSentiment.MINIMAL

            summary = BuybackSummary(
                ticker=ticker,
                market=self.market,
                period_days=days,
                total_amount=total_amount,
                total_shares=total_shares,
                buyback_yield=buyback_yield,
                dividend_yield=dividend_yield,
                total_shareholder_yield=total_shareholder_yield,
                record_count=len(records),
                active_programs=active_programs,
                sentiment=sentiment,
            )

            return BuybackFetchResult(
                success=True,
                ticker=ticker,
                market=self.market,
                source=self.source_name,
                records=records,
                summary=summary,
                market_cap=market_cap,
            )

        except Exception as e:
            return BuybackFetchResult(
                success=False,
                ticker=ticker,
                market=self.market,
                source=self.source_name,
                errors=[str(e)],
            )
