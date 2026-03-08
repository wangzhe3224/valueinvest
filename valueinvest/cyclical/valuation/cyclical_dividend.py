"""
Cyclical Dividend Valuation - Dividend-focused valuation for cyclical stocks.
"""
from typing import Dict, Any
from .base import BaseCyclicalValuation
from ..base import CyclicalStock, ValuationResult
from ..enums import MarketType


class CyclicalDividendValuation(BaseCyclicalValuation):
    """
    周期股股息估值

    主要用于美股周期股的收息防御策略：
    - 评估分红可持续性
    - 计算合理股息率
    - 结合总股东收益率（股息+回购）

    特点：
    1. 重点关注分红可持续性（FCF覆盖率）
    2. 美股更关注总股东收益率
    3. A股关注股息率与周期的关系
    """

    method_name = "Cyclical Dividend"

    # 股息率阈值
    A_SHARE_THRESHOLDS = {
        "buy": 6.0,  # 买入阈值：股息率 > 6%
        "fair": 4.0,  # 合理估值：股息率 ~ 4%
        "sell": 2.0,  # 卖出阈值：股息率 < 2%
    }

    US_THRESHOLDS = {
        "buy": 5.0,
        "fair": 3.5,
        "sell": 2.0,
    }

    # 分红比例阈值
    PAYOUT_RATIO_THRESHOLDS = {
        "safe": 0.60,  # 安全：分红比例 < 60%
        "moderate": 0.80,  # 中等：分红比例 60-80%
        "high": 1.00,  # 高：分红比例 > 80%
    }

    def calculate(self, stock: CyclicalStock) -> ValuationResult:
        """
        计算周期股股息估值

        Args:
            stock: 周期股数据

        Returns:
            ValuationResult: 估值结果
        """
        # 数据验证
        if stock.dividend_yield <= 0:
            return self._create_error_result(stock, "Dividend yield must be positive")

        if stock.current_price <= 0:
            return self._create_error_result(stock, "Current price must be positive")

        # 获取阈值
        thresholds = (
            self.A_SHARE_THRESHOLDS if stock.market == MarketType.A_SHARE else self.US_THRESHOLDS
        )

        # 评估分红可持续性
        sustainability = self._assess_dividend_sustainability(stock)

        # 计算公允股息率
        fair_dividend_yield = self._calculate_fair_dividend_yield(stock, thresholds)

        # 计算公允价值
        # Dividend Yield = DPS / Price
        # Price = DPS / Dividend Yield
        if stock.dividend_yield > 0:
            # 从股息率倒推DPS
            dps = stock.current_price * (stock.dividend_yield / 100)
            fair_value = dps / (fair_dividend_yield / 100)
        else:
            return self._create_error_result(stock, "Cannot calculate fair value")

        # 评估
        assessment = self._assess_valuation(fair_value, stock.current_price, stock.market)

        # 行动建议
        action = self._determine_action(stock.dividend_yield, sustainability, thresholds)

        # 计算溢价/折价
        premium_discount = (
            ((fair_value - stock.current_price) / stock.current_price) * 100
            if stock.current_price > 0
            else 0
        )

        # 置信度
        confidence = self._assess_confidence(stock, sustainability)

        # 详细信息
        details = {
            "dividend_yield": stock.dividend_yield,
            "fair_dividend_yield": fair_dividend_yield,
            "payout_ratio": stock.payout_ratio,
            "sustainability": sustainability,
            "fcf_coverage": stock.fcf_to_net_income / stock.payout_ratio
            if stock.payout_ratio > 0
            else 0,
            "consecutive_years": stock.consecutive_dividend_years,
            "dividend_growth": stock.dividend_growth_rate,
            "buy_threshold": thresholds["buy"],
            "sell_threshold": thresholds["sell"],
        }

        return ValuationResult(
            method=self.method_name,
            fair_value=fair_value,
            current_value=stock.current_price,
            premium_discount=premium_discount,
            assessment=assessment,
            action=action,
            confidence=confidence,
            details=details,
        )

    def _assess_dividend_sustainability(self, stock: CyclicalStock) -> str:
        """
        评估分红可持续性

        Args:
            stock: 周期股数据

        Returns:
            str: 可持续性评级（High, Medium, Low）
        """
        # 分红比例
        payout_ratio = stock.payout_ratio

        # FCF覆盖率
        fcf_coverage = stock.fcf_to_net_income / payout_ratio if payout_ratio > 0 else 0

        # 分红历史
        has_history = stock.consecutive_dividend_years >= 5

        # 综合判断
        if payout_ratio < self.PAYOUT_RATIO_THRESHOLDS["safe"] and fcf_coverage > 1.5:
            return "High"
        elif payout_ratio < self.PAYOUT_RATIO_THRESHOLDS["moderate"] and fcf_coverage > 1.0:
            return "Medium"
        elif has_history and payout_ratio < self.PAYOUT_RATIO_THRESHOLDS["high"]:
            return "Medium"
        else:
            return "Low"

    def _calculate_fair_dividend_yield(
        self, stock: CyclicalStock, thresholds: Dict[str, float]
    ) -> float:
        """
        计算公允股息率

        基于分红可持续性和周期位置调整

        Args:
            stock: 周期股数据
            thresholds: 阈值

        Returns:
            float: 公允股息率
        """
        base_yield = thresholds["fair"]

        # 根据分红可持续性调整
        sustainability = self._assess_dividend_sustainability(stock)
        if sustainability == "High":
            adjustment = -0.5  # 可持续性好，接受更低股息率
        elif sustainability == "Low":
            adjustment = 1.0  # 可持续性差，要求更高股息率
        else:
            adjustment = 0.0

        return base_yield + adjustment

    def _determine_action(
        self, dividend_yield: float, sustainability: str, thresholds: Dict[str, float]
    ) -> str:
        """
        确定行动建议

        Args:
            dividend_yield: 股息率
            sustainability: 可持续性
            thresholds: 阈值

        Returns:
            str: 行动建议
        """
        # 分红不可持续，不建议买入
        if sustainability == "Low":
            if dividend_yield > thresholds["buy"]:
                return "HOLD"  # 高股息但不可持续，持有观望
            else:
                return "SELL"

        # 分红可持续
        if dividend_yield >= thresholds["buy"]:
            return "STRONG_BUY"
        elif dividend_yield >= thresholds["fair"]:
            return "BUY"
        elif dividend_yield > thresholds["sell"]:
            return "HOLD"
        else:
            return "REDUCE"

    def _assess_confidence(self, stock: CyclicalStock, sustainability: str) -> str:
        """
        评估置信度

        Args:
            stock: 周期股数据
            sustainability: 可持续性

        Returns:
            str: 置信度
        """
        # 分红历史
        has_history = stock.consecutive_dividend_years >= 5

        # FCF数据
        has_fcf_data = stock.fcf_to_net_income > 0

        if sustainability == "High" and has_history and has_fcf_data:
            return "High"
        elif has_history or has_fcf_data:
            return "Medium"
        else:
            return "Low"

    def get_method_info(self) -> Dict[str, Any]:
        """获取方法信息"""
        info = super().get_method_info()
        info.update(
            {
                "best_for": [
                    "分红稳定的成熟周期股",
                    "美股收息防御策略",
                    "追求稳定现金流的投资者",
                ],
                "limitations": [
                    "不适用于不分红公司",
                    "分红可能被削减",
                    "周期下行时股息率波动大",
                ],
                "key_metrics": [
                    "Dividend Yield（股息率）",
                    "Payout Ratio（分红比例）",
                    "FCF Coverage（FCF覆盖率）",
                    "Consecutive Dividend Years（连续分红年数）",
                ],
                "warning": "警惕周期顶点的高股息陷阱：股息率10%可能是因为股价暴跌",
            }
        )
        return info
