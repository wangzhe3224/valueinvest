# ValueInvest

A modular Python library for comprehensive stock valuation using multiple methodologies with real-time data fetching and news sentiment analysis.

## ✨ Recent Updates

**2026-03-28**: Major data quality and valuation fixes
- Fixed 12+ fields returning None/0 from `Stock.from_api()` (operating_cash_flow, ebitda, sector, inventory, prior_* data, etc.)
- Fixed Graham Number, Magic Formula, and Value Trap detector edge cases
- Added `revenue_cagr_5y`, `earnings_cagr_5y`, and other computed properties
- See [CHANGELOG.md](CHANGELOG.md) for detailed changes

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
- **Buyback Analysis**: Share repurchase tracking and shareholder yield
- **Free Cash Flow Analysis**: FCF quality, SBC impact, and profitability metrics
- **Quality Scoring**: Piotroski F-Score, Altman Z-Score for financial health
- **Earnings Manipulation Detection**: Beneish M-Score for fraud risk assessment
- **Relative Valuation**: PE/PB comparison vs historical and peer averages
- **Cyclical Stock Analysis**: Cycle position scoring, cyclical-adjusted valuation (PB/PE/FCF), market-specific strategies
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
pip install -e ".[learn]"      # Jupyter notebooks + visualization

# For learning notebooks (recommended)
pip install -e ".[learn,fetch]"  # Learning + all data sources

## Quick Start

### Command Line

```bash
# Analyze A-share stock
python scripts/stock_analyzer.py 600887           # 伊利股份
python scripts/stock_analyzer.py 600900           # 长江电力
python scripts/stock_analyzer.py 601398 --bank    # 工商银行 (force bank analysis)

# Analyze US stock
python scripts/stock_analyzer.py AAPL

# Options
python scripts/stock_analyzer.py 600887 --period 3y     # 3-year history
python scripts/stock_analyzer.py 600900 --dividend      # Force dividend analysis
python scripts/stock_analyzer.py 601398 --growth        # Force growth analysis

# With news analysis
python scripts/stock_analyzer.py 600887 --news          # Include news sentiment
python scripts/stock_analyzer.py AAPL --news --llm      # Use LLM for analysis
python scripts/stock_analyzer.py 600887 --news --news-days 60  # 60-day news

# With insider trading analysis
python scripts/stock_analyzer.py 600887 --insider       # Include insider trading
python scripts/stock_analyzer.py AAPL --insider --insider-days 180  # 180-day insider trades

# With buyback analysis (recommended for US stocks)
python scripts/stock_analyzer.py AAPL --buyback         # Include buyback analysis
python scripts/stock_analyzer.py 600887 --buyback       # A-share buyback analysis

# With FCF (Free Cash Flow) analysis
python scripts/stock_analyzer.py AAPL --fcf             # Include FCF analysis
python scripts/stock_analyzer.py AAPL --fcf --fcf-years 7  # 7-year FCF history
python scripts/stock_analyzer.py AAPL --buyback --fcf   # Full shareholder return analysis

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
python scripts/stock_analyzer.py 600887 --news --agent
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

## Buyback Analysis

For US stocks, buyback yield is often more important than dividend yield (e.g., AAPL returns ~2.3% via buyback vs ~0.4% dividend).

### Basic Usage

```python
from valueinvest.buyback import BuybackRegistry

# Auto-detect market
fetcher = BuybackRegistry.get_fetcher("AAPL")
result = fetcher.fetch_buyback("AAPL", days=365)

# Access summary
summary = result.summary
print(f"Buyback Yield: {summary.buyback_yield:.2f}%")
print(f"Dividend Yield: {summary.dividend_yield:.2f}%")
print(f"Total Shareholder Yield: {summary.total_shareholder_yield:.2f}%")
print(f"Sentiment: {summary.sentiment.value}")  # aggressive/moderate/minimal/none

# Yearly buyback amounts
for year, amount in summary.yearly_amounts.items():
    print(f"{year}: ${amount/1e9:.2f}B")

# Access individual records
for record in result.records[:5]:
    print(f"{record.execution_date}: ${record.amount/1e9:.2f}B")
```

### Buyback Data Sources

| Source | Markets | Data | Auth |
|--------|---------|------|------|
| AKShare (东方财富) | A-shares | ✅ 回购计划与执行 | Free |
| yfinance | US/Intl | ✅ Cash flow buyback | Free |

### CLI Usage

```bash
python scripts/stock_analyzer.py AAPL --buyback            # US stock buyback analysis
python scripts/stock_analyzer.py 600887 --buyback          # A-share buyback analysis
python scripts/stock_analyzer.py AAPL --buyback --buyback-days 730  # 2-year history
```

## Free Cash Flow (FCF) Analysis

FCF analysis helps evaluate the quality of a company's cash generation, including SBC (Stock-Based Compensation) impact on true profitability.

### Basic Usage

```python
from valueinvest.cashflow import CashFlowRegistry

# Auto-detect market
fetcher = CashFlowRegistry.get_fetcher("AAPL")
result = fetcher.fetch_cashflow("AAPL", years=5)

# Access summary
summary = result.summary
print(f"FCF Quality: {summary.fcf_quality.value}")  # EXCELLENT/GOOD/ACCEPTABLE/POOR/NEGATIVE
print(f"FCF Trend: {summary.fcf_trend.value}")    # IMPROVING/STABLE/DECLINING/VOLATILE
print(f"FCF Yield: {summary.fcf_yield:.2f}%")
print(f"FCF Margin: {summary.fcf_margin:.2f}%")

# SBC-adjusted (True FCF)
print(f"True FCF (SBC-adjusted): ${summary.latest_true_fcf/1e9:.2f}B")
print(f"True FCF Yield: {summary.true_fcf_yield:.2f}%")
print(f"SBC as % of FCF: {summary.sbc_as_pct_of_fcf:.1f}%")

# Profitability quality
print(f"FCF / Net Income: {summary.fcf_to_net_income:.2f}x")
print(f"FCF CAGR: {summary.fcf_cagr:.1f}%")
```

### Key Metrics

| Metric | Description |
| :--- | :--- |
| FCF Quality | EXCELLENT (>15% yield), GOOD (10-15%), ACCEPTABLE (5-10%), POOR (0-5%), NEGATIVE (<0) |
| FCF Trend | IMPROVING, STABLE, DECLINING, VOLATILE |
| FCF Yield | FCF / Market Cap |
| FCF Margin | FCF / Revenue |
| True FCF | FCF - SBC (stock-based compensation) |
| FCF / Net Income | Cash quality of earnings (>1.0 is excellent) |

### FCF Data Sources

| Source | Markets | Data | Auth |
| :--- | :--- | :--- | :--- |
| yfinance | US/Intl | ✅ Cash flow statement | Free |

### CLI Usage

```bash
python scripts/stock_analyzer.py AAPL --fcf                  # FCF analysis (default 5 years)
python scripts/stock_analyzer.py AAPL --fcf --fcf-years 7   # 7-year FCF history
python scripts/stock_analyzer.py AAPL --buyback --fcf       # Combined shareholder return analysis
```

## Piotroski F-Score

The Piotroski F-Score is a 9-point scale that evaluates the financial strength of a company, developed by accounting professor Joseph Piotroski. It's particularly useful for identifying high-quality value stocks.

### Basic Usage

```python
from valueinvest import Stock
from valueinvest.valuation import ValuationEngine
from valueinvest.valuation.quality import calculate_f_score

# Method 1: Via Engine (uses Stock's prior year fields)
stock = Stock(
    ticker="AAPL",
    name="Apple Inc.",
    current_price=180.0,
    shares_outstanding=15.5e9,
    net_income=100e9,
    total_assets=350e9,
    total_liabilities=120e9,
    current_assets=60e9,
    fcf=110e9,
    operating_margin=30.0,
    revenue=400e9,
    # Prior year data for trend analysis
    prior_roa=0.28,
    prior_debt_ratio=0.35,
    prior_current_ratio=0.9,
    prior_shares_outstanding=16.0e9,
    prior_gross_margin=28.0,
    prior_asset_turnover=1.1,
)

engine = ValuationEngine()
result = engine.run_single(stock, "piotroski_f")
print(f"F-Score: {result.details['f_score']}/9")
print(f"Risk Level: {result.details['risk_level']}")

# Method 2: Via convenience function
fscore = calculate_f_score(
    stock,
    prior_roa=0.28,
    prior_debt_ratio=0.35,
    prior_current_ratio=0.9,
    prior_shares_outstanding=16.0e9,
    prior_gross_margin=28.0,
    prior_asset_turnover=1.1,
)
print(f"F-Score: {fscore.total_score}/9")
print(f"Profitability: {fscore.profitability_score}/4")
print(f"Leverage: {fscore.leverage_score}/3")
print(f"Efficiency: {fscore.efficiency_score}/2")
```

### The 9 Criteria

| Category | Criteria | Points |
| :--- | :--- | :--- |
| **Profitability** | ROA > 0 | 1 |
| | Operating Cash Flow > 0 | 1 |
| | ROA improved vs prior year | 1 |
| | OCF > Net Income (earnings quality) | 1 |
| **Leverage/Liquidity** | Debt ratio decreased | 1 |
| | Current ratio increased | 1 |
| | No significant share dilution | 1 |
| **Operating Efficiency** | Gross margin improved | 1 |
| | Asset turnover improved | 1 |

### Interpretation

| Score | Interpretation | Risk Level |
| :--- | :--- | :--- |
| 8-9 | Strong - Excellent financial health | Low |
| 6-7 | Good - Solid financial position | Low |
| 4-5 | Average - Some financial concerns | Medium |
| 0-3 | Weak - Poor financial health | High |

### CLI Usage

```bash
python scripts/stock_analyzer.py 600887 --method piotroski_f
```

## Beneish M-Score

The Beneish M-Score is an 8-variable model developed by Professor Messod D. Beneish to detect earnings manipulation. It identifies companies that may be manipulating their financial statements.

### Basic Usage

```python
from valueinvest import Stock
from valueinvest.valuation import ValuationEngine
from valueinvest.valuation.mscore import calculate_m_score

# Method 1: Via Engine (requires prior year data in Stock)
stock = Stock(
    ticker="AAPL",
    name="Apple Inc.",
    current_price=180.0,
    revenue=400e9,
    net_income=100e9,
    total_assets=350e9,
    accounts_receivable=30e9,
    # Prior year data for comparison
    prior_revenue=380e9,
    prior_gross_margin=28.0,
    prior_total_assets=330e9,
)

engine = ValuationEngine()
result = engine.run_single(stock, "beneish_m")
print(f"M-Score: {result.details['m_score']}")
print(f"Manipulation Risk: {result.details['manipulation_risk']}")

# Method 2: Via convenience function
m_result = calculate_m_score(
    stock,
    prior_revenue=380e9,
    prior_gross_margin=28.0,
    prior_total_assets=330e9,
)
print(f"M-Score: {m_result.m_score:.2f}")
print(f"Is Manipulator: {m_result.is_manipulator}")
```

### The 8 Variables

| Variable | Name | What It Measures |
| :--- | :--- | :--- |
| DSRI | Days Sales Receivable Index | Revenue inflation via loose credit |
| GMI | Gross Margin Index | Deteriorating margins |
| AQI | Asset Quality Index | Increased intangibles/other assets |
| SGI | Sales Growth Index | Pressure from high growth |
| DEPI | Depreciation Index | Aggressive depreciation policy |
| SGAI | SG&A Index | Declining efficiency |
| LVGI | Leverage Index | Increasing debt |
| TATA | Total Accruals to Total Assets | Low earnings quality |

### Interpretation

| M-Score | Interpretation | Risk Level |
| :--- | :--- | :--- |
| < -2.22 | Non-manipulator | Low |
| -2.22 to -1.78 | Potential manipulator | Medium |
| > -1.78 | High probability manipulator | High |

### CLI Usage

```bash
python scripts/stock_analyzer.py AAPL --method beneish_m
```

---

## Relative Valuation (PE/PB)

Relative valuation compares current multiples to historical averages and peer groups - the standard approach used in professional equity research.

### PE Relative Valuation

Compares current P/E ratio to historical and peer averages. Best for profitable companies with stable earnings.

#### Basic Usage

```python
from valueinvest import Stock
from valueinvest.valuation import ValuationEngine

stock = Stock(
    ticker="AAPL",
    name="Apple Inc.",
    current_price=180.0,
    eps=6.0,
    pe_ratio=30.0,
    historical_pe=[25, 28, 30, 32, 27],  # 5-year history
)

engine = ValuationEngine()
result = engine.run_single(stock, "pe_relative")

print(f"Current P/E: {result.details['current_pe']:.1f}x")
print(f"Historical Avg: {result.details['historical_avg_pe']:.1f}x")
print(f"Percentile: {result.details['percentile_in_history']:.0f}th")
print(f"vs Historical: {result.details['vs_historical_pct']:+.1f}%")
```

#### Interpretation

- **Bottom quartile (0-25th percentile)**: Potentially undervalued or deteriorating fundamentals
- **Middle range (40-60th percentile)**: Fair value
- **Top quartile (75-100th percentile)**: Potentially overvalued or improving fundamentals

### PB Relative Valuation

Compares current P/B ratio to historical and peer averages. Best for banks, financials, and asset-heavy companies.

#### Basic Usage

```python
from valueinvest import Stock
from valueinvest.valuation import ValuationEngine

stock = Stock(
    ticker="601398",
    name="工商银行",
    current_price=5.0,
    bvps=8.0,
    pb_ratio=0.625,
    historical_pb=[0.7, 0.8, 0.65, 0.75, 0.72],  # 5-year history
)

engine = ValuationEngine()
result = engine.run_single(stock, "pb_relative")

print(f"Current P/B: {result.details['current_pb']:.2f}x")
print(f"Historical Avg: {result.details['historical_avg_pb']:.2f}x")
print(f"Fair Value: ${result.fair_value:.2f}")
```

#### When to Use P/B Relative

- Banks and financial institutions
- Asset-heavy industries (manufacturing, utilities)
- Value investing strategies
- Companies trading below book value (P/B < 1.0)

### CLI Usage

```bash
# PE Relative
python scripts/stock_analyzer.py AAPL --method pe_relative

# PB Relative
python scripts/stock_analyzer.py 601398 --method pb_relative
```

---

## Cyclical Stock Analysis

The cyclical stock analysis module provides comprehensive tools for analyzing cyclical stocks (shipping, steel, metals, energy, etc.) with different strategies for A-share and US markets.

### Key Features

- **Cycle Position Scoring**: Multi-dimensional scoring (valuation, financial, industry, sentiment) to determine cycle phase (Bottom → Top)
- **Cyclical-Adjusted Valuation Methods**:
  - **Cyclical PB**: Dynamic PB thresholds based on cycle phase (A-share: Buy < 1.0-1.2x, US: Buy < 1.0-1.4x)
  - **Cyclical PE**: Normalized earnings using 3-5 year averages to avoid "cycle top low PE trap"
  - **Cyclical FCF**: Free cash flow yield analysis (A-share: Buy > 10%, US: Buy > 12%)
  - **Cyclical Dividend**: Dividend sustainability assessment for US stocks
- **Differentiated Strategies**:
  - **A-Share**: Trading-oriented (1-3 year holding, +50-200% target return)
  - **US**: Dividend-defensive (5-10 year holding, 6-10% annual return)
- **Investment Rating**: 强烈推荐/推荐/中性/谨慎/不推荐 with 0-100 scoring

### Basic Usage

```python
from valueinvest.cyclical import (
    CyclicalAnalysisEngine,
    CyclicalStock,
    CycleType,
    MarketType,
)

# Create stock data
stock = CyclicalStock(
    ticker="601919",
    name="中远海控",
    market=MarketType.A_SHARE,
    current_price=15.79,
    cycle_type=CycleType.SHIPPING,
    pb=1.09,
    bvps=14.5,
    eps=1.73,
    pe=9.1,
    fcf_yield=0.079,  # 7.9%
    fcf_per_share=1.25,
    fcf_to_net_income=1.1,
    dividend_yield=0.05,  # 5.0%
    debt_ratio=0.35,
    roe=0.12,  # 12.0%
    historical_pb=[1.5, 2.0, 1.8, 2.5, 1.2],
)

# Run complete analysis
engine = CyclicalAnalysisEngine()
result = engine.analyze(stock)

# View results
print(f"股票: {result.stock.name} ({result.stock.ticker})")
print(f"周期阶段: {result.cycle_analysis.phase_display}")
print(f"周期得分: {result.cycle_analysis.total_score:.2f}/5.0")
print(f"综合评分: {result.overall_score}/100")
print(f"投资评级: {result.investment_rating}")
print(f"投资行动: {result.strategy_recommendation.action_display}")
print(f"建议仓位: {result.strategy_recommendation.target_allocation:.1%}")
print(f"目标价格: ¥{result.strategy_recommendation.target_price:.2f}")
```

### Cycle Types

| Cycle Type | Examples | Characteristics |
| :--- | :--- | :--- |
| SHIPPING | 中远海控, 中远海能 | BDI-driven, 3-5 year cycles |
| COMMODITY | 中国铝业, 紫金矿业 | Metal prices, global demand |
| CAPACITY | 宝钢股份, 万华化学 | Supply-demand, capex cycles |
| ENERGY | 中国石油, Exxon | Oil/gas prices, OPEC policy |
| FINANCIAL | Banks, Insurance | Interest rate, credit cycles |
| REAL_ESTATE | Developers | Property market, policy |

### Cycle Phases

| Phase | Score | Strategy | Valuation Focus |
| :--- | :--- | :--- | :--- |
| Bottom | 0-2.0 | Strong Buy | PB < 1.0, FCF yield > 10% |
| Early Upside | 2.0-3.0 | Buy | PB 1.0-1.5, momentum building |
| Mid Upside | 3.0-3.5 | Hold/Add | PB 1.5-2.0, ride the trend |
| Late Upside | 3.5-4.0 | Reduce | PB > 2.0, take profits |
| Top | 4.0-5.0 | Sell | PB > 2.5-3.0, exit position |

### CLI Usage

```bash
# Analyze cyclical stock
python scripts/stock_analyzer.py 601919 --cyclical
python scripts/stock_analyzer.py 601919 --cyclical --cycle-type SHIPPING

# With news analysis
python scripts/stock_analyzer.py 601919 --cyclical --news
```

### Example Analyses

- **中远海控 (601919)**: Shipping cyclical - see `scripts/analyze_cyclical_stock.py`
- **云天化 (600096)**: Phosphorus chemical cyclical - see `scripts/analyze_600096.py` and report at `reports/600096/2026-03-09_600096_analysis.md`

---

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
| **PE Relative** | **Peer comparison** | **Current PE vs Historical/Peer Avg** |
| **PB Relative** | **Asset-heavy, Banks** | **Current PB vs Historical/Peer Avg** |
| **Beneish M-Score** | **Fraud detection** | **8-variable earnings manipulation score** |
| Piotroski F-Score | Quality screening | 9-point financial strength score |
| Altman Z-Score | Bankruptcy risk | Z = 1.2X1 + 1.4X2 + 3.3X3 + 0.6X4 + 1.0X5 |
| **Cyclical PB** | **Cyclical stocks** | **Dynamic PB thresholds based on cycle phase** |
| **Cyclical PE** | **Cyclical stocks** | **Normalized earnings using 3-5 year average** |
| **Cyclical FCF** | **Cyclical stocks** | **FCF yield with cycle-adjusted thresholds** |
| **Cyclical Dividend** | **Cyclical stocks (US)** | **Dividend sustainability + FCF coverage** |

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
│   ├── quality.py           # Piotroski F-Score, Altman Z-Score, Owner Earnings
│   ├── value_trap.py        # Value trap detection
│   ├── magic_formula.py     # Magic Formula
│   ├── mscore.py            # Beneish M-Score (earnings manipulation)
│   └── relative.py          # PE/PB Relative valuation
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
├── buyback/                 # Buyback/repurchase analysis
│   ├── base.py              # BuybackRecord, BuybackSummary, BuybackFetchResult
│   ├── registry.py          # Market detection & fetcher registry
│   └── fetcher/
│       ├── base.py          # BaseBuybackFetcher (ABC)
│       ├── akshare_buyback.py  # A-share (东方财富回购数据)
│       └── yfinance_buyback.py # US stock cash flow buyback
├── cashflow/                # Free Cash Flow analysis
│   ├── base.py              # CashFlowRecord, CashFlowSummary, CashFlowFetchResult
│   ├── registry.py          # Market detection & fetcher registry
│   └── fetcher/
│       ├── base.py          # BaseCashFlowFetcher (ABC)
│       └── yfinance_cashflow.py # US stock cash flow data
├── cyclical/                # Cyclical stock analysis
│   ├── base.py              # CyclicalStock, CycleScore, ValuationResult
│   ├── enums.py             # CycleType, CyclePhase, MarketType, etc.
│   ├── engine.py            # CyclicalAnalysisEngine
│   ├── position_scorer.py   # Cycle position scoring system
│   ├── valuation/           # Cyclical valuation methods
│   │   ├── cyclical_pb.py   # Cyclical PB valuation
│   │   ├── cyclical_pe.py   # Cyclical PE valuation
│   │   ├── cyclical_fcf.py  # Cyclical FCF valuation
│   │   └── cyclical_dividend.py # Cyclical dividend valuation
│   └── strategy/            # Market-specific strategies
│       ├── ashare_strategy.py  # A-share (trading-oriented)
│       └── us_strategy.py      # US (dividend-defensive)
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

scripts/stock_analyzer.py            # CLI entry point

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
