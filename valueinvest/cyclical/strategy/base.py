"""
Base class for cyclical stock investment strategies.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from ..base import CyclicalStock, StrategyRecommendation, Checklist, CyclicalAnalysisResult


class BaseCyclicalStrategy(ABC):
    """周期股投资策略基类"""

    strategy_name: str = "Base Cyclical Strategy"

    @abstractmethod
    def generate_recommendation(
        self, stock: CyclicalStock, analysis: CyclicalAnalysisResult
    ) -> StrategyRecommendation:
        """
        生成投资建议

        Args:
            stock: 周期股数据
            analysis: 分析结果

        Returns:
            StrategyRecommendation: 策略建议
        """
        pass

    @abstractmethod
    def get_buy_checklist(self, stock: CyclicalStock) -> Checklist:
        """
        获取买入清单

        Args:
            stock: 周期股数据

        Returns:
            Checklist: 买入清单
        """
        pass

    @abstractmethod
    def get_sell_checklist(self, stock: CyclicalStock) -> Checklist:
        """
        获取卖出清单

        Args:
            stock: 周期股数据

        Returns:
            Checklist: 卖出清单
        """
        pass
