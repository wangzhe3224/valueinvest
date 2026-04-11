#!/usr/bin/env python3
"""
Stock Analysis Tool - 多维度股票估值分析

Usage:
    python stock_analyzer.py 600887           # A股伊利股份
    python stock_analyzer.py AAPL             # 美股苹果
    python stock_analyzer.py 601398 --bank    # 银行股分析
    python stock_analyzer.py 600887 --news    # 包含新闻分析
    python stock_analyzer.py 600887 --news --agent  # 使用 coding agent 深度分析
"""
import argparse
import sys
import os
from datetime import datetime

from valueinvest import Stock, StockHistory, ValuationEngine
from valueinvest.news.base import Market


def analyze_stock(
    ticker: str,
    company_type: str = "auto",
    history_period: str = "5y",
    include_news: bool = False,
    use_llm: bool = False,
    use_agent: bool = False,
    news_days: int = 30,
    include_insider: bool = False,
    insider_days: int = 90,
    include_buyback: bool = False,
    buyback_days: int = 365,
    include_fcf: bool = False,
    fcf_years: int = 5,
    include_cyclical: bool = False,
    include_peers: bool = False,
):
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

    news_analysis = None
    if include_news:
        print(f"正在获取 {ticker} 新闻数据...")
        try:
            news_analysis = fetch_and_analyze_news(
                ticker,
                use_llm=use_llm,
                use_agent=use_agent,
                days=news_days,
                stock=stock,
                company_type=company_type,
            )
        except Exception as e:
            print(f"警告: 无法获取新闻数据 - {e}")

    insider_result = None
    if include_insider:
        print(f"正在获取 {ticker} 内部人交易数据...")
        try:
            insider_result = fetch_insider_trades(ticker, days=insider_days)
        except Exception as e:
            print(f"警告: 无法获取内部人交易数据 - {e}")

    buyback_result = None
    if include_buyback:
        print(f"正在获取 {ticker} 回购数据...")
        try:
            buyback_result = fetch_buyback(ticker, days=buyback_days)
        except Exception as e:
            print(f"警告: 无法获取回购数据 - {e}")

    fcf_result = None
    if include_fcf:
        print(f"正在获取 {ticker} 自由现金流数据...")
        try:
            fcf_result = fetch_fcf(ticker, years=fcf_years)
        except Exception as e:
            print(f"警告: 无法获取自由现金流数据 - {e}")

    cyclical_result = None
    if include_cyclical:
        print(f"正在分析 {ticker} 周期股特征...")
        try:
            from valueinvest.cyclical import (
                CyclicalAnalysisEngine,
                CyclicalStock,
                CycleType,
                MarketType,
            )

            # 检测市场类型
            if ticker.isdigit() and len(ticker) == 6:
                market = MarketType.A_SHARE
            else:
                market = MarketType.US

            # 检测周期类型
            cycle_type = CyclicalAnalysisEngine.detect_cycle_type(ticker, stock.name)

            # 创建周期股数据
            cyclical_stock = CyclicalStock(
                ticker=ticker,
                name=stock.name,
                market=market,
                current_price=stock.current_price,
                cycle_type=cycle_type,
                pb=stock.pb_ratio if hasattr(stock, 'pb_ratio') else stock.bvps / stock.current_price if stock.bvps > 0 else 0,
                bvps=stock.bvps,
                eps=stock.eps,
                pe=stock.pe_ratio if hasattr(stock, 'pe_ratio') else stock.current_price / stock.eps if stock.eps > 0 else 0,
                fcf_yield=stock.fcf / (stock.current_price * stock.shares_outstanding) if stock.fcf > 0 else 0,
                fcf_per_share=stock.fcf / stock.shares_outstanding if stock.shares_outstanding > 0 else 0,
                fcf_to_net_income=stock.fcf / stock.net_income if stock.net_income > 0 else 0,
                dividend_yield=stock.dividend_yield,
                debt_ratio=stock.total_liabilities / stock.total_assets if stock.total_assets > 0 else 0,
                roe=stock.roe,
                historical_pb=stock.historical_pb if hasattr(stock, 'historical_pb') else [],
            )

            # 运行分析
            engine = CyclicalAnalysisEngine()
            cyclical_result = engine.analyze(cyclical_stock)

            print(f"✓ 周期股分析完成")
        except Exception as e:
            print(f"警告: 无法进行周期股分析 - {e}")

    peer_result = None
    if include_peers:
        print(f"正在分析 {ticker} 同行对比...")
        try:
            from valueinvest.peer_comparison import PeerComparisonEngine

            engine = PeerComparisonEngine()
            peer_result = engine.analyze(stock)
            print(f"✓ 同行对比完成")
        except Exception as e:
            print(f"警告: 无法进行同行对比 - {e}")

    print_report(
        stock, history, company_type, history_period, news_analysis, insider_result, buyback_result, fcf_result, cyclical_result, peer_result
    )
def detect_company_type(stock: Stock, history: StockHistory) -> str:
    UTILITIES_TICKERS = {
        "600900",
        "601985",
        "600011",
        "600795",
        "600886",
        "000539",
        "000543",
        "000600",
        "001896",
    }

    if stock.ticker in UTILITIES_TICKERS:
        return "dividend"

    BANK_TICKERS = {
        "601398",
        "601288",
        "600036",
        "601166",
        "600000",
        "601988",
        "600016",
        "601818",
        "600015",
        "601998",
        "002142",
        "600919",
        "601229",
        "600908",
        "601838",
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


def fetch_insider_trades(ticker: str, days: int = 90):
    from valueinvest.insider.registry import InsiderRegistry

    fetcher = InsiderRegistry.get_fetcher(ticker)
    result = fetcher.fetch_insider_trades(ticker, days=days)
    return result


def fetch_buyback(ticker: str, days: int = 365):
    from valueinvest.buyback.registry import BuybackRegistry

    fetcher = BuybackRegistry.get_fetcher(ticker)
    result = fetcher.fetch_buyback(ticker, days=days)
    return result


def fetch_fcf(ticker: str, years: int = 5):
    from valueinvest.cashflow.registry import CashFlowRegistry

    fetcher = CashFlowRegistry.get_fetcher(ticker)
    result = fetcher.fetch_cashflow(ticker, years=years)
    return result

def fetch_and_analyze_news(
    ticker: str,
    use_llm: bool = False,
    use_agent: bool = False,
    days: int = 30,
    stock=None,
    company_type: str = "general",
):
    from valueinvest.news.registry import NewsRegistry
    from valueinvest.news.analyzer.keyword_analyzer import KeywordSentimentAnalyzer
    from valueinvest.news.analyzer.llm_analyzer import LLMSentimentAnalyzer
    from valueinvest.news.analyzer.agent_analyzer import (
        AgentSentimentAnalyzer,
        create_agent_analysis_prompt,
        enhance_analysis_with_agent_result,
    )

    fetcher = NewsRegistry.get_fetcher(ticker)
    fetch_result = fetcher.fetch_all(ticker, days=days)

    if use_agent:
        print("  使用 Coding Agent 进行深度分析...")
        analyzer = AgentSentimentAnalyzer()
        analysis_result = analyzer.analyze_batch(fetch_result.news, ticker)
        analysis_result.guidance = fetch_result.guidance
        analysis_result.analyzer_type = "agent"

        if stock:
            stock_name = stock.name if stock else ticker
            current_price = stock.current_price if stock else 0.0
        else:
            stock_name = ticker
            current_price = 0.0

        analysis_result.agent_prompt = create_agent_analysis_prompt(
            ticker=ticker,
            stock_name=stock_name,
            current_price=current_price,
            company_type=company_type,
            news=fetch_result.news,
            days=days,
        )

    elif use_llm:
        api_key = os.environ.get("OPENAI_API_KEY")
        analyzer = LLMSentimentAnalyzer(api_key=api_key)
        analysis_result = analyzer.analyze_batch(fetch_result.news, ticker)
        analysis_result.guidance = fetch_result.guidance

    else:
        analyzer = KeywordSentimentAnalyzer()
        analysis_result = analyzer.analyze_batch(fetch_result.news, ticker)
        analysis_result.guidance = fetch_result.guidance

    return analysis_result


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
        # Only use fallback if dividend_growth_rate wasn't fetched from data source
        if stock.dividend_growth_rate == 0:
            stock.dividend_growth_rate = min(stock.growth_rate, 5)
        stock.dividend_growth_rate = min(stock.growth_rate, 5)
    elif company_type == "growth":
        stock.cost_of_capital = 10.0  # 成长股要求更高回报
        stock.discount_rate = 10.0


def print_report(
    stock: Stock,
    history: StockHistory,
    company_type: str,
    history_period: str = "5y",
    news_analysis=None,
    insider_result=None,
    buyback_result=None,
    fcf_result=None,
    cyclical_result=None,
    peer_result=None,
):
    engine = ValuationEngine()

    if company_type == "bank":
        results = engine.run_bank(stock)
    elif company_type == "dividend":
        results = engine.run_dividend(stock)
    elif company_type == "growth":
        results = engine.run_growth(stock)
    else:
        results = engine.run_all(stock)

    valid_results = [
        r for r in results if r.fair_value and r.fair_value > 0 and "Error" not in r.assessment
    ]

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

    if news_analysis and news_analysis.news:
        print_news_analysis(news_analysis)

    if insider_result and insider_result.has_trades:
        print_insider_trades(insider_result)

    if buyback_result and buyback_result.has_records:
        print_buyback(buyback_result)

    if buyback_result and buyback_result.summary and buyback_result.summary.has_buyback:
        print_shareholder_yield(stock, buyback_result.summary)

    if fcf_result and fcf_result.summary and fcf_result.summary.has_fcf_data:
        print_fcf_analysis(fcf_result, buyback_result.summary if buyback_result else None)

    if peer_result and peer_result.has_sufficient_peers:
        print_peer_comparison(peer_result, stock)
    elif peer_result and not peer_result.has_sufficient_peers:
        print("\n" + "=" * 70)
        print("【同行对比】")
        print("=" * 70)
        print()
        for w in peer_result.warnings:
            print(f"  ⚠️ {w}")

    print("\n" + "=" * 70)
    print("【估值汇总】")
    print("=" * 70)
    print()

    sorted_results = sorted(valid_results, key=lambda x: x.fair_value)
    print("| 方法 | 公允价值 | 溢价/折价 | 评估 |")
    print("|------|----------|-----------|------|")
    for r in sorted_results:
        name = r.method[:20]
        print(
            f"| {name:20} | ¥{r.fair_value:>7.2f} | {r.premium_discount:>+7.1f}% | {r.assessment[:10]:10} |"
        )

    print()
    fair_values = [r.fair_value for r in valid_results]
    avg_value = sum(fair_values) / len(fair_values)
    median_value = sorted(fair_values)[len(fair_values) // 2]

    print("【统计汇总】")
    print(f"  有效估值方法数: {len(valid_results)}")
    print(f"  公允价值范围: ¥{min(fair_values):.2f} - ¥{max(fair_values):.2f}")
    print(f"  平均公允价值: ¥{avg_value:.2f}")
    print(f"  中位数公允价值: ¥{median_value:.2f}")

    avg_premium = ((avg_value - stock.current_price) / stock.current_price) * 100

    undervalued = len([r for r in valid_results if r.assessment == "Undervalued"])
    overvalued = len([r for r in valid_results if r.assessment == "Overvalued"])

    print()
    print(f"  相对平均值: {avg_premium:+.1f}%")
    print(f"  低估方法数: {undervalued}/{len(valid_results)}")
    print(f"  高估方法数: {overvalued}/{len(valid_results)}")

    print("\n" + "=" * 70)
    print("【最终结论】")
    print("=" * 70)
    print()

    conservative = sorted(fair_values)[:3]
    optimistic = sorted(fair_values)[-3:]

    cons_avg = sum(conservative) / len(conservative)
    opt_avg = sum(optimistic) / len(optimistic)

    print(
        f"估值区间: ¥{cons_avg:.0f}-{sorted(fair_values)[len(fair_values)//2]:.0f} (保守) / ¥{stock.current_price:.0f} (现价) / ¥{opt_avg:.0f}+ (乐观)"
    )
    print()

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

    target_price = median_value * 0.85
    stop_loss = cons_avg * 0.9

    print(
        f"  1. 已持有者: {'继续持有' if stock.dividend_yield and stock.dividend_yield > 3 else '持有观望'}"
    )
    print(f"  2. 潜在买入: 等待回调至¥{target_price:.0f}以下")
    print(f"  3. 目标价位: ¥{target_price:.0f} (提供15%+安全边际)")
    print(f"  4. 止损位: ¥{stop_loss:.0f}")
    print()

    if stock.dividend_yield:
        div_return = stock.dividend_yield
    else:
        div_return = 0

    print("预期回报:")
    print(f"  保守: 股息{div_return:.1f}% + 增长0-2% = {div_return:.1f}-{div_return+2:.1f}%/年")
    print(
        f"  中性: 股息{div_return:.1f}% + 增长{stock.growth_rate:.0f}% = {div_return+stock.growth_rate:.1f}%/年"
    )
    print(
        f"  乐观: 股息{div_return:.1f}% + 增长{stock.growth_rate*1.5:.0f}% = {div_return+stock.growth_rate*1.5:.1f}%/年"
    )
    print()


def print_news_analysis(analysis):
    print("\n" + "=" * 70)
    print("【新闻情感分析】")
    print("=" * 70)
    print()

    sentiment_emoji = {
        "positive": "📈",
        "slightly_positive": "↗️",
        "neutral": "➡️",
        "slightly_negative": "↘️",
        "negative": "📉",
    }
    emoji = sentiment_emoji.get(analysis.sentiment_label, "➡️")

    print(f"  情感得分: {emoji} {analysis.sentiment_score:+.2f} ({analysis.sentiment_label})")
    print(f"  分析新闻数: {len(analysis.news)} 条 (7日内: {analysis.news_count_7d})")
    print(
        f"  正面/负面/中性: {analysis.positive_count}/{analysis.negative_count}/{analysis.neutral_count}"
    )
    print(f"  置信度: {analysis.confidence:.0%}")

    if analysis.key_themes:
        print()
        print("【关键主题】")
        for theme in analysis.key_themes[:5]:
            print(f"  • {theme}")

    if analysis.risks:
        print()
        print("【风险提示】")
        for risk in analysis.risks[:5]:
            print(f"  ⚠️ {risk}")

    if analysis.catalysts:
        print()
        print("【潜在催化剂】")
        for catalyst in analysis.catalysts[:5]:
            print(f"  ✅ {catalyst}")

    recent_news = sorted(analysis.news, key=lambda n: n.publish_date, reverse=True)[:5]
    if recent_news:
        print()
        print("【近期重要新闻】")
        for news in recent_news:
            sentiment_mark = "+" if news.is_positive else ("-" if news.is_negative else " ")
            date_str = news.publish_date.strftime("%m-%d")
            title = news.title[:40] + "..." if len(news.title) > 40 else news.title
            print(f"  [{sentiment_mark}] {date_str} {title}")


def print_insider_trades(insider_result):
    print("\n" + "=" * 70)
    print("【内部人交易】")
    print("=" * 70)
    print()

    summary = insider_result.summary
    if summary:
        sentiment_emoji = {"bullish": "📈", "bearish": "📉", "neutral": "➡️"}
        emoji = sentiment_emoji.get(summary.sentiment, "➡️")

        print(f"  情绪: {emoji} {summary.sentiment.upper()}")
        print(
            f"  交易笔数: {summary.total_trades} (买入: {summary.buy_count}, 卖出: {summary.sell_count})"
        )
        print(f"  净交易: {summary.net_shares:+,.0f} 股 (¥{summary.net_value:+,.0f})")
        print(f"  参与高管: {summary.unique_insiders} 人")
        print(f"  CEO/CFO交易: {summary.key_insider_trades} 笔")

        if summary.buy_value > 0 or summary.sell_value > 0:
            print(f"  买入比例: {summary.buy_ratio:.0%}")

    recent_trades = insider_result.trades[:10]
    if recent_trades:
        print()
        print("【近期交易】")
        print("| 日期 | 高管 | 职位 | 类型 | 股数 | 金额 |")
        print("|------|------|------|------|------|------|")
        for trade in recent_trades:
            date_str = trade.trade_date.strftime("%m-%d")
            name = trade.insider_name[:6]
            title = trade.title.value[:6]
            ttype = "买入" if trade.is_buy else ("卖出" if trade.is_sell else "其他")
            shares = f"{trade.shares:,.0f}"
            value = f"¥{trade.value:,.0f}" if trade.value else "-"
            print(f"| {date_str} | {name} | {title} | {ttype} | {shares} | {value} |")


def print_buyback(buyback_result):
    print("\n" + "=" * 70)
    print("【回购分析】")
    print("=" * 70)
    print()

    summary = buyback_result.summary
    if summary:
        sentiment_emoji = {
            "aggressive": "🟢",
            "moderate": "🟡",
            "minimal": "⚪",
            "none": "⚫",
        }
        emoji = sentiment_emoji.get(summary.sentiment.value, "➡️")

        print(f"  回购情绪: {emoji} {summary.sentiment.value.upper()}")
        print(f"  回购收益率: {summary.buyback_yield:.2f}%")
        print(f"  总股东收益率: {summary.total_shareholder_yield:.2f}%")

        if summary.shares_reduction_rate > 0:
            print(f"  股份减少率: {summary.shares_reduction_rate:.2f}%/年")

        if summary.yearly_amounts:
            print(f"  年度回购:")
            for year, amount in sorted(summary.yearly_amounts.items(), reverse=True)[:4]:
                if buyback_result.market == Market.US:
                    print(f"    {year}: ${amount/1e9:.2f}B")
                else:
                    print(f"    {year}: ¥{amount/1e8:.2f}亿")

        if summary.active_programs > 0:
            print(f"  进行中计划: {summary.active_programs} 个")

    recent_records = buyback_result.records[:5]
    if recent_records:
        print()
        print("【回购记录】")
        print("| 日期 | 股数 | 金额 | 状态 |")
        print("|------|------|------|------|")
        for record in recent_records:
            date_str = record.announce_date.strftime("%m-%d") if record.announce_date else "-"
            shares = f"{record.shares_repurchased:,.0f}" if record.shares_repurchased else "-"
            amount = f"¥{record.amount:,.0f}" if record.amount else "-"
            status = "完成" if record.is_completed else "进行中"
            print(f"| {date_str} | {shares} | {amount} | {status} |")


def print_shareholder_yield(stock, buyback_summary):
    print("\n" + "=" * 70)
    print("【股东回报分析】")
    print("=" * 70)
    print()

    print("  ┌─────────────────────────────────────┐")
    print(f"  │  股息率:      {buyback_summary.dividend_yield:>6.2f}%           │")
    print(f"  │  回购收益率:  {buyback_summary.buyback_yield:>6.2f}%           │")
    print("  ├─────────────────────────────────────┤")
    print(f"  │  总股东收益率: {buyback_summary.total_shareholder_yield:>6.2f}%          │")
    print("  └─────────────────────────────────────┘")
    print()

    if buyback_summary.exceeds_dividend:
        print("  💡 回购收益率 > 股息率，公司更倾向于通过回购回报股东")

    if buyback_summary.is_aggressive:
        print("  💡 激进回购 (>3%)，公司对自身价值有信心")


def print_fcf_analysis(fcf_result, buyback_summary=None):
    """Print Free Cash Flow analysis section."""
    print("\n" + "=" * 70)
    print("【自由现金流 (FCF) 分析】")
    print("=" * 70)
    print()

    summary = fcf_result.summary
    market = fcf_result.market
    currency = "$" if market == Market.US else "¥"
    unit = 1e9 if market == Market.US else 1e8
    unit_label = "B" if market == Market.US else "亿"

    # Quality indicator
    quality_emoji = {
        "excellent": "🟢",
        "good": "🟢",
        "acceptable": "🟡",
        "poor": "🟠",
        "negative": "🔴",
    }
    quality = summary.fcf_quality.value
    emoji = quality_emoji.get(quality, "➡️")

    print(f"  FCF 质量: {emoji} {quality.upper()}")
    print(f"  FCF 趋势: {summary.fcf_trend.value.upper()}")
    print()

    # Key metrics
    print("【核心指标】")
    print(f"  最新年度 FCF: {currency}{summary.latest_fcf/unit:.2f}{unit_label}")
    print(f"  FCF 收益率: {summary.fcf_yield:.2f}%")
    print(f"  FCF 利润率: {summary.fcf_margin:.2f}%")
    print(f"  每股 FCF: {currency}{summary.fcf_per_share:.2f}")
    print()

    # SBC adjustment
    if summary.sbc_as_pct_of_fcf > 0:
        print("【SBC (股权激励) 调整】")
        latest_sbc_year = max(summary.yearly_sbc.keys()) if summary.yearly_sbc else 0
        sbc_amount = summary.yearly_sbc.get(latest_sbc_year, 0) if latest_sbc_year else 0
        print(f"  SBC 金额: {currency}{sbc_amount/unit:.2f}{unit_label}")
        print(f"  SBC 占 FCF: {summary.sbc_as_pct_of_fcf:.1f}%")
        print(f"  真实 FCF (扣除SBC): {currency}{summary.latest_true_fcf/unit:.2f}{unit_label}")
        print(f"  真实 FCF 收益率: {summary.true_fcf_yield:.2f}%")
        print(f"  真实 FCF 利润率: {summary.true_fcf_margin:.2f}%")
        print()

    # Quality metrics
    print("【盈利质量】")
    print(f"  FCF / 净利润: {summary.fcf_to_net_income:.2f}x")
    if summary.fcf_to_net_income >= 1.0:
        print("    💡 FCF > 净利润，盈利质量优秀")
    elif summary.fcf_to_net_income >= 0.8:
        print("    💡 FCF 接近净利润，盈利质量良好")
    elif summary.fcf_to_net_income >= 0.5:
        print("    ⚠️ FCF 显著低于净利润，需关注")
    else:
        print("    🚨 FCF 远低于净利润，盈利质量堪忧")
    print()

    # Historical trend
    if len(summary.yearly_fcf) > 1:
        print("【历史趋势】")
        print(f"  FCF CAGR ({len(summary.yearly_fcf)}年): {summary.fcf_cagr:+.1f}%")
        print(f"  收入 CAGR ({len(summary.yearly_revenue)}年): {summary.revenue_cagr:+.1f}%")
        print(f"  FCF 为正年数: {summary.positive_fcf_years}/{summary.record_count}")
        print()

        # Yearly data table
        print("【年度 FCF 数据】")
        print("| 年份 | FCF | 真实FCF | 收入 | SBC | FCF利润率 |")
        print("|------|-----|---------|------|-----|----------|")
        for year in sorted(summary.yearly_fcf.keys(), reverse=True)[:5]:
            fcf = summary.yearly_fcf.get(year, 0)
            true_fcf = summary.yearly_true_fcf.get(year, 0)
            revenue = summary.yearly_revenue.get(year, 0)
            sbc = summary.yearly_sbc.get(year, 0)
            margin = (fcf / revenue * 100) if revenue > 0 else 0
            print(f"| {year} | {currency}{fcf/unit:.1f}{unit_label} | {currency}{true_fcf/unit:.1f}{unit_label} | {currency}{revenue/unit:.1f}{unit_label} | {currency}{sbc/unit:.1f}{unit_label} | {margin:.1f}% |")
        print()

    # Comparison with shareholder yield
    if buyback_summary and buyback_summary.has_buyback:
        print("【与股东回报对比】")
        print(f"  FCF 收益率: {summary.fcf_yield:.2f}%")
        print(f"  总股东收益率: {buyback_summary.total_shareholder_yield:.2f}%")
        if summary.fcf_yield > buyback_summary.total_shareholder_yield:
            print("    💡 FCF 收益率 > 股东收益率，公司有充足现金支持回购/分红")
        elif summary.fcf_yield > 0:
            print("    ⚠️ FCF 收益率 < 股东收益率，回购/分红可能依赖借贷或储备")
        print()

    # Investment implications
    print("【投资启示】")
    if summary.fcf_quality.value in ("excellent", "good"):
        if summary.fcf_trend.value == "improving":
            print("  ✅ 高质量FCF + 改善趋势，现金牛特征明显")
        else:
            print("  ✅ 高质量FCF，现金创造能力强")
    elif summary.fcf_quality.value == "acceptable":
        print("  🟡 FCF质量尚可，需持续监控")
    else:
        print("  ⚠️ FCF质量堪忧，投资需谨慎")

    if summary.sbc_is_material:
        print(f"  ⚠️ SBC 占 FCF {summary.sbc_as_pct_of_fcf:.0f}%，股权稀释显著")

def print_peer_comparison(peer_result, stock):
    """Print peer comparison analysis section."""
    print("\n" + "=" * 70)
    print("【同行对比分析】")
    print("=" * 70)
    print()

    print(f"  行业: {peer_result.industry_name}")
    print(f"  同行数量: {peer_result.peer_count}")
    print(f"  市值排名: #{peer_result.rank_in_peers} / {peer_result.peer_count + 1}")
    print(f"  综合评分: {peer_result.composite_score:.0f}/100 ({peer_result.rating.value.upper()})")
    print()

    # Metric comparison table
    print("【指标对比】")
    print("| 指标 | 当前值 | 同行均值 | 同行中位 | 百分位 | 评估 |")
    print("|------|--------|----------|----------|--------|------|")
    for mc in peer_result.metric_comparisons:
        if not mc.is_available:
            continue
        direction = "\u2191" if mc.direction.value == "higher_better" else "\u2193"
        assessment = mc.assessment
        print(
            f"| {direction} {mc.metric_name:18} | {mc.target_value:>8.1f} | {mc.peer_avg:>8.1f} | {mc.peer_median:>8.1f} | {mc.percentile:>5.0f}th | {assessment:20} |"
        )
    print()

    # Category scores
    print("【分类评分】")
    if peer_result.valuation_score > 0:
        label = "低估值" if peer_result.valuation_score <= 30 else ("合理" if peer_result.valuation_score <= 60 else "偏高")
        print(f"  估值评分: {peer_result.valuation_score:.0f}/100 ({label})")
    if peer_result.profitability_score > 0:
        label = "优秀" if peer_result.profitability_score >= 70 else ("一般" if peer_result.profitability_score >= 40 else "偏弱")
        print(f"  盈利评分: {peer_result.profitability_score:.0f}/100 ({label})")
    if peer_result.growth_score > 0:
        label = "高增长" if peer_result.growth_score >= 70 else ("一般" if peer_result.growth_score >= 40 else "低增长")
        print(f"  增长评分: {peer_result.growth_score:.0f}/100 ({label})")
    print()

    # Strengths and weaknesses
    if peer_result.strengths:
        print("【相对优势】")
        for s in peer_result.strengths[:3]:
            print(f"  ✅ {s}")
        print()
    if peer_result.weaknesses:
        print("【相对劣势】")
        for w in peer_result.weaknesses[:3]:
            print(f"  ⚠️ {w}")
        print()

    # Analysis summary
    if peer_result.analysis:
        print("【分析要点】")
        for a in peer_result.analysis:
            print(f"  • {a}")
        print()


def get_type_label(company_type: str) -> str:
    labels = {
        "bank": "银行/金融",
        "dividend": "分红股",
        "growth": "成长股",
        "value": "价值股",
        "general": "一般",
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
  python stock_analyzer.py 600887 --news    # 包含新闻情感分析
  python stock_analyzer.py AAPL --news --llm  # 使用LLM API进行新闻分析
  python stock_analyzer.py 600887 --news --agent  # 使用 Coding Agent 深度分析
  python stock_analyzer.py 600887 --insider  # 包含内部人交易分析
  python stock_analyzer.py AAPL --insider --insider-days 180  # 180天内部人交易
  python stock_analyzer.py AAPL --buyback   # 包含回购分析 (美股推荐)
  python stock_analyzer.py 600887 --buyback # 包含回购分析 (A股)
  python stock_analyzer.py AAPL --fcf       # 包含自由现金流分析
  python stock_analyzer.py PYPL --buyback --fcf  # 回购+FCF综合分析
        """,
    )

    parser.add_argument("ticker", help="股票代码 (如 600887, AAPL)")
    parser.add_argument(
        "--type",
        "-t",
        choices=["auto", "bank", "dividend", "growth", "value"],
        default="auto",
        help="公司类型 (默认自动检测)",
    )
    parser.add_argument("--bank", "-b", action="store_true", help="银行股分析 (等同于 --type bank)")
    parser.add_argument("--dividend", "-d", action="store_true", help="分红股分析")
    parser.add_argument("--growth", "-g", action="store_true", help="成长股分析")
    parser.add_argument("--period", "-p", default="5y", help="历史数据周期 (默认5y)")
    parser.add_argument("--news", "-n", action="store_true", help="包含新闻情感分析")
    parser.add_argument(
        "--llm", action="store_true", help="使用LLM API进行新闻分析 (需要OPENAI_API_KEY)"
    )
    parser.add_argument(
        "--agent", action="store_true", help="使用 Coding Agent 进行深度新闻分析 (无需API key)"
    )
    parser.add_argument("--news-days", type=int, default=30, help="新闻分析天数 (默认30)")
    parser.add_argument("--insider", "-i", action="store_true", help="包含内部人交易分析")
    parser.add_argument("--insider-days", type=int, default=90, help="内部人交易分析天数 (默认90)")
    parser.add_argument("--buyback", action="store_true", help="包含回购分析 (美股推荐)")
    parser.add_argument("--buyback-days", type=int, default=365, help="回购分析天数 (默认365)")
    parser.add_argument("--fcf", action="store_true", help="包含自由现金流分析 (推荐与回购分析一起使用)")
    parser.add_argument("--fcf-years", type=int, default=5, help="FCF分析年数 (默认5)")
    parser.add_argument("--cyclical", "-c", action="store_true", help="周期股分析 (航运、钢铁、有色、能源等)")
    parser.add_argument("--peers", action="store_true", help="包含同行对比分析")

    args = parser.parse_args()

    if args.bank:
        args.type = "bank"
    elif args.dividend:
        args.type = "dividend"
    elif args.growth:
        args.type = "growth"
    elif args.cyclical:
        args.type = "cyclical"

    analyze_stock(
        args.ticker,
        args.type,
        args.period,
        include_news=args.news,
        use_llm=args.llm,
        use_agent=args.agent,
        news_days=args.news_days,
        include_insider=args.insider,
        insider_days=args.insider_days,
        include_buyback=args.buyback,
        buyback_days=args.buyback_days,
        include_fcf=args.fcf,
        fcf_years=args.fcf_years,
        include_peers=args.peers,
    )


if __name__ == "__main__":
    main()
