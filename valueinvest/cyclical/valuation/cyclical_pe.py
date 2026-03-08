"""
Cyclical PE Valuation - Price-to-Earnings valuation adjusted for cycle using normalized earnings.
"""
import statistics
from typing import Dict, Any, List, Optional
from .base import BaseCyclicalValuation
from ..base import CyclicalStock, ValuationResult
from ..enums import MarketType


class CyclicalPEValuation(BaseCyclicalValuation):
    """
    周期调整PE估值

    使用周期调整后的利润（3-5年平均EPS）来计算PE，避免周期顶点低PE陷阱：
    - 周期顶点：当前PE可能很低（5x），但利润即将暴跌
    - 周期底部：当前PE可能很高（50x），但利润即将恢复

    特点：
    1. 使用3-5年平均EPS计算周期调整PE
    2. A股和美股使用不同的阈值
    3. 结合ROE趋势判断
    """

    method_name = "Cyclical PE"

    # A股PE阈值
    A_SHARE_THRESHOLDS = {
        "buy": 12.0,  # 买入阈值
        "fair": 15.0,  # 合理估值
        "sell": 20.0,  # 卖出阈值
    }

    # 美股PE阈值（更保守）
    US_THRESHOLDS = {
        "buy": 10.0,
        "fair": 13.0,
        "sell": 16.0,
    }

    def calculate(self, stock: CyclicalStock) -> ValuationResult:
        """
        计算周期调整PE估值

        Args:
            stock: 周期股数据

        Returns:
            ValuationResult: 估值结果
        """
        # 数据验证
        if stock.eps <= 0:
            return self._create_error_result(stock, "EPS must be positive")

        if stock.current_price <= 0:
            return self._create_error_result(stock, "Current price must be positive")

        # 获取阈值
        thresholds = (
            self.A_SHARE_THRESHOLDS if stock.market == MarketType.A_SHARE else self.US_THRESHOLDS
        )

        # 计算周期调整PE
        cyclical_adjusted_pe = self._calculate_cyclical_adjusted_pe(stock)

        # 计算周期调整EPS
        cyclical_adjusted_eps = self._calculate_cyclical_adjusted_eps(stock)

        # 公允价值 = 周期调整EPS × 公允PE
        fair_value = cyclical_adjusted_eps * thresholds["fair"]

        # 评估
        assessment = self._assess_valuation(fair_value, stock.current_price, stock.market)

        # 行动建议
        action = self._determine_action(cyclical_adjusted_pe, thresholds)

        # 计算溢价/折价
        premium_discount = (
            ((fair_value - stock.current_price) / stock.current_price) * 100
            if stock.current_price > 0
            else 0
        )

        # 置信度
        confidence = self._assess_confidence(stock, cyclical_adjusted_eps)

        # 详细信息
        details = {
            "current_pe": stock.pe if stock.pe > 0 else stock.current_price / stock.eps,
            "cyclical_adjusted_pe": cyclical_adjusted_pe,
            "cyclical_adjusted_eps": cyclical_adjusted_eps,
            "current_eps": stock.eps,
            "fair_pe": thresholds["fair"],
            "buy_threshold": thresholds["buy"],
            "sell_threshold": thresholds["sell"],
            "pe_adjustment_factor": cyclical_adjusted_pe
            / (stock.pe if stock.pe > 0 else stock.current_price / stock.eps),
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

    def _calculate_cyclical_adjusted_pe(self, stock: CyclicalStock) -> float:
        """
        计算周期调整PE

        使用当前价格除以周期调整EPS

        Args:
            stock: 周期股数据

        Returns:
            float: 周期调整PE
        """
        cyclical_eps = self._calculate_cyclical_adjusted_eps(stock)

        if cyclical_eps <= 0:
            return 0.0

        return stock.current_price / cyclical_eps

    def _calculate_cyclical_adjusted_eps(self, stock: CyclicalStock) -> float:
        """
        计算周期调整EPS（3-5年平均）

        如果有历史ROE数据，使用ROE计算历史EPS
        否则使用当前EPS作为基准

        Args:
            stock: 周期股数据

        Returns:
            float: 周期调整EPS
        """
        # 如果已经有周期调整PE，直接使用
        if stock.cyclical_adjusted_pe > 0:
            return stock.current_price / stock.cyclical_adjusted_pe

        # 如果有历史ROE数据，计算历史EPS
        if stock.historical_roe and len(stock.historical_roe) >= 3:
            avg_roe = statistics.mean(stock.historical_roe)
            # EPS = ROE × BVPS
            cyclical_eps = (avg_roe / 100) * stock.bvps
            return cyclical_eps

        # 否则使用当前EPS（保守）
        return stock.eps

    def _determine_action(self, cyclical_adjusted_pe: float, thresholds: Dict[str, float]) -> str:
        """
        确定行动建议

        Args:
            cyclical_adjusted_pe: 周期调整PE
            thresholds: 阈值

        Returns:
            str: 行动建议
        """
        if cyclical_adjusted_pe <= 0:
            return "ERROR"

        if cyclical_adjusted_pe < thresholds["buy"]:
            return "STRONG_BUY"
        elif cyclical_adjusted_pe < thresholds["fair"]:
            return "BUY"
        elif cyclical_adjusted_pe < thresholds["sell"]:
            return "HOLD"
        else:
            return "SELL"

    def _assess_confidence(self, stock: CyclicalStock, cyclical_eps: float) -> str:
        """
        评估置信度

        Args:
            stock: 周期股数据
            cyclical_eps: 周期调整EPS

        Returns:
            str: 置信度
        """
        # 历史数据充分性
        has_sufficient_history = stock.historical_roe and len(stock.historical_roe) >= 5

        # EPS稳定性
        eps_reasonable = 0.5 * stock.eps <= cyclical_eps <= 2.0 * stock.eps

        if has_sufficient_history and eps_reasonable:
            return "High"
        elif has_sufficient_history or eps_reasonable:
            return "Medium"
        else:
            return "Low"

    def get_method_info(self) -> Dict[str, Any]:
        """获取方法信息"""
        info = super().get_method_info()
        info.update(
            {
                "best_for": [
                    "盈利波动的周期股",
                    "有历史ROE数据的公司",
                    "避免周期顶点低PE陷阱",
                ],
                "limitations": [
                    "需要历史ROE数据",
                    "不适用于亏损公司",
                    "不适用于负资产公司",
                ],
                "key_metrics": [
                    "周期调整PE",
                    "周期调整EPS",
                    "历史ROE平均",
                ],
                "warning": "避免周期顶点低PE陷阱：PE 5x看似便宜，但利润可能即将暴跌",
            }
        )
        return info
