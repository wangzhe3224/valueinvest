"""
Base class for cyclical stock valuation methods.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from ..base import CyclicalStock, ValuationResult
from ..enums import MarketType


class BaseCyclicalValuation(ABC):
    """周期股估值基类"""

    method_name: str = "Base Cyclical"

    @abstractmethod
    def calculate(self, stock: CyclicalStock) -> ValuationResult:
        """
        计算估值

        Args:
            stock: 周期股数据

        Returns:
            ValuationResult: 估值结果
        """
        pass

    def _assess_valuation(self, fair_value: float, current_price: float, market: MarketType) -> str:
        """
        评估估值水平

        Args:
            fair_value: 公允价值
            current_price: 当前价格
            market: 市场类型

        Returns:
            str: 评估结果（Undervalued, Fair, Overvalued）
        """
        if fair_value <= 0 or current_price <= 0:
            return "N/A"

        if market == MarketType.A_SHARE:
            # A股：更激进的阈值
            threshold_high = 0.20
            threshold_low = -0.20
        else:
            # 美股：更保守的阈值
            threshold_high = 0.15
            threshold_low = -0.15

        premium = ((fair_value - current_price) / current_price) * 100

        if premium > threshold_high * 100:
            return "Undervalued"
        elif premium < threshold_low * 100:
            return "Overvalued"
        else:
            return "Fair"

    def _create_error_result(self, stock: CyclicalStock, reason: str) -> ValuationResult:
        """
        创建错误结果

        Args:
            stock: 周期股数据
            reason: 错误原因

        Returns:
            ValuationResult: 错误结果
        """
        return ValuationResult(
            method=self.method_name,
            fair_value=0,
            current_value=stock.current_price,
            premium_discount=0,
            assessment="N/A",
            action="ERROR",
            confidence="N/A",
            details={"error": reason},
        )

    def get_method_info(self) -> Dict[str, Any]:
        """
        获取方法信息

        Returns:
            Dict: 方法信息
        """
        return {
            "method": self.method_name,
            "description": self.__doc__ or "",
        }
