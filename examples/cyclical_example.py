"""
Quick Usage Example for Cyclical Stock Analysis

This example demonstrates how to use the cyclical stock analysis module
to analyze a shipping stock (中远海控).
"""

from valueinvest.cyclical import (
    CyclicalStock,
    CyclePositionScorer,
    CycleType,
    CyclePhase,
    MarketType,
    IndicatorCategory,
    CycleIndicator,
    CyclicalPBValuation,
    CyclicalPEValuation,
    AShareCyclicalStrategy,
    CyclicalAnalysisResult,
)


def analyze_shipping_stock():
    """分析航运股（中远海控）"""

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

    print("=" * 70)
    print(f"周期股分析：{stock.name} ({stock.ticker})")
    print("=" * 70)
    print(f"\n【基本信息】")
    print(f"  市场: {stock.market_display}")
    print(f"  周期类型: {stock.cycle_type.value}")
    print(f"  当前价格: ¥{stock.current_price:.2f}")
    print(f"  PB: {stock.pb:.2f}x")
    print(f"  PE: {stock.pe:.1f}x")
    print(f"  股息率: {stock.dividend_yield:.1%}")

    # 2. 创建评分器并添加指标
    scorer = CyclePositionScorer(market=MarketType.A_SHARE)

    # 添加估值指标
    scorer.add_indicator(
        CycleIndicator(
            name="PB估值",
            value=stock.pb,
            category=IndicatorCategory.VALUATION,
            percentile=20.0,  # PB在历史低位
            weight=1.0,
        )
    )

    # 添加财务指标
    scorer.add_indicator(
        CycleIndicator(
            name="ROE",
            value=stock.roe,
            category=IndicatorCategory.FINANCIAL,
            percentile=40.0,  # ROE中等偏低
            weight=1.0,
        )
    )

    # 添加行业指标（模拟航运数据）
    scorer.add_indicator(
        CycleIndicator(
            name="BDI指数",
            value=1500,  # BDI指数
            category=IndicatorCategory.INDUSTRY,
            percentile=25.0,  # BDI在低位
            weight=1.0,
        )
    )

    # 3. 计算周期位置
    cycle_score = scorer.calculate_score()
    stock.current_phase = cycle_score.phase
    stock.cycle_score = cycle_score

    print(f"\n【周期位置分析】")
    print(f"  周期阶段: {cycle_score.phase_display} {cycle_score.phase_emoji}")
    print(f"  周期得分: {cycle_score.total_score:.2f}/5.0")
    print(f"  置信度: {cycle_score.confidence}")
    print(f"  评估: {cycle_score.assessment}")

    if cycle_score.rationale:
        print(f"\n  分析理由:")
        for reason in cycle_score.rationale:
            print(f"    • {reason}")

    # 4. 运行估值方法
    print(f"\n【估值分析】")

    # PB估值
    pb_valuation = CyclicalPBValuation()
    pb_result = pb_valuation.calculate(stock)
    print(f"\n  PB估值:")
    print(f"    公允价值: ¥{pb_result.fair_value:.2f}")
    print(f"    当前价值: ¥{pb_result.current_value:.2f}")
    print(f"    溢价/折价: {pb_result.premium_discount:+.1f}%")
    print(f"    评估: {pb_result.assessment}")
    print(f"    行动建议: {pb_result.action}")

    # PE估值
    pe_valuation = CyclicalPEValuation()
    pe_result = pe_valuation.calculate(stock)
    print(f"\n  PE估值:")
    print(f"    公允价值: ¥{pe_result.fair_value:.2f}")
    print(f"    评估: {pe_result.assessment}")
    print(f"    行动建议: {pe_result.action}")

    # 5. 生成策略建议
    print(f"\n【策略建议】")

    analysis = CyclicalAnalysisResult(
        stock=stock,
        cycle_analysis=cycle_score,
        valuation_results={
            "pb": pb_result,
            "pe": pe_result,
        },
    )

    strategy = AShareCyclicalStrategy()
    recommendation = strategy.generate_recommendation(stock, analysis)

    print(f"  投资行动: {recommendation.action_display} {recommendation.action_signal}")
    print(f"  建议仓位: {recommendation.target_allocation:.1%}")
    print(f"  目标价格: ¥{recommendation.target_price:.2f}")
    print(f"  止损价格: ¥{recommendation.stop_loss_price:.2f}")
    print(f"  预期收益: {recommendation.expected_return:.1f}%")
    print(f"  持有周期: {recommendation.holding_period}")
    print(f"  策略类型: {recommendation.strategy_type.value}")

    if recommendation.rationale:
        print(f"\n  投资理由:")
        for reason in recommendation.rationale:
            print(f"    • {reason}")

    # 6. 买入/卖出清单
    buy_checklist = strategy.get_buy_checklist(stock)

    print(f"\n【买入清单】 (通过 {buy_checklist.passed_count}/{buy_checklist.total_count} 项)")
    for item, passed in buy_checklist.items.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {item}")

    print(f"\n" + "=" * 70)
    print(f"分析完成！")
    print("=" * 70)


if __name__ == "__main__":
    analyze_shipping_stock()
