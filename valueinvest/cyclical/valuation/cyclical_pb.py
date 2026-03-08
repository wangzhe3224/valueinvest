"""
Cyclical PB Valuation - Price-to-Book valuation adjusted for cycle position.
"""
import statistics
from typing import Dict, Any, Optional
from .base import BaseCyclicalValuation
from ..base import CyclicalStock, ValuationResult
from ..enums import CyclePhase, MarketType


class CyclicalPBValuation(BaseCyclicalValuation):
    """
    周期调整PB估值

    根据周期阶段动态调整PB估值阈值：
    - 周期底部：PB < 1.0x 为低估
    - 周期上行：PB < 1.5x 可买入
    - 周期顶点：PB > 2.0x 应卖出

    特点：
    1. 使用历史PB中位数作为公允PB
    2. 根据周期阶段调整买入/卖出阈值
    3. A股和美股使用不同的阈值体系
    """

    method_name = "Cyclical PB"

    # A股不同周期阶段的PB阈值
    A_SHARE_THRESHOLDS = {
        CyclePhase.BOTTOM: {"buy": 1.0, "hold": 1.5, "sell": 2.0},
        CyclePhase.LATE_DOWNSIDE: {"buy": 1.0, "hold": 1.5, "sell": 2.0},
        CyclePhase.EARLY_UPSIDE: {"buy": 1.2, "hold": 1.8, "sell": 2.2},
        CyclePhase.MID_UPSIDE: {"buy": 1.5, "hold": 2.0, "sell": 2.5},
        CyclePhase.LATE_UPSIDE: {"buy": 1.8, "hold": 2.2, "sell": 2.8},
        CyclePhase.TOP: {"buy": 2.0, "hold": 2.5, "sell": 3.0},
        CyclePhase.EARLY_DOWNSIDE: {"buy": 1.8, "hold": 2.2, "sell": 2.5},
        CyclePhase.MID_DOWNSIDE: {"buy": 1.5, "hold": 1.8, "sell": 2.0},
    }

    # 美股不同周期阶段的PB阈值（更保守）
    US_THRESHOLDS = {
        CyclePhase.BOTTOM: {"buy": 1.0, "hold": 1.3, "sell": 1.5},
        CyclePhase.LATE_DOWNSIDE: {"buy": 1.0, "hold": 1.3, "sell": 1.5},
        CyclePhase.EARLY_UPSIDE: {"buy": 1.1, "hold": 1.4, "sell": 1.6},
        CyclePhase.MID_UPSIDE: {"buy": 1.2, "hold": 1.5, "sell": 1.7},
        CyclePhase.LATE_UPSIDE: {"buy": 1.3, "hold": 1.6, "sell": 1.8},
        CyclePhase.TOP: {"buy": 1.4, "hold": 1.7, "sell": 2.0},
        CyclePhase.EARLY_DOWNSIDE: {"buy": 1.3, "hold": 1.6, "sell": 1.8},
        CyclePhase.MID_DOWNSIDE: {"buy": 1.2, "hold": 1.5, "sell": 1.6},
    }

    def calculate(self, stock: CyclicalStock) -> ValuationResult:
        """
        计算周期调整PB估值

        Args:
            stock: 周期股数据

        Returns:
            ValuationResult: 估值结果
        """
        # 数据验证
        if stock.bvps <= 0:
            return self._create_error_result(stock, "BVPS must be positive")

        if stock.pb <= 0:
            return self._create_error_result(stock, "PB must be positive")

        # 获取对应市场的阈值
        thresholds = (
            self.A_SHARE_THRESHOLDS if stock.market == MarketType.A_SHARE else self.US_THRESHOLDS
        )

        # 获取当前周期阶段的阈值
        phase_thresholds = thresholds.get(stock.current_phase, thresholds[CyclePhase.MID_UPSIDE])

        # 计算公允PB（基于历史PB中位数）
        fair_pb = self._calculate_fair_pb(stock, phase_thresholds)

        # 计算公允价值
        fair_value = stock.bvps * fair_pb
        current_value = stock.bvps * stock.pb

        # 评估
        assessment = self._assess_valuation(fair_value, stock.current_price, stock.market)

        # 行动建议
        action = self._determine_action(stock.pb, phase_thresholds)

        # 计算溢价/折价
        premium_discount = (
            ((fair_value - stock.current_price) / stock.current_price) * 100
            if stock.current_price > 0
            else 0
        )

        # 计算置信度
        confidence = self._assess_confidence(stock)

        # 详细信息
        details = {
            "current_pb": stock.pb,
            "fair_pb": fair_pb,
            "bvps": stock.bvps,
            "cycle_phase": stock.current_phase.value,
            "buy_threshold": phase_thresholds["buy"],
            "hold_threshold": phase_thresholds["hold"],
            "sell_threshold": phase_thresholds["sell"],
            "historical_pb_avg": statistics.mean(stock.historical_pb)
            if stock.historical_pb
            else None,
            "historical_pb_median": statistics.median(stock.historical_pb)
            if stock.historical_pb
            else None,
        }

        return ValuationResult(
            method=self.method_name,
            fair_value=fair_value,
            current_value=current_value,
            premium_discount=premium_discount,
            assessment=assessment,
            action=action,
            confidence=confidence,
            details=details,
        )

    def _calculate_fair_pb(self, stock: CyclicalStock, phase_thresholds: Dict[str, float]) -> float:
        """
        计算公允PB

        优先使用历史PB中位数，如果没有历史数据则使用周期阶段阈值

        Args:
            stock: 周期股数据
            phase_thresholds: 周期阶段阈值

        Returns:
            float: 公允PB
        """
        if stock.historical_pb and len(stock.historical_pb) >= 3:
            # 使用历史PB中位数
            return statistics.median(stock.historical_pb)
        else:
            # 使用hold阈值作为公允PB
            return phase_thresholds["hold"]

    def _determine_action(self, current_pb: float, phase_thresholds: Dict[str, float]) -> str:
        """
        确定行动建议

        Args:
            current_pb: 当前PB
            phase_thresholds: 周期阶段阈值

        Returns:
            str: 行动建议
        """
        if current_pb < phase_thresholds["buy"]:
            return "STRONG_BUY"
        elif current_pb < phase_thresholds["hold"]:
            return "BUY"
        elif current_pb < phase_thresholds["sell"]:
            return "HOLD"
        else:
            return "SELL"

    def _assess_confidence(self, stock: CyclicalStock) -> str:
        """
        评估置信度

        基于历史数据的完整性和周期判断的确定性

        Args:
            stock: 周期股数据

        Returns:
            str: 置信度
        """
        confidence = "Medium"

        # 历史数据充分性
        if stock.historical_pb and len(stock.historical_pb) >= 5:
            confidence = "High"
        elif not stock.historical_pb or len(stock.historical_pb) < 3:
            confidence = "Low"

        # 周期判断确定性
        if stock.cycle_score:
            if stock.cycle_score.confidence == "High":
                # 保持或提升
                pass
            elif stock.cycle_score.confidence == "Low":
                # 降级
                if confidence == "High":
                    confidence = "Medium"
                else:
                    confidence = "Low"

        return confidence

    def get_method_info(self) -> Dict[str, Any]:
        """获取方法信息"""
        info = super().get_method_info()
        info.update(
            {
                "best_for": [
                    "重资产行业（钢铁、航运、有色）",
                    "周期性行业",
                    "资产质量稳定的公司",
                ],
                "limitations": [
                    "不适用于轻资产公司",
                    "不适用于负资产公司",
                    "需要历史PB数据支持",
                ],
                "key_metrics": [
                    "PB（市净率）",
                    "BVPS（每股净资产）",
                    "历史PB分位",
                ],
            }
        )
        return info
