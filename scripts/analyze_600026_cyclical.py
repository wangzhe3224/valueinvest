"""
中远海能（600026）周期性分析脚本
"""

import json
from valueinvest.cyclical import (
    CyclicalStock,
    CyclicalAnalysisEngine,
    CycleType,
    MarketType,
    CycleStrength,
    CyclePositionScorer,
    IndicatorCategory,
    CycleIndicator,
)


def main():
    # 从之前获取的数据中提取关键信息
    # 基本数据来自 fetch_stock_data.py 的输出

    stock = CyclicalStock(
        ticker="600026",
        name="中远海能",
        market=MarketType.A_SHARE,
        current_price=22.72,
        cycle_type=CycleType.SHIPPING,
        cycle_strength=CycleStrength.STRONG,
        # 基本面数据
        pb=3.32,  # 从输出中获取
        bvps=6.85,
        eps=0.57,
        pe=39.8,
        fcf_yield=0.019,  # FCF / Market Cap = 23.78亿 / 1241.7亿 = 1.9%
        fcf_per_share=0.44,  # FCF / Shares = 23.78亿 / 54.65亿
        fcf_to_net_income=0.87,  # FCF / Net Income
        dividend_yield=0.0,
        debt_ratio=0.29,  # Net Debt / (Net Debt + Equity)
        roe=0.0,  # 需要从其他数据源获取
        operating_margin=20.43,
        # 历史PB数据（模拟，实际应从历史数据获取）
        historical_pb=[1.2, 1.5, 1.8, 2.2, 2.8, 3.5, 3.2],
    )

    # 创建评分器并添加指标
    scorer = CyclePositionScorer(market=MarketType.A_SHARE)

    # 添加估值指标 - PB在历史高位（约80%分位）
    scorer.add_indicator(
        CycleIndicator(
            name="PB估值",
            value=stock.pb,
            category=IndicatorCategory.VALUATION,
            percentile=80.0,  # PB在历史高位
            weight=1.0,
        )
    )

    # 添加财务指标 - ROE为0（可能缺少数据）
    scorer.add_indicator(
        CycleIndicator(
            name="ROE",
            value=0.0,
            category=IndicatorCategory.FINANCIAL,
            percentile=50.0,  # ROE数据缺失，假设中等
            weight=0.8,  # 降低权重
        )
    )

    # 添加行业指标（模拟航运数据）
    # BDI指数在中等偏低位置
    scorer.add_indicator(
        CycleIndicator(
            name="BDI指数",
            value=1500,  # BDI指数
            category=IndicatorCategory.INDUSTRY,
            percentile=35.0,  # BDI在低位偏中
            weight=1.0,
        )
    )

    # VLCC运价在中等位置
    scorer.add_indicator(
        CycleIndicator(
            name="VLCC运价",
            value=45000,  # VLCC日租金（美元/天）
            category=IndicatorCategory.INDUSTRY,
            percentile=40.0,  # VLCC运价在40%分位
            weight=1.0,
        )
    )

    # 计算周期位置
    cycle_score = scorer.calculate_score()
    stock.current_phase = cycle_score.phase
    stock.cycle_score = cycle_score

    # 运行完整分析
    engine = CyclicalAnalysisEngine()
    result = engine.analyze(stock)

    # 手动更新周期分析结果（因为engine会重新计算）
    result.cycle_analysis = cycle_score

    # 输出JSON格式结果
    output = {
        "ticker": result.stock.ticker,
        "name": result.stock.name,
        "current_price": result.stock.current_price,
        "cycle_analysis": {
            "phase": result.cycle_analysis.phase.value,
            "phase_display": result.cycle_analysis.phase_display,
            "phase_emoji": result.cycle_analysis.phase_emoji,
            "total_score": result.cycle_analysis.total_score,
            "confidence": result.cycle_analysis.confidence,
            "assessment": result.cycle_analysis.assessment,
            "rationale": result.cycle_analysis.rationale,
        },
        "valuation_results": {},
        "strategy_recommendation": None,
        "buy_checklist": None,
        "sell_checklist": None,
        "risks": result.risks,
        "catalysts": result.catalysts,
        "overall_score": result.overall_score,
        "investment_rating": result.investment_rating,
        "risk_level": result.risk_level,
    }

    # 估值结果
    if result.valuation_results:
        for method, val_result in result.valuation_results.items():
            output["valuation_results"][method] = {
                "method": val_result.method,
                "fair_value": val_result.fair_value,
                "current_value": val_result.current_value,
                "premium_discount": val_result.premium_discount,
                "assessment": val_result.assessment,
                "action": val_result.action,
            }

    # 策略建议
    if result.strategy_recommendation:
        rec = result.strategy_recommendation
        output["strategy_recommendation"] = {
            "action": rec.action.value,
            "action_display": rec.action_display,
            "action_signal": rec.action_signal,
            "target_allocation": rec.target_allocation,
            "target_price": rec.target_price,
            "stop_loss_price": rec.stop_loss_price,
            "expected_return": rec.expected_return,
            "holding_period": rec.holding_period,
            "strategy_type": rec.strategy_type.value,
            "rationale": rec.rationale,
        }

    # 买入清单
    if result.buy_checklist:
        output["buy_checklist"] = {
            "passed_count": result.buy_checklist.passed_count,
            "total_count": result.buy_checklist.total_count,
            "items": result.buy_checklist.items,
        }

    # 卖出清单
    if result.sell_checklist:
        output["sell_checklist"] = {
            "passed_count": result.sell_checklist.passed_count,
            "total_count": result.sell_checklist.total_count,
            "items": result.sell_checklist.items,
        }

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
