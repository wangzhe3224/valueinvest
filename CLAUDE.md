# ValueInvest

Python library for stock valuation using multiple methodologies with real-time data fetching and news sentiment analysis.

## Tech Stack
- Python 3.9+, dataclasses, abc
- AKShare (A股数据), yfinance (美股数据), tushare (可选)
- OpenAI API (可选，用于 LLM 情感分析)

## Setup

```bash
# Create venv
uv venv --python 3.11
source .venv/bin/activate

# Install with data sources
uv pip install --python .venv/bin/python -e ".[fetch]"  # All sources
uv pip install --python .venv/bin/python -e ".[us]"     # US stocks only
uv pip install --python .venv/bin/python -e ".[ashare]" # A-shares (free)
```

## Architecture
```
valueinvest/
├── stock.py              # Stock dataclass, StockHistory, from_api()
├── valuation/
│   ├── base.py           # BaseValuation (ABC), ValuationResult (dataclass)
│   ├── engine.py         # ValuationEngine (runs methods, aggregates results)
│   ├── graham.py         # Graham Number, Graham Formula, NCAV
│   ├── dcf.py            # DCF, Reverse DCF
│   ├── epv.py            # Earnings Power Value
│   ├── ddm.py            # Gordon Growth, Two-Stage DDM
│   ├── growth.py         # PEG, GARP, Rule of 40
│   ├── bank.py           # P/B Valuation, Residual Income
│   └── magic_formula.py  # Joel Greenblatt's Magic Formula (EY + ROC)
├── news/                 # News & sentiment analysis
│   ├── base.py           # NewsItem, Guidance, NewsAnalysisResult
│   ├── registry.py       # Market detection & fetcher registry
│   ├── fetcher/
│   │   ├── base.py       # BaseNewsFetcher (ABC)
│   │   ├── akshare_news.py  # A-share news (East Money)
│   │   └── yfinance_news.py # US stock news & analyst data
│   └── analyzer/
│       ├── base.py       # BaseSentimentAnalyzer (ABC)
│       ├── keyword_analyzer.py  # Keyword-based sentiment
│       └── llm_analyzer.py      # LLM-based sentiment (OpenAI)
├── data/
│   ├── presets.py        # Pre-configured stock data
│   └── fetcher/          # Data fetching module
│       ├── base.py       # BaseFetcher, FetchResult, HistoryResult
│       ├── akshare.py    # A-shares (free, no auth)
│       ├── yfinance.py   # US/International stocks
│       └── tushare.py    # A-shares (requires token)
└── reports/
    ├── reporter.py       # Format output tables
    └── enhanced_reporter.py  # Enhanced report with news
```

## Key Patterns

### Fetch Stock Data
```python
from valueinvest import Stock

# Fetch fundamentals only
stock = Stock.from_api("600887")  # A-share
stock = Stock.from_api("AAPL")    # US stock

# Fetch price history separately
history = Stock.fetch_price_history("600887", period="5y")

# QFQ (前复权) - for valuation comparison
stats_qfq = history.get_price_stats(days=30, adjust="qfq")

# HFQ (后复权) - real returns including dividends
real_cagr = history.cagr_hfq
```

### Run Valuations
```python
from valueinvest import ValuationEngine

engine = ValuationEngine()
results = engine.run_all(stock)
results = engine.run_dividend(stock)  # Dividend stocks
results = engine.run_bank(stock)      # Banks
results = engine.run_growth(stock)    # Growth stocks
```

### Add New Valuation Method
- Extend `BaseValuation`, implement `calculate(stock) -> ValuationResult`
- Register in `ValuationEngine._methods` dict

### News & Sentiment Analysis
```python
from valueinvest.news import NewsItem, NewsAnalysisResult
from valueinvest.news.registry import NewsRegistry
from valueinvest.news.analyzer.keyword_analyzer import KeywordSentimentAnalyzer

# Fetch news (auto-detect market)
fetcher = NewsRegistry.get_fetcher("600887")
result = fetcher.fetch_all("600887", days=30)

# Analyze sentiment
analyzer = KeywordSentimentAnalyzer()
analysis = analyzer.analyze_batch(result.news, "600887")
analysis.guidance = result.guidance

# Access results
print(f"Sentiment: {analysis.sentiment_score:+.2f}")
print(f"Themes: {analysis.key_themes}")
print(f"Risks: {analysis.risks}")
```

### LLM-based Sentiment Analysis (Optional)
```python
from valueinvest.news.analyzer.llm_analyzer import LLMSentimentAnalyzer
import os

os.environ["OPENAI_API_KEY"] = "sk-xxx"
analyzer = LLMSentimentAnalyzer()
analysis = analyzer.analyze_batch(result.news, "AAPL")
```

### Agent-based Analysis (No API Key Required)
```python
from valueinvest.news.analyzer.agent_analyzer import (
    AgentSentimentAnalyzer,
    create_agent_analysis_prompt,
    enhance_analysis_with_agent_result,
)

# Create agent analyzer with context
analyzer = AgentSentimentAnalyzer(
    stock_name="伊利股份",
    current_price=26.0,
    company_type="value",
)

# Get initial analysis (uses keyword-based as base)
analysis = analyzer.analyze_batch(news, "600887")

# Create prompt for coding agent (ultrabrain/deep)
prompt = create_agent_analysis_prompt(
    ticker="600887",
    stock_name="伊利股份",
    current_price=26.0,
    company_type="value",
    news=news,
    days=30,
)

# Use task tool with ultrabrain agent
# Then enhance with agent response:
enhanced = enhance_analysis_with_agent_result(analysis, agent_response)
```

### Access Guidance & Analyst Data
```python
if analysis.has_guidance:
    guidance = analysis.latest_guidance
    
    # Company guidance
    if guidance.has_company_guidance:
        print(f"EPS: {guidance.company_eps_low}-{guidance.company_eps_high}")
    
    # Analyst expectations
    if guidance.has_analyst_data:
        print(f"Analyst EPS: {guidance.analyst_eps_mean}")
        print(f"Rating: {guidance.analyst_rating.value}")
        print(f"vs Consensus: {guidance.guidance_vs_consensus}")
```

### Enhanced Reporter
```python
from valueinvest.reports.enhanced_reporter import EnhancedReporter

reporter = EnhancedReporter()
report = reporter.render(
    stock=stock,
    history=history,
    valuation_results=results,
    news_analysis=analysis,
    company_type="value",
)
print(report)
```

## CLI Tool

```bash
# Analyze stock
python stock_analyzer.py 600887           # A-share
python stock_analyzer.py AAPL             # US stock
python stock_analyzer.py 601398 --bank    # Force bank analysis
python stock_analyzer.py 600900 --dividend  # Force dividend analysis
python stock_analyzer.py 600887 --period 3y  # 3-year history

# With news analysis
python stock_analyzer.py 600887 --news    # Include news sentiment (keyword-based)
python stock_analyzer.py AAPL --news --llm  # Use LLM API (requires OPENAI_API_KEY)
python stock_analyzer.py 600887 --news --agent  # Use coding agent (no API key needed)
python stock_analyzer.py 600887 --news --news-days 60  # 60-day news
```

## Data Sources

| Source | Markets | Auth | Install |
|--------|---------|------|---------|
| AKShare | A-shares | Free | `pip install valueinvest[ashare]` |
| yfinance | US/Intl | Free | `pip install valueinvest[us]` |
| Tushare | A-shares | Token | `TUSHARE_TOKEN=xxx pip install valueinvest[tushare]` |

Auto-detection by ticker format:
- 6 digits (600887) → AKShare
- Letters (AAPL) → yfinance

## News Data Sources

| Source | Markets | News | Guidance | Auth |
|--------|---------|------|----------|------|
| AKShare | A-shares | ✅ East Money | ❌ | Free |
| yfinance | US/Intl | ✅ Yahoo Finance | ✅ Analyst data | Free |

## QFQ vs HFQ Price Adjustment

| Type | Use Case | Characteristics |
|------|----------|-----------------|
| QFQ (前复权) | Valuation comparison | Current price unchanged, historical adjusted |
| HFQ (后复权) | Real investment returns | Historical unchanged, dividends compounded |

```python
# QFQ CAGR: price-only growth
# HFQ CAGR: total return including dividends reinvested
print(f"Price CAGR: {history.cagr:.2f}%")
print(f"Real CAGR: {history.cagr_hfq:.2f}%")
```

## Company Type Detection

Automatic classification based on ticker and financials:
- **Utilities list** (600900, etc.) → Dividend
- **Bank list** (601398, etc.) → Bank
- **Dividend yield > 3%** → Dividend
- **HFQ CAGR > 10%** → Growth
- **HFQ CAGR < 5%** → Value

## Extending News Module

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
        # Implement news fetching
        ...
    
    def fetch_guidance(self, ticker):
        return []

# Register fetcher
NewsRegistry.register_fetcher(Market.HK, HKNewsFetcher)

# Register market detector
NewsRegistry.register_detector(
    lambda t: Market.HK if t.isdigit() and len(t) == 5 else None
)
```

## Conventions
- Use dataclasses for data containers
- Type hints on all public APIs
- `ValuationResult.fair_value` is the intrinsic value estimate
- Assessment threshold: ±15% for "Fair", otherwise "Undervalued/Overvalued"
- Separate API calls for fundamentals vs price history
- News sentiment score: -1 (most negative) to +1 (most positive)
- Sentiment labels: positive (>0.3), negative (<-0.3), neutral (between)
