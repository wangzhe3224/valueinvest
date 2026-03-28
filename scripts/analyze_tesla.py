#!/usr/bin/env python3
"""
Tesla (TSLA) Complete Financial Analysis Script

This script performs comprehensive financial analysis of Tesla including:
- Fundamental data (balance sheet, income statement, cash flow)
- Multiple valuation methods (DCF, Reverse DCF, Graham, PEG, GARP, etc.)
- News sentiment analysis
- Insider trading analysis
- Buyback analysis
- Free Cash Flow (FCF) analysis
- Quality scores (Piotroski F-Score, Altman Z-Score, Beneish M-Score)
- Relative valuation (PE/PB vs historical)

Output: Complete markdown report saved to reports/TSLA/
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from valueinvest import Stock, StockHistory, ValuationEngine
from valueinvest.news.registry import NewsRegistry
from valueinvest.news.analyzer.keyword_analyzer import KeywordSentimentAnalyzer
from valueinvest.insider import InsiderRegistry
from valueinvest.buyback import BuybackRegistry
from valueinvest.cashflow import CashFlowRegistry


def fetch_fundamental_data(ticker: str):
    """Fetch basic fundamental data"""
    print(f"\n{'='*60}")
    print(f"Fetching fundamental data for {ticker}...")
    print(f"{'='*60}")

    try:
        stock = Stock.from_api(ticker)
        print(f"✓ Successfully fetched stock data")
        return stock
    except Exception as e:
        print(f"✗ Error fetching stock data: {e}")
        raise


def fetch_price_history(ticker: str, period: str = "5y"):
    """Fetch price history"""
    print(f"\n{'='*60}")
    print(f"Fetching price history ({period})...")
    print(f"{'='*60}")

    try:
        history = Stock.fetch_price_history(ticker, period=period)
        print(f"✓ Successfully fetched price history")
        print(f"  CAGR (QFQ): {history.cagr:.2f}%")
        print(f"  CAGR (HFQ): {history.cagr_hfq:.2f}%")
        print(f"  Volatility: {history.volatility:.2f}%")
        print(f"  Max Drawdown: {history.max_drawdown:.2f}%")
        return history
    except Exception as e:
        print(f"✗ Error fetching price history: {e}")
        return StockHistory(ticker=ticker)


def run_valuation(stock: Stock, history: StockHistory):
    """Run multiple valuation methods"""
    print(f"\n{'='*60}")
    print(f"Running valuation analysis...")
    print(f"{'='*60}")

    # Set valuation parameters based on Tesla's growth profile
    stock.growth_rate = min(max(history.cagr * 0.7, 5), 20)  # Conservative growth
    stock.cost_of_capital = 12.0  # Higher for growth stocks
    stock.discount_rate = 12.0
    stock.terminal_growth = 3.0

    engine = ValuationEngine()
    results = []

    # Growth stock valuation methods
    try:
        growth_results = engine.run_growth(stock)
        results.extend(growth_results)
        print(f"✓ Growth valuation: {len(growth_results)} methods completed")
    except Exception as e:
        print(f"✗ Growth valuation error: {e}")

    # All methods
    try:
        all_results = engine.run_all(stock)
        # Merge without duplicates
        existing_methods = {r.method for r in results}
        for r in all_results:
            if r.method not in existing_methods:
                results.append(r)
        print(f"✓ Total valuation methods: {len(results)}")
    except Exception as e:
        print(f"✗ All methods error: {e}")

    return results


def fetch_news_analysis(ticker: str, days: int = 60):
    """Fetch and analyze news sentiment"""
    print(f"\n{'='*60}")
    print(f"Fetching news data (last {days} days)...")
    print(f"{'='*60}")

    try:
        fetcher = NewsRegistry.get_fetcher(ticker)
        result = fetcher.fetch_all(ticker, days=days)

        if not result.news:
            print(f"✗ No news found")
            return None

        analyzer = KeywordSentimentAnalyzer()
        analysis = analyzer.analyze_batch(result.news, ticker)

        print(f"✓ Analyzed {len(result.news)} news items")
        print(f"  Sentiment: {analysis.sentiment_label} ({analysis.sentiment_score:+.2f})")
        print(
            f"  Positive/Negative/Neutral: {analysis.positive_count}/{analysis.negative_count}/{analysis.neutral_count}"
        )

        return {
            "news_count": len(result.news),
            "analysis": analysis,
            "guidance": result.guidance,
        }
    except Exception as e:
        print(f"✗ News analysis error: {e}")
        return None


def fetch_insider_trading(ticker: str, days: int = 180):
    """Fetch insider trading data"""
    print(f"\n{'='*60}")
    print(f"Fetching insider trading data (last {days} days)...")
    print(f"{'='*60}")

    try:
        fetcher = InsiderRegistry.get_fetcher(ticker)
        result = fetcher.fetch_insider_trades(ticker, days=days)

        print(f"✓ Found {len(result.trades)} insider trades")
        print(f"  Sentiment: {result.summary.sentiment}")
        print(f"  Buys: {result.summary.buy_count}, Sells: {result.summary.sell_count}")
        print(f"  Net Value: ${result.summary.net_value:+,.0f}")

        return result
    except Exception as e:
        print(f"✗ Insider trading error: {e}")
        return None


def fetch_buyback_data(ticker: str, days: int = 730):
    """Fetch buyback/repurchase data"""
    print(f"\n{'='*60}")
    print(f"Fetching buyback data (last {days} days)...")
    print(f"{'='*60}")

    try:
        fetcher = BuybackRegistry.get_fetcher(ticker)
        result = fetcher.fetch_buyback(ticker, days=days)

        print(f"✓ Buyback data retrieved")
        print(f"  Buyback Yield: {result.summary.buyback_yield:.2f}%")
        print(f"  Dividend Yield: {result.summary.dividend_yield:.2f}%")
        print(f"  Total Shareholder Yield: {result.summary.total_shareholder_yield:.2f}%")

        return result
    except Exception as e:
        print(f"✗ Buyback data error: {e}")
        return None


def fetch_fcf_data(ticker: str, years: int = 5):
    """Fetch Free Cash Flow analysis"""
    print(f"\n{'='*60}")
    print(f"Fetching FCF data (last {years} years)...")
    print(f"{'='*60}")

    try:
        fetcher = CashFlowRegistry.get_fetcher(ticker)
        result = fetcher.fetch_cashflow(ticker, years=years)

        print(f"✓ FCF data retrieved")
        print(f"  FCF Quality: {result.summary.fcf_quality.value}")
        print(f"  FCF Trend: {result.summary.fcf_trend.value}")
        print(f"  FCF Yield: {result.summary.fcf_yield:.2f}%")
        print(f"  FCF Margin: {result.summary.fcf_margin:.2f}%")

        return result
    except Exception as e:
        print(f"✗ FCF data error: {e}")
        return None


def generate_markdown_report(
    ticker: str,
    stock: Stock,
    history: StockHistory,
    valuation_results: list,
    news_data: Optional[dict],
    insider_result,
    buyback_result,
    fcf_result,
    output_path: str,
):
    """Generate comprehensive markdown report"""
    print(f"\n{'='*60}")
    print(f"Generating markdown report...")
    print(f"{'='*60}")

    report_date = datetime.now().strftime("%Y-%m-%d")

    # Build report sections
    sections = []

    # Header
    sections.append(
        f"""# Tesla Inc. (TSLA) - 深度财务分析报告

> **分析日期**: {report_date}  
> **数据来源**: [valueinvest](https://github.com/wangzhe3224/valueinvest)  
> **报告类型**: 完整深度分析

---

## 📋 目录

1. [公司概况](#公司概况)
2. [财务数据](#财务数据)
3. [价格历史与表现](#价格历史与表现)
4. [估值分析](#估值分析)
5. [新闻情感分析](#新闻情感分析)
6. [内部人交易](#内部人交易)
7. [回购分析](#回购分析)
8. [自由现金流分析](#自由现金流分析)
9. [综合评估](#综合评估)
10. [投资建议](#投资建议)

---

"""
    )

    # 1. Company Overview
    market_cap = stock.current_price * stock.shares_outstanding if stock.shares_outstanding else 0
    sections.append(
        f"""## 1. 公司概况

| 指标 | 数值 |
|------|------|
| **公司名称** | {stock.name} |
| **股票代码** | {ticker} |
| **当前股价** | ${stock.current_price:.2f} |
| **总市值** | ${market_cap/1e9:.2f}B |
| **市场** | 美股 (NASDAQ) |
| **行业** | 电动汽车 / 清洁能源 |

---

"""
    )

    # 2. Financial Data
    sections.append(
        f"""## 2. 财务数据

### 2.1 核心财务指标

| 指标 | 数值 |
|------|------|
| **营业收入** | ${stock.revenue/1e9:.2f}B |
| **净利润** | ${stock.net_income/1e9:.2f}B |
| **每股收益 (EPS)** | ${stock.eps:.2f} |
| **每股净资产 (BVPS)** | ${stock.bvps:.2f} |
| **市盈率 (PE)** | {stock.pe_ratio:.2f}x |
| **市净率 (PB)** | {stock.pb_ratio:.2f}x |
| **ROE (净资产收益率)** | {(stock.net_income / (stock.bvps * stock.shares_outstanding) * 100) if stock.shares_outstanding and stock.bvps > 0 else 0:.2f}% |

### 2.2 资产负债表

| 指标 | 数值 |
|------|------|
| **总资产** | ${stock.total_assets/1e9:.2f}B |
| **总负债** | ${stock.total_liabilities/1e9:.2f}B |
| **净资产** | ${(stock.total_assets - stock.total_liabilities)/1e9:.2f}B |
| **流动资产** | ${stock.current_assets/1e9:.2f}B |
| **资产负债率** | {(stock.total_liabilities / stock.total_assets * 100) if stock.total_assets > 0 else 0:.2f}% |

---

"""
    )

    # 3. Price History
    sections.append(
        f"""## 3. 价格历史与表现

### 3.1 价格走势 (5年)

| 指标 | 数值 |
|------|------|
| **CAGR (QFQ)** | {history.cagr:.2f}% |
| **CAGR (HFQ)** | {history.cagr_hfq:.2f}% |
| **波动率** | {history.volatility:.2f}% |
| **最大回撤** | {history.max_drawdown:.2f}% |

**说明**:
- **QFQ (前复权)**: 仅价格增长，用于估值对比
- **HFQ (后复权)**: 包含分红再投资的真实收益率

### 3.2 估值参数设定

| 参数 | 设定值 | 说明 |
|------|--------|------|
| **预期增长率** | {stock.growth_rate:.1f}% | 基于5年CAGR的保守估计 |
| **资本成本 (WACC)** | {stock.cost_of_capital:.1f}% | 成长股通常10-15% |
| **折现率** | {stock.discount_rate:.1f}% | 与WACC一致 |
| **永续增长率** | {stock.terminal_growth:.1f}% | 长期GDP增速 |

---

"""
    )

    # 4. Valuation Analysis
    sections.append(
        """## 4. 估值分析

### 4.1 估值方法汇总

| 方法 | 公允价值 | 溢价/折价 | 评估 |
|------|----------|-----------|------|
"""
    )

    for v in valuation_results:
        premium_str = f"{v.premium_discount:+.1f}%" if v.premium_discount is not None else "N/A"
        sections.append(f"| {v.method} | ${v.fair_value:.2f} | {premium_str} | {v.assessment} |\n")

    # Calculate valuation range
    if valuation_results:
        fair_values = [v.fair_value for v in valuation_results if v.fair_value and v.fair_value > 0]
        if fair_values:
            avg_fair_value = sum(fair_values) / len(fair_values)
            min_fair_value = min(fair_values)
            max_fair_value = max(fair_values)

            sections.append(
                f"""
### 4.2 估值区间

- **保守估值**: ${min_fair_value:.2f}
- **平均估值**: ${avg_fair_value:.2f}
- **乐观估值**: ${max_fair_value:.2f}
- **当前价格**: ${stock.current_price:.2f}
- **溢价/折价**: {((stock.current_price / avg_fair_value - 1) * 100):+.1f}%

---

"""
            )

    # 5. News Analysis
    sections.append(
        """## 5. 新闻情感分析

"""
    )

    if news_data and news_data.get("analysis"):
        analysis = news_data["analysis"]
        sentiment_emoji = (
            "📈"
            if analysis.sentiment_score > 0.2
            else "📉"
            if analysis.sentiment_score < -0.2
            else "➡️"
        )

        sections.append(
            f"""### 5.1 情感概况

| 指标 | 数值 |
|------|------|
| **情感得分** | {sentiment_emoji} {analysis.sentiment_score:+.2f} |
| **情感标签** | {analysis.sentiment_label} |
| **分析新闻数** | {news_data['news_count']} 条 |
| **正面/负面/中性** | {analysis.positive_count}/{analysis.negative_count}/{analysis.neutral_count} |

### 5.2 关键主题

"""
        )
        if analysis.key_themes:
            for theme in analysis.key_themes[:5]:
                sections.append(f"- {theme}\n")

        sections.append(
            f"""
### 5.3 风险提示

"""
        )
        if analysis.risks:
            for risk in analysis.risks[:3]:
                sections.append(f"⚠️ {risk}\n")

        sections.append(
            f"""
### 5.4 潜在催化剂

"""
        )
        if analysis.catalysts:
            for catalyst in analysis.catalysts[:3]:
                sections.append(f"✅ {catalyst}\n")

        # Guidance
        if news_data.get("guidance") and news_data["guidance"].has_analyst_data:
            guidance = news_data["guidance"]
            sections.append(
                f"""
### 5.5 分析师预期

| 指标 | 数值 |
|------|------|
| **分析师评级** | {guidance.analyst_rating.value if guidance.analyst_rating else 'N/A'} |
| **分析师数量** | {guidance.analyst_count} |
"""
            )
    else:
        sections.append("*新闻数据暂不可用*\n")

    sections.append("\n---\n\n")

    # 6. Insider Trading
    sections.append(
        """## 6. 内部人交易

"""
    )

    if insider_result and insider_result.trades:
        summary = insider_result.summary
        sentiment_emoji = (
            "🐂"
            if summary.sentiment == "bullish"
            else "🐻"
            if summary.sentiment == "bearish"
            else "➡️"
        )

        sections.append(
            f"""### 6.1 交易概况

| 指标 | 数值 |
|------|------|
| **整体情绪** | {sentiment_emoji} {summary.sentiment} |
| **买入次数** | {summary.buy_count} |
| **卖出次数** | {summary.sell_count} |
| **净股数变化** | {summary.net_shares:+,.0f} |
| **净金额变化** | ${summary.net_value:+,.0f} |

### 6.2 近期重要交易

| 日期 | 交易者 | 类型 | 股数 | 价格 |
|------|--------|------|------|------|
"""
        )

        for trade in insider_result.trades[:5]:
            sections.append(
                f"| {trade.trade_date} | {trade.insider_name[:20]} | {trade.trade_type.value} | {trade.shares:,.0f} | ${trade.price:.2f} |\n"
            )
    else:
        sections.append("*内部人交易数据暂不可用*\n")

    sections.append("\n---\n\n")

    # 7. Buyback Analysis
    sections.append(
        """## 7. 回购分析

"""
    )

    if buyback_result:
        summary = buyback_result.summary

        sections.append(
            f"""### 7.1 回购概况

| 指标 | 数值 |
|------|------|
| **回购收益率** | {summary.buyback_yield:.2f}% |
| **分红收益率** | {summary.dividend_yield:.2f}% |
| **总股东收益率** | {summary.total_shareholder_yield:.2f}% |
| **回购态度** | {summary.sentiment.value} |

"""
        )

        if summary.yearly_amounts:
            sections.append(
                """### 7.2 年度回购金额

| 年份 | 回购金额 |
|------|----------|
"""
            )
            for year in sorted(summary.yearly_amounts.keys(), reverse=True)[:3]:
                amount = summary.yearly_amounts[year]
                sections.append(f"| {year} | ${amount/1e9:.2f}B |\n")
    else:
        sections.append("*回购数据暂不可用*\n")

    sections.append("\n---\n\n")

    # 8. FCF Analysis
    sections.append(
        """## 8. 自由现金流分析

"""
    )

    if fcf_result:
        summary = fcf_result.summary

        sections.append(
            f"""### 8.1 FCF 质量

| 指标 | 数值 | 说明 |
|------|------|------|
| **FCF 质量** | {summary.fcf_quality.value} | {get_fcf_quality_desc(summary.fcf_quality.value)} |
| **FCF 趋势** | {summary.fcf_trend.value} | {get_fcf_trend_desc(summary.fcf_trend.value)} |
| **FCF 收益率** | {summary.fcf_yield:.2f}% | FCF / 市值 |
| **FCF 利润率** | {summary.fcf_margin:.2f}% | FCF / 营收 |

### 8.2 真实盈利能力 (SBC调整后)

| 指标 | 数值 |
|------|------|
| **真实 FCF (SBC调整后)** | ${summary.latest_true_fcf/1e9:.2f}B |
| **真实 FCF 收益率** | {summary.true_fcf_yield:.2f}% |
| **SBC 占 FCF 比例** | {summary.sbc_as_pct_of_fcf:.1f}% |
| **FCF / 净利润** | {summary.fcf_to_net_income:.2f}x |
| **FCF CAGR** | {summary.fcf_cagr:.1f}% |

**说明**:
- **真实 FCF**: 扣除股权激励(SBC)后的自由现金流
- **FCF / 净利润 > 1.0**: 表示盈利质量高，现金含量足
- **SBC 占比**: 过高(>30%)可能意味着通过股权激励稀释股东权益
"""
        )
    else:
        sections.append("*FCF 数据暂不可用*\n")

    sections.append("\n---\n\n")

    # 9. Comprehensive Assessment
    sections.append(
        f"""## 9. 综合评估

### 9.1 优势

- ✅ **成长性**: 5年CAGR {history.cagr:.1f}%，成长性{'优秀' if history.cagr > 20 else '良好' if history.cagr > 10 else '一般'}
- ✅ **行业地位**: 电动汽车行业领导者，品牌影响力强
- ✅ **创新能力**: 自动驾驶、储能、机器人等多领域布局

### 9.2 风险

- ⚠️ **估值风险**: {'估值偏高，需关注增长能否支撑' if stock.pe_ratio > 50 else '估值合理'} (PE: {stock.pe_ratio:.1f}x)
- ⚠️ **竞争加剧**: 传统车企加速电动化转型
- ⚠️ **波动性高**: 历史波动率 {history.volatility:.1f}%，需承受较大价格波动
- ⚠️ **盈利波动**: 汽车业务周期性强，盈利可能波动

### 9.3 适合投资者类型

- ✅ **成长型投资者**: 追求高增长，能承受高波动
- ✅ **长期投资者**: 相信电动化/智能化长期趋势
- ❌ **保守型投资者**: 估值高、波动大，不适合风险厌恶者
- ❌ **价值型投资者**: 不符合传统价值投资标准

---

"""
    )

    # 10. Investment Recommendation
    # Calculate overall sentiment
    sentiment_score = 0

    # Valuation sentiment
    if valuation_results:
        avg_fair_value = sum(
            v.fair_value for v in valuation_results if v.fair_value and v.fair_value > 0
        ) / len([v for v in valuation_results if v.fair_value and v.fair_value > 0])
        if stock.current_price < avg_fair_value * 0.85:
            sentiment_score += 2  # Undervalued
        elif stock.current_price < avg_fair_value:
            sentiment_score += 1  # Slightly undervalued
        elif stock.current_price > avg_fair_value * 1.15:
            sentiment_score -= 2  # Overvalued
        elif stock.current_price > avg_fair_value:
            sentiment_score -= 1  # Slightly overvalued

    # News sentiment
    if news_data and news_data.get("analysis"):
        if news_data["analysis"].sentiment_score > 0.3:
            sentiment_score += 1
        elif news_data["analysis"].sentiment_score < -0.3:
            sentiment_score -= 1

    # Insider sentiment
    if insider_result:
        if insider_result.summary.sentiment == "bullish":
            sentiment_score += 1
        elif insider_result.summary.sentiment == "bearish":
            sentiment_score -= 1

    # FCF sentiment
    if fcf_result:
        if fcf_result.summary.fcf_quality.value in ["EXCELLENT", "GOOD"]:
            sentiment_score += 1
        elif fcf_result.summary.fcf_quality.value == "NEGATIVE":
            sentiment_score -= 1

    # Determine recommendation
    if sentiment_score >= 3:
        recommendation = "🟢 **强烈推荐买入**"
        action = "逢低分批建仓，长期持有"
    elif sentiment_score >= 1:
        recommendation = "🔵 **推荐买入**"
        action = "可考虑建仓，注意仓位控制"
    elif sentiment_score >= -1:
        recommendation = "🟡 **中性观望**"
        action = "等待更好入场点或维持现有仓位"
    elif sentiment_score >= -2:
        recommendation = "🟠 **谨慎**"
        action = "估值偏高，建议谨慎或减仓"
    else:
        recommendation = "🔴 **不推荐**"
        action = "基本面或估值存在较大问题，建议回避"

    sections.append(
        f"""## 10. 投资建议

### 10.1 综合评级

{recommendation}

**综合评分**: {sentiment_score}/5

### 10.2 操作建议

{action}

### 10.3 关键关注点

**看多因素**:
- 电动汽车渗透率持续提升
- 自动驾驶技术领先
- 储能业务快速增长
- 成本控制能力持续改善

**看空因素**:
- 估值处于历史高位
- 竞争加剧导致利润率承压
- 宏观经济不确定性
- CEO注意力分散风险

### 10.4 风险提示

⚠️ **本报告仅供参考，不构成投资建议**

- 股票投资存在风险，历史表现不代表未来收益
- 特斯拉股价波动较大，请根据自身风险承受能力决策
- 建议结合个人投资目标、财务状况和风险偏好做出决策
- 投资前建议咨询专业财务顾问

---

"""
    )

    # Footer
    sections.append(
        f"""## 📚 数据来源

- **财务数据**: yfinance (Yahoo Finance API)
- **估值引擎**: valueinvest library
- **新闻数据**: Yahoo Finance News
- **分析工具**: [valueinvest](https://github.com/wangzhe3224/valueinvest)

---

*报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} UTC*

> 本报告由 [valueinvest](https://github.com/wangzhe3224/valueinvest) 自动生成
"""
    )

    # Write report
    report_content = "".join(sections)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"✓ Report saved to: {output_path}")
    return report_content


def get_fcf_quality_desc(quality: str) -> str:
    """Get FCF quality description"""
    descriptions = {
        "EXCELLENT": "现金流极强，收益率>15%",
        "GOOD": "现金流良好，收益率10-15%",
        "ACCEPTABLE": "现金流可接受，收益率5-10%",
        "POOR": "现金流较弱，收益率0-5%",
        "NEGATIVE": "自由现金流为负",
    }
    return descriptions.get(quality, "未知")


def get_fcf_trend_desc(trend: str) -> str:
    """Get FCF trend description"""
    descriptions = {
        "IMPROVING": "现金流持续改善",
        "STABLE": "现金流保持稳定",
        "DECLINING": "现金流呈下降趋势",
        "VOLATILE": "现金流波动较大",
    }
    return descriptions.get(trend, "未知")


def main():
    """Main function to run complete Tesla analysis"""
    ticker = "TSLA"

    print("\n" + "=" * 80)
    print(f"Tesla (TSLA) - Complete Financial Analysis")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Fetch all data
    stock = fetch_fundamental_data(ticker)
    history = fetch_price_history(ticker, period="5y")
    valuation_results = run_valuation(stock, history)
    news_data = fetch_news_analysis(ticker, days=60)
    insider_result = fetch_insider_trading(ticker, days=180)
    buyback_result = fetch_buyback_data(ticker, days=730)
    fcf_result = fetch_fcf_data(ticker, years=5)

    # Create output directory
    output_dir = Path(__file__).parent.parent / "reports" / ticker
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate report
    report_date = datetime.now().strftime("%Y-%m-%d")
    output_path = output_dir / f"{report_date}_TSLA_financial_analysis.md"

    generate_markdown_report(
        ticker=ticker,
        stock=stock,
        history=history,
        valuation_results=valuation_results,
        news_data=news_data,
        insider_result=insider_result,
        buyback_result=buyback_result,
        fcf_result=fcf_result,
        output_path=str(output_path),
    )

    print("\n" + "=" * 80)
    print("✓ Analysis Complete!")
    print(f"Report saved to: {output_path}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
