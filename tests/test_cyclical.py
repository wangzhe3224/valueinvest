"""
Tests for cyclical stock analysis module.
"""
import pytest
from valueinvest.cyclical import (
    CycleType,
    CyclePhase,
    CycleStrength,
    MarketType,
    InvestmentAction,
    InvestmentStrategy,
    IndicatorCategory,
    CycleIndicator,
    CycleScore,
    CyclicalStock,
    CyclePositionScorer,
    CyclicalPBValuation,
    CyclicalPEValuation,
    CyclicalFCFValuation,
    CyclicalDividendValuation,
    AShareCyclicalStrategy,
    USCyclicalStrategy,
    CyclicalAnalysisResult,
)


class TestEnums:
    """测试枚举类型"""
    
    def test_cycle_phase_properties(self):
        """测试周期阶段属性"""
        assert CyclePhase.BOTTOM.is_buyable is True
        assert CyclePhase.BOTTOM.is_downside is False
        
        assert CyclePhase.TOP.is_sellable is True
        assert CyclePhase.TOP.is_upside is False
        
        assert CyclePhase.MID_UPSIDE.is_upside is True
        assert CyclePhase.MID_DOWNSIDE.is_downside is True
    
    def test_cycle_phase_display_name(self):
        """测试周期阶段显示名"""
        assert CyclePhase.BOTTOM.display_name == "周期底部"
        assert CyclePhase.EARLY_UPSIDE.display_name == "上行初期"
        assert CyclePhase.TOP.display_name == "周期顶点"
    
    def test_investment_action_signal(self):
        """测试投资行动信号"""
        assert InvestmentAction.STRONG_BUY.signal == "🟢🟢"
        assert InvestmentAction.BUY.signal == "🟢"
        assert InvestmentAction.SELL.signal == "🔴"
        assert InvestmentAction.WATCH.signal == "⚪"


class TestCycleIndicator:
    """测试周期指标"""
    
    def test_indicator_score(self):
        """测试指标评分"""
        # 低分位 -> 低分（底部）
        ind1 = CycleIndicator(
            name="PB",
            value=1.0,
            category=IndicatorCategory.VALUATION,
            percentile=10.0
        )
        assert ind1.score == 1.0
        
        # 高分位 -> 高分（顶点）
        ind2 = CycleIndicator(
            name="PB",
            value=3.0,
            category=IndicatorCategory.VALUATION,
            percentile=90.0
        )
        assert ind2.score == 5.0
        
        # 中等分位 -> 中等分
        ind3 = CycleIndicator(
            name="PB",
            value=2.0,
            category=IndicatorCategory.VALUATION,
            percentile=50.0
        )
        assert ind3.score == 3.0
    
    def test_indicator_status(self):
        """测试指标状态"""
        ind = CycleIndicator(
            name="PB",
            value=1.0,
            category=IndicatorCategory.VALUATION,
            percentile=10.0
        )
        assert ind.status == "极低"
        
        ind.percentile = 50.0
        assert ind.status == "中等"
        
        ind.percentile = 90.0
        assert ind.status == "极高"


class TestCyclePositionScorer:
    """测试周期位置评分器"""
    
    def test_scorer_basic(self):
        """测试基本评分功能"""
        scorer = CyclePositionScorer(market=MarketType.A_SHARE)
        
        # 添加估值指标
        scorer.add_indicator(CycleIndicator(
            name="PB",
            value=1.0,
            category=IndicatorCategory.VALUATION,
            percentile=10.0,
            weight=1.0
        ))
        
        # 添加财务指标
        scorer.add_indicator(CycleIndicator(
            name="ROE",
            value=5.0,
            category=IndicatorCategory.FINANCIAL,
            percentile=20.0,
            weight=1.0
        ))
        
        # 计算得分
        score = scorer.calculate_score()
        
        assert 1.0 <= score.total_score <= 5.0
        assert score.phase in list(CyclePhase)
        assert score.confidence in ["High", "Medium", "Low"]
        assert len(score.indicators) == 2
    
    def test_scorer_determine_phase(self):
        """测试周期阶段判断"""
        scorer = CyclePositionScorer()
        
        # 底部
        phase = scorer._determine_phase(1.2)
        assert phase == CyclePhase.BOTTOM
        
        # 上行初期
        phase = scorer._determine_phase(2.2)
        assert phase == CyclePhase.EARLY_UPSIDE
        
        # 中期
        phase = scorer._determine_phase(3.0)
        assert phase == CyclePhase.MID_UPSIDE
        
        # 顶点
        phase = scorer._determine_phase(4.3)
        assert phase == CyclePhase.TOP


class TestCyclicalPBValuation:
    """测试周期调整PB估值"""
    
    def test_pb_valuation_bottom(self):
        """测试底部PB估值"""
        stock = CyclicalStock(
            ticker="601919",
            name="中远海控",
            market=MarketType.A_SHARE,
            current_price=15.79,
            cycle_type=CycleType.SHIPPING,
            current_phase=CyclePhase.BOTTOM,
            pb=0.9,
            bvps=14.5,
            historical_pb=[1.5, 2.0, 1.8, 2.5, 1.2],
        )
        
        valuation = CyclicalPBValuation()
        result = valuation.calculate(stock)
        
        assert result.method == "Cyclical PB"
        assert result.fair_value > 0
        assert result.action in ["STRONG_BUY", "BUY"]
    
    def test_pb_valuation_top(self):
        """测试顶点PB估值 - PB > sell threshold"""
        stock = CyclicalStock(
            ticker="601919",
            name="中远海控",
            market=MarketType.A_SHARE,
            current_price=45.0,  # Price implies PB = 45/14.5 = 3.1
            cycle_type=CycleType.SHIPPING,
            current_phase=CyclePhase.TOP,
            pb=3.1,  # > sell threshold of 3.0
            bvps=14.5,
            historical_pb=[1.5, 2.0, 1.8, 2.5, 1.2],
        )
        
        valuation = CyclicalPBValuation()
        result = valuation.calculate(stock)
        
        assert result.action == "SELL"
    
    def test_pb_valuation_error_handling(self):
        """测试错误处理"""
        # BVPS为0
        stock = CyclicalStock(
            ticker="601919",
            name="中远海控",
            market=MarketType.A_SHARE,
            current_price=15.79,
            cycle_type=CycleType.SHIPPING,
            pb=1.0,
            bvps=0,  # 错误数据
        )
        
        valuation = CyclicalPBValuation()
        result = valuation.calculate(stock)
        
        assert result.assessment == "N/A"
        assert result.action == "ERROR"


class TestAShareCyclicalStrategy:
    """测试A股周期股策略"""
    
    def test_strategy_bottom_buy(self):
        """测试底部买入策略"""
        stock = CyclicalStock(
            ticker="601919",
            name="中远海控",
            market=MarketType.A_SHARE,
            current_price=15.79,
            cycle_type=CycleType.SHIPPING,
            current_phase=CyclePhase.BOTTOM,
            pb=0.9,
            bvps=14.5,
            dividend_yield=5.0,
        )
        
        cycle_score = CycleScore(
            total_score=1.8,
            phase=CyclePhase.BOTTOM,
        )
        
        analysis = CyclicalAnalysisResult(
            stock=stock,
            cycle_analysis=cycle_score,
        )
        
        strategy = AShareCyclicalStrategy()
        recommendation = strategy.generate_recommendation(stock, analysis)
        
        assert recommendation.action in [InvestmentAction.STRONG_BUY, InvestmentAction.BUY]
        assert recommendation.target_allocation > 0
        assert recommendation.holding_period == "1-3年"
        assert recommendation.strategy_type == InvestmentStrategy.CYCLICAL_TRADING
    
    def test_buy_checklist(self):
        """测试买入清单"""
        stock = CyclicalStock(
            ticker="601919",
            name="中远海控",
            market=MarketType.A_SHARE,
            current_price=15.79,
            cycle_type=CycleType.SHIPPING,
            current_phase=CyclePhase.BOTTOM,
            pb=0.9,
            bvps=14.5,
            debt_ratio=0.5,
            fcf_to_net_income=1.2,
            dividend_yield=0.05,
            roe=10.0,
        )
        
        strategy = AShareCyclicalStrategy()
        checklist = strategy.get_buy_checklist(stock)
        
        assert isinstance(checklist.items, dict)
        assert len(checklist.items) > 0


class TestIntegration:
    """集成测试"""
    
    def test_full_analysis_workflow(self):
        """测试完整分析流程"""
        # 1. 创建股票数据
        stock = CyclicalStock(
            ticker="601919",
            name="中远海控",
            market=MarketType.A_SHARE,
            current_price=15.79,
            cycle_type=CycleType.SHIPPING,
            cycle_strength=CycleStrength.STRONG,
            pb=1.09,
            bvps=14.5,
            eps=1.73,
            pe=9.1,
            fcf_yield=7.9,
            fcf_per_share=1.25,
            fcf_to_net_income=1.1,
            dividend_yield=5.0,
            debt_ratio=0.35,
            roe=12.0,
            historical_pb=[1.5, 2.0, 1.8, 2.5, 1.2],
        )
        
        # 2. 创建评分器并添加指标
        scorer = CyclePositionScorer(market=MarketType.A_SHARE)
        
        scorer.add_indicator(CycleIndicator(
            name="PB",
            value=stock.pb,
            category=IndicatorCategory.VALUATION,
            percentile=20.0,
            weight=1.0
        ))
        
        scorer.add_indicator(CycleIndicator(
            name="ROE",
            value=stock.roe,
            category=IndicatorCategory.FINANCIAL,
            percentile=30.0,
            weight=1.0
        ))
        
        # 3. 计算周期位置
        cycle_score = scorer.calculate_score()
        stock.current_phase = cycle_score.phase
        stock.cycle_score = cycle_score
        
        # 4. 运行估值
        pb_valuation = CyclicalPBValuation()
        pb_result = pb_valuation.calculate(stock)
        
        # 5. 生成策略建议
        analysis = CyclicalAnalysisResult(
            stock=stock,
            cycle_analysis=cycle_score,
            valuation_results={
                "pb": pb_result,
            }
        )
        
        strategy = AShareCyclicalStrategy()
        recommendation = strategy.generate_recommendation(stock, analysis)
        
        # 6. 获取清单
        buy_checklist = strategy.get_buy_checklist(stock)
        
        analysis.buy_checklist = buy_checklist
        analysis.strategy_recommendation = recommendation
        
        # 验证结果
        assert analysis.stock.ticker == "601919"
        assert analysis.cycle_analysis.total_score > 0
        assert len(analysis.valuation_results) == 1
        assert analysis.strategy_recommendation is not None
        assert analysis.buy_checklist is not None
        
        # 打印摘要
        print(f"\n=== 周期股分析结果 ===")
        print(f"股票: {stock.name} ({stock.ticker})")
        print(f"周期阶段: {cycle_score.phase_display}")
        print(f"周期得分: {cycle_score.total_score:.2f}/5.0")
        print(f"PB估值: {pb_result.fair_value:.2f} ({pb_result.action})")
        print(f"投资建议: {recommendation.action_display}")
        print(f"建议仓位: {recommendation.target_allocation:.1%}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
