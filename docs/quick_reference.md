# ValueInvest Quick Reference

> One-page cheat sheet for the most common patterns. For complete documentation, see README.md or AGENTS.md.

---

## 🚀 3 Most Common Patterns

### Pattern 1: Basic Stock Analysis

```python
from valueinvest import Stock, ValuationEngine

# Fetch data (auto-detects market)
stock = Stock.from_api("AAPL")  # or "600887" for A-share

# Run all valuations
engine = ValuationEngine()
results = engine.run_all(stock)

# View results
for result in results:
    print(f"{result.method}: ${result.fair_value:.2f} ({result.assessment})")
```

**When to use**: Default choice for any stock analysis

---

### Pattern 2: Analysis with News & History

```python
from valueinvest import Stock, ValuationEngine
from valueinvest.news.registry import NewsRegistry
from valueinvest.news.analyzer.keyword_analyzer import KeywordSentimentAnalyzer

ticker = "600887"

# 1. Stock data & valuation
stock = Stock.from_api(ticker)
results = ValuationEngine().run_all(stock)

# 2. Price history
history = Stock.fetch_price_history(ticker, period="5y")
print(f"5-Year CAGR: {history.cagr:.2f}%")

# 3. News sentiment (optional)
news_fetcher = NewsRegistry.get_fetcher(ticker)
news_result = news_fetcher.fetch_all(ticker, days=30)

analyzer = KeywordSentimentAnalyzer()
sentiment = analyzer.analyze_batch(news_result.news, ticker)
print(f"Sentiment: {sentiment.sentiment_label}")
```

**When to use**: When you need context beyond valuation (news, trends, sentiment)

---

### Pattern 3: Full Analysis with All Features

```python
from valueinvest import Stock, ValuationEngine
from valueinvest.news.registry import NewsRegistry
from valueinvest.insider import InsiderRegistry
from valueinvest.buyback import BuybackRegistry

ticker = "AAPL"

# 1. Basic data
stock = Stock.from_api(ticker)
results = ValuationEngine().run_all(stock)

# 2. Price history
history = Stock.fetch_price_history(ticker, period="5y")

# 3. News
news_fetcher = NewsRegistry.get_fetcher(ticker)
news_result = news_fetcher.fetch_all(ticker, days=30)

# 4. Insider trading
insider_fetcher = InsiderRegistry.get_fetcher(ticker)
insider_result = insider_fetcher.fetch_insider_trades(ticker, days=365)

# 5. Buyback
buyback_fetcher = BuybackRegistry.get_fetcher(ticker)
buyback_result = buyback_fetcher.fetch_buyback(ticker, days=365)

# 6. Summary
print(f"Stock: {stock.name}")
print(f"PE Ratio: {stock.pe_ratio:.1f}")
print(f"5Y CAGR: {history.cagr:.2f}%")
print(f"Insider Sentiment: {insider_result.summary.sentiment}")
print(f"Total Shareholder Yield: {buyback_result.summary.total_shareholder_yield:.2f}%")
```

**When to use**: Complete due diligence for investment decisions

---

## 📊 Method Selection Guide

| Company Type | Method | Command | Examples |
|--------------|--------|---------|----------|
| **High Dividend** (>3%) | Dividend | `engine.run_dividend(stock)` | Utilities, REITs |
| **High Growth** (>10%) | Growth | `engine.run_growth(stock)` | Tech, SaaS |
| **Banks/Financial** | Bank | `engine.run_bank(stock)` | Banks, Insurance |
| **Cyclical** | Cyclical | `CyclicalAnalysisEngine()` | Shipping, Mining |
| **Unknown/General** | All | `engine.run_all(stock)` | Default |

---

## 🔧 Quick Commands

### CLI (Command Line)

```bash
# Basic analysis
python scripts/stock_analyzer.py 600887

# With news
python scripts/stock_analyzer.py 600887 --news

# With insider trading
python scripts/stock_analyzer.py AAPL --insider

# With buyback analysis
python scripts/stock_analyzer.py AAPL --buyback

# Full analysis
python scripts/stock_analyzer.py AAPL --news --insider --buyback

# Cyclical stock
python scripts/stock_analyzer.py 601919 --cyclical

# Force specific analysis type
python scripts/stock_analyzer.py 600900 --dividend  # Force dividend analysis
python scripts/stock_analyzer.py MSFT --growth      # Force growth analysis
python scripts/stock_analyzer.py 601398 --bank      # Force bank analysis
```

### Python API

```python
# Import shortcuts
from valueinvest import (
    Stock,                    # Main data container
    ValuationEngine,          # Run valuations
    NewsRegistry,             # News data
    InsiderRegistry,          # Insider trading
    BuybackRegistry,          # Buyback data
    CyclicalAnalysisEngine,   # Cyclical stocks
)

# Single stock
stock = Stock.from_api("AAPL")

# Multiple stocks
stocks = [Stock.from_api(t) for t in ["AAPL", "MSFT", "GOOGL"]]

# Price history
history = Stock.fetch_price_history("AAPL", period="5y")

# Single valuation method
engine = ValuationEngine()
result = engine.run_single(stock, "graham_number")
```

---

## 🎯 Market Detection

The library **auto-detects** market by ticker format:

| Ticker Format | Market | Data Source | Auth |
|---------------|--------|-------------|------|
| 6 digits (`600887`) | A-share (China) | AKShare | Free |
| Letters (`AAPL`) | US/International | yfinance | Free |

**Examples**:
```python
# A-share (China) - Auto-detected
stock = Stock.from_api("600887")  # 伊利股份

# US Stock - Auto-detected
stock = Stock.from_api("AAPL")    # Apple Inc.

# No manual market specification needed!
```

---

## 📈 Valuation Methods

### Most Common Methods

| Method | Best For | Run Command |
|--------|----------|-------------|
| **Graham Number** | Value stocks | `engine.run_single(stock, "graham_number")` |
| **DCF** | Growth stocks | `engine.run_single(stock, "dcf")` |
| **PEG** | Fast-growing | `engine.run_single(stock, "peg")` |
| **DDM** | Dividend stocks | `engine.run_single(stock, "ddm")` |
| **P/B** | Banks | `engine.run_single(stock, "pb_valuation")` |

### Run Multiple Methods

```python
# All methods (20+)
results = engine.run_all(stock)

# Category-specific
results = engine.run_growth(stock)      # Growth methods only
results = engine.run_dividend(stock)    # Dividend methods only
results = engine.run_bank(stock)        # Bank methods only
```

---

## 🆘 Common Errors & Solutions

### Error: "No data for ticker"

**Cause**: Invalid ticker format or not supported

**Solution**:
```python
# Check format
ticker = "AAPL"  # ✅ US stock (letters)
ticker = "600887"  # ✅ A-share (6 digits)
ticker = "AAPL123"  # ❌ Invalid format
```

---

### Error: "Network timeout"

**Cause**: API rate limit or network issue

**Solution**:
```python
import time

tickers = ["AAPL", "MSFT", "GOOGL"]
for ticker in tickers:
    stock = Stock.from_api(ticker)
    time.sleep(0.5)  # Add delay between requests
```

---

### Error: "Missing required field"

**Cause**: API couldn't fetch all data

**Solution**:
```python
stock = Stock.from_api("600887")

# Check for None values
if stock.pe_ratio is None:
    print("PE ratio not available, using alternative method")
    
# Set manual values if needed
stock.growth_rate = 10.0  # Set manually
stock.discount_rate = 9.0
```

---

## 📝 Quick Examples

### Example 1: Screen for Undervalued Stocks

```python
from valueinvest import Stock, ValuationEngine

tickers = ["AAPL", "MSFT", "GOOGL", "AMZN"]
engine = ValuationEngine()

for ticker in tickers:
    stock = Stock.from_api(ticker)
    results = engine.run_all(stock)
    
    # Count undervalued methods
    undervalued_count = sum(1 for r in results if r.assessment == "Undervalued")
    
    if undervalued_count > len(results) / 2:
        avg_fair_value = sum(r.fair_value for r in results) / len(results)
        print(f"{ticker}: ${avg_fair_value:.2f} (Majority undervalued)")
```

---

### Example 2: Track Insider Sentiment

```python
from valueinvest.insider import InsiderRegistry

ticker = "AAPL"
fetcher = InsiderRegistry.get_fetcher(ticker)
result = fetcher.fetch_insider_trades(ticker, days=90)

print(f"Insider Sentiment: {result.summary.sentiment}")
print(f"Buy Count: {result.summary.buy_count}")
print(f"Sell Count: {result.summary.sell_count}")
print(f"Net Shares: {result.summary.net_shares:+,}")
```

---

### Example 3: Analyze Shareholder Returns

```python
from valueinvest.buyback import BuybackRegistry

ticker = "AAPL"
fetcher = BuybackRegistry.get_fetcher(ticker)
result = fetcher.fetch_buyback(ticker, days=365)

summary = result.summary
print(f"Dividend Yield: {summary.dividend_yield:.2f}%")
print(f"Buyback Yield: {summary.buyback_yield:.2f}%")
print(f"Total Shareholder Yield: {summary.total_shareholder_yield:.2f}%")
```

---

## 🔄 Typical Workflows

### Workflow 1: Quick Check (1 minute)
```python
stock = Stock.from_api("AAPL")
results = ValuationEngine().run_all(stock)
# Done!
```

### Workflow 2: Standard Analysis (5 minutes)
```python
stock = Stock.from_api("AAPL")
results = ValuationEngine().run_all(stock)
history = Stock.fetch_price_history("AAPL", period="5y")
news = NewsRegistry.get_fetcher("AAPL").fetch_all("AAPL")
# More comprehensive
```

### Workflow 3: Full Due Diligence (15 minutes)
```python
# All features
stock = Stock.from_api("AAPL")
results = ValuationEngine().run_all(stock)
history = Stock.fetch_price_history("AAPL", period="5y")
news = NewsRegistry.get_fetcher("AAPL").fetch_all("AAPL")
insider = InsiderRegistry.get_fetcher("AAPL").fetch_insider_trades("AAPL")
buyback = BuybackRegistry.get_fetcher("AAPL").fetch_buyback("AAPL")
# Complete picture
```

---

## 📚 More Resources

- **Full Documentation**: `README.md`
- **Agent Guide**: `AGENTS.md`
- **Examples**: `examples/` folder
- **Scripts**: `scripts/` folder
- **Generated Reports**: `reports/` folder

---

**Total Lines: ~350** (Quick reference for common patterns)
