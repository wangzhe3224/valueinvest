"""
Cyclical FCF Valuation - Free Cash Flow valuation for cyclical stocks.
"""
import statistics
from typing import Dict, Any
from .base import BaseCyclicalValuation
from ..base import CyclicalStock, ValuationResult
from ..enums import MarketType


class CyclicalFCFValuation(BaseCyclicalValuation):
    """
    周期调整FCF估值

    使用自由现金流收益率来评估周期股：
    - FCF Yield = FCF / Market Cap
    - 周期底部：FCF Yield > 10% 为低估
    - 周期顶点：FCF Yield < 5% 为高估

    特点：
    1. 关注现金流而非利润（更难操纵）
    2. A股和美股使用不同阈值
    3. 结合FCF质量（FCF/净利润）
    """

    method_name = "Cyclical FCF"

    # FCF收益率阈值
    A_SHARE_THRESHOLDS = {
        "buy": 10.0,  # 买入阈值：FCF Yield > 10%
        "fair": 7.0,  # 合理估值：FCF Yield ~ 7%
        "sell": 5.0,  # 卖出阈值：FCF Yield < 5%
    }

    US_THRESHOLDS = {
        "buy": 12.0,
        "fair": 8.0,
        "sell": 6.0,
    }

    def calculate(self, stock: CyclicalStock) -> ValuationResult:
        """
        计算周期调整FCF估值

        Args:
            stock: 周期股数据

        Returns:
            ValuationResult: 估值结果
        """
        # 数据验证
        if stock.fcf_yield <= 0:
            return self._create_error_result(stock, "FCF yield must be positive")

        if stock.current_price <= 0:
            return self._create_error_result(stock, "Current price must be positive")

        # 获取阈值
        thresholds = (
            self.A_SHARE_THRESHOLDS if stock.market == MarketType.A_SHARE else self.US_THRESHOLDS
        )

        # 计算公允FCF收益率
        fair_fcf_yield = thresholds["fair"]

        # 计算公允价值
        # FCF Yield = FCF / Market Cap
        # Market Cap = FCF / FCF Yield
        # Price = (FCF / FCF Yield) / Shares = FCF per Share / FCF Yield

        if stock.fcf_per_share > 0:
            fair_value = stock.fcf_per_share / (fair_fcf_yield / 100)
        else:
            # 使用市值倒推
            if stock.fcf_yield > 0:
                implied_fcf = stock.market_cap * (stock.fcf_yield / 100)
                fair_market_cap = implied_fcf / (fair_fcf_yield / 100)
                fair_value = fair_market_cap / (stock.market_cap / stock.current_price)
            else:
                return self._create_error_result(stock, "Cannot calculate fair value")

        # 评估
        assessment = self._assess_valuation(fair_value, stock.current_price, stock.market)

        # 行动建议
        action = self._determine_action(stock.fcf_yield, thresholds)

        # 计算溢价/折价
        premium_discount = (
            ((fair_value - stock.current_price) / stock.current_price) * 100
            if stock.current_price > 0
            else 0
        )

        # 置信度
        confidence = self._assess_confidence(stock)

        # 详细信息
        details = {
            "fcf_yield": stock.fcf_yield,
            "fair_fcf_yield": fair_fcf_yield,
            "fcf_per_share": stock.fcf_per_share,
            "fcf_to_net_income": stock.fcf_to_net_income,
            "fcf_quality": self._assess_fcf_quality(stock),
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

    def _determine_action(self, fcf_yield: float, thresholds: Dict[str, float]) -> str:
        """
        确定行动建议

        Args:
            fcf_yield: FCF收益率
            thresholds: 阈值

        Returns:
            str: 行动建议
        """
        if fcf_yield >= thresholds["buy"]:
            return "STRONG_BUY"
        elif fcf_yield >= thresholds["fair"]:
            return "BUY"
        elif fcf_yield > thresholds["sell"]:
            return "HOLD"
        else:
            return "SELL"

    def _assess_fcf_quality(self, stock: CyclicalStock) -> str:
        """
        评估FCF质量

        Args:
            stock: 周期股数据

        Returns:
            str: FCF质量评级
        """
        if stock.fcf_to_net_income >= 1.2:
            return "Excellent"
        elif stock.fcf_to_net_income >= 1.0:
            return "Good"
        elif stock.fcf_to_net_income >= 0.8:
            return "Acceptable"
        else:
            return "Poor"

    def _assess_confidence(self, stock: CyclicalStock) -> str:
        """
        评估置信度

        Args:
            stock: 周期股数据

        Returns:
            str: 置信度
        """
        # FCF质量
        fcf_quality = stock.fcf_to_net_income >= 1.0

        # 历史数据
        has_history = stock.historical_fcf_yield and len(stock.historical_fcf_yield) >= 3

        if fcf_quality and has_history:
            return "High"
        elif fcf_quality or has_history:
            return "Medium"
        else:
            return "Low"

    def get_method_info(self) -> Dict[str, Any]:
        """获取方法信息"""
        info = super().get_method_info()
        info.update(
            {
                "best_for": [
                    "现金流稳定的周期股",
                    "资本密集型行业",
                    "需要避免利润操纵的情况",
                ],
                "limitations": [
                    "不适用于负FCF公司",
                    "资本开支波动大的公司需要谨慎",
                ],
                "key_metrics": [
                    "FCF Yield（自由现金流收益率）",
                    "FCF / Net Income（现金流质量）",
                    "FCF per Share（每股自由现金流）",
                ],
            }
        )
        return info
