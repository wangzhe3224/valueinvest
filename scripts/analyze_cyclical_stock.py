#!/usr/bin/env python3
"""
周期股深度分析脚本
分析中远海控 (601919) - 典型航运周期股
"""
import sys
from datetime import datetime

from valueinvest.cyclical import (
    CyclicalAnalysisEngine,
    CyclicalStock,
    CycleType,
    CycleStrength,
    MarketType,
)

def create_analysis_report():
    """生成中远海控完整分析报告"""
    
    # 股票数据（2026-03-08 实时数据）
    stock = CyclicalStock(
        ticker="601919",
        name="中远海控",
        market=MarketType.A_SHARE,
        current_price=15.79,  # 实时价格
        cycle_type=CycleType.SHIPPING,
        cycle_strength=CycleStrength.STRONG,
        cycle_length_years=7,
        pb=1.09,
        pe=9.1,
        ps=0.8,
        fcf_yield=7.9,
        dividend_yield=0.05,
        bvps=14.5,
        eps=1.73,
        fcf_per_share=1.25,
        debt_ratio=0.35,
        roe=12.0,
        roa=8.0,
        fcf_to_net_income=1.1,
        gross_margin=25.0,
        operating_margin=18.0,
        payout_ratio=30.0,
        dividend_growth_rate=5.0,
        historical_pb=[1.5, 2.0, 1.8, 2.5, 1.2],
        historical_pe=[8.0, 12.0, 10.5, 18.0, 7.5],
        historical_roe=[8.5, 12.3, 15.6, 22.5, 12.0],
        market_cap=200e9,
        revenue=300e9,
        net_income=50e9,
        total_assets=280e9,
    )
    
    print("=" * 80)
    print(f"周期股深度分析报告")
    print("=" * 80)
    print(f"\n股票: {stock.name} ({stock.ticker})")
    print(f"市场: {stock.market_display}")
    print(f"周期类型: {stock.cycle_type.value} ({stock.cycle_strength.display_name})")
    print(f"分析日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"\n当前价格: ¥{stock.current_price:.2f}")
    print(f"市值: ¥{stock.market_cap/1e9:.0f}亿")
    
    engine = CyclicalAnalysisEngine()
    result = engine.analyze(stock)
    
    # 周期位置分析
    print("\n" + "=" * 80)
    print("【一、周期位置分析】")
    print("=" * 80)
    
    cycle_score = result.cycle_analysis
    print(f"\n周期阶段: {cycle_score.phase_display} {cycle_score.phase_emoji}")
    print(f"周期得分: {cycle_score.total_score:.2f}/5.0")
    print(f"置信度: {cycle_score.confidence}")
    print(f"\n评估结论: {cycle_score.assessment}")
    
    print(f"\n分维度得分:")
    print(f"  • 估值指标: {cycle_score.valuation_score:.2f}/5.0")
    print(f"  • 财务指标: {cycle_score.financial_score:.2f}/5.0")
    print(f"  • 行业指标: {cycle_score.industry_score:.2f}/5.0")
    print(f"  • 情绪指标: {cycle_score.sentiment_score:.2f}/5.0")
    
    if cycle_score.rationale:
        print(f"\n分析依据:")
        for i, reason in enumerate(cycle_score.rationale, 1):
            print(f"  {i}. {reason}")
    
    # 估值分析
    print("\n" + "=" * 80)
    print("【二、估值分析】")
    print("=" * 80)
    
    for method_name, val_result in result.valuation_results.items():
        print(f"\n{val_result.method}:")
        print(f"  公允价值: ¥{val_result.fair_value:.2f}")
        print(f"  当前价值: ¥{val_result.current_value:.2f}")
        print(f"  溢价/折价: {val_result.premium_discount:+.1f}%")
        print(f"  安全边际: {val_result.margin_of_safety:.1f}%")
        print(f"  评估: {val_result.assessment}")
        print(f"  行动建议: {val_result.action}")
        print(f"  置信度: {val_result.confidence}")
        
        if val_result.details:
            print(f"  详细信息:")
            for key, value in val_result.details.items():
                if isinstance(value, float):
                    print(f"    - {key}: {value:.2f}")
                else:
                    print(f"    - {key}: {value}")
    
    # 策略建议
    print("\n" + "=" * 80)
    print("【三、投资策略建议】")
    print("=" * 80)
    
    if result.strategy_recommendation:
        rec = result.strategy_recommendation
        print(f"\n投资行动: {rec.action_display} {rec.action_signal}")
        print(f"建议仓位: {rec.target_allocation:.1%}")
        print(f"目标价格: ¥{rec.target_price:.2f}")
        print(f"止损价格: ¥{rec.stop_loss_price:.2f}")
        print(f"预期收益: {rec.expected_return:.1f}%")
        print(f"持有周期: {rec.holding_period}")
        print(f"策略类型: {rec.strategy_type.display_name}")
        
        if rec.rationale:
            print(f"\n投资理由:")
            for i, reason in enumerate(rec.rationale, 1):
                print(f"  {i}. {reason}")
    
    # 投资清单
    print("\n" + "=" * 80)
    print("【四、投资清单】")
    print("=" * 80)
    
    if result.buy_checklist:
        buy = result.buy_checklist
        print(f"\n买入清单 (通过 {buy.passed_count}/{buy.total_count} 项):")
        for item, passed in buy.items.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {item}")
    
    if result.sell_checklist:
        sell = result.sell_checklist
        print(f"\n卖出清单 (通过 {sell.passed_count}/{sell.total_count} 项):")
        for item, passed in sell.items.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {item}")
    
    # 风险与催化剂
    print("\n" + "=" * 80)
    print("【五、风险与催化剂】")
    print("=" * 80)
    
    if result.risks:
        print(f"\n⚠️  风险提示 ({len(result.risks)}项):")
        for i, risk in enumerate(result.risks, 1):
            print(f"  {i}. {risk}")
    
    if result.catalysts:
        print(f"\n✅ 潜在催化剂 ({len(result.catalysts)}项):")
        for i, catalyst in enumerate(result.catalysts, 1):
            print(f"  {i}. {catalyst}")
    
    # 综合评分
    print("\n" + "=" * 80)
    print("【六、综合评估】")
    print("=" * 80)
    
    print(f"\n综合评分: {result.overall_score}/100")
    print(f"投资评级: {result.investment_rating}")
    print(f"风险等级: {result.risk_level}")
    print(f"推荐状态: {'✅ 推荐投资' if result.is_recommended else '⚠️  谨慎投资'}")
    
    # 投资建议总结
    print("\n" + "=" * 80)
    print("【七、投资建议总结】")
    print("=" * 80)
    
    print(f"\n📊 核心观点:")
    if cycle_score.total_score < 2.5:
        print(f"  • 当前处于周期底部区域，估值极具吸引力")
        print(f"  • PB {stock.pb:.2f}x 处于历史低位，安全边际高")
        print(f"  • 股息率 {stock.dividend_yield:.1%} 提供良好安全垫")
    elif cycle_score.total_score > 4.0:
        print(f"  • 当前处于周期高位，风险大于机会")
        print(f"  • ROE {stock.roe:.1f}% 处于历史高位，难以持续")
        print(f"  • 建议逐步减仓，锁定利润")
    else:
        print(f"  • 当前处于周期中段，需谨慎观察")
        print(f"  • 关注行业景气度变化和估值水平")
    
    print(f"\n💡 操作建议:")
    if result.strategy_recommendation:
        rec = result.strategy_recommendation
        if rec.action.value in ["strong_buy", "buy"]:
            print(f"  • 建议分批建仓，单次买入不超过{rec.target_allocation:.0%}仓位")
            print(f"  • 目标价 ¥{rec.target_price:.2f}，止损价 ¥{rec.stop_loss_price:.2f}")
            print(f"  • 预期收益 {rec.expected_return:.0f}%，持有周期 {rec.holding_period}")
        elif rec.action.value in ["sell", "reduce"]:
            print(f"  • 建议逐步减仓，降低周期股仓位")
            print(f"  • 保留底仓或完全清仓，等待下一个周期")
        else:
            print(f"  • 建议持有观望，不宜大幅加仓")
            print(f"  • 密切关注周期指标变化")
    
    print(f"\n⚠️  风险提示:")
    print(f"  • 周期股波动性大，需要严格止损")
    print(f"  • 不要在周期顶点追高，PE低不代表便宜")
    print(f"  • 关注行业供需关系和价格走势")
    print(f"  • 建议仓位控制在合理范围内")
    
    print("\n" + "=" * 80)
    print("分析完成")
    print("=" * 80)
    
    return result


if __name__ == "__main__":
    try:
        result = create_analysis_report()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
