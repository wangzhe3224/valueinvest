#!/usr/bin/env python3
"""
演示版本：使用示例股票列表筛选被低估的大盘股

如果网络获取全部A股失败，使用此脚本
"""
from valueinvest.screener import screen_stocks
import json
from datetime import datetime

# 预定义的大盘股列表（市值>=200亿）
DEMO_STOCKS = [
    # 消费
    "600887",  # 伊利股份
    "000858",  # 五粮液
    "000568",  # 泸州老窖
    "000333",  # 美的集团
    "000651",  # 格力电器
    # 金融
    "601398",  # 工商银行
    "601288",  # 农业银行
    "601939",  # 建设银行
    "601318",  # 中国平安
    "600036",  # 招商银行
    # 公用事业
    "600900",  # 长江电力
    "601985",  # 中国核电
    # 能源
    "601857",  # 中国石油
    "600028",  # 中国石化
    "601088",  # 中国神华
    # 科技
    "000725",  # 京东方A
    "002415",  # 海康威视
    "002475",  # 立讯精密
    # 基建
    "601668",  # 中国建筑
    "601390",  # 中国中铁
    # 医药
    "600276",  # 恒瑞医药
    "000661",  # 长春高新
    # 新能源
    "300750",  # 宁德时代
    "002594",  # 比亚迪
]


def main():
    print("=" * 80)
    print("A股价值股筛选（演示版）")
    print("=" * 80)
    print(f"\n股票池: {len(DEMO_STOCKS)} 只大盘股")
    print("策略: 价值策略（MOS>=20%, ROE>=10%, PE<=15）")
    print("\n开始筛选...\n")

    # 运行筛选
    result = screen_stocks(
        tickers=DEMO_STOCKS,
        strategy="value",
        max_workers=5,
        include_news=False,
        include_insider=False,
        verbose=True,
    )

    # 输出结果
    print("\n" + "=" * 80)
    print("筛选结果")
    print("=" * 80)
    print(f"总计分析: {result.summary.total_stocks} 只")
    print(f"符合条件: {result.summary.qualified_count} 只")
    print(f"未通过: {result.summary.failed_count} 只")
    print(f"错误: {result.summary.error_count} 只")
    print(f"通过率: {result.summary.pass_rate:.1f}%")
    print(f"耗时: {result.summary.duration_seconds:.1f}秒")

    if not result.qualified:
        print("\n没有找到符合条件的股票")
        print("\n建议:")
        print("1. 放宽筛选条件")
        print("2. 尝试其他策略 (quality, garp)")
        return

    # 显示结果
    print(f"\n排名前 {len(result.qualified)} 只符合条件的股票:")
    print("-" * 80)
    print(
        f"{'排名':>4} {'代码':<8} {'名称':<10} {'评级':>4} {'综合分':>7} {'估值分':>7} "
        f"{'安全边际':>8} {'ROE':>6} {'市值(亿)':>10}"
    )
    print("-" * 80)

    for i, r in enumerate(result.qualified, 1):
        name = r.name[:8] if r.name else "-"
        line = (
            f"{i:>4} {r.ticker:<8} {name:<10} {r.grade:>4} "
            f"{r.composite_score:>7.1f} {r.valuation_score:>7.1f} "
            f"{r.margin_of_safety:>+7.1f}% {r.roe:>5.1f}% {r.market_cap/1e8:>9.1f}"
        )
        print(line)

    print("=" * 80)

    # 详细信息（前5只）
    print(f"\n前 5 只股票详细信息:")
    print("=" * 80)

    for i, r in enumerate(result.qualified[:5], 1):
        print(f"\n【{i}. {r.ticker} - {r.name}】")
        print(f"  综合评级: {r.grade} ({r.composite_score:.1f}分)")
        print(f"  当前价格: ¥{r.current_price:.2f}")
        print(f"  市值: ¥{r.market_cap/1e8:.1f}亿")
        print(f"  ")
        print(f"  【估值】")
        print(f"    公允价值: ¥{r.fair_value_median:.2f}")
        print(f"    安全边际: {r.margin_of_safety:+.1f}%")
        print(f"    评估: {r.valuation_assessment}")
        print(f"    P/E: {r.pe_ratio:.1f}, P/B: {r.pb_ratio:.2f}")
        print(f"  ")
        print(f"  【质量】")
        print(f"    ROE: {r.roe:.1f}%")
        print(f"    FCF收益率: {r.fcf_yield:.2f}%")
        print(f"    Altman Z: {r.altman_z:.2f}")
        print(f"    评估: {r.quality_assessment}")
        print(f"  ")
        print(f"  【评分明细】")
        print(f"    估值分: {r.valuation_score:.1f}")
        print(f"    质量分: {r.quality_score:.1f}")
        print(f"    情感分: {r.sentiment_score:.1f}")
        print(f"    动量分: {r.momentum_score:.1f}")

        if r.dividend_yield > 0:
            print(f"    股息率: {r.dividend_yield:.2f}%")

        print(f"  ")
        print(f"  通过过滤器: {', '.join(r.passed_filters)}")
        if r.failed_filters:
            print(f"  未通过: {', '.join(r.failed_filters)}")

    # 保存结果
    save_file = "demo_screening_results.json"
    result_data = {
        "timestamp": datetime.now().isoformat(),
        "strategy": "value",
        "summary": {
            "total": result.summary.total_stocks,
            "qualified": result.summary.qualified_count,
            "pass_rate": result.summary.pass_rate,
        },
        "results": [r.to_dict() for r in result.qualified],
    }

    with open(save_file, "w", encoding="utf-8") as f:
        json.dump(result_data, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存到: {save_file}")


if __name__ == "__main__":
    main()
