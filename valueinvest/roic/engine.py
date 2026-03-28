"""Economic Profit Engine: combines ROIC and WACC analysis."""

from typing import List, Optional

from valueinvest.stock import Stock

from .base import EconomicProfitResult, ROICResult, WACCResult
from .roic import calculate_roic
from .wacc import calculate_wacc


class EconomicProfitEngine:
    """Analyzes whether a company creates or destroys economic value."""

    def __init__(
        self,
        beta: Optional[float] = None,
        risk_free_rate: Optional[float] = None,
        equity_risk_premium: float = 6.0,
        cost_of_equity_override: Optional[float] = None,
        cost_of_debt_override: Optional[float] = None,
        wacc_override: Optional[float] = None,
        invested_capital_override: Optional[float] = None,
    ):
        self.beta = beta
        self.risk_free_rate = risk_free_rate
        self.equity_risk_premium = equity_risk_premium
        self.cost_of_equity_override = cost_of_equity_override
        self.cost_of_debt_override = cost_of_debt_override
        self.wacc_override = wacc_override
        self.invested_capital_override = invested_capital_override

    def analyze(self, stock: Stock) -> EconomicProfitResult:
        """Run full ROIC vs WACC analysis.

        Args:
            stock: Stock instance with financial data

        Returns:
            EconomicProfitResult with ROIC, WACC, spread, and value creation analysis
        """
        # Calculate ROIC
        roic_result = calculate_roic(
            stock,
            invested_capital_override=self.invested_capital_override,
        )

        # Calculate WACC
        if self.wacc_override is not None:
            tax_rate = stock.tax_rate if stock.tax_rate > 0 else 25.0
            wacc_result = WACCResult(
                cost_of_equity=stock.cost_of_capital,
                cost_of_debt=0.0,
                equity_weight=1.0,
                debt_weight=0.0,
                wacc=self.wacc_override,
                beta_used=self.beta,
                risk_free_rate=self.risk_free_rate,
                equity_risk_premium=self.equity_risk_premium,
                tax_rate_used=tax_rate,
                method="Simplified (override)",
                confidence="Low",
            )
        else:
            wacc_result = calculate_wacc(
                stock,
                beta=self.beta,
                risk_free_rate=self.risk_free_rate,
                equity_risk_premium=self.equity_risk_premium,
                cost_of_equity_override=self.cost_of_equity_override,
                cost_of_debt_override=self.cost_of_debt_override,
            )

        # Calculate spread and economic profit
        spread = roic_result.roic - wacc_result.wacc
        economic_profit = roic_result.invested_capital * spread / 100
        economic_profit_margin = spread  # EP margin equals ROIC-WACC spread

        value_created = spread > 0

        # Years to double invested capital at the spread rate
        years_to_double = None
        if spread > 0:
            # Rule of 72: years = 72 / spread
            years_to_double = 72.0 / spread

        # Build analysis
        analysis = self._build_analysis(stock, roic_result, wacc_result, spread)

        # Collect warnings
        warnings = self._collect_warnings(stock, roic_result, wacc_result)

        return EconomicProfitResult(
            ticker=stock.ticker,
            roic_result=roic_result,
            wacc_result=wacc_result,
            roic_wacc_spread=spread,
            economic_profit=economic_profit,
            economic_profit_margin=economic_profit_margin,
            value_created=value_created,
            years_to_double=years_to_double,
            analysis=analysis,
            warnings=warnings,
        )

    def _build_analysis(
        self,
        stock: Stock,
        roic_result: ROICResult,
        wacc_result: WACCResult,
        spread: float,
    ) -> List[str]:
        lines = []

        if spread > 0:
            lines.append(
                f"{stock.ticker} is a value creator: ROIC ({roic_result.roic:.2f}%) "
                f"> WACC ({wacc_result.wacc:.2f}%), spread = {spread:+.2f}pp"
            )
            if roic_result.invested_capital > 0:
                ep = roic_result.invested_capital * spread / 100
                lines.append(f"Annual economic profit: {ep:,.0f}")
        elif spread < 0:
            lines.append(
                f"{stock.ticker} is a value destroyer: ROIC ({roic_result.roic:.2f}%) "
                f"< WACC ({wacc_result.wacc:.2f}%), spread = {spread:+.2f}pp"
            )
        else:
            lines.append(
                f"{stock.ticker} breaks even: ROIC = WACC = {roic_result.roic:.2f}%"
            )

        return lines

    def _collect_warnings(
        self,
        stock: Stock,
        roic_result: ROICResult,
        wacc_result: WACCResult,
    ) -> List[str]:
        warnings = []

        if roic_result.confidence == "Low":
            warnings.append("Low confidence in ROIC calculation due to data limitations")

        if wacc_result.confidence == "Low":
            warnings.append("Low confidence in WACC calculation")

        if roic_result.invested_capital <= 0:
            warnings.append("Invested capital is zero or negative; ROIC is not meaningful")

        if abs(roic_result.roic - wacc_result.wacc) < 1.0:
            warnings.append("ROIC and WACC are very close; value creation is marginal")

        return warnings
