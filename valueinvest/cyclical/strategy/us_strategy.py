"""
US Cyclical Stock Strategy - Dividend-defensive approach for US cyclical stocks.

US cyclical stocks are treated as income instruments with stable returns over 5-10 year
holding periods. The focus is on dividend sustainability and total shareholder yield.
"""
from typing import Dict, Any
from .base import BaseCyclicalStrategy
from ..base import CyclicalStock, CyclicalAnalysisResult, StrategyRecommendation, Checklist
from ..enums import CyclePhase, InvestmentAction, InvestmentStrategy


class USCyclicalStrategy(BaseCyclicalStrategy):
    """
    美股周期股策略

    特点：
    1. 收息防御工具（5-10年持有）
    2. 目标收益 6-10%/年（股息+增长）
    3. 低波动，长期复利
    4. 核心指标：P/FCF、股息可持续性、护城河
    """

    # 仓位配置
    MAX_SINGLE_POSITION = 0.08  # 单只股票最大仓位 8%
    MAX_TOTAL_POSITION = 0.25  # 周期股总仓位 25%

    # 预期收益
    TARGET_DIVIDEND_YIELD = 0.04  # 目标股息率 4%
    TARGET_RETURN = 0.08  # 目标总收益 8%/年
    HOLDING_PERIOD = "5-10年"  # 持有周期

    def generate_recommendation(
        self, stock: CyclicalStock, analysis: CyclicalAnalysisResult
    ) -> StrategyRecommendation:
        """
        生成美股周期股投资建议

        Args:
            stock: 周期股数据
            analysis: 分析结果

        Returns:
            StrategyRecommendation: 策略建议
        """
        # 分红可持续性评分
        dividend_score = self._assess_dividend_sustainability(stock)

        # 估值评分
        valuation_score = self._assess_valuation(stock)

        # 综合评分
        total_score = dividend_score * 0.6 + valuation_score * 0.4

        # 决策矩阵
        if total_score >= 4.0 and stock.fcf_yield > 0.10:
            action = InvestmentAction.BUY
            allocation = self.MAX_SINGLE_POSITION
        elif total_score >= 3.5:
            action = InvestmentAction.BUY
            allocation = 0.06
        elif total_score >= 3.0:
            action = InvestmentAction.HOLD
            allocation = 0.05
        elif total_score >= 2.5:
            action = InvestmentAction.HOLD
            allocation = 0.03
        elif total_score < 2.0:
            action = InvestmentAction.SELL
            allocation = 0.0
        else:
            action = InvestmentAction.REDUCE
            allocation = 0.02

        # 如果分红削减风险高，立即卖出
        if dividend_score < 2.0:
            action = InvestmentAction.SELL
            allocation = 0.0

        # 计算目标价
        target_price = self._calculate_target_price(stock)

        # 止损价（美股策略不太强调止损，但设置一个底线）
        stop_loss_price = stock.current_price * 0.7

        # 预期收益
        expected_return = self.TARGET_RETURN * 100  # 转换为百分比

        # 估算总股东收益率
        total_shareholder_yield = self._estimate_total_shareholder_yield(stock)

        # 生成理由
        rationale = self._generate_rationale(
            stock, analysis, action, dividend_score, valuation_score
        )

        return StrategyRecommendation(
            action=action,
            target_allocation=allocation,
            target_price=target_price,
            stop_loss_price=stop_loss_price,
            expected_return=expected_return,
            holding_period=self.HOLDING_PERIOD,
            strategy_type=InvestmentStrategy.DIVIDEND_DEFENSIVE,
            dividend_yield=stock.dividend_yield,
            total_shareholder_yield=total_shareholder_yield,
            expected_annual_return=self.TARGET_RETURN,
            rationale=rationale,
        )

    def get_buy_checklist(self, stock: CyclicalStock) -> Checklist:
        """
        美股周期股买入清单

        Args:
            stock: 周期股数据

        Returns:
            Checklist: 买入清单
        """
        items = {
            "分红历史": stock.consecutive_dividend_years >= 5,
            "分红可持续": stock.debt_ratio < 0.60 and stock.fcf_to_net_income > 1.5,
            "FCF覆盖率": stock.fcf_to_net_income > 1.5,
            "负债率": stock.debt_ratio < 0.50,
            "估值合理": stock.fcf_yield > 0.08,
            "周期位置": stock.current_phase not in [CyclePhase.TOP, CyclePhase.EARLY_DOWNSIDE],
            "利息覆盖": stock.interest_coverage > 5.0 if stock.interest_coverage > 0 else True,
        }

        return Checklist(items=items)

    def get_sell_checklist(self, stock: CyclicalStock) -> Checklist:
        """
        美股周期股卖出清单

        Args:
            stock: 周期股数据

        Returns:
            Checklist: 卖出清单
        """
        items = {
            "分红削减": False,  # 需要监控，如果为True立即卖出
            "FCF恶化": stock.fcf_to_net_income < 1.0,
            "估值极端": stock.fcf_yield < 0.05,
            "负债恶化": stock.debt_ratio > 0.60,
            "利息覆盖恶化": stock.interest_coverage < 3.0 if stock.interest_coverage > 0 else False,
        }

        return Checklist(items=items)

    def _assess_dividend_sustainability(self, stock: CyclicalStock) -> float:
        """
        评估分红可持续性（1.0-5.0）

        Args:
            stock: 周期股数据

        Returns:
            float: 分红可持续性得分
        """
        score = 3.0

        # 分红比例
        payout_ratio = stock.payout_ratio
        if payout_ratio < 0.4:
            score += 1.0
        elif payout_ratio < 0.6:
            score += 0.5
        elif payout_ratio > 0.8:
            score -= 1.0

        # FCF覆盖
        fcf_coverage = stock.fcf_to_net_income / payout_ratio if payout_ratio > 0 else 0
        if fcf_coverage > 2.0:
            score += 0.5
        elif fcf_coverage < 1.0:
            score -= 1.0

        # 分红历史
        if stock.consecutive_dividend_years >= 10:
            score += 0.5
        elif stock.consecutive_dividend_years < 3:
            score -= 0.5

        # 负债率
        if stock.debt_ratio < 0.4:
            score += 0.5
        elif stock.debt_ratio > 0.6:
            score -= 0.5

        return max(min(score, 5.0), 1.0)

    def _assess_valuation(self, stock: CyclicalStock) -> float:
        """
        评估估值（1.0-5.0）

        Args:
            stock: 周期股数据

        Returns:
            float: 估值得分
        """
        score = 3.0

        # P/FCF（隐含的FCF yield）
        if stock.fcf_yield > 0.12:
            score += 1.5
        elif stock.fcf_yield > 0.10:
            score += 1.0
        elif stock.fcf_yield > 0.08:
            score += 0.5
        elif stock.fcf_yield < 0.05:
            score -= 1.5
        elif stock.fcf_yield < 0.06:
            score -= 1.0

        # 股息率
        if stock.dividend_yield > 5.0:
            score += 0.5
        elif stock.dividend_yield < 2.0:
            score -= 0.5

        # PB（美股不太看重PB，但作为参考）
        if stock.pb < 1.5:
            score += 0.3

        return max(min(score, 5.0), 1.0)

    def _calculate_target_price(self, stock: CyclicalStock) -> float:
        """
        计算目标价

        基于公允FCF收益率

        Args:
            stock: 周期股数据

        Returns:
            float: 目标价
        """
        # 目标FCF收益率 8%
        target_fcf_yield = 0.08

        if stock.fcf_per_share > 0:
            return stock.fcf_per_share / target_fcf_yield
        else:
            # 使用当前价格作为基准
            return stock.current_price * 1.2  # 保守估计 20% 上涨空间

    def _estimate_total_shareholder_yield(self, stock: CyclicalStock) -> float:
        """
        估算总股东收益率（股息+回购）

        Args:
            stock: 周期股数据

        Returns:
            float: 总股东收益率（%）
        """
        # 股息率
        dividend_yield = stock.dividend_yield

        # 估算回购收益率（需要从buyback模块获取，这里简化处理）
        # 假设回购收益率为股息率的50%
        estimated_buyback_yield = dividend_yield * 0.5

        return dividend_yield + estimated_buyback_yield

    def _generate_rationale(
        self,
        stock: CyclicalStock,
        analysis: CyclicalAnalysisResult,
        action: InvestmentAction,
        dividend_score: float,
        valuation_score: float,
    ) -> list:
        """
        生成投资理由

        Args:
            stock: 周期股数据
            analysis: 分析结果
            action: 投资行动
            dividend_score: 分红可持续性得分
            valuation_score: 估值得分

        Returns:
            list: 理由列表
        """
        rationale = []

        # 分红可持续性
        if dividend_score >= 4.0:
            rationale.append(f"分红可持续性高（得分 {dividend_score:.1f}/5.0）")
        elif dividend_score >= 3.0:
            rationale.append(f"分红可持续性中等（得分 {dividend_score:.1f}/5.0）")
        else:
            rationale.append(f"分红可持续性低（得分 {dividend_score:.1f}/5.0），谨慎")

        # 估值水平
        if valuation_score >= 4.0:
            rationale.append(f"估值具有吸引力（FCF Yield {stock.fcf_yield:.1%}）")
        elif valuation_score >= 3.0:
            rationale.append(f"估值合理（FCF Yield {stock.fcf_yield:.1%}）")

        # 分红历史
        if stock.consecutive_dividend_years >= 10:
            rationale.append(f"连续分红 {stock.consecutive_dividend_years} 年，记录良好")

        # 财务质量
        if stock.debt_ratio < 0.4:
            rationale.append(f"负债率 {stock.debt_ratio:.1%}，财务稳健")

        # 总股东收益率
        total_yield = self._estimate_total_shareholder_yield(stock)
        rationale.append(f"总股东收益率约 {total_yield:.1%}（股息+回购）")

        # 行动建议
        if action == InvestmentAction.BUY:
            rationale.append("买入：分红可持续+估值合理+长期持有")
        elif action == InvestmentAction.HOLD:
            rationale.append("持有：继续享受股息收益")
        elif action == InvestmentAction.REDUCE:
            rationale.append("减仓：分红风险增加，降低仓位")
        elif action == InvestmentAction.SELL:
            rationale.append("卖出：分红削减风险高或估值极端")

        return rationale
