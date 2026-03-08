"""
Cycle Position Scorer - Determines where a stock is in its cycle.

This module implements a multi-dimensional scoring system to identify
cycle positions using quantitative, industry, and sentiment indicators.
"""
from typing import List, Dict, Optional
from .base import CycleScore, CycleIndicator
from .enums import CyclePhase, IndicatorCategory, MarketType
import statistics


class CyclePositionScorer:
    """
    周期位置评分器

    使用多维指标评估股票当前所处的周期位置：
    1. 估值指标（PB, PE, 股息率等）
    2. 财务指标（ROE, 负债率, 现金流等）
    3. 行业指标（价格、运价、开工率等）
    4. 情绪指标（市场关注度、分析师评级等）
    """

    # 指标权重配置（不同市场可以调整）
    A_SHARE_WEIGHTS = {
        "valuation": 0.30,  # 估值指标权重
        "financial": 0.20,  # 财务指标权重
        "industry": 0.35,  # 行业指标权重
        "sentiment": 0.15,  # 情绪指标权重
    }

    US_WEIGHTS = {
        "valuation": 0.35,  # 估值指标权重（美股更看重估值）
        "financial": 0.25,  # 财务指标权重
        "industry": 0.25,  # 行业指标权重
        "sentiment": 0.15,  # 情绪指标权重
    }

    def __init__(self, market: MarketType = MarketType.A_SHARE):
        """
        初始化评分器

        Args:
            market: 市场类型（A股或美股）
        """
        self.market = market
        self.weights = self.A_SHARE_WEIGHTS if market == MarketType.A_SHARE else self.US_WEIGHTS

        # 各维度指标列表
        self.valuation_indicators: List[CycleIndicator] = []
        self.financial_indicators: List[CycleIndicator] = []
        self.industry_indicators: List[CycleIndicator] = []
        self.sentiment_indicators: List[CycleIndicator] = []

    def add_indicator(self, indicator: CycleIndicator):
        """
        添加指标到对应维度

        Args:
            indicator: 周期指标
        """
        if indicator.category == IndicatorCategory.VALUATION:
            self.valuation_indicators.append(indicator)
        elif indicator.category == IndicatorCategory.FINANCIAL:
            self.financial_indicators.append(indicator)
        elif indicator.category == IndicatorCategory.INDUSTRY:
            self.industry_indicators.append(indicator)
        elif indicator.category == IndicatorCategory.SENTIMENT:
            self.sentiment_indicators.append(indicator)

    def add_indicators(self, indicators: List[CycleIndicator]):
        """
        批量添加指标

        Args:
            indicators: 指标列表
        """
        for indicator in indicators:
            self.add_indicator(indicator)

    def calculate_score(self) -> CycleScore:
        """
        计算周期位置得分

        Returns:
            CycleScore: 周期位置评分结果
        """
        # 计算各维度得分
        valuation_score = self._calculate_dimension_score(self.valuation_indicators)
        financial_score = self._calculate_dimension_score(self.financial_indicators)
        industry_score = self._calculate_dimension_score(self.industry_indicators)
        sentiment_score = self._calculate_dimension_score(self.sentiment_indicators)

        # 加权总分
        total_score = (
            valuation_score * self.weights["valuation"]
            + financial_score * self.weights["financial"]
            + industry_score * self.weights["industry"]
            + sentiment_score * self.weights["sentiment"]
        )

        # 判断周期阶段
        phase = self._determine_phase(total_score)

        # 评估置信度
        confidence = self._assess_confidence(
            valuation_score, financial_score, industry_score, sentiment_score
        )

        # 生成分析理由
        rationale = self._generate_rationale(
            valuation_score, financial_score, industry_score, sentiment_score
        )

        # 汇总所有指标
        all_indicators = (
            self.valuation_indicators
            + self.financial_indicators
            + self.industry_indicators
            + self.sentiment_indicators
        )

        return CycleScore(
            total_score=total_score,
            phase=phase,
            confidence=confidence,
            valuation_score=valuation_score,
            financial_score=financial_score,
            industry_score=industry_score,
            sentiment_score=sentiment_score,
            indicators=all_indicators,
            rationale=rationale,
        )

    def _calculate_dimension_score(self, indicators: List[CycleIndicator]) -> float:
        """
        计算某维度得分（1.0-5.0）

        Args:
            indicators: 该维度的指标列表

        Returns:
            float: 维度得分（1.0-5.0）
        """
        if not indicators:
            return 3.0  # 默认中性

        # 计算加权平均得分
        total_weight = sum(ind.weight for ind in indicators)
        if total_weight == 0:
            return 3.0

        weighted_score = sum(ind.score * ind.weight for ind in indicators)

        return weighted_score / total_weight

    def _determine_phase(self, score: float) -> CyclePhase:
        """
        根据得分判断周期阶段

        Args:
            score: 总分（1.0-5.0）

        Returns:
            CyclePhase: 周期阶段
        """
        if score < 1.5:
            return CyclePhase.BOTTOM
        elif score < 2.0:
            return CyclePhase.LATE_DOWNSIDE
        elif score < 2.5:
            return CyclePhase.EARLY_UPSIDE
        elif score < 3.0:
            return CyclePhase.MID_UPSIDE
        elif score < 3.5:
            return CyclePhase.MID_UPSIDE  # 中期延续
        elif score < 4.0:
            return CyclePhase.LATE_UPSIDE
        elif score < 4.5:
            return CyclePhase.TOP
        elif score < 4.8:
            return CyclePhase.EARLY_DOWNSIDE
        else:
            return CyclePhase.MID_DOWNSIDE

    def _assess_confidence(
        self, valuation: float, financial: float, industry: float, sentiment: float
    ) -> str:
        """
        评估置信度

        基于各维度得分的一致性来判断置信度

        Args:
            valuation: 估值得分
            financial: 财务得分
            industry: 行业得分
            sentiment: 情绪得分

        Returns:
            str: 置信度（High, Medium, Low）
        """
        scores = [valuation, financial, industry, sentiment]
        variance = max(scores) - min(scores)

        # 检查是否有足够的数据
        total_indicators = (
            len(self.valuation_indicators)
            + len(self.financial_indicators)
            + len(self.industry_indicators)
            + len(self.sentiment_indicators)
        )

        if total_indicators < 3:
            return "Low"

        if variance < 0.5 and total_indicators >= 5:
            return "High"
        elif variance < 1.0:
            return "Medium"
        else:
            return "Low"

    def _generate_rationale(
        self, valuation: float, financial: float, industry: float, sentiment: float
    ) -> List[str]:
        """
        生成分析理由

        Args:
            valuation: 估值得分
            financial: 财务得分
            industry: 行业得分
            sentiment: 情绪得分

        Returns:
            List[str]: 分析理由列表
        """
        rationale = []

        # 估值指标分析
        if valuation < 2.0:
            rationale.append("估值处于历史低位（PB < 1.2x, 股息率 > 4%）")
        elif valuation > 4.0:
            rationale.append("估值处于历史高位（PB > 2.0x, 股息率 < 3%）")
        elif valuation < 3.0:
            rationale.append("估值偏低，具有一定安全边际")

        # 财务指标分析
        if financial < 2.5:
            rationale.append("财务指标显示周期底部特征（ROE < 5%, 现金流改善）")
        elif financial > 3.5:
            rationale.append("财务指标显示周期景气（ROE > 15%, 盈利能力强）")

        # 行业指标分析
        if industry < 2.0:
            rationale.append("行业指标显示周期底部（价格/运价/开工率处于低位）")
        elif industry > 4.0:
            rationale.append("行业指标显示周期顶点（价格高企，新订单/产能扩张增加）")
        elif industry < 3.0:
            rationale.append("行业景气度偏低，供需关系改善中")

        # 情绪指标分析
        if sentiment < 2.5:
            rationale.append("市场情绪悲观，关注度低（逆向买入机会）")
        elif sentiment > 4.0:
            rationale.append("市场情绪亢奋，全民热议（警惕见顶风险）")

        # 综合判断
        avg_score = (valuation + financial + industry + sentiment) / 4
        if avg_score < 2.5:
            rationale.append("综合判断：处于周期底部区域，具备投资价值")
        elif avg_score > 4.0:
            rationale.append("综合判断：处于周期高位，风险大于机会")

        return rationale

    def get_indicator_summary(self) -> Dict[str, List[Dict]]:
        """
        获取指标摘要

        Returns:
            Dict: 各维度指标摘要
        """

        def summarize(indicators: List[CycleIndicator]) -> List[Dict]:
            return [
                {
                    "name": ind.name,
                    "value": ind.value,
                    "percentile": ind.percentile,
                    "score": ind.score,
                    "status": ind.status,
                    "trend": ind.trend,
                }
                for ind in indicators
            ]

        return {
            "valuation": summarize(self.valuation_indicators),
            "financial": summarize(self.financial_indicators),
            "industry": summarize(self.industry_indicators),
            "sentiment": summarize(self.sentiment_indicators),
        }

    def clear(self):
        """清空所有指标"""
        self.valuation_indicators.clear()
        self.financial_indicators.clear()
        self.industry_indicators.clear()
        self.sentiment_indicators.clear()

    @staticmethod
    def calculate_percentile(current_value: float, historical_values: List[float]) -> float:
        """
        计算当前值在历史数据中的分位

        Args:
            current_value: 当前值
            historical_values: 历史数据列表

        Returns:
            float: 分位（0-100）
        """
        if not historical_values:
            return 50.0

        count_below = sum(1 for v in historical_values if v < current_value)
        return (count_below / len(historical_values)) * 100

    @staticmethod
    def determine_trend(recent_values: List[float], window: int = 5) -> str:
        """
        判断趋势

        Args:
            recent_values: 最近的数据列表
            window: 窗口大小

        Returns:
            str: 趋势（"up", "down", "stable"）
        """
        if len(recent_values) < window:
            return "stable"

        recent = recent_values[-window:]
        first_half = statistics.mean(recent[: window // 2])
        second_half = statistics.mean(recent[window // 2 :])

        change_pct = ((second_half - first_half) / first_half) * 100 if first_half != 0 else 0

        if change_pct > 5:
            return "up"
        elif change_pct < -5:
            return "down"
        else:
            return "stable"
