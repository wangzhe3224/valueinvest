# ValueInvest

A modular Python library for comprehensive stock valuation using multiple methodologies with real-time data fetching.

## Features

- **Real-time Data Fetching**: A-shares (AKShare), US stocks (yfinance), optional Tushare
- **Graham Valuation**: Graham Number, Graham Formula, NCAV (Net-Net)
- **Discounted Cash Flow**: DCF (10-year projection), Reverse DCF
- **Earnings Power Value**: Zero-growth intrinsic value
- **Dividend Models**: Gordon Growth, Two-Stage DDM
- **Growth Valuation**: PEG Ratio, GARP, Rule of 40
- **Bank Valuation**: P/B Valuation, Residual Income Model
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
├── data/
│   ├── presets.py           # Pre-configured stocks
│   └── fetcher/             # Data fetching
│       ├── base.py          # Base classes
│       ├── akshare.py       # A-shares (free)
│       ├── yfinance.py      # US/Intl stocks
│       └── tushare.py       # A-shares (token)
└── reports/
    └── reporter.py          # Report formatting

stock_analyzer.py            # CLI entry point
```

## Example Output

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

【历史表现 (5y)】
  股价CAGR (qfq): -8.24%
  真实回报 (hfq): -6.40%
  年化波动率: 27.98%
  最大回撤: -53.74%

【近30日价格 (QFQ前复权)】
  最高: ¥28.62
  最低: ¥26.14
  均价: ¥27.09
  最新: ¥26.48
  涨跌幅: -7.44%

【真实投资回报 (HFQ后复权)】
  含分红再投资CAGR: -6.40%

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
【最终结论】
======================================================================

估值区间: ¥18-21 (保守) / ¥26 (现价) / ¥40+ (乐观)

【综合评级】: 合理偏高

投资建议:
  1. 已持有者: 继续持有
  2. 潜在买入: 等待回调至¥22以下
  3. 目标价位: ¥22 (提供15%安全边际)
  4. 止损位: ¥18
```

## License

MIT License
