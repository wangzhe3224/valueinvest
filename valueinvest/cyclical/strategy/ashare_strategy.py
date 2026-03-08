"""
A-Share Cyclical Stock Strategy - Trading-oriented approach for Chinese cyclical stocks.

A-share cyclical stocks are treated as trading instruments with high return potential
over 1-3 year holding periods. The focus is on cycle timing and high returns.
"""
from typing import Dict, Any
from .base import BaseCyclicalStrategy
from ..base import CyclicalStock, CyclicalAnalysisResult, StrategyRecommendation, Checklist
from ..enums import CyclePhase, InvestmentAction, InvestmentStrategy


class AShareCyclicalStrategy(BaseCyclicalStrategy):
    """
    A股周期股策略

    特点：
    1. 周期博弈工具（1-3年持有）
    2. 目标收益 +50-200%
    3. 高波动，需要精准择时
    4. 核心指标：PB、周期位置、股息率
    """

    # 仓位配置
    MAX_SINGLE_POSITION = 0.10  # 单只股票最大仓位 10%
    MAX_TOTAL_POSITION = 0.35  # 周期股总仓位 35%

    # 预期收益
    TARGET_RETURN = 0.50  # 目标收益 50%
    HOLDING_PERIOD = "1-3年"  # 持有周期

    def generate_recommendation(
        self, stock: CyclicalStock, analysis: CyclicalAnalysisResult
    ) -> StrategyRecommendation:
        """
        生成A股周期股投资建议

        Args:
            stock: 周期股数据
            analysis: 分析结果

        Returns:
            StrategyRecommendation: 策略建议
        """
        phase = stock.current_phase
        score = analysis.cycle_analysis.total_score

        # 决策矩阵
        if phase in [CyclePhase.BOTTOM, CyclePhase.LATE_DOWNSIDE]:
            if score < 2.0 and stock.pb < 1.0:
                action = InvestmentAction.STRONG_BUY
                allocation = self.MAX_SINGLE_POSITION
            elif score < 2.5 and stock.pb < 1.2:
                action = InvestmentAction.BUY
                allocation = 0.07
            else:
                action = InvestmentAction.HOLD
                allocation = 0.05

        elif phase == CyclePhase.EARLY_UPSIDE:
            if score < 2.5 and stock.pb < 1.5:
                action = InvestmentAction.BUY
                allocation = 0.07
            elif score < 3.0:
                action = InvestmentAction.HOLD
                allocation = 0.05
            else:
                action = InvestmentAction.WATCH
                allocation = 0.03

        elif phase == CyclePhase.MID_UPSIDE:
            action = InvestmentAction.HOLD
            allocation = 0.05

        elif phase == CyclePhase.LATE_UPSIDE:
            if stock.pb > 2.5:
                action = InvestmentAction.SELL
                allocation = 0.0
            else:
                action = InvestmentAction.REDUCE
                allocation = 0.03

        elif phase == CyclePhase.TOP:
            action = InvestmentAction.SELL
            allocation = 0.0

        elif phase == CyclePhase.EARLY_DOWNSIDE:
            action = InvestmentAction.SELL
            allocation = 0.0

        else:  # MID_DOWNSIDE
            action = InvestmentAction.WATCH
            allocation = 0.0

        # 计算目标价和止损价
        target_price = self._calculate_target_price(stock, analysis)
        stop_loss_price = self._calculate_stop_loss(stock)
        expected_return = (
            ((target_price - stock.current_price) / stock.current_price) * 100
            if stock.current_price > 0
            else 0
        )

        # 生成理由
        rationale = self._generate_rationale(stock, analysis, action)

        return StrategyRecommendation(
            action=action,
            target_allocation=allocation,
            target_price=target_price,
            stop_loss_price=stop_loss_price,
            expected_return=expected_return,
            holding_period=self.HOLDING_PERIOD,
            strategy_type=InvestmentStrategy.CYCLICAL_TRADING,
            dividend_yield=stock.dividend_yield,
            rationale=rationale,
        )

    def get_buy_checklist(self, stock: CyclicalStock) -> Checklist:
        """
        A股周期股买入清单

        Args:
            stock: 周期股数据

        Returns:
            Checklist: 买入清单
        """
        items = {
            "周期位置": stock.current_phase
            in [CyclePhase.BOTTOM, CyclePhase.EARLY_UPSIDE, CyclePhase.LATE_DOWNSIDE],
            "估值安全": stock.pb < 1.2,
            "资产质量": stock.debt_ratio < 0.60,
            "现金流": stock.fcf_to_net_income > 0.8,
            "分红能力": stock.dividend_yield > 0.03,
            "ROE水平": stock.roe > 5.0,
            "历史PB低位": (
                stock.historical_pb
                and stock.pb < sum(stock.historical_pb[-5:]) / len(stock.historical_pb[-5:]) * 0.8
                if stock.historical_pb and len(stock.historical_pb) >= 5
                else True
            ),
        }

        return Checklist(items=items)

    def get_sell_checklist(self, stock: CyclicalStock) -> Checklist:
        """
        A股周期股卖出清单

        Args:
            stock: 周期股数据

        Returns:
            Checklist: 卖出清单
        """
        items = {
            "周期位置": stock.current_phase in [CyclePhase.TOP, CyclePhase.EARLY_DOWNSIDE],
            "估值过高": stock.pb > 2.0,
            "ROE恶化": stock.roe < 5.0,
            "行业信号": stock.cycle_score.industry_score > 4.0 if stock.cycle_score else False,
            "市场情绪": stock.cycle_score.sentiment_score > 4.0 if stock.cycle_score else False,
        }

        return Checklist(items=items)

    def _calculate_target_price(
        self, stock: CyclicalStock, analysis: CyclicalAnalysisResult
    ) -> float:
        """
        计算目标价

        基于周期位置和估值水平

        Args:
            stock: 周期股数据
            analysis: 分析结果

        Returns:
            float: 目标价
        """
        # 基于PB估值
        if stock.current_phase in [CyclePhase.BOTTOM, CyclePhase.EARLY_UPSIDE]:
            target_pb = 1.8  # 目标PB 1.8x
        elif stock.current_phase == CyclePhase.MID_UPSIDE:
            target_pb = 1.5
        else:
            target_pb = 1.3

        return stock.bvps * target_pb

    def _calculate_stop_loss(self, stock: CyclicalStock) -> float:
        """
        计算止损价

        Args:
            stock: 周期股数据

        Returns:
            float: 止损价
        """
        # PB 0.7x 作为止损
        return stock.bvps * 0.7

    def _generate_rationale(
        self, stock: CyclicalStock, analysis: CyclicalAnalysisResult, action: InvestmentAction
    ) -> list:
        """
        生成投资理由

        Args:
            stock: 周期股数据
            analysis: 分析结果
            action: 投资行动

        Returns:
            list: 理由列表
        """
        rationale = []

        # 周期位置
        rationale.append(f"周期阶段：{stock.current_phase.display_name}")

        # 估值水平
        if stock.pb < 1.0:
            rationale.append(f"PB {stock.pb:.2f}x，低于净资产，安全边际高")
        elif stock.pb < 1.5:
            rationale.append(f"PB {stock.pb:.2f}x，估值合理偏低")

        # 财务质量
        if stock.debt_ratio < 0.5:
            rationale.append(f"负债率 {stock.debt_ratio:.1%}，财务健康")

        # 分红
        if stock.dividend_yield > 0.04:
            rationale.append(f"股息率 {stock.dividend_yield:.1%}，提供安全垫")

        # 行动建议
        if action == InvestmentAction.STRONG_BUY:
            rationale.append("强烈买入：周期底部+低估值+高质量")
        elif action == InvestmentAction.BUY:
            rationale.append("买入：周期上行初期，估值合理")
        elif action == InvestmentAction.HOLD:
            rationale.append("持有：等待周期进一步明朗")
        elif action == InvestmentAction.REDUCE:
            rationale.append("减仓：周期接近顶点，锁定部分收益")
        elif action == InvestmentAction.SELL:
            rationale.append("卖出：周期见顶或下行，规避风险")

        return rationale
