from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .data.fetcher import BaseFetcher, HistoryResult
    import pandas as pd


@dataclass
class StockHistory:
    ticker: str
    df: Optional["pd.DataFrame"] = None
    df_hfq: Optional["pd.DataFrame"] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    cagr: float = 0.0
    cagr_hfq: float = 0.0
    volatility: float = 0.0
    max_drawdown: float = 0.0
    prices: List[float] = field(default_factory=list)
    prices_hfq: List[float] = field(default_factory=list)
    adjust_type: str = "qfq"

    @classmethod
    def from_history_result(cls, result: "HistoryResult", result_hfq: Optional["HistoryResult"] = None) -> "StockHistory":
        history = cls(
            ticker=result.ticker,
            df=result.df,
            start_date=result.start_date,
            end_date=result.end_date,
            cagr=result.calculate_cagr(),
            volatility=result.calculate_volatility(),
            max_drawdown=result.calculate_max_drawdown(),
            prices=result.prices,
        )
        
        if result_hfq and result_hfq.df is not None:
            history.df_hfq = result_hfq.df
            history.prices_hfq = result_hfq.prices
            history.cagr_hfq = result_hfq.calculate_cagr()
        
        return history

    def get_recent_prices(self, days: int = 30, adjust: str = "qfq") -> List[dict]:
        df = self.df_hfq if adjust == "hfq" else self.df
        if df is None or df.empty:
            return []
        
        recent = df.tail(days)
        result = []
        for idx, row in recent.iterrows():
            date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)
            result.append({
                "date": date_str,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": int(row["volume"]) if row["volume"] else 0,
            })
        return result

    def get_price_stats(self, days: int = 30, adjust: str = "qfq") -> dict:
        df = self.df_hfq if adjust == "hfq" else self.df
        if df is None or df.empty:
            return {}
        
        recent = df.tail(days)
        closes = recent["close"]
        
        return {
            "period_days": len(recent),
            "high": float(closes.max()),
            "low": float(closes.min()),
            "avg": float(closes.mean()),
            "latest": float(closes.iloc[-1]),
            "change_pct": float((closes.iloc[-1] - closes.iloc[0]) / closes.iloc[0] * 100),
        }


@dataclass
class Stock:
    ticker: str
    name: str = ""
    current_price: float = 0.0
    shares_outstanding: float = 0.0
    
    eps: float = 0.0
    bvps: float = 0.0
    revenue: float = 0.0
    net_income: float = 0.0
    fcf: float = 0.0
    
    current_assets: float = 0.0
    total_liabilities: float = 0.0
    total_assets: float = 0.0
    net_debt: float = 0.0
    
    depreciation: float = 0.0
    capex: float = 0.0
    net_working_capital: float = 0.0
    net_fixed_assets: float = 0.0
    ebit: float = 0.0
    
    operating_margin: float = 0.0
    tax_rate: float = 0.0
    roe: float = 0.0
    
    growth_rate: float = 0.0
    dividend_per_share: float = 0.0
    dividend_yield: float = 0.0
    dividend_growth_rate: float = 0.0
    
    china_10y_yield: float = 1.80
    aaa_corporate_yield: float = 2.28
    cost_of_capital: float = 10.0
    discount_rate: float = 10.0
    terminal_growth: float = 2.0
    
    growth_rate_1_5: float = 5.0
    growth_rate_6_10: float = 3.0
    
    npl_ratio: float = 0.0
    provision_coverage: float = 0.0
    capital_adequacy_ratio: float = 0.0
    
    sectors: list = field(default_factory=list)
    exchange: str = "SH"
    currency: str = "CNY"
    
    extra: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def pe_ratio(self) -> float:
        return self.current_price / self.eps if self.eps > 0 else 0
    
    @property
    def pb_ratio(self) -> float:
        return self.current_price / self.bvps if self.bvps > 0 else 0
    
    @property
    def market_cap(self) -> float:
        return self.current_price * self.shares_outstanding
    
    @property
    def enterprise_value(self) -> float:
        return self.market_cap + self.net_debt
    
    @property
    def payout_ratio(self) -> float:
        return (self.dividend_per_share / self.eps * 100) if self.eps > 0 else 0
    
    @property
    def fcf_per_share(self) -> float:
        return self.fcf / self.shares_outstanding if self.shares_outstanding > 0 else 0
    
    @classmethod
    def from_api(
        cls,
        ticker: str,
        source: Optional[str] = None,
        fetcher: Optional["BaseFetcher"] = None,
        tushare_token: Optional[str] = None,
    ) -> "Stock":
        from .data.fetcher import get_fetcher

        fetcher = fetcher or get_fetcher(ticker, source, tushare_token)
        result = fetcher.fetch_all(ticker)

        if not result.success:
            raise ValueError(f"Failed to fetch {ticker}: {result.errors}")

        return cls.from_dict(result.data)

    @classmethod
    def fetch_price_history(
        cls,
        ticker: str,
        source: Optional[str] = None,
        fetcher: Optional["BaseFetcher"] = None,
        tushare_token: Optional[str] = None,
        period: str = "5y",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        include_hfq: bool = True,
    ) -> StockHistory:
        from .data.fetcher import get_fetcher

        fetcher = fetcher or get_fetcher(ticker, source, tushare_token)
        
        qfq_result = fetcher.fetch_history(
            ticker,
            start_date=start_date,
            end_date=end_date,
            period=period,
            adjust="qfq",
        )
        
        hfq_result = None
        if include_hfq:
            hfq_result = fetcher.fetch_history(
                ticker,
                start_date=start_date,
                end_date=end_date,
                period=period,
                adjust="hfq",
            )
        
        return StockHistory.from_history_result(qfq_result, hfq_result)

    @classmethod
    def from_dict(cls, data: dict) -> "Stock":
        return cls(
            ticker=data.get("ticker", ""),
            name=data.get("name", ""),
            current_price=data.get("current_price", 0.0),
            shares_outstanding=data.get("shares_outstanding", 0.0),
            eps=data.get("eps", 0.0),
            bvps=data.get("bvps", 0.0),
            revenue=data.get("revenue", 0.0),
            net_income=data.get("net_income", 0.0),
            fcf=data.get("fcf", 0.0),
            current_assets=data.get("current_assets", 0.0),
            total_liabilities=data.get("total_liabilities", 0.0),
            total_assets=data.get("total_assets", 0.0),
            net_debt=data.get("net_debt", 0.0),
            depreciation=data.get("depreciation", 0.0),
            capex=data.get("capex", 0.0),
            net_working_capital=data.get("net_working_capital", 0.0),
            net_fixed_assets=data.get("net_fixed_assets", 0.0),
            ebit=data.get("ebit", 0.0),
            operating_margin=data.get("operating_margin", 0.0),
            tax_rate=data.get("tax_rate", 0.0),
            roe=data.get("roe", 0.0),
            growth_rate=data.get("growth_rate", 0.0),
            dividend_per_share=data.get("dividend_per_share", 0.0),
            dividend_yield=data.get("dividend_yield", 0.0),
            dividend_growth_rate=data.get("dividend_growth_rate", 0.0),
            china_10y_yield=data.get("china_10y_yield", 1.80),
            aaa_corporate_yield=data.get("aaa_corporate_yield", 2.28),
            cost_of_capital=data.get("cost_of_capital", 10.0),
            discount_rate=data.get("discount_rate", 10.0),
            terminal_growth=data.get("terminal_growth", 2.0),
            growth_rate_1_5=data.get("growth_rate_1_5", 5.0),
            growth_rate_6_10=data.get("growth_rate_6_10", 3.0),
            npl_ratio=data.get("npl_ratio", 0.0),
            provision_coverage=data.get("provision_coverage", 0.0),
            capital_adequacy_ratio=data.get("capital_adequacy_ratio", 0.0),
            sectors=data.get("sectors", []),
            exchange=data.get("exchange", "SH"),
            currency=data.get("currency", "CNY"),
            extra=data.get("extra", {}),
        )
    
    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "name": self.name,
            "current_price": self.current_price,
            "shares_outstanding": self.shares_outstanding,
            "eps": self.eps,
            "bvps": self.bvps,
            "revenue": self.revenue,
            "net_income": self.net_income,
            "fcf": self.fcf,
            "pe_ratio": self.pe_ratio,
            "pb_ratio": self.pb_ratio,
            "dividend_yield": self.dividend_yield,
            "roe": self.roe,
            "market_cap": self.market_cap,
        }
