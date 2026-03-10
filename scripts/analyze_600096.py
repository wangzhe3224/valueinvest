#!/usr/bin/env python3
"""
云天化 (SH:600096) - 磷化工周期股深度分析
分析中国最大磷化工龙头企业的周期状况
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
    """生成云天化完整分析报告"""

    # 股票数据 (基于2024-2025年财务数据和最新市场信息)
    # 注: 需要更新为实时价格数据
    stock = CyclicalStock(
        ticker="600096",
        name="云天化",
        market=MarketType.A_SHARE,
        current_price=13.5,  # 估算当前价格 (需实时更新)
        cycle_type=CycleType.COMMODITY,
        cycle_strength=CycleStrength.STRONG,
        cycle_length_years=5,  # 磷化工周期约3-5年
        # 估值指标
        pb=1.8,  # 估算PB (需实时数据)
        pe=6.5,  # 估算PE (需实时数据)
        ps=0.7,  # 市销率
        fcf_yield=0.08,  # FCF收益率约8%
        dividend_yield=0.025,  # 股息率约2.5%
        bvps=7.5,  # 每股净资产 (估算)
        eps=2.08,  # 每股收益 (基于47.29亿净利润)
        fcf_per_share=2.77,  # FCF per share (基于62.98亿FCF)
        # 财务指标
        debt_ratio=0.55,  # 资产负债率约55%
        roe=27.7,  # ROE约27.7% (周期高位)
        roa=12.5,  # ROA约12.5%
        fcf_to_net_income=1.33,  # FCF/净利润 = 62.98/47.29 = 1.33
        gross_margin=22.0,  # 毛利率约22%
        operating_margin=15.9,  # 营业利润率15.9%
        payout_ratio=25.0,  # 分红率约25%
        dividend_growth_rate=10.0,  # 分红增长率
        # 历史数据 (估算，需实际数据)
        historical_pb=[1.2, 1.5, 1.8, 2.2, 1.6],
        historical_pe=[8.0, 12.0, 6.5, 10.0, 7.5],
        historical_roe=[8.0, 12.0, 18.0, 27.7, 15.0],
        # 规模指标
        market_cap=250e9,  # 市值约250亿 (估算)
        revenue=375.99e9,  # 营业收入375.99亿
        net_income=47.29e9,  # 净利润47.29亿
        total_assets=380e9,  # 总资产约380亿
    )

    print("=" * 80)
    print("云天化 (SH:600096) - 磷化工周期股深度分析报告")
    print("=" * 80)
    print(f"\n公司: {stock.name} ({stock.ticker})")
    print(f"市场: {stock.market_display}")
    print(f"周期类型: {stock.cycle_type.value} ({stock.cycle_strength.display_name})")
    print(f"分析日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"\n当前价格: ¥{stock.current_price:.2f}")
    print(f"市值: ¥{stock.market_cap/1e9:.0f}亿")

    # 行业背景
    print("\n" + "=" * 80)
    print("【行业背景：磷化工周期分析】")
    print("=" * 80)

    print("\n1️⃣  行业概况")
    print("  云天化是中国最大的磷化工企业，主要产品包括:")
    print("  • 磷肥: 磷酸二铵(DAP)、磷酸一铵(MAP)")
    print("  • 氮肥: 尿素")
    print("  • 精细磷化工: 聚甲醛(POM)、饲料级磷酸钙盐")
    print("  • 新能源材料: 磷酸铁锂")

    print("\n2️⃣  周期驱动因素")
    print("  • 农业需求: 粮食价格→化肥需求→磷肥价格")
    print("  • 原料成本: 硫磺、磷矿石、合成氨价格")
    print("  • 供给约束: 磷矿资源稀缺性、环保限产")
    print("  • 政策影响: 出口配额、保供稳价")

    print("\n3️⃣  当前周期位置 (2024-2025)")
    print("  • 磷矿石价格: 900-1040元/吨 (历史高位)")
    print("  • 磷矿石供需: 紧平衡，资源稀缺性凸显")
    print("  • DAP价格: 3658元/吨 (2025年1月)")
    print("  • 磷酸铁锂需求: 快速增长，2024年+49.8%")
    print("  • 行业景气度: 中高位，ROE处于27.7%高位")

    print("\n4️⃣  云天化竞争优势")
    print("  • 资源优势: 磷矿储量约8亿吨，国内最大")
    print("  • 一体化优势: 磷矿-磷肥-精细化工全产业链")
    print("  • 成本优势: 原料高度自给，成本控制能力强")
    print("  • 转型优势: 积极布局磷酸铁锂等新能源材料")

    # 运行周期分析引擎
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

    # 估值汇总
    print(f"\n【估值汇总】")
    fair_values = [v.fair_value for v in result.valuation_results.values()]
    if fair_values:
        avg_fair_value = sum(fair_values) / len(fair_values)
        print(f"  平均公允价值: ¥{avg_fair_value:.2f}")
        print(f"  估值区间: ¥{min(fair_values):.2f} - ¥{max(fair_values):.2f}")
        print(
            f"  当前价格偏离: {((stock.current_price - avg_fair_value) / avg_fair_value * 100):+.1f}%"
        )

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
        print(f"  • 当前处于周期中高位，需谨慎观察")
        print(f"  • 磷矿石资源稀缺性支撑长期价值")
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
    print(f"  • 关注磷矿石价格和化肥需求变化")
    print(f"  • 建议仓位控制在合理范围内")

    # 云天化特有风险
    print(f"\n🔍 云天化特有风险:")
    print(f"  • 资产负债率55%较高，财务杠杆风险")
    print(f"  • 原材料价格波动(硫磺、合成氨)")
    print(f"  • 出口政策不确定性")
    print(f"  • 新能源材料业务盈利不确定性")

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
