"""
Cash flow data fetcher for US stocks using yfinance.

Data sources:
- Cash flow statement: Free Cash Flow, Operating Cash Flow, CapEx, SBC
- Income statement: Net Income, Revenue, EBITDA
- Balance sheet: Shares Outstanding
- Info: Market Cap, Current Price
"""
from datetime import date
from typing import Optional, Dict, Any, List
import math

from .base import BaseCashFlowFetcher
from ..base import (
    CashFlowFetchResult,
    CashFlowRecord,
    CashFlowSummary,
    FCFQuality,
    FCFTrend,
    Market,
)


class YFinanceCashFlowFetcher(BaseCashFlowFetcher):
    """Fetch cash flow data for US stocks via yfinance."""

    def __init__(self):
        self._ticker_obj = None
        self._info = None

    @property
    def market(self) -> Market:
        return Market.US

    @property
    def source_name(self) -> str:
        return "yfinance"

    def _get_ticker_obj(self, ticker: str):
        if self._ticker_obj is None or getattr(self._ticker_obj, "ticker", None) != ticker:
            try:
                import yfinance as yf

                self._ticker_obj = yf.Ticker(ticker)
                self._info = None
            except ImportError as e:
                raise ImportError(
                    "yfinance is required for US stock cash flow data. "
                    "Install with: pip install valueinvest[us]"
                ) from e
        return self._ticker_obj

    def _get_info(self, ticker: str) -> Dict[str, Any]:
        if self._info is None:
            stock = self._get_ticker_obj(ticker)
            self._info = stock.info or {}
        return self._info

    def fetch_cashflow(
        self,
        ticker: str,
        years: int = 5,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> CashFlowFetchResult:
        try:
            stock = self._get_ticker_obj(ticker)
            info = self._get_info(ticker)

            if not info:
                return CashFlowFetchResult(
                    success=False,
                    ticker=ticker,
                    market=self.market,
                    source=self.source_name,
                    errors=[f"No data found for ticker: {ticker}"],
                )

            # Get market data
            market_cap = info.get("marketCap", 0) or 0
            shares_outstanding = (
                info.get("sharesOutstanding", 0) or info.get("impliedSharesOutstanding", 0) or 0
            )
            current_price = info.get("currentPrice", 0) or info.get("regularMarketPrice", 0) or 0

            # Get financial statements
            cashflow = stock.cashflow
            financials = stock.financials
            balance_sheet = stock.balance_sheet

            records: List[CashFlowRecord] = []
            yearly_fcf: Dict[int, float] = {}
            yearly_true_fcf: Dict[int, float] = {}
            yearly_revenue: Dict[int, float] = {}
            yearly_sbc: Dict[int, float] = {}
            yearly_capex: Dict[int, float] = {}
            yearly_net_income: Dict[int, float] = {}

            if cashflow is None or cashflow.empty:
                return CashFlowFetchResult(
                    success=False,
                    ticker=ticker,
                    market=self.market,
                    source=self.source_name,
                    errors=["No cash flow data available"],
                    market_cap=market_cap,
                    shares_outstanding=shares_outstanding,
                    current_price=current_price,
                )

            # Extract data from cash flow statement
            for col in cashflow.columns[:years]:
                try:
                    # Get fiscal year
                    if hasattr(col, "year"):
                        fiscal_year = col.year
                        report_date = (
                            col.date()
                            if hasattr(col, "date")
                            else date(col.year, col.month, col.day)
                        )
                    else:
                        fiscal_year = int(str(col)[:4])
                        report_date = date(fiscal_year, 12, 31)

                    # Helper to safely get value
                    def get_value(row_name: str, df=cashflow) -> float:
                        try:
                            if row_name in df.index:
                                val = df.loc[row_name, col]
                                if val is not None and str(val) != "nan":
                                    return float(val)
                        except (KeyError, TypeError, ValueError):
                            pass
                        return 0.0

                    # Cash flow data
                    operating_cf = get_value("Operating Cash Flow")
                    if operating_cf == 0:
                        operating_cf = get_value("Cash Flow From Continuing Operating Activities")

                    capex = get_value("Capital Expenditure")
                    if capex == 0:
                        capex = get_value("Purchase Of Ppe") + get_value("Purchase Of Business")

                    fcf = get_value("Free Cash Flow")
                    if fcf == 0 and operating_cf != 0:
                        fcf = operating_cf + capex  # CapEx is usually negative

                    sbc = get_value("Stock Based Compensation")

                    # Depreciation & Amortization
                    depreciation = get_value("Depreciation")
                    amortization = get_value("Amortization")
                    if depreciation == 0:
                        depreciation = get_value("Depreciation And Amortization")
                        amortization = 0

                    # Interest and taxes
                    interest_paid = abs(get_value("Interest Paid"))
                    taxes_paid = abs(get_value("Income Tax Paid"))

                    # Income statement data
                    net_income = 0.0
                    revenue = 0.0
                    ebitda = 0.0

                    if financials is not None and not financials.empty:
                        if col in financials.columns:

                            def get_fin_value(row_name: str) -> float:
                                try:
                                    if row_name in financials.index:
                                        val = financials.loc[row_name, col]
                                        if val is not None and str(val) != "nan":
                                            return float(val)
                                except (KeyError, TypeError, ValueError):
                                    pass
                                return 0.0

                            net_income = get_fin_value("Net Income")
                            if net_income == 0:
                                net_income = get_fin_value("Net Income Common Stockholders")
                            revenue = get_fin_value("Total Revenue")
                            ebitda = get_fin_value("EBITDA")

                    # Shares outstanding for this year
                    year_shares = shares_outstanding
                    if balance_sheet is not None and not balance_sheet.empty:
                        if col in balance_sheet.columns:
                            try:
                                if "Share Issued" in balance_sheet.index:
                                    val = balance_sheet.loc["Share Issued", col]
                                    if val is not None and str(val) != "nan":
                                        year_shares = float(val)
                            except (KeyError, TypeError, ValueError):
                                pass

                    # Calculate true FCF (SBC-adjusted)
                    true_fcf = fcf - sbc

                    # Skip if no meaningful data
                    if fcf == 0 and operating_cf == 0:
                        continue

                    record = CashFlowRecord(
                        ticker=ticker,
                        market=self.market,
                        fiscal_year=fiscal_year,
                        operating_cash_flow=operating_cf,
                        capital_expenditure=capex,
                        free_cash_flow=fcf,
                        stock_based_comp=sbc,
                        true_fcf=true_fcf,
                        net_income=net_income,
                        revenue=revenue,
                        ebitda=ebitda,
                        depreciation=depreciation,
                        amortization=amortization,
                        interest_paid=interest_paid,
                        taxes_paid=taxes_paid,
                        shares_outstanding=year_shares,
                        source=self.source_name,
                        report_date=report_date,
                    )
                    records.append(record)

                    # Store yearly data
                    yearly_fcf[fiscal_year] = fcf
                    yearly_true_fcf[fiscal_year] = true_fcf
                    yearly_revenue[fiscal_year] = revenue
                    yearly_sbc[fiscal_year] = sbc
                    yearly_capex[fiscal_year] = abs(capex)
                    yearly_net_income[fiscal_year] = net_income

                except Exception as e:
                    continue

            if not records:
                return CashFlowFetchResult(
                    success=False,
                    ticker=ticker,
                    market=self.market,
                    source=self.source_name,
                    errors=["Could not extract any cash flow records"],
                    market_cap=market_cap,
                    shares_outstanding=shares_outstanding,
                    current_price=current_price,
                )

            # Sort records by year
            records.sort(key=lambda r: r.fiscal_year, reverse=True)
            latest = records[0]

            # Calculate summary metrics
            fcf_yield = (latest.free_cash_flow / market_cap * 100) if market_cap > 0 else 0
            true_fcf_yield = (latest.true_fcf / market_cap * 100) if market_cap > 0 else 0
            fcf_margin = latest.fcf_margin
            true_fcf_margin = latest.true_fcf_margin
            fcf_per_share = latest.fcf_per_share
            fcf_to_net_income = latest.fcf_to_net_income
            sbc_as_pct_of_fcf = latest.sbc_as_pct_of_fcf
            sbc_impact = (
                ((latest.stock_based_comp / latest.free_cash_flow) * 100)
                if latest.free_cash_flow > 0
                else 0
            )

            # Calculate CAGR
            fcf_cagr = self._calculate_cagr(yearly_fcf)
            revenue_cagr = self._calculate_cagr(yearly_revenue)

            # Determine FCF quality
            fcf_quality = self._determine_fcf_quality(latest)

            # Determine FCF trend
            fcf_trend = self._determine_fcf_trend(list(yearly_fcf.values()))

            # Count positive/negative years
            positive_years = sum(1 for f in yearly_fcf.values() if f > 0)
            negative_years = sum(1 for f in yearly_fcf.values() if f < 0)

            summary = CashFlowSummary(
                ticker=ticker,
                market=self.market,
                period_years=len(records),
                latest_fcf=latest.free_cash_flow,
                latest_true_fcf=latest.true_fcf,
                latest_revenue=latest.revenue,
                latest_net_income=latest.net_income,
                fcf_yield=fcf_yield,
                fcf_margin=fcf_margin,
                fcf_per_share=fcf_per_share,
                true_fcf_yield=true_fcf_yield,
                true_fcf_margin=true_fcf_margin,
                fcf_to_net_income=fcf_to_net_income,
                sbc_as_pct_of_fcf=sbc_as_pct_of_fcf,
                sbc_impact_on_fcf=sbc_impact,
                fcf_cagr=fcf_cagr,
                revenue_cagr=revenue_cagr,
                fcf_trend=fcf_trend,
                fcf_quality=fcf_quality,
                yearly_fcf=yearly_fcf,
                yearly_true_fcf=yearly_true_fcf,
                yearly_revenue=yearly_revenue,
                yearly_sbc=yearly_sbc,
                yearly_capex=yearly_capex,
                record_count=len(records),
                positive_fcf_years=positive_years,
                negative_fcf_years=negative_years,
                market_cap=market_cap,
                shares_outstanding=shares_outstanding,
                current_price=current_price,
            )

            return CashFlowFetchResult(
                success=True,
                ticker=ticker,
                market=self.market,
                source=self.source_name,
                records=records,
                summary=summary,
                market_cap=market_cap,
                shares_outstanding=shares_outstanding,
                current_price=current_price,
            )

        except Exception as e:
            return CashFlowFetchResult(
                success=False,
                ticker=ticker,
                market=self.market,
                source=self.source_name,
                errors=[str(e)],
            )

    def _calculate_cagr(self, yearly_data: Dict[int, float]) -> float:
        """Calculate compound annual growth rate."""
        if len(yearly_data) < 2:
            return 0.0

        sorted_years = sorted(yearly_data.keys())
        first_year = sorted_years[0]
        last_year = sorted_years[-1]

        start_value = yearly_data[first_year]
        end_value = yearly_data[last_year]

        if start_value <= 0 or end_value <= 0:
            return 0.0

        years = last_year - first_year
        if years <= 0:
            return 0.0

        try:
            cagr = ((end_value / start_value) ** (1 / years) - 1) * 100
            return cagr
        except (ValueError, ZeroDivisionError):
            return 0.0

    def _determine_fcf_quality(self, record: CashFlowRecord) -> FCFQuality:
        """Determine FCF quality based on metrics."""
        if record.free_cash_flow < 0:
            return FCFQuality.NEGATIVE

        fcf_to_ni = record.fcf_to_net_income

        if fcf_to_ni > 1.1:
            return FCFQuality.EXCELLENT
        elif fcf_to_ni >= 0.8:
            return FCFQuality.GOOD
        elif fcf_to_ni >= 0.5:
            return FCFQuality.ACCEPTABLE
        else:
            return FCFQuality.POOR

    def _determine_fcf_trend(self, fcf_values: List[float]) -> FCFTrend:
        """Determine FCF trend over time."""
        if len(fcf_values) < 3:
            return FCFTrend.STABLE

        # Remove zeros and sort chronologically
        values = [v for v in fcf_values if v != 0]
        if len(values) < 3:
            return FCFTrend.STABLE

        # Check for consistent growth/decline
        increases = sum(1 for i in range(1, len(values)) if values[i] > values[i - 1])
        decreases = sum(1 for i in range(1, len(values)) if values[i] < values[i - 1])

        total = increases + decreases
        if total == 0:
            return FCFTrend.STABLE

        increase_ratio = increases / total

        if increase_ratio >= 0.7:
            return FCFTrend.IMPROVING
        elif increase_ratio <= 0.3:
            return FCFTrend.DECLINING
        elif 0.4 <= increase_ratio <= 0.6:
            return FCFTrend.STABLE
        else:
            return FCFTrend.VOLATILE
