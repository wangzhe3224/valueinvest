#!/usr/bin/env python3
"""
寻找A股被低估的大盘股

功能：
1. 获取所有A股股票列表
2. 过滤掉小盘微盘股（市值 < 100亿）
3. 使用价值策略筛选被低估的股票
4. 按综合评分排序输出结果
"""
import sys
from typing import List, Tuple
import pandas as pd
from valueinvest.screener import screen_stocks, ScreeningOutput
from valueinvest.screener.base import BaseFilter, FilterResult, FilterCategory, ScreeningResult


class MarketCapFilter(BaseFilter):
    """市值过滤器 - 过滤小盘微盘股"""

    name = "market_cap"
    description = "Minimum Market Cap (exclude small/micro-cap)"
    category = FilterCategory.QUALITY

    def __init__(self, min_market_cap: float = 100e8):
        """
        Args:
            min_market_cap: 最小市值（元），默认100亿
        """
        self.min_market_cap = min_market_cap

    def apply(self, result: ScreeningResult) -> FilterResult:
        value = result.market_cap
        passed = value >= self.min_market_cap

        if passed:
            reason = f"市值 {value/1e8:.1f}亿 >= {self.min_market_cap/1e8:.1f}亿"
        else:
            reason = f"市值 {value/1e8:.1f}亿 < {self.min_market_cap/1e8:.1f}亿 (小盘股)"

        return self._create_result(passed, reason, value / 1e8, self.min_market_cap / 1e8)


def get_all_ashare_stocks(min_market_cap: float = 100e8) -> List[Tuple[str, str, float]]:
    """
    获取所有A股大盘股

    Args:
        min_market_cap: 最小市值（元），默认100亿

    Returns:
        List of (ticker, name, market_cap) tuples
    """
    print(f"正在获取A股股票列表...")

    try:
        import akshare as ak
    except ImportError:
        print("错误: 需要安装 akshare")
        print("运行: pip install akshare")
        sys.exit(1)

    # 获取所有A股实时数据
    df = ak.stock_zh_a_spot_em()

    print(f"总计 {len(df)} 只A股股票")

    # 过滤大盘股
    stocks = []
    for _, row in df.iterrows():
        ticker = str(row["代码"])
        name = str(row["名称"])
        market_cap = float(row["总市值"]) if pd.notna(row["总市值"]) else 0

        # 过滤条件
        if market_cap >= min_market_cap:
            stocks.append((ticker, name, market_cap))

    # 按市值排序
    stocks.sort(key=lambda x: x[2], reverse=True)

    print(f"市值 >= {min_market_cap/1e8:.0f}亿 的股票: {len(stocks)} 只")

    return stocks


def format_results(output: ScreeningOutput, show_top: int = 20) -> str:
    """格式化筛选结果"""
    lines = []

    # Summary
    lines.append("\n" + "=" * 80)
    lines.append("A股价值股筛选结果")
    lines.append("=" * 80)
    lines.append(f"总计分析: {output.summary.total_stocks} 只")
    lines.append(f"符合条件: {output.summary.qualified_count} 只")
    lines.append(f"未通过: {output.summary.failed_count} 只")
    lines.append(f"错误: {output.summary.error_count} 只")
    lines.append(f"通过率: {output.summary.pass_rate:.1f}%")
    lines.append(f"耗时: {output.summary.duration_seconds:.1f}秒")

    if not output.qualified:
        lines.append("\n没有找到符合条件的股票")
        return "\n".join(lines)

    # Top stocks table
    lines.append(f"\n排名前 {min(show_top, len(output.qualified))} 只股票:")
    lines.append("-" * 80)
    lines.append(
        f"{'排名':>4} {'代码':<8} {'名称':<10} {'评级':>4} {'综合分':>7} {'估值分':>7} "
        f"{'安全边际':>8} {'ROE':>6} {'市值(亿)':>10}"
    )
    lines.append("-" * 80)

    for i, r in enumerate(output.qualified[:show_top], 1):
        name = r.name[:8] if r.name else "-"
        line = (
            f"{i:>4} {r.ticker:<8} {name:<10} {r.grade:>4} "
            f"{r.composite_score:>7.1f} {r.valuation_score:>7.1f} "
            f"{r.margin_of_safety:>+7.1f}% {r.roe:>5.1f}% {r.market_cap/1e8:>9.1f}"
        )
        lines.append(line)

    lines.append("=" * 80)

    # Detailed view for top 5
    lines.append(f"\n排名前 5 详细信息:")
    lines.append("=" * 80)

    for i, r in enumerate(output.qualified[:5], 1):
        lines.append(f"\n【{i}. {r.ticker} - {r.name}】")
        lines.append(f"  综合评级: {r.grade} ({r.composite_score:.1f}分)")
        lines.append(f"  当前价格: ¥{r.current_price:.2f}")
        lines.append(f"  市值: ¥{r.market_cap/1e8:.1f}亿")
        lines.append(f"  ")
        lines.append(f"  【估值】")
        lines.append(f"    公允价值: ¥{r.fair_value_median:.2f}")
        lines.append(f"    安全边际: {r.margin_of_safety:+.1f}%")
        lines.append(f"    评估: {r.valuation_assessment}")
        lines.append(f"    P/E: {r.pe_ratio:.1f}, P/B: {r.pb_ratio:.2f}")
        lines.append(f"  ")
        lines.append(f"  【质量】")
        lines.append(f"    ROE: {r.roe:.1f}%")
        lines.append(f"    FCF收益率: {r.fcf_yield:.2f}%")
        lines.append(f"    Altman Z: {r.altman_z:.2f}")
        lines.append(f"    评估: {r.quality_assessment}")
        lines.append(f"  ")
        lines.append(f"  【其他】")
        lines.append(f"    估值分: {r.valuation_score:.1f}")
        lines.append(f"    质量分: {r.quality_score:.1f}")
        lines.append(f"    情感分: {r.sentiment_score:.1f}")
        lines.append(f"    动量分: {r.momentum_score:.1f}")

        if r.dividend_yield > 0:
            lines.append(f"    股息率: {r.dividend_yield:.2f}%")

        lines.append(f"  ")
        lines.append(f"  通过过滤器: {', '.join(r.passed_filters)}")
        if r.failed_filters:
            lines.append(f"  未通过: {', '.join(r.failed_filters)}")

    return "\n".join(lines)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="寻找A股被低估的大盘股",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 默认：市值>=100亿，使用价值策略
  python find_undervalued_stocks.py
  
  # 市值>=200亿
  python find_undervalued_stocks.py --min-cap 200
  
  # 市值>=500亿，使用质量策略
  python find_undervalued_stocks.py --min-cap 500 --strategy quality
  
  # 包含新闻和内幕分析（较慢）
  python find_undervalued_stocks.py --news --insider
  
  # 自定义价值策略参数
  python find_undervalued_stocks.py --min-mos 25 --min-roe 15 --max-pe 12
        """,
    )

    parser.add_argument(
        "--min-cap", type=float, default=100, help="最小市值（亿元），默认100亿 (default: 100)"
    )
    parser.add_argument(
        "--strategy",
        "-s",
        choices=["value", "growth", "dividend", "quality", "garp"],
        default="value",
        help="筛选策略 (default: value)",
    )
    parser.add_argument(
        "--max-stocks", type=int, default=100, help="最多分析的股票数量，0表示全部 (default: 100)"
    )
    parser.add_argument("--show-top", type=int, default=20, help="显示前N只股票 (default: 20)")
    parser.add_argument("--news", action="store_true", help="包含新闻情感分析")
    parser.add_argument("--insider", action="store_true", help="包含内幕交易分析")
    parser.add_argument(
        "--workers", "-w", type=int, default=10, help="并发工作线程数 (default: 10)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细进度")

    # 策略参数
    parser.add_argument("--min-mos", type=float, help="最小安全边际 %%")
    parser.add_argument("--min-roe", type=float, help="最小ROE %%")
    parser.add_argument("--max-pe", type=float, help="最大P/E")
    parser.add_argument("--max-pb", type=float, help="最大P/B")

    args = parser.parse_args()

    # 获取股票列表
    min_cap_yuan = args.min_cap * 1e8  # 转换为元
    stocks = get_all_ashare_stocks(min_market_cap=min_cap_yuan)

    if not stocks:
        print("没有找到符合市值要求的股票")
        return

    # 限制分析数量
    if args.max_stocks > 0:
        stocks = stocks[: args.max_stocks]
        print(f"将分析前 {len(stocks)} 只股票")

    tickers = [s[0] for s in stocks]

    # 构建策略参数
    strategy_kwargs = {}
    if args.min_mos:
        strategy_kwargs["min_mos"] = args.min_mos
    if args.min_roe:
        strategy_kwargs["min_roe"] = args.min_roe
    if args.max_pe:
        strategy_kwargs["max_pe"] = args.max_pe
    if args.max_pb:
        strategy_kwargs["max_pb"] = args.max_pb

    # 添加市值过滤器到策略
    # Note: 需要手动创建自定义策略并添加市值过滤器
    from valueinvest.screener.strategies import get_strategy

    strategy = get_strategy(args.strategy, **strategy_kwargs)
    # 将市值过滤器添加到策略的过滤器列表开头
    strategy.filters.insert(0, MarketCapFilter(min_market_cap=min_cap_yuan))

    print(f"\n开始筛选...")
    print(f"策略: {args.strategy}")
    print(f"市值要求: >= {args.min_cap}亿")
    if strategy_kwargs:
        print(f"自定义参数: {strategy_kwargs}")

    # 运行筛选
    from valueinvest.screener.pipeline import ScreeningPipeline

    pipeline = ScreeningPipeline(
        strategy_name=args.strategy,
        strategy_kwargs=strategy_kwargs,
        max_workers=args.workers,
        include_news=args.news,
        include_insider=args.insider,
        verbose=args.verbose,
    )
    # 替换策略以包含市值过滤器
    pipeline.strategy = strategy

    output = pipeline.screen(tickers)

    # 输出结果
    print(format_results(output, show_top=args.show_top))

    # 保存结果
    save_file = f"screening_results_{args.strategy}.json"
    import json
    from datetime import datetime

    result_data = {
        "timestamp": datetime.now().isoformat(),
        "strategy": args.strategy,
        "min_market_cap": args.min_cap,
        "summary": {
            "total": output.summary.total_stocks,
            "qualified": output.summary.qualified_count,
            "pass_rate": output.summary.pass_rate,
        },
        "results": [r.to_dict() for r in output.qualified],
    }

    with open(save_file, "w", encoding="utf-8") as f:
        json.dump(result_data, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存到: {save_file}")


if __name__ == "__main__":
    main()
