"""
Screening pipeline for processing multiple stocks.

This module provides:
- ScreeningPipeline: Main pipeline for concurrent stock screening
- Data collection from existing valuation, news, insider modules
- Result aggregation and ranking
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable
import time

from .base import ScreeningResult, ScreeningStrategy, ScoringWeights
from .scorers import CompositeScorer, get_scorer
from .strategies import get_strategy


@dataclass
class ScreeningSummary:
    """Summary of a screening run."""

    strategy_name: str
    total_stocks: int
    qualified_count: int
    failed_count: int
    error_count: int
    duration_seconds: float
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def pass_rate(self) -> float:
        if self.total_stocks == 0:
            return 0.0
        return self.qualified_count / self.total_stocks * 100


@dataclass
class ScreeningOutput:
    """Output of a screening run."""

    summary: ScreeningSummary
    qualified: List[ScreeningResult]
    disqualified: List[ScreeningResult]
    errors: List[Dict[str, Any]]


class ScreeningPipeline:
    """
    Main pipeline for screening stocks against a strategy.

    Features:
    - Concurrent data fetching
    - Filter application
    - Multi-factor scoring
    - Result ranking
    """

    def __init__(
        self,
        strategy_name: str = "value",
        strategy_kwargs: Optional[Dict[str, Any]] = None,
        max_workers: int = 5,
        include_news: bool = False,
        include_insider: bool = False,
        verbose: bool = False,
    ):
        """
        Initialize the screening pipeline.

        Args:
            strategy_name: Name of predefined strategy
            strategy_kwargs: Custom parameters for strategy
            max_workers: Max concurrent workers for data fetching
            include_news: Whether to fetch news sentiment data
            include_insider: Whether to fetch insider trading data
            verbose: Print progress messages
        """
        self.strategy = get_strategy(strategy_name, **(strategy_kwargs or {}))
        self.scorer = get_scorer(strategy_name)
        self.max_workers = max_workers
        self.include_news = include_news
        self.include_insider = include_insider
        self.verbose = verbose

        # Callbacks for progress reporting
        self._on_stock_complete: Optional[Callable[[str, bool], None]] = None

    def on_stock_complete(self, callback: Callable[[str, bool], None]):
        """Register callback for when a stock is processed."""
        self._on_stock_complete = callback

    def _log(self, message: str):
        """Print message if verbose mode."""
        if self.verbose:
            print(f"[Screener] {message}")

    def _analyze_stock(self, ticker: str) -> ScreeningResult:
        """
        Analyze a single stock and return screening result.

        This is the main data collection and analysis function.
        """
        result = ScreeningResult(ticker=ticker)

        try:
            # 1. Fetch basic stock data
            self._log(f"Fetching data for {ticker}...")
            stock = self._fetch_stock_data(ticker)

            result.name = stock.name
            result.current_price = stock.current_price
            result.market_cap = stock.market_cap

            # 2. Run valuation
            valuation_summary = self._run_valuation(stock)
            result.fair_value_median = valuation_summary.get("median_value", 0)
            result.fair_value_avg = valuation_summary.get("average_value", 0)
            result.margin_of_safety = valuation_summary.get("average_premium_discount", 0)
            result.undervalued_methods = valuation_summary.get("undervalued_count", 0)
            result.total_methods = valuation_summary.get("total_methods", 0)

            # 3. Extract quality metrics (calculate if not available)
            # ROE = EPS / BVPS * 100
            if stock.roe and stock.roe > 0:
                result.roe = stock.roe
            elif stock.eps and stock.bvps and stock.bvps > 0:
                result.roe = (stock.eps / stock.bvps) * 100
            else:
                result.roe = 0
            
            result.pe_ratio = stock.pe_ratio or 0
            result.pb_ratio = stock.pb_ratio or 0
            result.operating_margin = stock.operating_margin or 0
            
            # Dividend yield
            if stock.dividend_yield and stock.dividend_yield > 0:
                result.dividend_yield = stock.dividend_yield
            elif stock.dividend_per_share and stock.current_price and stock.current_price > 0:
                result.dividend_yield = (stock.dividend_per_share / stock.current_price) * 100
            else:
                result.dividend_yield = 0
            
            result.payout_ratio = stock.payout_ratio or 0
            result.dividend_growth_rate = stock.dividend_growth_rate or 0
            result.earnings_growth = stock.growth_rate or 0

            # Calculate FCF yield
            if stock.fcf and stock.market_cap:
                result.fcf_yield = (stock.fcf / stock.market_cap) * 100

            # Calculate Altman Z (simplified)
            result.altman_z = self._estimate_altman_z(stock)

            # Calculate ROIC (simplified)
            result.roic = self._estimate_roic(stock)

            # Calculate PEG
            if result.pe_ratio > 0 and result.earnings_growth > 0:
                result.peg_ratio = result.pe_ratio / result.earnings_growth

            # 4. Fetch price history for momentum
            self._fetch_momentum_data(ticker, result)

            # 5. Fetch sentiment data (optional)
            if self.include_news:
                self._fetch_news_sentiment(ticker, result)

            if self.include_insider:
                self._fetch_insider_sentiment(ticker, result)

            # 6. Apply strategy filters
            self.strategy.apply_filters(result)

            # 7. Calculate composite score
            self.scorer.score(result)

            self._log(
                f"Completed {ticker}: score={result.composite_score:.1f}, qualified={result.is_qualified}"
            )

        except Exception as e:
            result.errors.append(f"Analysis error: {str(e)}")
            result.is_qualified = False
            self._log(f"Error analyzing {ticker}: {e}")

        # Notify callback
        if self._on_stock_complete:
            self._on_stock_complete(ticker, result.is_qualified)

        return result

    def _fetch_stock_data(self, ticker: str):
        """Fetch stock data using existing data fetcher."""
        from valueinvest import Stock

        return Stock.from_api(ticker)

    def _run_valuation(self, stock) -> Dict[str, Any]:
        """Run valuation engine and return summary."""
        from valueinvest import ValuationEngine

        engine = ValuationEngine()

        # Get recommended methods based on stock type
        recommendations = engine.get_recommended_methods(stock)
        methods = recommendations["primary"] + recommendations["secondary"]

        results = engine.run_multiple(stock, methods)
        summary = engine.summary(results)

        return summary

    def _estimate_altman_z(self, stock) -> float:
        """
        Estimate Altman Z-Score from available data.

        Simplified calculation using available metrics.
        Full Z-Score requires: Working Capital/TA, Retained Earnings/TA,
        EBIT/TA, Market Cap/TL, Sales/TA
        """
        try:
            if not stock.total_assets or stock.total_assets == 0:
                return 0.0

            # Simplified components
            z = 0.0

            # Working Capital / Total Assets (approximated)
            if stock.net_working_capital:
                z += 1.2 * (stock.net_working_capital / stock.total_assets)

            # Retained Earnings / Total Assets
            if stock.retained_earnings:
                z += 1.4 * (stock.retained_earnings / stock.total_assets)

            # EBIT / Total Assets (approximated with operating_margin)
            if stock.ebit:
                z += 3.3 * (stock.ebit / stock.total_assets)

            # Market Cap / Total Liabilities
            if stock.total_liabilities and stock.total_liabilities > 0:
                z += 0.6 * (stock.market_cap / stock.total_liabilities)

            # Sales / Total Assets (approximated)
            if stock.revenue:
                z += 1.0 * (stock.revenue / stock.total_assets)

            return round(z, 2)

        except Exception:
            return 0.0

    def _estimate_roic(self, stock) -> float:
        """
        Estimate ROIC (Return on Invested Capital).

        ROIC = NOPAT / Invested Capital
        Simplified: Net Income / (Total Equity + Total Debt)
        """
        try:
            invested_capital = stock.bvps * stock.shares_outstanding + stock.net_debt
            if invested_capital and invested_capital > 0 and stock.net_income:
                return (stock.net_income / invested_capital) * 100
            return 0.0
        except Exception:
            return 0.0

    def _fetch_momentum_data(self, ticker: str, result: ScreeningResult):
        """Fetch price history for momentum calculations."""
        try:
            from valueinvest import Stock

            history = Stock.fetch_price_history(ticker, period="3y")

            result.cagr_3y = history.cagr_hfq or history.cagr or 0

            # Calculate price vs 52w high/low
            stats = history.get_price_stats(days=252, adjust="qfq")
            if stats:
                high = stats.get("high", 0)
                low = stats.get("low", 0)
                latest = stats.get("latest", 0)

                if high > 0 and latest > 0:
                    result.price_vs_52w_high = ((high - latest) / high) * 100
                if low > 0 and latest > 0:
                    result.price_vs_52w_low = ((latest - low) / low) * 100

        except Exception as e:
            self._log(f"Error fetching momentum data for {ticker}: {e}")

    def _fetch_news_sentiment(self, ticker: str, result: ScreeningResult):
        """Fetch news sentiment data."""
        try:
            from valueinvest.news.registry import NewsRegistry
            from valueinvest.news.analyzer.keyword_analyzer import KeywordSentimentAnalyzer

            fetcher = NewsRegistry.get_fetcher(ticker)
            news_result = fetcher.fetch_all(ticker, days=30)

            if news_result.news:
                analyzer = KeywordSentimentAnalyzer()
                analysis = analyzer.analyze_batch(news_result.news, ticker)

                result.news_sentiment = analysis.sentiment_score
                result.news_sentiment_label = analysis.sentiment_label

        except Exception as e:
            self._log(f"Error fetching news for {ticker}: {e}")

    def _fetch_insider_sentiment(self, ticker: str, result: ScreeningResult):
        """Fetch insider trading sentiment data."""
        try:
            from valueinvest.insider import InsiderRegistry

            fetcher = InsiderRegistry.get_fetcher(ticker)
            insider_result = fetcher.fetch_insider_trades(ticker, days=365)

            if insider_result.summary:
                result.insider_sentiment = insider_result.summary.sentiment
                result.insider_net_value = insider_result.summary.net_value

        except Exception as e:
            self._log(f"Error fetching insider data for {ticker}: {e}")

    def screen(self, tickers: List[str]) -> ScreeningOutput:
        """
        Screen a list of stocks against the strategy.

        Args:
            tickers: List of ticker symbols to screen

        Returns:
            ScreeningOutput with qualified, disqualified, and error results
        """
        start_time = time.time()

        self._log(f"Starting screening with strategy: {self.strategy.name}")
        self._log(f"Stock pool: {len(tickers)} tickers")

        # Run analysis concurrently
        results = []
        errors = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._analyze_stock, ticker): ticker for ticker in tickers}

            for future in futures:
                try:
                    result = future.result(timeout=60)  # 60s timeout per stock
                    results.append(result)
                except Exception as e:
                    ticker = futures[future]
                    errors.append(
                        {
                            "ticker": ticker,
                            "error": str(e),
                        }
                    )
                    results.append(
                        ScreeningResult(
                            ticker=ticker,
                            errors=[str(e)],
                            is_qualified=False,
                        )
                    )

        # Separate qualified and disqualified
        qualified = [r for r in results if r.is_qualified]
        disqualified = [r for r in results if not r.is_qualified and not r.errors]

        # Sort qualified by composite score (descending)
        qualified.sort(key=lambda r: r.composite_score, reverse=True)

        # Create summary
        duration = time.time() - start_time
        summary = ScreeningSummary(
            strategy_name=self.strategy.name,
            total_stocks=len(tickers),
            qualified_count=len(qualified),
            failed_count=len(disqualified),
            error_count=len(errors),
            duration_seconds=duration,
        )

        self._log(
            f"Screening complete: {len(qualified)} qualified, {len(disqualified)} failed, {len(errors)} errors"
        )
        self._log(f"Duration: {duration:.1f}s")

        return ScreeningOutput(
            summary=summary,
            qualified=qualified,
            disqualified=disqualified,
            errors=errors,
        )

    async def screen_async(self, tickers: List[str]) -> ScreeningOutput:
        """Async wrapper for screen method."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.screen, tickers)


def screen_stocks(
    tickers: List[str],
    strategy: str = "value",
    max_workers: int = 5,
    include_news: bool = False,
    include_insider: bool = False,
    verbose: bool = False,
    **strategy_kwargs,
) -> ScreeningOutput:
    """
    Convenience function to screen stocks.

    Args:
        tickers: List of ticker symbols
        strategy: Strategy name (value, growth, dividend, quality, garp)
        max_workers: Max concurrent workers
        include_news: Include news sentiment analysis
        include_insider: Include insider trading analysis
        verbose: Print progress
        **strategy_kwargs: Custom strategy parameters

    Returns:
        ScreeningOutput with results

    Example:
        >>> result = screen_stocks(
        ...     ["600887", "600900", "601398"],
        ...     strategy="value",
        ...     min_mos=15.0,
        ... )
        >>> print(f"Qualified: {len(result.qualified)}")
    """
    pipeline = ScreeningPipeline(
        strategy_name=strategy,
        strategy_kwargs=strategy_kwargs,
        max_workers=max_workers,
        include_news=include_news,
        include_insider=include_insider,
        verbose=verbose,
    )
    return pipeline.screen(tickers)
