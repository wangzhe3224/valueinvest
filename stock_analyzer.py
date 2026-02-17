#!/usr/bin/env python3
"""
Stock Analysis Tool - 多维度股票估值分析

Usage:
    python stock_analyzer.py 600887           # A股伊利股份
    python stock_analyzer.py AAPL             # 美股苹果
    python stock_analyzer.py 601398 --bank    # 银行股分析
"""
import argparse
import sys
from datetime import datetime

from valueinvest import Stock, StockHistory, ValuationEngine


def analyze_stock(ticker: str, company_type: str = "auto", history_period: str = "5y"):
    """执行股票分析并生成报告"""
    
    print(f"\n正在获取 {ticker} 数据...")
    
    # 获取数据
    try:
        stock, history = Stock.from_api_with_history(ticker, history_period=history_period)
    except Exception as e:
        print(f"错误: 无法获取数据 - {e}")
        sys.exit(1)
    
    # 自动检测公司类型
    if company_type == "auto":
        company_type = detect_company_type(stock, history)
    
    # 设置估值参数
    set_valuation_params(stock, company_type, history)
    
    # 生成报告
    print_report(stock, history, company_type)


def detect_company_type(stock: Stock, history: StockHistory) -> str:
    """根据财务特征检测公司类型"""
    
    # 银行特征: 代码以601或600开头的金融股
    if stock.ticker.startswith(("601", "600")) and stock.ticker[2:4] in ["398", "288", "988", "166"]:
        return "bank"
    
    # 高分红
    if stock.dividend_yield and stock.dividend_yield > 3:
        return "dividend"
    
    # 高增长
    if history.cagr and history.cagr > 10:
        return "growth"
    
    # 低增长/价值股
    if history.cagr and history.cagr < 5:
        return "value"
    
    return "general"


def set_valuation_params(stock: Stock, company_type: str, history: StockHistory):
    """根据公司类型设置估值参数"""
    
    # 通用参数
    stock.cost_of_capital = 9.0
    stock.discount_rate = 9.0
    stock.terminal_growth = 2.5
    
    # 使用历史CAGR作为增长率参考（如果为负则使用保守估计）
    if history.cagr and history.cagr > 0:
        stock.growth_rate = min(history.cagr, 10)  # 上限10%
    else:
        stock.growth_rate = 3.0
    
    stock.growth_rate_1_5 = stock.growth_rate
    stock.growth_rate_6_10 = stock.growth_rate * 0.6  # 后期增长放缓
    
    # 根据类型调整
    if company_type == "bank":
        stock.growth_rate = min(stock.growth_rate, 5)
        stock.growth_rate_1_5 = stock.growth_rate
        stock.growth_rate_6_10 = stock.growth_rate * 0.5
    elif company_type == "dividend":
        stock.dividend_growth_rate = min(stock.growth_rate, 5)
    elif company_type == "growth":
        stock.cost_of_capital = 10.0  # 成长股要求更高回报
        stock.discount_rate = 10.0


def print_report(stock: Stock, history: StockHistory, company_type: str):
    """打印分析报告"""
    
    engine = ValuationEngine()
    
    # 运行估值
    if company_type == "bank":
        results = engine.run_bank(stock)
    elif company_type == "dividend":
        results = engine.run_dividend(stock)
    elif company_type == "growth":
        results = engine.run_growth(stock)
    else:
        results = engine.run_all(stock)
    
    # 过滤有效结果
    valid_results = [r for r in results if r.fair_value and r.fair_value > 0 and "Error" not in r.assessment]
    
    # ===== 打印报告 =====
    print("\n" + "=" * 70)
    print(f"{stock.name} ({stock.ticker}) - 深度分析报告")
    print("=" * 70)
    
    # 公司概况
    print(f"\n【公司概况】")
    print(f"  公司: {stock.name}")
    print(f"  代码: {stock.ticker}")
    print(f"  类型: {get_type_label(company_type)}")
    print(f"  当前股价: ¥{stock.current_price:.2f}")
    print(f"  总市值: ¥{stock.current_price * stock.shares_outstanding / 1e8:.0f}亿")
    
    # 财务指标
    print(f"\n【最新财务数据】")
    if stock.revenue:
        print(f"  营业收入: ¥{stock.revenue/1e8:.0f}亿")
    if stock.net_income:
        print(f"  净利润: ¥{stock.net_income/1e8:.0f}亿")
    print(f"  每股收益 (EPS): ¥{stock.eps:.2f}")
    print(f"  每股净资产 (BVPS): ¥{stock.bvps:.2f}")
    print(f"  市盈率 (PE): {stock.pe_ratio:.1f}倍")
    print(f"  市净率 (PB): {stock.pb_ratio:.2f}倍")
    
    # 历史表现
    print(f"\n【历史表现 (5年)】")
    print(f"  股价CAGR: {history.cagr:.2f}%")
    print(f"  年化波动率: {history.volatility:.2f}%")
    print(f"  最大回撤: {history.max_drawdown:.2f}%")
    
    # 估值汇总表
    print("\n" + "=" * 70)
    print("【估值汇总】")
    print("=" * 70)
    print()
    
    sorted_results = sorted(valid_results, key=lambda x: x.fair_value)
    print("| 方法 | 公允价值 | 溢价/折价 | 评估 |")
    print("|------|----------|-----------|------|")
    for r in sorted_results:
        name = r.method[:20]
        print(f"| {name:20} | ¥{r.fair_value:>7.2f} | {r.premium_discount:>+7.1f}% | {r.assessment[:10]:10} |")
    
    # 统计分析
    print()
    fair_values = [r.fair_value for r in valid_results]
    avg_value = sum(fair_values) / len(fair_values)
    median_value = sorted(fair_values)[len(fair_values)//2]
    
    print("【统计汇总】")
    print(f"  有效估值方法数: {len(valid_results)}")
    print(f"  公允价值范围: ¥{min(fair_values):.2f} - ¥{max(fair_values):.2f}")
    print(f"  平均公允价值: ¥{avg_value:.2f}")
    print(f"  中位数公允价值: ¥{median_value:.2f}")
    
    # 综合评估
    avg_premium = ((avg_value - stock.current_price) / stock.current_price) * 100
    
    undervalued = len([r for r in valid_results if r.assessment == "Undervalued"])
    overvalued = len([r for r in valid_results if r.assessment == "Overvalued"])
    
    print()
    print(f"  相对平均值: {avg_premium:+.1f}%")
    print(f"  低估方法数: {undervalued}/{len(valid_results)}")
    print(f"  高估方法数: {overvalued}/{len(valid_results)}")
    
    # 最终结论
    print("\n" + "=" * 70)
    print("【最终结论】")
    print("=" * 70)
    print()
    
    # 确定估值区间
    conservative = sorted(fair_values)[:3]  # 最保守3个
    optimistic = sorted(fair_values)[-3:]   # 最乐观3个
    
    cons_avg = sum(conservative) / len(conservative)
    opt_avg = sum(optimistic) / len(optimistic)
    
    print(f"估值区间: ¥{cons_avg:.0f}-{sorted(fair_values)[len(fair_values)//2]:.0f} (保守) / ¥{stock.current_price:.0f} (现价) / ¥{opt_avg:.0f}+ (乐观)")
    print()
    
    # 综合评级
    if avg_premium < -15:
        rating = "低估 (Undervalued)"
        advice = "当前价格具有安全边际，可考虑建仓"
    elif avg_premium > 15:
        rating = "高估 (Overvalued)"
        advice = "当前价格偏高，等待回调"
    else:
        rating = "合理 (Fair)"
        advice = "当前价格处于合理区间"
    
    print(f"【综合评级】: {rating}")
    print()
    print("投资建议:")
    
    # 目标价和止损价
    target_price = median_value * 0.85  # 15%安全边际
    stop_loss = cons_avg * 0.9  # 最保守估值下浮10%
    
    print(f"  1. 已持有者: {'继续持有' if stock.dividend_yield and stock.dividend_yield > 3 else '持有观望'}")
    print(f"  2. 潜在买入: 等待回调至¥{target_price:.0f}以下")
    print(f"  3. 目标价位: ¥{target_price:.0f} (提供15%+安全边际)")
    print(f"  4. 止损位: ¥{stop_loss:.0f}")
    print()
    
    # 预期回报
    if stock.dividend_yield:
        div_return = stock.dividend_yield
    else:
        div_return = 0
    
    print("预期回报:")
    print(f"  保守: 股息{div_return:.1f}% + 增长0-2% = {div_return:.1f}-{div_return+2:.1f}%/年")
    print(f"  中性: 股息{div_return:.1f}% + 增长{stock.growth_rate:.0f}% = {div_return+stock.growth_rate:.1f}%/年")
    print(f"  乐观: 股息{div_return:.1f}% + 增长{stock.growth_rate*1.5:.0f}% = {div_return+stock.growth_rate*1.5:.1f}%/年")
    print()


def get_type_label(company_type: str) -> str:
    labels = {
        "bank": "银行/金融",
        "dividend": "分红股",
        "growth": "成长股",
        "value": "价值股",
        "general": "一般"
    }
    return labels.get(company_type, "一般")


def main():
    parser = argparse.ArgumentParser(
        description="多维度股票估值分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python stock_analyzer.py 600887           # A股伊利股份
  python stock_analyzer.py AAPL             # 美股苹果
  python stock_analyzer.py 601398 --bank    # 银行股分析
  python stock_analyzer.py 600887 --period 3y  # 3年历史数据
        """
    )
    
    parser.add_argument("ticker", help="股票代码 (如 600887, AAPL)")
    parser.add_argument("--type", "-t", choices=["auto", "bank", "dividend", "growth", "value"],
                        default="auto", help="公司类型 (默认自动检测)")
    parser.add_argument("--bank", "-b", action="store_true", help="银行股分析 (等同于 --type bank)")
    parser.add_argument("--dividend", "-d", action="store_true", help="分红股分析")
    parser.add_argument("--growth", "-g", action="store_true", help="成长股分析")
    parser.add_argument("--period", "-p", default="5y", help="历史数据周期 (默认5y)")
    
    args = parser.parse_args()
    
    if args.bank:
        args.type = "bank"
    elif args.dividend:
        args.type = "dividend"
    elif args.growth:
        args.type = "growth"
    
    args = parser.parse_args()
    
    analyze_stock(args.ticker, args.type, args.period)


if __name__ == "__main__":
    main()
