def print_cyclical_analysis(cyclical_result):
    """打印周期股分析结果"""
    if not cyclical_result:
        return

    print("\n" + "=" * 70)
    print("【周期股分析】")
    print("=" * 70)
    print()

    # 周期位置
    cycle = cyclical_result.cycle_analysis
    print(f"  周期阶段: {cycle.phase_display} {cycle.phase_emoji}")
    print(f"  周期得分: {cycle.total_score:.2f}/5.0")
    print(f"  置信度: {cycle.confidence}")
    print(f"  评估: {cycle.assessment}")

    # 估值分析
    if cyclical_result.valuation_results:
        print()
        print("【估值分析】")
        print("| 方法 | 公允价值 | 溢价/折价 | 评估 | 行动 |")
        print("|------|----------|-----------|------|------|")
        for method, result in cyclical_result.valuation_results.items():
            fair_val = f"¥{result.fair_value:.2f}"
            premium = f"{result.premium_discount:+.1f}%"
            assess = result.assessment
            action = result.action
            print(f"| {result.method} | {fair_val} | {premium} | {assess} | {action} |")

    # 策略建议
    if cyclical_result.strategy_recommendation:
        rec = cyclical_result.strategy_recommendation
        print()
        print("【策略建议】")
        print(f"  投资行动: {rec.action_display} {rec.action_signal}")
        print(f"  建议仓位: {rec.target_allocation:.1%}")
        print(f"  目标价格: ¥{rec.target_price:.2f}")
        print(f"  止损价格: ¥{rec.stop_loss_price:.2f}")
        print(f"  预期收益: {rec.expected_return:.1f}%")
        print(f"  持有周期: {rec.holding_period}")
        print(f"  策略类型: {rec.strategy_type.value}")

        if rec.rationale:
            print()
            print("  投资理由:")
            for reason in rec.rationale:
                print(f"    • {reason}")

    # 买入清单
    if cyclical_result.buy_checklist:
        checklist = cyclical_result.buy_checklist
        print()
        print(f"【买入清单】 (通过 {checklist.passed_count}/{checklist.total_count} 项)")
        for item, passed in checklist.items.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {item}")

    # 卖出清单
    if cyclical_result.sell_checklist:
        checklist = cyclical_result.sell_checklist
        print()
        print(f"【卖出清单】 (触发 {checklist.passed_count}/{checklist.total_count} 项)")
        for item, passed in checklist.items.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {item}")

    # 风险和催化剂
    if cyclical_result.risks:
        print()
        print("【风险提示】")
        for risk in cyclical_result.risks:
            print(f"  ⚠️  {risk}")

    if cyclical_result.catalysts:
        print()
        print("【潜在催化剂】")
        for catalyst in cyclical_result.catalysts:
            print(f"  ✅ {catalyst}")

    # 综合评分
    print()
    print("【综合评估】")
    print(f"  综合评分: {cyclical_result.overall_score}/100")
    print(f"  投资评级: {cyclical_result.investment_rating}")
    print(f"  风险等级: {cyclical_result.risk_level}")
