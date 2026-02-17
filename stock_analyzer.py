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
    
    print(f"\n正在获取 {ticker} 基本面数据...")
    
    try:
        stock = Stock.from_api(ticker)
    except Exception as e:
        print(f"错误: 无法获取基本面数据 - {e}")
        sys.exit(1)
    
    print(f"正在获取 {ticker} 价格历史...")
    
    try:
        history = Stock.fetch_price_history(ticker, period=history_period)
    except Exception as e:
        print(f"警告: 无法获取价格历史 - {e}")
        history = StockHistory(ticker=ticker)
    
    if company_type == "auto":
        company_type = detect_company_type(stock, history)
    
    set_valuation_params(stock, company_type, history)
    
    print_report(stock, history, company_type, history_period)


def detect_company_type(stock: Stock, history: StockHistory) -> str:
    
    UTILITIES_TICKERS = {
        "600900", "601985", "600011", "600795", "600886",
        "000539", "000543", "000600", "001896",
    }
    
    if stock.ticker in UTILITIES_TICKERS:
        return "dividend"
    
    BANK_TICKERS = {
        "601398", "601288", "600036", "601166", "600000",
        "601988", "600016", "601818", "600015", "601998",
        "002142", "600919", "601229", "600908", "601838",
    }
    
    if stock.ticker in BANK_TICKERS:
        return "bank"
    
    if stock.dividend_yield and stock.dividend_yield > 3:
        return "dividend"
    
    real_cagr = history.cagr_hfq if history.cagr_hfq != 0 else history.cagr
    
    if real_cagr and real_cagr > 10:
        return "growth"
    
    if real_cagr and real_cagr < 5:
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


def print_report(stock: Stock, history: StockHistory, company_type: str, history_period: str = "5y"):
    engine = ValuationEngine()
    
    if company_type == "bank":
        results = engine.run_bank(stock)
    elif company_type == "dividend":
        results = engine.run_dividend(stock)
    elif company_type == "growth":
        results = engine.run_growth(stock)
    else:
        results = engine.run_all(stock)
    
    valid_results = [r for r in results if r.fair_value and r.fair_value > 0 and "Error" not in r.assessment]
    
    print("\n" + "=" * 70)
    print(f"{stock.name} ({stock.ticker}) - 深度分析报告")
    print("=" * 70)
    
    print(f"\n【公司概况】")
    print(f"  公司: {stock.name}")
    print(f"  代码: {stock.ticker}")
    print(f"  类型: {get_type_label(company_type)}")
    print(f"  当前股价: ¥{stock.current_price:.2f}")
    print(f"  总市值: ¥{stock.current_price * stock.shares_outstanding / 1e8:.0f}亿")
    
    print(f"\n【最新财务数据】")
    if stock.revenue:
        print(f"  营业收入: ¥{stock.revenue/1e8:.0f}亿")
    if stock.net_income:
        print(f"  净利润: ¥{stock.net_income/1e8:.0f}亿")
    print(f"  每股收益 (EPS): ¥{stock.eps:.2f}")
    print(f"  每股净资产 (BVPS): ¥{stock.bvps:.2f}")
    print(f"  市盈率 (PE): {stock.pe_ratio:.1f}倍")
    print(f"  市净率 (PB): {stock.pb_ratio:.2f}倍")
    
    print(f"\n【历史表现 ({history_period})】")
    if history.prices:
        print(f"  股价CAGR (qfq): {history.cagr:.2f}%")
        print(f"  真实回报 (hfq): {history.cagr_hfq:.2f}%")
        print(f"  年化波动率: {history.volatility:.2f}%")
        print(f"  最大回撤: {history.max_drawdown:.2f}%")
        
        recent_stats = history.get_price_stats(days=30, adjust="qfq")
        if recent_stats:
            print()
            print(f"【近30日价格 (QFQ前复权)】")
            print(f"  最高: ¥{recent_stats['high']:.2f}")
            print(f"  最低: ¥{recent_stats['low']:.2f}")
            print(f"  均价: ¥{recent_stats['avg']:.2f}")
            print(f"  最新: ¥{recent_stats['latest']:.2f}")
            print(f"  涨跌幅: {recent_stats['change_pct']:+.2f}%")
        
        if history.cagr_hfq != 0:
            print()
            print(f"【真实投资回报 (HFQ后复权)】")
            print(f"  含分红再投资CAGR: {history.cagr_hfq:.2f}%")
            stats_hfq = history.get_price_stats(days=30, adjust="hfq")
            if stats_hfq:
                print(f"  (后复权价格: ¥{stats_hfq['latest']:.0f})")
        
        recent_prices = history.get_recent_prices(days=10, adjust="qfq")
        if recent_prices:
            print()
            print(f"【近10日收盘价 (QFQ)】")
            for i, p in enumerate(recent_prices[-10:]):
                change = ""
                if i > 0:
                    prev_close = recent_prices[i - 1]["close"]
                    if prev_close > 0:
                        change = f" ({(p['close']/prev_close - 1)*100:+.2f}%)"
                print(f"  {p['date']}: ¥{p['close']:.2f}{change}")
        
        print()
        print("  注: QFQ(前复权)用于与估值比较, HFQ(后复权)反映真实含分红回报")
    else:
        print("  (无历史价格数据)")
    
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
