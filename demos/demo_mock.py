#!/usr/bin/env python3
"""
模拟演示版本：使用模拟数据展示筛选系统

当网络不可用时，使用此脚本了解系统如何工作
"""
from valueinvest.screener.base import ScreeningResult
from valueinvest.screener.pipeline import ScreeningOutput, ScreeningSummary
from datetime import datetime
import json

# 模拟数据（基于真实市场情况的合理估计）
MOCK_STOCKS = [
    {
        "ticker": "600887",
        "name": "伊利股份",
        "current_price": 26.50,
        "market_cap": 1675e8,
        "composite_score": 72.5,
        "valuation_score": 78.3,
        "quality_score": 70.2,
        "sentiment_score": 65.0,
        "momentum_score": 68.5,
        "fair_value_median": 32.15,
        "margin_of_safety": 21.3,
        "roe": 18.3,
        "fcf_yield": 5.2,
        "altman_z": 3.45,
        "pe_ratio": 16.2,
        "pb_ratio": 2.97,
        "dividend_yield": 3.5,
        "is_qualified": True,
        "passed_filters": ["margin_of_safety", "roe", "altman_z", "pe_ratio"],
        "failed_filters": [],
    },
    {
        "ticker": "600900",
        "name": "长江电力",
        "current_price": 28.80,
        "market_cap": 6600e8,
        "composite_score": 69.8,
        "valuation_score": 65.2,
        "quality_score": 75.8,
        "sentiment_score": 70.0,
        "momentum_score": 62.3,
        "fair_value_median": 33.50,
        "margin_of_safety": 16.3,
        "roe": 14.2,
        "fcf_yield": 4.8,
        "altman_z": 3.12,
        "pe_ratio": 20.3,
        "pb_ratio": 2.85,
        "dividend_yield": 4.2,
        "is_qualified": False,
        "passed_filters": ["roe", "altman_z"],
        "failed_filters": ["margin_of_safety", "pe_ratio"],
    },
    {
        "ticker": "601398",
        "name": "工商银行",
        "current_price": 5.05,
        "market_cap": 18000e8,
        "composite_score": 71.2,
        "valuation_score": 76.5,
        "quality_score": 68.9,
        "sentiment_score": 62.0,
        "momentum_score": 58.5,
        "fair_value_median": 5.98,
        "margin_of_safety": 18.4,
        "roe": 11.8,
        "fcf_yield": 6.5,
        "altman_z": 2.85,
        "pe_ratio": 4.3,
        "pb_ratio": 0.52,
        "dividend_yield": 6.2,
        "is_qualified": False,
        "passed_filters": ["margin_of_safety", "pe_ratio"],
        "failed_filters": ["roe", "altman_z"],
    },
    {
        "ticker": "000858",
        "name": "五粮液",
        "current_price": 142.50,
        "market_cap": 5530e8,
        "composite_score": 58.3,
        "valuation_score": 45.2,
        "quality_score": 72.5,
        "sentiment_score": 60.0,
        "momentum_score": 55.8,
        "fair_value_median": 125.80,
        "margin_of_safety": -11.7,
        "roe": 22.5,
        "fcf_yield": 3.8,
        "altman_z": 4.12,
        "pe_ratio": 28.5,
        "pb_ratio": 6.32,
        "dividend_yield": 2.1,
        "is_qualified": False,
        "passed_filters": ["roe", "altman_z"],
        "failed_filters": ["margin_of_safety", "pe_ratio"],
    },
    {
        "ticker": "000333",
        "name": "美的集团",
        "current_price": 68.20,
        "market_cap": 4770e8,
        "composite_score": 62.5,
        "valuation_score": 58.3,
        "quality_score": 68.9,
        "sentiment_score": 65.0,
        "momentum_score": 57.2,
        "fair_value_median": 72.50,
        "margin_of_safety": 6.3,
        "roe": 16.8,
        "fcf_yield": 4.5,
        "altman_z": 3.28,
        "pe_ratio": 14.2,
        "pb_ratio": 3.15,
        "dividend_yield": 3.8,
        "is_qualified": False,
        "passed_filters": ["roe", "altman_z", "pe_ratio"],
        "failed_filters": ["margin_of_safety"],
    },
]


def create_mock_results():
    """创建模拟筛选结果"""
    results = []
    for data in MOCK_STOCKS:
        result = ScreeningResult(ticker=data["ticker"])
        result.name = data["name"]
        result.current_price = data["current_price"]
        result.market_cap = data["market_cap"]
        result.composite_score = data["composite_score"]
        result.valuation_score = data["valuation_score"]
        result.quality_score = data["quality_score"]
        result.sentiment_score = data["sentiment_score"]
        result.momentum_score = data["momentum_score"]
        result.fair_value_median = data["fair_value_median"]
        result.margin_of_safety = data["margin_of_safety"]
        result.roe = data["roe"]
        result.fcf_yield = data["fcf_yield"]
        result.altman_z = data["altman_z"]
        result.pe_ratio = data["pe_ratio"]
        result.pb_ratio = data["pb_ratio"]
        result.dividend_yield = data["dividend_yield"]
        result.is_qualified = data["is_qualified"]
        result.passed_filters = data["passed_filters"]
        result.failed_filters = data["failed_filters"]
        results.append(result)

    return results


def main():
    print("=" * 80)
    print("A股价值股筛选系统（模拟演示）")
    print("=" * 80)
    print("\n⚠️  注意: 这是模拟数据，用于演示系统功能")
    print("网络恢复后，运行真实版本: python find_undervalued_stocks.py\n")

    # 创建模拟结果
    results = create_mock_results()

    # 按综合评分排序
    results.sort(key=lambda x: x.composite_score, reverse=True)

    qualified = [r for r in results if r.is_qualified]
    disqualified = [r for r in results if not r.is_qualified]

    # 输出结果
    print("=" * 80)
    print("筛选结果（价值策略：MOS>=20%, ROE>=10%, PE<=15, Z>=2.99）")
    print("=" * 80)
    print(f"总计分析: {len(results)} 只")
    print(f"符合条件: {len(qualified)} 只")
    print(f"未通过: {len(disqualified)} 只")
    print(f"通过率: {len(qualified)/len(results)*100:.1f}%")

    if qualified:
        print(f"\n✅ 符合条件的股票 ({len(qualified)}只):")
        print("-" * 80)
        print(
            f"{'排名':>4} {'代码':<8} {'名称':<10} {'评级':>4} {'综合分':>7} {'安全边际':>8} {'ROE':>6} {'PE':>6}"
        )
        print("-" * 80)

        for i, r in enumerate(qualified, 1):
            line = (
                f"{i:>4} {r.ticker:<8} {r.name:<10} {r.grade:>4} "
                f"{r.composite_score:>7.1f} {r.margin_of_safety:>+7.1f}% "
                f"{r.roe:>5.1f}% {r.pe_ratio:>5.1f}"
            )
            print(line)

        # 详细信息
        print(f"\n详细分析（前 {min(3, len(qualified))} 只）:")
        print("=" * 80)

        for i, r in enumerate(qualified[:3], 1):
            print(f"\n【{i}. {r.ticker} - {r.name}】")
            print(f"  综合评级: {r.grade} ({r.composite_score:.1f}分)")
            print(f"  当前价格: ¥{r.current_price:.2f}")
            print(f"  市值: ¥{r.market_cap/1e8:.1f}亿")
            print(f"  ")
            print(f"  【估值分析】")
            print(f"    公允价值: ¥{r.fair_value_median:.2f}")
            print(f"    安全边际: {r.margin_of_safety:+.1f}%")
            print(f"    评估: {r.valuation_assessment}")
            print(f"    P/E: {r.pe_ratio:.1f}, P/B: {r.pb_ratio:.2f}")
            print(f"  ")
            print(f"  【质量指标】")
            print(f"    ROE: {r.roe:.1f}%")
            print(f"    FCF收益率: {r.fcf_yield:.2f}%")
            print(f"    Altman Z: {r.altman_z:.2f} ({'安全区' if r.altman_z >= 3 else '警戒区'})")
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
            print(f"  ✅ 通过: {', '.join(r.passed_filters)}")

    # 显示接近符合条件的股票
    print(f"\n⚠️  接近符合条件 ({len(disqualified)}只):")
    print("-" * 80)
    print(f"{'排名':>4} {'代码':<8} {'名称':<10} {'评级':>4} {'综合分':>7} {'未通过过滤器':<30}")
    print("-" * 80)

    for i, r in enumerate(disqualified, 1):
        failed = ", ".join(r.failed_filters)
        line = (
            f"{i:>4} {r.ticker:<8} {r.name:<10} {r.grade:>4} "
            f"{r.composite_score:>7.1f} {failed:<30}"
        )
        print(line)

    print("=" * 80)

    # 投资建议
    print("\n【投资建议】")
    print("-" * 80)
    if qualified:
        print(f"1. 重点关注: {', '.join([r.ticker for r in qualified])}")
        print(f"2. 这些股票满足价值投资的核心标准")
        print(f"3. 建议进一步研究基本面和行业前景")
    else:
        print("1. 当前市场估值偏高，严格价值标准难以找到标的")
        print("2. 可考虑:")
        print("   - 放宽标准（MOS>=15%, PE<=18）")
        print("   - 使用质量策略（寻找优质企业）")
        print("   - 使用GARP策略（合理价格成长）")

    print("\n【下一步】")
    print("-" * 80)
    print("1. 网络恢复后运行真实筛选:")
    print("   python find_undervalued_stocks.py")
    print()
    print("2. 深度分析个股:")
    print("   python stock_analyzer.py 600887 --news --insider")
    print()
    print("3. 尝试其他策略:")
    print("   python find_undervalued_stocks.py --strategy quality")
    print("   python find_undervalued_stocks.py --strategy garp")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
