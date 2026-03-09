# ValueInvest - Agent Guide

> Quick reference for AI coding agents. Command-first, task-organized, closure-defined.

---

## Build & Test Commands

```bash
# Install
pip install -e ".[fetch]"     # All data sources
pip install -e ".[us]"        # US stocks only
pip install -e ".[ashare]"    # A-shares only (free)

# Test
pytest tests/ -v --tb=short

# Type check
mypy valueinvest/ --strict

# Lint & format
ruff check . --fix && ruff format .

# Full verification
ruff check . && pytest -v && mypy valueinvest/
```

---

## Common Tasks (Copy-Paste Ready)

### Task 1: Analyze Single Stock (30 seconds)

```python
from valueinvest import Stock, ValuationEngine

# Fetch data (auto-detect market: 6 digits = A-share, letters = US)
stock = Stock.from_api("AAPL")

# Run all valuations
engine = ValuationEngine()
results = engine.run_all(stock)

# Print results
for r in results:
    print(f"{r.method}: ${r.fair_value:.2f} ({r.assessment})")
```

### Task 2: Full Analysis with News (2 minutes)

```python
from valueinvest import Stock, ValuationEngine
from valueinvest.news.registry import NewsRegistry
from valueinvest.news.analyzer.keyword_analyzer import KeywordSentimentAnalyzer

ticker = "600887"

# 1. Stock data
stock = Stock.from_api(ticker)
results = ValuationEngine().run_all(stock)

# 2. Price history
history = Stock.fetch_price_history(ticker, period="5y")
print(f"5Y CAGR: {history.cagr:.2f}%")

# 3. News (optional)
news_fetcher = NewsRegistry.get_fetcher(ticker)
news_result = news_fetcher.fetch_all(ticker, days=30)

# 4. Sentiment analysis
analyzer = KeywordSentimentAnalyzer()
sentiment = analyzer.analyze_batch(news_result.news, ticker)
print(f"Sentiment: {sentiment.sentiment_label} ({sentiment.sentiment_score:+.2f})")
```

### Task 3: Compare Multiple Stocks (5 minutes)

```python
from valueinvest import Stock, ValuationEngine

tickers = ["AAPL", "MSFT", "GOOGL"]
stocks = [Stock.from_api(t) for t in tickers]

engine = ValuationEngine()

for stock in stocks:
    results = engine.run_all(stock)
    avg_fair_value = sum(r.fair_value for r in results) / len(results)
    premium = (stock.current_price / avg_fair_value - 1) * 100
    
    print(f"{stock.ticker}: PE={stock.pe_ratio:.1f}, "
          f"Fair Value=${avg_fair_value:.2f}, "
          f"Premium={premium:+.1f}%")
```

### Task 4: Insider Trading + Buyback Analysis

```python
from valueinvest.insider import InsiderRegistry
from valueinvest.buyback import BuybackRegistry

ticker = "AAPL"

# Insider trading
insider = InsiderRegistry.get_fetcher(ticker)
insider_result = insider.fetch_insider_trades(ticker, days=365)
print(f"Insider Sentiment: {insider_result.summary.sentiment}")
print(f"Net Shares: {insider_result.summary.net_shares:+,}")

# Buyback
buyback = BuybackRegistry.get_fetcher(ticker)
buyback_result = buyback.fetch_buyback(ticker, days=365)
print(f"Total Shareholder Yield: {buyback_result.summary.total_shareholder_yield:.2f}%")
```

### Task 5: Cyclical Stock Analysis

```python
from valueinvest.cyclical import (
    CyclicalAnalysisEngine,
    CyclicalStock,
    CycleType,
    MarketType,
)

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
    fcf_yield=0.079,
    dividend_yield=0.05,
    debt_ratio=0.35,
    roe=0.12,
    historical_pb=[1.5, 2.0, 1.8, 2.5, 1.2],
)

engine = CyclicalAnalysisEngine()
result = engine.analyze(stock)

print(f"Cycle Phase: {result.cycle_analysis.phase_display}")
print(f"Investment Rating: {result.investment_rating}")
print(f"Target Price: ¥{result.strategy_recommendation.target_price:.2f}")
```

---

## API Quick Reference

### Core Classes
- `Stock` - Main data container with 50+ fields
- `ValuationEngine` - Run valuations (20+ methods)
- `StockHistory` - Price data with QFQ/HFQ adjustment

### Registries (Auto-detect Market)
- `NewsRegistry.get_fetcher(ticker)` - News & guidance
- `InsiderRegistry.get_fetcher(ticker)` - Insider trading
- `BuybackRegistry.get_fetcher(ticker)` - Buyback data
- `CashFlowRegistry.get_fetcher(ticker)` - FCF analysis

### Most Used Methods
```python
# Data fetching
stock = Stock.from_api(ticker)
history = Stock.fetch_price_history(ticker, period="5y")

# Valuation
engine = ValuationEngine()
engine.run_all(stock)          # All methods
engine.run_growth(stock)       # Growth stocks
engine.run_dividend(stock)     # Dividend stocks
engine.run_bank(stock)         # Banks
engine.run_single(stock, "graham_number")  # Single method

# Convenience functions
from valueinvest.valuation.quality import calculate_f_score
from valueinvest.valuation.mscore import calculate_m_score

f_score = calculate_f_score(stock, prior_roa=0.28, ...)
m_score = calculate_m_score(stock, prior_revenue=380e9, ...)
```

---

## Method Selection Guide

| Company Type | Method | When to Use | Examples |
|--------------|--------|-------------|----------|
| 高分红 (>3%) | `run_dividend()` | Stable dividends, utilities | 600900, utilities |
| 高增长 (>10%) | `run_growth()` | Fast-growing companies | Tech, SaaS |
| 银行/金融 | `run_bank()` | Financial institutions | 601398, banks |
| 周期股 | Cyclical Engine | Shipping, commodities, energy | 601919, cyclicals |
| 通用 | `run_all()` | Default for unknown types | All stocks |

---

## Market Detection Logic

```python
# Auto-detection by ticker format
if ticker.isdigit() and len(ticker) == 6:
    # A-share → AKShare (free)
    market = "A_SHARE"
elif ticker.isalpha():
    # US/Intl → yfinance (free)
    market = "US"
```

---

## Definition of Done

A task is complete when **ALL** conditions pass:

1. ✅ `ruff check .` exits 0
2. ✅ `pytest tests/` exits 0
3. ✅ `mypy valueinvest/` exits 0
4. ✅ New functions have docstrings with examples
5. ✅ Breaking changes update CHANGELOG.md
6. ✅ Examples added to `examples/` folder
7. ✅ Code placed in correct location:
   - `valueinvest/` - Core library
   - `scripts/` - Analysis scripts
   - `examples/` - User examples

---

## When Blocked

### Missing Data
- Use `yfinance` API directly
- Search web for recent financials
- Add manual fields: `stock.growth_rate = 10.0`

### API Errors
- Add retry with exponential backoff
- Check rate limits (yfinance: ~2000 requests/hour)
- Use cached data if available

### Type Errors
- Add Pydantic validators
- Use `| None` for optional fields
- **NEVER** use `Any`, `@ts-ignore`, `@ts-expect-error`

### Test Failures
- Read error message carefully
- Fix root cause, not symptom
- Run single test: `pytest tests/test_file.py::test_name -v`

### **NEVER DO**
- ❌ Skip tests to "pass"
- ❌ Delete failing test files
- ❌ Use `# type: ignore` comments
- ❌ Force push to main/master
- ❌ Commit without explicit request

---

## Project Structure

```
valueinvest/
├── stock.py                 # Core data models
├── valuation/               # Valuation methods (20+)
│   ├── engine.py           # Unified engine
│   ├── graham.py           # Graham methods
│   ├── dcf.py              # DCF models
│   ├── ddm.py              # Dividend models
│   ├── growth.py           # PEG, GARP, etc.
│   ├── bank.py             # Bank valuation
│   ├── quality.py          # F-Score, Z-Score
│   └── mscore.py           # M-Score (fraud detection)
├── news/                    # News & sentiment
├── insider/                 # Insider trading
├── buyback/                 # Buyback analysis
├── cashflow/                # FCF analysis
├── cyclical/                # Cyclical stocks
├── data/                    # Data fetching
│   ├── fetcher/            # AKShare, yfinance, Tushare
│   └── freshness.py        # Data validation
└── reports/                 # Report generation

scripts/                     # Analysis scripts
examples/                    # User examples
reports/                     # Generated reports
```

---

## Error Handling Examples

```python
# Handle missing data
try:
    stock = Stock.from_api("INVALID")
except Exception as e:
    print(f"Failed to fetch: {e}")
    # Try alternative data source or web search

# Handle None values
if stock.pe_ratio is None:
    print("PE ratio not available")
    # Use alternative valuation method

# Handle rate limits
import time
for ticker in tickers:
    stock = Stock.from_api(ticker)
    time.sleep(0.5)  # Avoid rate limits
```

---

## Common Patterns

### Pattern 1: Try Multiple Valuation Methods
```python
results = engine.run_all(stock)
undervalued = [r for r in results if r.assessment == "Undervalued"]
if len(undervalued) > len(results) / 2:
    print("Majority of methods suggest undervalued")
```

### Pattern 2: Validate Data Freshness
```python
from datetime import datetime, timedelta

if stock.data_date < datetime.now() - timedelta(days=7):
    print("Warning: Data is >7 days old")
```

### Pattern 3: Progressive Enhancement
```python
# Start with basic analysis
stock = Stock.from_api(ticker)
results = engine.run_all(stock)

# Add news if needed
if "negative" in [r.assessment for r in results]:
    news = NewsRegistry.get_fetcher(ticker).fetch_all(ticker)
    # Analyze news for red flags
```

---

## Data Sources

| Source | Markets | Auth | Install |
|--------|---------|------|---------|
| AKShare | A-shares | Free | `pip install valueinvest[ashare]` |
| yfinance | US/Intl | Free | `pip install valueinvest[us]` |
| Tushare | A-shares | Token | `TUSHARE_TOKEN=xxx pip install valueinvest[tushare]` |

---

## Tips for Agents

1. **Always validate ticker format** before API calls
2. **Use registries** for market-specific features (news, insider, buyback)
3. **Handle None values** - not all stocks have all data
4. **Check data freshness** - financials may be outdated
5. **Combine multiple methods** - single valuation is unreliable
6. **Start simple** - use `run_all()` first, then refine
7. **Read existing examples** in `examples/` folder
8. **Check CLAUDE.md** for coding rules

---

## Examples Location

- Basic analysis: `examples/demo_mock.py`
- Cyclical stocks: `examples/cyclical_example.py`
- Screening: `examples/demo_screening.py`
- Full scripts: `scripts/stock_analyzer.py`

---

**Total Lines: ~140** (under 150 for context window efficiency)
