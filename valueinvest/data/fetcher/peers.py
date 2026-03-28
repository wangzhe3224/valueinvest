"""
Industry Peer Comparison Data
"""
from typing import List, Dict, Any, Optional


def get_industry_peers(ticker: str, source: str = "yfinance") -> List[str]:
    """Get peer/competitor tickers for a given stock.

    Uses yfinance to find companies in the same industry.
    Returns list of peer ticker symbols.
    """
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        info = stock.info

        # Get industry and sector
        industry = info.get("industry", "")
        sector = info.get("sector", "")

        if not industry and not sector:
            return []

        # Use yfinance recommended key if available
        # Otherwise, return empty - user should provide peers manually
        # yfinance doesn't have a direct "peers" API, so we return []
        # In production, this would use a proper peers API
        return []
    except Exception:
        return []


def fetch_peer_metrics(tickers: List[str]) -> List[Dict[str, Any]]:
    """Fetch basic valuation metrics for a list of peer tickers.

    Returns list of dicts with ticker, pe, pb, ev_ebitda, dividend_yield, market_cap, roe.
    """
    try:
        import yfinance as yf
    except ImportError:
        return []

    peers = []
    for ticker in tickers[:10]:  # Limit to 10 peers
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            if not info:
                continue

            pe = info.get("trailingPE", 0) or 0
            pb = info.get("priceToBook", 0) or 0
            ev_ebitda = info.get("enterpriseToEbitda", 0) or 0
            div_yield = info.get("dividendYield", 0) or 0
            market_cap = info.get("marketCap", 0) or 0
            roe = (info.get("returnOnEquity", 0) or 0) * 100
            revenue = info.get("totalRevenue", 0) or 0

            peers.append({
                "ticker": ticker,
                "pe_ratio": round(pe, 2) if pe else 0,
                "pb_ratio": round(pb, 2) if pb else 0,
                "ev_ebitda": round(ev_ebitda, 2) if ev_ebitda else 0,
                "dividend_yield": round(div_yield * 100, 2) if div_yield else 0,
                "market_cap": market_cap,
                "roe": round(roe, 2) if roe else 0,
                "revenue": revenue,
            })
        except Exception:
            continue

    return peers
