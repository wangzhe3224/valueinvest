# ValueInvest

A modular Python library for comprehensive stock valuation using multiple methodologies with real-time data fetching and news sentiment analysis.

## Features

- **Real-time Data Fetching**: A-shares (AKShare), US stocks (yfinance), optional Tushare
- **Graham Valuation**: Graham Number, Graham Formula, NCAV (Net-Net)
- **Discounted Cash Flow**: DCF (10-year projection), Reverse DCF
- **Earnings Power Value**: Zero-growth intrinsic value
- **Dividend Models**: Gordon Growth, Two-Stage DDM
- **Growth Valuation**: PEG Ratio, GARP, Rule of 40
- **Bank Valuation**: P/B Valuation, Residual Income Model
- **News & Sentiment Analysis**: Keyword-based and LLM-based sentiment analysis
- **Analyst Data**: Company guidance and analyst expectations
- **Insider Trading**: Track executive buy/sell activity (A-share & US)
- **QFQ/HFQ Price Adjustment**: Proper price adjustment for valuation comparison and real returns

## Installation

```bash
# Create virtual environment
uv venv --python 3.11
source .venv/bin/activate

# Install with data sources
pip install -e ".[fetch]"      # All data sources
pip install -e ".[us]"         # US stocks only (yfinance)
pip install -e ".[ashare]"     # A-shares only (AKShare, free)
pip install -e ".[tushare]"    # A-shares with Tushare (requires token)
```

## Quick Start

### Command Line

```bash
# Analyze A-share stock
python stock_analyzer.py 600887           # 伊利股份
python stock_analyzer.py 600900           # 长江电力
python stock_analyzer.py 601398 --bank    # 工商银行 (force bank analysis)

# Analyze US stock
python stock_analyzer.py AAPL

# Options
python stock_analyzer.py 600887 --period 3y     # 3-year history
python stock_analyzer.py 600900 --dividend      # Force dividend analysis
python stock_analyzer.py 601398 --growth        # Force growth analysis

# With news analysis
python stock_analyzer.py 600887 --news          # Include news sentiment
python stock_analyzer.py AAPL --news --llm      # Use LLM for analysis
python stock_analyzer.py 600887 --news --news-days 60  # 60-day news

# With insider trading analysis
python stock_analyzer.py 600887 --insider       # Include insider trading
python stock_analyzer.py AAPL --insider --insider-days 180  # 180-day insider trades
```

### Python API

```python
from valueinvest import Stock, ValuationEngine

# Fetch real-time data
stock = Stock.from_api("600887")  # A-share
stock = Stock.from_api("AAPL")    # US stock

# Fetch price history separately
history = Stock.fetch_price_history("600887", period="5y")

# QFQ (前复权) - for valuation comparison
print(f"Price CAGR: {history.cagr:.2f}%")

# HFQ (后复权) - real returns including dividends
print(f"Real CAGR: {history.cagr_hfq:.2f}%")

# Run valuation
engine = ValuationEngine()
results = engine.run_all(stock)

# Category-specific methods
results = engine.run_dividend(stock)  # Dividend stocks
results = engine.run_bank(stock)      # Banks
results = engine.run_growth(stock)    # Growth stocks
```

## News & Sentiment Analysis

### Basic Usage

```python
from valueinvest.news.registry import NewsRegistry
from valueinvest.news.analyzer.keyword_analyzer import KeywordSentimentAnalyzer

# Fetch news (auto-detect market: A-share or US)
fetcher = NewsRegistry.get_fetcher("600887")
result = fetcher.fetch_all("600887", days=30)

# Analyze sentiment with keyword matching
analyzer = KeywordSentimentAnalyzer()
analysis = analyzer.analyze_batch(result.news, "600887")

# Access results
print(f"Sentiment Score: {analysis.sentiment_score:+.2f}")  # -1 to 1
print(f"Sentiment Label: {analysis.sentiment_label}")        # positive/negative/neutral
print(f"Key Themes: {analysis.key_themes}")
print(f"Risks: {analysis.risks}")
print(f"Catalysts: {analysis.catalysts}")

# News counts
print(f"Positive: {analysis.positive_count}")
print(f"Negative: {analysis.negative_count}")
print(f"Neutral: {analysis.neutral_count}")
```

### LLM-based Analysis (Optional)

For higher quality analysis, use the LLM analyzer with OpenAI:

```python
from valueinvest.news.analyzer.llm_analyzer import LLMSentimentAnalyzer
import os

os.environ["OPENAI_API_KEY"] = "sk-xxx"

analyzer = LLMSentimentAnalyzer(model="gpt-4o-mini")
analysis = analyzer.analyze_batch(result.news, "AAPL")

# LLM provides additional insights
for item in analysis.news:
    print(f"Rationale: {item.rationale}")  # Explanation for each news item
```

### Agent-based Analysis (No API Key Required)

Use coding agents for deep analysis without external API dependencies:

```python
from valueinvest.news.analyzer.agent_analyzer import (
    AgentSentimentAnalyzer,
    create_agent_analysis_prompt,
    enhance_analysis_with_agent_result,
)

# Create agent analyzer with stock context
analyzer = AgentSentimentAnalyzer(
    stock_name="伊利股份",
    current_price=26.0,
    company_type="value",
)

# Get initial analysis (keyword-based as foundation)
analysis = analyzer.analyze_batch(news, "600887")

# Create prompt for coding agent (use with ultrabrain/deep)
prompt = create_agent_analysis_prompt(
    ticker="600887",
    stock_name="伊利股份",
    current_price=26.0,
    company_type="value",
    news=news,
    days=30,
)

# After getting response from coding agent, enhance the analysis:
agent_response = {
    "sentiment_score": 0.65,
    "key_themes": ["业绩增长", "分红提升"],
    "risks": ["竞争加剧"],
    "catalysts": ["新品发布"],
}
enhanced = enhance_analysis_with_agent_result(analysis, agent_response)
```

CLI usage for agent-based analysis:
```bash
# Use coding agent for deep news analysis
python stock_analyzer.py 600887 --news --agent
```

### Guidance & Analyst Data

```python
# Access analyst guidance
if analysis.has_guidance:
    guidance = analysis.latest_guidance
    
    print(f"Fiscal Year: {guidance.fiscal_year} Q{guidance.quarter}")
    
    # Company guidance
    if guidance.has_company_guidance:
        print(f"EPS Guidance: {guidance.company_eps_low}-{guidance.company_eps_high}")
    
    # Analyst expectations
    if guidance.has_analyst_data:
        print(f"Analyst EPS Mean: {guidance.analyst_eps_mean}")
        print(f"Analyst Count: {guidance.analyst_count}")
        print(f"Rating: {guidance.analyst_rating.value}")
    
    # Compare guidance vs consensus
    print(f"vs Consensus: {guidance.guidance_vs_consensus}")  # above/below/in_line
```

## Insider Trading

### Basic Usage

```python
from valueinvest.insider import InsiderRegistry

# Auto-detect market
fetcher = InsiderRegistry.get_fetcher("600887")
result = fetcher.fetch_insider_trades("600887", days=365)

# Access summary
print(f"Sentiment: {result.summary.sentiment}")  # bullish/bearish/neutral
print(f"Buys: {result.summary.buy_count}, Sells: {result.summary.sell_count}")
print(f"Net shares: {result.summary.net_shares:+,.0f}")
print(f"Net value: ¥{result.summary.net_value:+,.0f}")

# Access individual trades
for trade in result.trades[:5]:
    print(f"{trade.trade_date}: {trade.insider_name} {trade.trade_type.value} {trade.shares:,.0f} @ ¥{trade.price}")
```

### Insider Trading Data Sources

| Source | Markets | Data | Auth |
|--------|---------|------|------|
| AKShare (同花顺) | A-shares | ✅ 高管增减持 | Free |
| yfinance | US/Intl | ✅ Insider purchases | Free |

### News Data Sources

| Source | Markets | News | Guidance | Auth |
|--------|---------|------|----------|------|
| AKShare | A-shares | ✅ East Money | ❌ | Free |
| yfinance | US/Intl | ✅ Yahoo Finance | ✅ Analyst data | Free |

## Data Sources

| Source | Markets | Auth | Install |
|--------|---------|------|---------|
| AKShare | A-shares | Free | `pip install valueinvest[ashare]` |
| yfinance | US/Intl | Free | `pip install valueinvest[us]` |
| Tushare | A-shares | Token | `TUSHARE_TOKEN=xxx pip install valueinvest[tushare]` |

Auto-detection by ticker format:
- 6 digits (600887) → AKShare
- Letters (AAPL) → yfinance

## QFQ vs HFQ Price Adjustment

| Type | Use Case | Characteristics |
|------|----------|-----------------|
| QFQ (前复权) | Valuation comparison | Current price unchanged, historical adjusted |
| HFQ (后复权) | Real investment returns | Historical unchanged, dividends compounded |

```python
history = Stock.fetch_price_history("600900", period="5y")

# QFQ: Price-only growth (for comparing with valuation)
print(f"QFQ CAGR: {history.cagr:.2f}%")

# HFQ: Total return including dividends reinvested
print(f"HFQ CAGR: {history.cagr_hfq:.2f}%")

# Recent prices
stats_qfq = history.get_price_stats(days=30, adjust="qfq")
stats_hfq = history.get_price_stats(days=30, adjust="hfq")
```

## Company Type Detection

Automatic classification based on ticker and financials:
- **Utilities** (600900, etc.) → Dividend
- **Banks** (601398, etc.) → Bank
- **Dividend yield > 3%** → Dividend
- **HFQ CAGR > 10%** → Growth
- **HFQ CAGR < 5%** → Value

## Available Valuation Methods

| Method | Best For | Key Formula |
|--------|----------|-------------|
| Graham Number | Defensive investors | √(22.5 × EPS × BVPS) |
| Graham Formula | Moderate growth | V = (EPS × (8.5 + 2g) × 4.4) / Y |
| NCAV | Deep value | (Assets - Liabilities) / Shares |
| DCF | Growth companies | PV(Free Cash Flows) + Terminal Value |
| Reverse DCF | Any | What growth is priced in? |
| EPV | Mature companies | Distributable CF / Cost of Capital |
| DDM | Dividend stocks | D / (r - g) |
| Two-Stage DDM | Dividend growth | Stage 1 + Terminal perpetuity |
| PEG | Profitable growth | P/E ÷ Growth Rate |
| GARP | Growth at reasonable price | Future EPS × Target P/E, discounted |
| Rule of 40 | SaaS/Subscription | Growth % + Margin % ≥ 40 |
| P/B Valuation | Banks | Fair P/B = (ROE - g) / (COE - g) |
| Residual Income | Banks | Book Value + PV(Excess Returns) |

## Project Structure

```
valueinvest/
├── stock.py                 # Stock dataclass, StockHistory
├── valuation/
│   ├── base.py              # Base classes
│   ├── engine.py            # Unified engine
│   ├── graham.py            # Graham methods
│   ├── dcf.py               # DCF methods
│   ├── epv.py               # Earnings Power Value
│   ├── ddm.py               # Dividend models
│   ├── growth.py            # Growth valuation
│   ├── bank.py              # Bank valuation
│   └── magic_formula.py     # Magic Formula
├── news/                    # News & sentiment analysis
│   ├── base.py              # NewsItem, Guidance, NewsAnalysisResult
│   ├── registry.py          # Market detection & fetcher registry
│   ├── fetcher/
│   │   ├── base.py          # BaseNewsFetcher (ABC)
│   │   ├── akshare_news.py  # A-share news (East Money)
│   │   └── yfinance_news.py # US stock news & analyst data
│   └── analyzer/
│       ├── base.py          # BaseSentimentAnalyzer (ABC)
│       ├── keyword_analyzer.py  # Keyword-based sentiment
│       ├── llm_analyzer.py      # LLM-based sentiment (OpenAI)
│       └── agent_analyzer.py    # Coding agent-based sentiment
├── insider/                 # Insider trading data
│   ├── base.py              # InsiderTrade, InsiderSummary, InsiderFetchResult
│   ├── registry.py          # Market detection & fetcher registry
│   └── fetcher/
│       ├── base.py          # BaseInsiderFetcher (ABC)
│       ├── akshare_insider.py  # A-share (同花顺高管增减持)
│       └── yfinance_insider.py # US stock insider transactions
├── data/
│   ├── presets.py           # Pre-configured stocks
│   └── fetcher/             # Data fetching
│       ├── base.py          # Base classes
│       ├── akshare.py       # A-shares (free)
│       ├── yfinance.py      # US/Intl stocks
│       └── tushare.py       # A-shares (token)
└── reports/
    ├── reporter.py          # Report formatting
    └── enhanced_reporter.py # Enhanced report with news

stock_analyzer.py            # CLI entry point
```

## Example Output

### With News Analysis

```
======================================================================
伊利股份 (600887) - 深度分析报告
======================================================================

【公司概况】
  公司: 伊利股份
  代码: 600887
  类型: 价值股
  当前股价: ¥26.48
  总市值: ¥1675亿

【最新财务数据】
  营业收入: ¥903亿
  净利润: ¥104亿
  每股收益 (EPS): ¥1.65
  每股净资产 (BVPS): ¥8.90
  市盈率 (PE): 16.0倍
  市净率 (PB): 2.97倍

======================================================================
【新闻情感分析】
======================================================================

  情感得分: 📈 +0.25 (positive)
  分析新闻数: 25 条 (7日内: 8)
  正面/负面/中性: 12/5/8
  置信度: 72%
  趋势: ➡️ 稳定

【关键主题】
  • 原材料成本下降
  • 渠道扩张
  • 产品创新

【风险提示】
  ⚠️ 竞争加剧
  ⚠️ 成本波动

【潜在催化剂】
  ✅ 新品发布
  ✅ 旺季销售

【近期重要新闻】
  [+] 02-15 伊利股份发布业绩预告，净利润增长20%...
  [+] 02-14 公司宣布分红方案，股息率提升至3.5%...
  [ ] 02-12 行业分析：乳制品市场稳中有升...

======================================================================
【估值汇总】
======================================================================

| 方法                | 公允价值 | 溢价/折价 | 评估      |
|---------------------|----------|-----------|-----------|
| Graham Number       | ¥  18.18 |   -31.3%  | Overvalued|
| DDM (Gordon Growth) | ¥  20.94 |   -20.9%  | Overvalued|
| GARP                | ¥  19.54 |   -26.2%  | Overvalued|
| Reverse DCF         | ¥  26.48 |    +0.0%  | Priced in |
| Graham Formula      | ¥  46.17 |   +74.4%  | Undervalued|

======================================================================
【综合结论】
======================================================================

估值区间: ¥18-21 (保守) / ¥26 (现价) / ¥40+ (乐观)

【综合评级】: 🟡 合理 + 正面消息

投资建议:
  1. 目标买入价: ¥22 (15%安全边际)
  2. 止损位: ¥16
  3. 情绪面: 近期消息偏正面，可积极关注
```

## Extending the News Module

### Adding a New Market

```python
from valueinvest.news.base import Market
from valueinvest.news.fetcher.base import BaseNewsFetcher
from valueinvest.news.registry import NewsRegistry

class HKNewsFetcher(BaseNewsFetcher):
    market = Market.HK
    
    @property
    def source_name(self) -> str:
        return "hk_source"
    
    def fetch_news(self, ticker, days=30, start_date=None, end_date=None):
        # Implement news fetching for Hong Kong stocks
        ...
    
    def fetch_guidance(self, ticker):
        # Implement guidance fetching
        ...

# Register the new fetcher
NewsRegistry.register_fetcher(Market.HK, HKNewsFetcher)

# Register market detector
NewsRegistry.register_detector(
    lambda t: Market.HK if t.isdigit() and len(t) == 5 else None
)
```

## Extending the Insider Module

### Adding a New Market

```python
from valueinvest.news.base import Market
from valueinvest.insider.base import InsiderTrade, InsiderFetchResult
from valueinvest.insider.fetcher.base import BaseInsiderFetcher
from valueinvest.insider.registry import InsiderRegistry

class HKInsiderFetcher(BaseInsiderFetcher):
    market = Market.HK
    
    @property
    def source_name(self) -> str:
        return "hk_source"
    
    def fetch_insider_trades(self, ticker, days=90, start_date=None, end_date=None):
        # Implement insider trading fetching for Hong Kong stocks
        ...

# Register the new fetcher
InsiderRegistry.register_fetcher(Market.HK, HKInsiderFetcher)
```

## License

MIT License
