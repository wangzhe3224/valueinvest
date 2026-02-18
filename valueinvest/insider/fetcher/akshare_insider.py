"""
A-share insider trading fetcher using akshare.

Fetches insider transactions (高管增减持) from THS.
"""
from datetime import datetime, date
from typing import List, Optional
import re

from .base import BaseInsiderFetcher
from ..base import InsiderTrade, InsiderFetchResult, InsiderSummary, TradeType, InsiderTitle
from valueinvest.news.base import Market


class AKShareInsiderFetcher(BaseInsiderFetcher):
    market = Market.A_SHARE
    
    @property
    def source_name(self) -> str:
        return "akshare"
    
    def fetch_insider_trades(
        self,
        ticker: str,
        days: int = 90,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> InsiderFetchResult:
        import akshare as ak
        
        start_dt, end_dt = self._get_date_range(days, start_date, end_date)
        start_date_only = start_dt.date() if hasattr(start_dt, 'date') else start_dt
        end_date_only = end_dt.date() if hasattr(end_dt, 'date') else end_dt
        
        trades: List[InsiderTrade] = []
        errors = []
        
        try:
            df = ak.stock_management_change_ths(symbol=ticker)
            
            if df is None or df.empty:
                return InsiderFetchResult(
                    success=True,
                    ticker=ticker,
                    market=Market.A_SHARE,
                    source=self.source_name,
                    trades=[],
                    summary=InsiderSummary(
                        ticker=ticker,
                        market=Market.A_SHARE,
                        period_days=days,
                    ),
                    errors=[],
                )
            
            for _, row in df.iterrows():
                trade_date = self._parse_date(row.get("变动日期"))
                if trade_date is None:
                    continue
                
                if not (start_date_only <= trade_date <= end_date_only):
                    continue
                
                insider_name = str(row.get("变动人", "Unknown"))
                title = self._parse_title(str(row.get("与公司高管关系", "")))
                
                change_str = str(row.get("变动数量", ""))
                shares, trade_type = self._parse_change_str(change_str)
                
                price = self._parse_price(row.get("交易均价"))
                value = abs(shares * price * 10000) if price else 0.0
                
                remaining_str = str(row.get("剩余股数", "0"))
                shares_owned_after = self._parse_shares_cn(remaining_str)
                
                method = str(row.get("股份变动途径", ""))
                if "激励" in method or "期权" in method:
                    final_trade_type = TradeType.GRANT
                else:
                    final_trade_type = trade_type
                
                trade = InsiderTrade(
                    ticker=ticker,
                    insider_name=insider_name,
                    title=title,
                    trade_type=final_trade_type,
                    trade_date=trade_date,
                    shares=abs(shares * 10000),
                    price=price,
                    value=value,
                    market=Market.A_SHARE,
                    shares_owned_after=shares_owned_after * 10000 if shares_owned_after else None,
                    source="akshare_ths",
                    raw_data=row.to_dict() if hasattr(row, 'to_dict') else {},
                )
                trades.append(trade)
            
        except Exception as e:
            errors.append(f"akshare insider fetch failed: {e}")
        
        trades.sort(key=lambda t: t.trade_date, reverse=True)
        
        summary = None
        if trades:
            summary = self._calculate_summary(trades, ticker, Market.A_SHARE, days)
        else:
            summary = InsiderSummary(
                ticker=ticker,
                market=Market.A_SHARE,
                period_days=days,
            )
        
        return InsiderFetchResult(
            success=len(errors) == 0 or len(trades) > 0,
            ticker=ticker,
            market=Market.A_SHARE,
            source=self.source_name,
            trades=trades,
            summary=summary,
            errors=errors,
        )
    
    def _parse_date(self, value) -> Optional[date]:
        if value is None:
            return None
        if hasattr(value, 'date'):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d"]:
                try:
                    return datetime.strptime(value[:19], fmt).date()
                except ValueError:
                    continue
        return None
    
    def _parse_change_str(self, value: str) -> tuple:
        if not value:
            return (0.0, TradeType.OTHER)
        
        match = re.match(r"(增持|减持|卖出|买入)([\d.]+)(万|亿)?", str(value).strip())
        if match:
            action = match.group(1)
            num = float(match.group(2))
            unit = match.group(3)
            
            if unit == "亿":
                num *= 10000
            
            trade_type = TradeType.BUY if action in ("增持", "买入") else TradeType.SELL
            return (num, trade_type)
        
        return (0.0, TradeType.OTHER)
    
    def _parse_shares_cn(self, value: str) -> float:
        if not value:
            return 0.0
        try:
            clean = str(value).replace(",", "").replace("，", "").strip()
            match = re.match(r"([\d.]+)(万|亿)?", clean)
            if match:
                num = float(match.group(1))
                unit = match.group(2)
                if unit == "万":
                    return num
                elif unit == "亿":
                    return num * 10000
                return num
            return 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def _parse_price(self, value) -> float:
        if value is None:
            return 0.0
        try:
            if hasattr(value, 'item'):
                return float(value.item())
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    def _parse_title(self, title_str: str) -> InsiderTitle:
        if not title_str:
            return InsiderTitle.UNKNOWN
        
        title_lower = str(title_str).lower()
        
        if "ceo" in title_lower or "首席执行官" in title_lower or "总经理" in title_lower:
            return InsiderTitle.CEO
        if "cfo" in title_lower or "首席财务官" in title_lower or "财务总监" in title_lower:
            return InsiderTitle.CFO
        if "coo" in title_lower or "首席运营官" in title_lower:
            return InsiderTitle.COO
        if "董事长" in title_lower:
            return InsiderTitle.CHAIRMAN
        if "监事" in title_lower:
            return InsiderTitle.DIRECTOR
        if "董事" in title_lower:
            return InsiderTitle.DIRECTOR
        if "高级管理人员" in title_lower or "高管" in title_lower:
            return InsiderTitle.OFFICER
        if "副总" in title_lower:
            return InsiderTitle.VP
        
        return InsiderTitle.OTHER
