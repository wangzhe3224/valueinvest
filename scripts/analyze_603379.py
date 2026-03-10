#!/usr/bin/env python3
"""
三美股份 (603379) 周期性分析脚本
"""

from valueinvest.cyclical import (
    CyclicalAnalysisEngine,
    CyclicalStock,
    CycleType,
    MarketType,
    CycleStrength,
)
import json

# 创建股票数据
stock = CyclicalStock(
    ticker="603379",
    name="三美股份",
    market=MarketType.A_SHARE,
    current_price=76.68,
    cycle_type=CycleType.COMMODITY,  # 氟化工产品价格周期
    cycle_strength=CycleStrength.MODERATE,
    # 估值指标
    pb=6.15,
    pe=29.49,
    bvps=12.47,
    eps=2.60,
    # 财务指标
    roe=0.2233,  # 22.33%
    operating_margin=0.3567,  # 35.67%
    debt_ratio=0.1743,  # 17.43%
    # FCF数据（估算）
    fcf_yield=0.08,  # 8% 估算
    fcf_per_share=6.13,  # 估算
    fcf_to_net_income=0.37,  # FCF/净利润 比率
    # 分红数据
    dividend_yield=0.00,  # 无分红
    # 历史PB（用于周期性分析）
    historical_pb=[4.04, 3.26, 3.08, 3.11, 3.36, 3.89],
)

# 运行完整分析
engine = CyclicalAnalysisEngine()
result = engine.analyze(stock)

# 输出结果
print("=" * 80)
print(f"股票: {result.stock.name} ({result.stock.ticker})")
print("=" * 80)
print()

print("【周期分析】")
print(f"周期阶段: {result.cycle_analysis.phase_display}")
print(f"周期得分: {result.cycle_analysis.total_score:.2f}/5.0")
print(f"  - 估值得分: {result.cycle_analysis.valuation_score:.2f}/5.0")
print(f"  - 财务得分: {result.cycle_analysis.financial_score:.2f}/5.0")
print(f"  - 行业得分: {result.cycle_analysis.industry_score:.2f}/5.0")
print(f"  - 情绪得分: {result.cycle_analysis.sentiment_score:.2f}/5.0")
print()

print("【估值结果】")
if result.valuation_results:
    for val_result in result.valuation_results:
        print(f"  - {val_result}")
else:
    print("  无估值结果")
print()

print("【综合评分】")
print(f"综合得分: {result.overall_score}/100")
print(f"投资评级: {result.investment_rating}")
print()

print("【投资建议】")
if result.strategy_recommendation:
    print(f"投资行动: {result.strategy_recommendation.action_display}")
    print(f"建议仓位: {result.strategy_recommendation.target_allocation:.1%}")
    if result.strategy_recommendation.target_price:
        print(f"目标价格: ¥{result.strategy_recommendation.target_price:.2f}")
print()

print("【风险提示】")
if result.risks:
    for risk in result.risks:
        print(f"  ⚠️ {risk}")
else:
    print("  无重大风险")
print()

print("【潜在催化剂】")
if result.catalysts:
    for catalyst in result.catalysts:
        print(f"  ✅ {catalyst}")
else:
    print("  暂无明显催化剂")
print()

print("=" * 80)
print("分析完成")
print("=" * 80)

# 将结果保存为JSON（用于报告生成）
output = {
    "ticker": result.stock.ticker,
    "name": result.stock.name,
    "current_price": result.stock.current_price,
    "cycle_phase": result.cycle_analysis.phase_display,
    "cycle_score": result.cycle_analysis.total_score,
    "overall_score": result.overall_score,
    "investment_rating": result.investment_rating,
    "action": result.strategy_recommendation.action_display
    if result.strategy_recommendation
    else None,
    "target_allocation": result.strategy_recommendation.target_allocation
    if result.strategy_recommendation
    else None,
    "target_price": result.strategy_recommendation.target_price
    if result.strategy_recommendation
    else None,
    "risks": result.risks,
    "catalysts": result.catalysts,
}

print("\n【JSON输出】")
print(json.dumps(output, ensure_ascii=False, indent=2))
