#!/usr/bin/env python3
"""
CLI for stock screening.

Usage:
    python -m valueinvest.screener.cli --strategy value --tickers 600887,600900
    python -m valueinvest.screener.cli --strategy dividend --file stocks.txt
    python -m valueinvest.screener.cli --list-strategies
"""
import argparse
import json
import sys
from typing import List, Optional

from .base import ScreeningResult
from .pipeline import screen_stocks
from .strategies import list_strategies
from .filters import list_filters


def format_table(results: List[ScreeningResult], show_all: bool = False) -> str:
    """Format screening results as a table."""
    if not results:
        return "No qualified stocks found."

    lines = []

    # Header
    if show_all:
        header = f"{'排名':>4} {'代码':<8} {'名称':<8} {'评级':>4} {'综合分':>7} {'估值分':>7} {'质量分':>7} {'情感分':>7} {'安全边际':>8} {'ROE':>6} {'股息率':>7}"
    else:
        header = f"{'排名':>4} {'代码':<8} {'名称':<8} {'评级':>4} {'综合分':>7} {'估值分':>7} {'质量分':>7} {'安全边际':>8} {'ROE':>6}"

    lines.append("=" * len(header))
    lines.append(header)
    lines.append("-" * len(header))

    # Rows
    for i, r in enumerate(results, 1):
        name = r.name[:6] if r.name else "-"
        if show_all:
            line = (
                f"{i:>4} {r.ticker:<8} {name:<8} {r.grade:>4} "
                f"{r.composite_score:>7.1f} {r.valuation_score:>7.1f} {r.quality_score:>7.1f} "
                f"{r.sentiment_score:>7.1f} {r.margin_of_safety:>+7.1f}% {r.roe:>5.1f}% {r.dividend_yield:>6.2f}%"
            )
        else:
            line = (
                f"{i:>4} {r.ticker:<8} {name:<8} {r.grade:>4} "
                f"{r.composite_score:>7.1f} {r.valuation_score:>7.1f} {r.quality_score:>7.1f} "
                f"{r.margin_of_safety:>+7.1f}% {r.roe:>5.1f}%"
            )
        lines.append(line)

    lines.append("=" * len(header))

    return "\n".join(lines)


def format_detail(result: ScreeningResult) -> str:
    """Format a single result with full details."""
    lines = []
    lines.append(f"\n{'='*60}")
    lines.append(f"{result.ticker} - {result.name or 'Unknown'}")
    lines.append(f"{'='*60}")

    # Basic info
    lines.append(f"\n当前价格: ¥{result.current_price:.2f}")
    lines.append(f"市值: ¥{result.market_cap/1e8:.1f}亿")
    lines.append(f"综合评级: {result.grade} ({result.composite_score:.1f}分)")

    # Scores
    lines.append(f"\n【评分明细】")
    lines.append(f"  估值分: {result.valuation_score:.1f}")
    lines.append(f"  质量分: {result.quality_score:.1f}")
    lines.append(f"  情感分: {result.sentiment_score:.1f}")
    lines.append(f"  动量分: {result.momentum_score:.1f}")

    # Valuation
    lines.append(f"\n【估值指标】")
    lines.append(f"  公允价值(中位数): ¥{result.fair_value_median:.2f}")
    lines.append(f"  安全边际: {result.margin_of_safety:+.1f}%")
    lines.append(f"  估值评估: {result.valuation_assessment}")
    lines.append(f"  P/E: {result.pe_ratio:.1f}")
    lines.append(f"  P/B: {result.pb_ratio:.2f}")
    lines.append(f"  PEG: {result.peg_ratio:.2f}" if result.peg_ratio > 0 else "  PEG: N/A")

    # Quality
    lines.append(f"\n【质量指标】")
    lines.append(f"  ROE: {result.roe:.1f}%")
    lines.append(f"  FCF收益率: {result.fcf_yield:.2f}%")
    lines.append(f"  Altman Z: {result.altman_z:.2f}")
    lines.append(f"  ROIC: {result.roic:.1f}%")
    lines.append(f"  质量评估: {result.quality_assessment}")

    # Dividend
    if result.dividend_yield > 0:
        lines.append(f"\n【分红指标】")
        lines.append(f"  股息率: {result.dividend_yield:.2f}%")
        lines.append(f"  分红率: {result.payout_ratio:.1f}%")
        lines.append(f"  分红增长: {result.dividend_growth_rate:.1f}%")

    # Sentiment
    lines.append(f"\n【情感信号】")
    lines.append(f"  新闻情感: {result.news_sentiment:+.2f}")
    lines.append(f"  内幕交易: {result.insider_sentiment}")
    lines.append(f"  情感评估: {result.sentiment_assessment}")

    # Filters
    if result.passed_filters:
        lines.append(f"\n【通过过滤器】: {', '.join(result.passed_filters)}")
    if result.failed_filters:
        lines.append(f"【未通过过滤器】: {', '.join(result.failed_filters)}")

    return "\n".join(lines)


def parse_tickers(args) -> List[str]:
    """Parse tickers from CLI arguments."""
    tickers = []

    if args.tickers:
        tickers.extend([t.strip() for t in args.tickers.split(",")])

    if args.file:
        try:
            with open(args.file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        tickers.append(line)
        except FileNotFoundError:
            print(f"Error: File not found: {args.file}")
            sys.exit(1)

    if not tickers:
        print("Error: No tickers provided. Use --tickers or --file")
        sys.exit(1)

    return tickers


def main():
    parser = argparse.ArgumentParser(
        description="股票筛选系统 - 多因子策略筛选器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用价值策略筛选股票
  python -m valueinvest.screener.cli --strategy value --tickers 600887,600900,601398

  # 从文件读取股票池
  python -m valueinvest.screener.cli --strategy dividend --file stocks.txt

  # 包含新闻和内幕分析
  python -m valueinvest.screener.cli --strategy quality --tickers AAPL,MSFT --news --insider

  # 输出JSON格式
  python -m valueinvest.screener.cli --strategy garp --tickers 600887 --output json

  # 自定义策略参数
  python -m valueinvest.screener.cli --strategy value --min-mos 25 --min-roe 12
        """,
    )

    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--tickers", "-t", help="股票代码列表，逗号分隔 (e.g., 600887,600900)")
    input_group.add_argument("--file", "-f", help="股票代码文件，每行一个")
    input_group.add_argument(
        "--list-strategies", "-l", action="store_true", help="列出所有可用策略"
    )
    input_group.add_argument("--list-filters", action="store_true", help="列出所有可用过滤器")

    # Strategy options
    parser.add_argument(
        "--strategy",
        "-s",
        default="value",
        choices=["value", "growth", "dividend", "quality", "garp"],
        help="筛选策略 (default: value)",
    )

    # Strategy customization
    parser.add_argument("--min-mos", type=float, help="最小安全边际 %%")
    parser.add_argument("--min-roe", type=float, help="最小ROE %%")
    parser.add_argument("--max-pe", type=float, help="最大P/E")
    parser.add_argument("--max-pb", type=float, help="最大P/B")
    parser.add_argument("--min-dividend", type=float, help="最小股息率 %%")
    parser.add_argument("--min-growth", type=float, help="最小增长率 %%")

    # Data options
    parser.add_argument("--news", action="store_true", help="包含新闻情感分析")
    parser.add_argument("--insider", action="store_true", help="包含内幕交易分析")
    parser.add_argument("--workers", "-w", type=int, default=5, help="并发工作线程数")

    # Output options
    parser.add_argument(
        "--output", "-o", choices=["table", "json", "detail"], default="table", help="输出格式"
    )
    parser.add_argument("--all", "-a", action="store_true", help="显示所有列")
    parser.add_argument("--save", help="保存结果到文件")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细进度")

    args = parser.parse_args()

    # Handle list commands
    if args.list_strategies:
        print("\n可用策略:")
        print("-" * 60)
        for s in list_strategies():
            print(f"\n{s['name'].upper()}: {s['description']}")
            print(f"  默认过滤: {', '.join(s['default_filters'])}")
            print(
                f"  权重: 估值{s['weights']['valuation']}% / 质量{s['weights']['quality']}% / "
                f"情感{s['weights']['sentiment']}% / 动量{s['weights']['momentum']}%"
            )
        return

    if args.list_filters:
        print("\n可用过滤器:")
        print("-" * 60)
        for f in list_filters():
            print(f"  {f['name']:<20} [{f['category']}] {f['description']}")
        return

    # Parse tickers
    tickers = parse_tickers(args)

    # Build strategy kwargs
    strategy_kwargs = {}
    if args.min_mos:
        strategy_kwargs["min_mos"] = args.min_mos
    if args.min_roe:
        strategy_kwargs["min_roe"] = args.min_roe
    if args.max_pe:
        strategy_kwargs["max_pe"] = args.max_pe
    if args.max_pb:
        strategy_kwargs["max_pb"] = args.max_pb
    if args.min_dividend:
        strategy_kwargs["min_yield"] = args.min_dividend
    if args.min_growth:
        strategy_kwargs["min_growth"] = args.min_growth

    # Run screening
    print(f"\n开始筛选...")
    print(f"策略: {args.strategy}")
    print(f"股票池: {len(tickers)} 只")

    result = screen_stocks(
        tickers=tickers,
        strategy=args.strategy,
        max_workers=args.workers,
        include_news=args.news,
        include_insider=args.insider,
        verbose=args.verbose,
        **strategy_kwargs,
    )

    # Print summary
    print(f"\n{'='*60}")
    print(f"筛选结果: {args.strategy.upper()} 策略")
    print(f"{'='*60}")
    print(f"总计: {result.summary.total_stocks} 只")
    print(f"符合条件: {result.summary.qualified_count} 只")
    print(f"未通过: {result.summary.failed_count} 只")
    print(f"错误: {result.summary.error_count} 只")
    print(f"通过率: {result.summary.pass_rate:.1f}%")
    print(f"耗时: {result.summary.duration_seconds:.1f}秒")

    # Output results
    if args.output == "table":
        print("\n" + format_table(result.qualified, show_all=args.all))

    elif args.output == "json":
        output = {
            "summary": {
                "strategy": result.summary.strategy_name,
                "total": result.summary.total_stocks,
                "qualified": result.summary.qualified_count,
                "pass_rate": result.summary.pass_rate,
                "duration": result.summary.duration_seconds,
            },
            "results": [r.to_dict() for r in result.qualified],
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))

    elif args.output == "detail":
        for r in result.qualified[:10]:  # Limit to top 10
            print(format_detail(r))

    # Save if requested
    if args.save:
        output = {
            "summary": {
                "strategy": result.summary.strategy_name,
                "total": result.summary.total_stocks,
                "qualified": result.summary.qualified_count,
                "pass_rate": result.summary.pass_rate,
                "duration": result.summary.duration_seconds,
            },
            "results": [r.to_dict() for r in result.qualified],
            "disqualified": [r.to_dict() for r in result.disqualified],
            "errors": result.errors,
        }
        with open(args.save, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"\n结果已保存到: {args.save}")


if __name__ == "__main__":
    main()
