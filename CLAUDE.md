# ValueInvest

Python library for stock valuation using multiple methodologies with real-time data fetching.

## Tech Stack
- Python 3.9+, dataclasses, abc
- AKShare (A股数据), yfinance (美股数据), tushare (可选)

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
├── data/
│   ├── presets.py        # Pre-configured stock data
│   └── fetcher/          # Data fetching module
│       ├── base.py       # BaseFetcher, FetchResult, HistoryResult
│       ├── akshare.py    # A-shares (free, no auth)
│       ├── yfinance.py   # US/International stocks
│       └── tushare.py    # A-shares (requires token)
└── reports/reporter.py   # Format output tables
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

## CLI Tool

```bash
# Analyze stock
python stock_analyzer.py 600887           # A-share
python stock_analyzer.py AAPL             # US stock
python stock_analyzer.py 601398 --bank    # Force bank analysis
python stock_analyzer.py 600900 --dividend  # Force dividend analysis
python stock_analyzer.py 600887 --period 3y  # 3-year history
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

## Conventions
- Use dataclasses for data containers
- Type hints on all public APIs
- `ValuationResult.fair_value` is the intrinsic value estimate
- Assessment threshold: ±15% for "Fair", otherwise "Undervalued/Overvalued"
- Separate API calls for fundamentals vs price history
