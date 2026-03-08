"""
Cyclical Analysis Engine - Unified engine for comprehensive cyclical stock analysis.

This engine integrates all components:
- Cycle position scoring
- Multiple valuation methods
- Market-specific strategies
- Buy/sell checklists
"""
from typing import Dict, Any, Optional, List
from .base import (
    CyclicalStock,
    CycleScore,
    CycleIndicator,
    CyclicalAnalysisResult,
    ValuationResult,
    StrategyRecommendation,
    Checklist,
)
from .enums import CycleType, CyclePhase, MarketType, IndicatorCategory
from .position_scorer import CyclePositionScorer
from .valuation import (
    CyclicalPBValuation,
    CyclicalPEValuation,
    CyclicalFCFValuation,
    CyclicalDividendValuation,
)
from .strategy import AShareCyclicalStrategy, USCyclicalStrategy


class CyclicalAnalysisEngine:
    """
    周期股分析引擎

    整合所有分析组件，提供完整的周期股分析流程：
    1. 自动检测周期类型
    2. 计算周期位置
    3. 运行多种估值方法
    4. 生成市场特定策略建议
    5. 提供买入/卖出清单

    Usage:
        engine = CyclicalAnalysisEngine()

        stock = CyclicalStock(
            ticker="601919",
            name="中远海控",
            market=MarketType.A_SHARE,
            current_price=15.79,
            cycle_type=CycleType.SHIPPING,
            pb=1.09,
            bvps=14.5,
        )

        result = engine.analyze(stock)

        print(f"Cycle Phase: {result.cycle_analysis.phase_display}")
        print(f"Action: {result.strategy_recommendation.action_display}")
    """

    # 周期类型到行业的映射
    CYCLE_TYPE_MAPPING = {
        # 航运
        "601919": CycleType.SHIPPING,  # 中远海控
        "600026": CycleType.SHIPPING,  # 中远海能
        "601872": CycleType.SHIPPING,  # 招商轮船
        "601975": CycleType.SHIPPING,  # 招商南油
        # 钢铁
        "600019": CycleType.CAPACITY,  # 宝钢股份
        "000932": CycleType.CAPACITY,  # 华菱钢铁
        "600282": CycleType.CAPACITY,  # 南钢股份
        # 有色金属
        "601600": CycleType.COMMODITY,  # 中国铝业
        "601899": CycleType.COMMODITY,  # 紫金矿业
        "603993": CycleType.COMMODITY,  # 洛阳钼业
        # 能源
        "601857": CycleType.ENERGY,  # 中国石油
        "600028": CycleType.ENERGY,  # 中国石化
        "XOM": CycleType.ENERGY,  # Exxon Mobil
        "CVX": CycleType.ENERGY,  # Chevron
        # 化工
        "600309": CycleType.CAPACITY,  # 万华化学
    }

    def __init__(self):
        """初始化分析引擎"""
        # 估值方法
        self.valuation_methods = {
            "cyclical_pb": CyclicalPBValuation(),
            "cyclical_pe": CyclicalPEValuation(),
            "cyclical_fcf": CyclicalFCFValuation(),
            "cyclical_dividend": CyclicalDividendValuation(),
        }

        # 策略
        self.strategies = {
            MarketType.A_SHARE: AShareCyclicalStrategy(),
            MarketType.US: USCyclicalStrategy(),
        }

    def analyze(self, stock: CyclicalStock) -> CyclicalAnalysisResult:
        """
        完整周期股分析

        Args:
            stock: 周期股数据

        Returns:
            CyclicalAnalysisResult: 完整分析结果
        """
        # 1. 周期位置分析
        cycle_score = self._analyze_cycle_position(stock)
        stock.current_phase = cycle_score.phase
        stock.cycle_score = cycle_score

        # 2. 估值分析
        valuation_results = self._analyze_valuation(stock)

        # 3. 创建分析结果
        analysis = CyclicalAnalysisResult(
            stock=stock,
            cycle_analysis=cycle_score,
            valuation_results=valuation_results,
        )

        # 4. 策略建议
        strategy = self.strategies.get(stock.market)
        if strategy:
            analysis.strategy_recommendation = strategy.generate_recommendation(stock, analysis)

            # 5. 买入/卖出清单
            analysis.buy_checklist = strategy.get_buy_checklist(stock)
            analysis.sell_checklist = strategy.get_sell_checklist(stock)

        # 6. 风险和催化剂
        analysis.risks = self._identify_risks(stock, cycle_score)
        analysis.catalysts = self._identify_catalysts(stock, cycle_score)

        # 7. 综合评分
        analysis.overall_score = self._calculate_overall_score(analysis)
        analysis.investment_rating = self._determine_rating(analysis.overall_score)

        return analysis

    def _analyze_cycle_position(self, stock: CyclicalStock) -> CycleScore:
        """
        分析周期位置

        Args:
            stock: 周期股数据

        Returns:
            CycleScore: 周期位置评分
        """
        scorer = CyclePositionScorer(market=stock.market)

        # 添加估值指标
        self._add_valuation_indicators(scorer, stock)

        # 添加财务指标
        self._add_financial_indicators(scorer, stock)

        # 如果有额外指标，也添加进去
        # （可以由用户手动添加，或者从行业指标获取器获取）

        return scorer.calculate_score()

    def _add_valuation_indicators(self, scorer: CyclePositionScorer, stock: CyclicalStock):
        """添加估值指标"""
        # PB
        if stock.pb > 0 and stock.historical_pb:
            percentile = CyclePositionScorer.calculate_percentile(stock.pb, stock.historical_pb)
            scorer.add_indicator(
                CycleIndicator(
                    name="PB估值",
                    value=stock.pb,
                    category=IndicatorCategory.VALUATION,
                    percentile=percentile,
                    historical_avg=sum(stock.historical_pb) / len(stock.historical_pb),
                    weight=0.3,
                )
            )

        # 股息率
        if stock.dividend_yield > 0:
            # 反向：股息率高表示价格低
            percentile = 100 - min(stock.dividend_yield * 1000, 100)  # 简化计算
            scorer.add_indicator(
                CycleIndicator(
                    name="股息率",
                    value=stock.dividend_yield * 100,
                    category=IndicatorCategory.VALUATION,
                    percentile=percentile,
                    weight=0.2,
                )
            )

    def _add_financial_indicators(self, scorer: CyclePositionScorer, stock: CyclicalStock):
        """添加财务指标"""
        # ROE
        if stock.roe > 0:
            # ROE高表示盈利能力强（周期上行）
            percentile = min(stock.roe * 5, 100)  # 简化计算
            scorer.add_indicator(
                CycleIndicator(
                    name="ROE",
                    value=stock.roe,
                    category=IndicatorCategory.FINANCIAL,
                    percentile=percentile,
                    weight=0.3,
                )
            )

        # FCF质量
        if stock.fcf_to_net_income > 0:
            # FCF/净利润 > 1 表示现金流好
            percentile = min(stock.fcf_to_net_income * 50, 100)
            scorer.add_indicator(
                CycleIndicator(
                    name="FCF质量",
                    value=stock.fcf_to_net_income,
                    category=IndicatorCategory.FINANCIAL,
                    percentile=percentile,
                    weight=0.2,
                )
            )

    def _analyze_valuation(self, stock: CyclicalStock) -> Dict[str, ValuationResult]:
        """
        运行所有估值方法

        Args:
            stock: 周期股数据

        Returns:
            Dict[str, ValuationResult]: 估值结果字典
        """
        results = {}

        for method_name, method in self.valuation_methods.items():
            try:
                result = method.calculate(stock)
                results[method_name] = result
            except Exception as e:
                # 如果某个方法失败，跳过
                print(f"Warning: {method_name} valuation failed: {e}")

        return results

    def _identify_risks(self, stock: CyclicalStock, cycle_score: CycleScore) -> List[str]:
        """
        识别风险

        Args:
            stock: 周期股数据
            cycle_score: 周期评分

        Returns:
            List[str]: 风险列表
        """
        risks = []

        # 周期风险
        if cycle_score.total_score > 4.0:
            risks.append("周期处于高位，下行风险大")
        elif cycle_score.total_score > 3.5:
            risks.append("周期接近顶点，注意风险")

        # 估值风险
        if stock.pb > 2.0:
            risks.append("PB估值较高，安全边际不足")

        # 财务风险
        if stock.debt_ratio > 0.6:
            risks.append("负债率较高，周期下行时压力大")

        if stock.fcf_to_net_income < 1.0:
            risks.append("现金流质量差，盈利可能虚高")

        # 分红风险（美股）
        if stock.market == MarketType.US and stock.payout_ratio > 0.8:
            risks.append("分红比例过高，可能削减股息")

        return risks

    def _identify_catalysts(self, stock: CyclicalStock, cycle_score: CycleScore) -> List[str]:
        """
        识别催化剂

        Args:
            stock: 周期股数据
            cycle_score: 周期评分

        Returns:
            List[str]: 催化剂列表
        """
        catalysts = []

        # 周期催化剂
        if cycle_score.total_score < 2.5:
            catalysts.append("周期处于底部区域，上行空间大")
        elif cycle_score.total_score < 3.0:
            catalysts.append("周期即将反转，布局良机")

        # 估值催化剂
        if stock.pb < 1.0:
            catalysts.append("PB < 1.0，安全边际极高")
        elif stock.pb < 1.2:
            catalysts.append("估值合理偏低，安全边际足")

        # 分红催化剂
        if stock.dividend_yield > 0.05:
            catalysts.append(f"股息率 {stock.dividend_yield:.1%}，提供安全垫")

        # 财务催化剂
        if stock.fcf_to_net_income > 1.2:
            catalysts.append("现金流质量优秀，盈利可持续")

        if stock.debt_ratio < 0.4:
            catalysts.append("财务健康，抗风险能力强")

        return catalysts

    def _calculate_overall_score(self, analysis: CyclicalAnalysisResult) -> float:
        """
        计算综合评分（0-100）

        基于多个维度：
        - 周期位置（40%）
        - 估值吸引力（30%）
        - 财务质量（20%）
        - 策略建议（10%）

        Args:
            analysis: 分析结果

        Returns:
            float: 综合评分（0-100）
        """
        score = 0.0

        # 1. 周期位置得分（40%）
        # 周期底部得分高，顶点得分低
        cycle_score = analysis.cycle_analysis.total_score
        cycle_position_score = (5.0 - cycle_score) / 4.0 * 100  # 反向，底部100分，顶点0分
        score += cycle_position_score * 0.40

        # 2. 估值吸引力得分（30%）
        # 计算所有估值方法的平均溢价/折价
        if analysis.valuation_results:
            avg_premium = sum(
                r.premium_discount for r in analysis.valuation_results.values()
            ) / len(analysis.valuation_results)
            # 折价20% = 100分，溢价20% = 0分
            valuation_score = max(min((20 - avg_premium) / 40 * 100, 100), 0)
            score += valuation_score * 0.30

        # 3. 财务质量得分（20%）
        financial_score = 50  # 默认50分
        if analysis.stock.debt_ratio < 0.4:
            financial_score += 25
        elif analysis.stock.debt_ratio > 0.6:
            financial_score -= 25

        if analysis.stock.fcf_to_net_income > 1.2:
            financial_score += 15
        elif analysis.stock.fcf_to_net_income < 0.8:
            financial_score -= 15

        financial_score = max(min(financial_score, 100), 0)
        score += financial_score * 0.20

        # 4. 策略建议得分（10%）
        if analysis.strategy_recommendation:
            action = analysis.strategy_recommendation.action
            if action.value == "strong_buy":
                action_score = 100
            elif action.value == "buy":
                action_score = 80
            elif action.value == "hold":
                action_score = 50
            elif action.value == "reduce":
                action_score = 30
            elif action.value == "sell":
                action_score = 10
            else:
                action_score = 40  # watch

            score += action_score * 0.10

        return round(score, 1)

    def _determine_rating(self, overall_score: float) -> str:
        """
        确定投资评级

        Args:
            overall_score: 综合评分（0-100）

        Returns:
            str: 投资评级
        """
        if overall_score >= 75:
            return "强烈推荐"
        elif overall_score >= 60:
            return "推荐"
        elif overall_score >= 45:
            return "中性"
        elif overall_score >= 30:
            return "谨慎"
        else:
            return "不推荐"

    @classmethod
    def detect_cycle_type(cls, ticker: str, name: str = "") -> Optional[CycleType]:
        """
        自动检测周期类型

        Args:
            ticker: 股票代码
            name: 股票名称

        Returns:
            Optional[CycleType]: 检测到的周期类型
        """
        # 先查映射表
        if ticker in cls.CYCLE_TYPE_MAPPING:
            return cls.CYCLE_TYPE_MAPPING[ticker]

        # 根据名称关键词判断
        name_lower = name.lower()

        shipping_keywords = ["航运", "海运", "轮船", "海控", "shipping", "marine"]
        steel_keywords = ["钢铁", "steel", "宝钢", "华菱"]
        metals_keywords = ["铝业", "铜业", "矿业", "aluminum", "copper", "mining"]
        energy_keywords = ["石油", "石化", "oil", "petroleum", "energy"]

        for keyword in shipping_keywords:
            if keyword in name_lower:
                return CycleType.SHIPPING

        for keyword in steel_keywords:
            if keyword in name_lower:
                return CycleType.CAPACITY

        for keyword in metals_keywords:
            if keyword in name_lower:
                return CycleType.COMMODITY

        for keyword in energy_keywords:
            if keyword in name_lower:
                return CycleType.ENERGY

        # 默认返回产能周期
        return CycleType.CAPACITY

    def get_supported_methods(self) -> List[str]:
        """
        获取支持的估值方法列表

        Returns:
            List[str]: 方法列表
        """
        return list(self.valuation_methods.keys())

    def get_method_info(self, method_name: str) -> Optional[Dict[str, Any]]:
        """
        获取估值方法信息

        Args:
            method_name: 方法名称

        Returns:
            Optional[Dict]: 方法信息
        """
        if method_name in self.valuation_methods:
            return self.valuation_methods[method_name].get_method_info()
        return None
