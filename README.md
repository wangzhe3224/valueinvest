# ValueInvest

A modular Python library for comprehensive stock valuation using multiple methodologies with real-time data fetching, financial trend analysis, and news sentiment.

## ✨ Recent Updates

**v1.6.1** (2026-08-20): Fixed PeerComparisonEngine crash — `_get_peer_values` referenced non-existent `Stock.effective_net_margin` when deriving peer net margin; now derives it via `_derive_net_margin()`.

**v1.6.0** (2026-07-30): Added Trend & Growth-Signal Analysis — new `trend` module with multi-year quarterly series (revenue, gross/net margin, fcf yield, CCC) via stockanalysis/FMP/tushare fetchers (registry-pluggable), growth-signal scoring (CAGR, YoY acceleration, inflection, streak, stability) with CCC industry-applicability gating, and trend visualization (matplotlib `plot` extra); new `trend-analysis` skill.

**v1.5.1** (2026-07-25): Fixed YFinanceFetcher fundamentals crash on net-interest-income companies (e.g. GRMN) — invalid pandas API `financials.loc.get(...)` raised `AttributeError` and wiped the entire fetch; now uses guarded `.loc[...]` access with broadened `except` clauses.

**v1.5.0** (2026-06-12): Added Earnings Patch module (`data.patch`) for injecting manually collected quarterly earnings data when API data is delayed.

**v1.4.0** (2026-05-31): Added DuPont ROE Decomposition (3-step & 5-step) and SOTP (Sum-of-the-Parts) Valuation for conglomerates.

**v1.3.0** (2026-04-20): Added Accounting Red Flags Detection — 11 signals across 4 categories.

**v1.2.0** (2026-04-11): Added Peer Comparison Analysis and Implied Growth Rate Analysis.

See [CHANGELOG.md](CHANGELOG.md) for full history.

## Features

**Data & Fetching**
- Real-time data: A-shares (AKShare), US stocks (yfinance), optional Tushare
- QFQ/HFQ price adjustment for valuation comparison and real returns
- Earnings Patch: inject manually collected quarterly data when API lags

**Valuation (20+ methods)**
- Graham (Number, Formula, NCAV), DCF / Reverse DCF, Earnings Power Value
- Dividend (Gordon Growth, Two-Stage DDM), Growth (PEG, GARP, Rule of 40)
- Bank (P/B, Residual Income), SOTP (Sum-of-the-Parts for conglomerates)
- Relative Valuation (PE/PB vs historical & peer averages)

**Quality & Risk**
- Piotroski F-Score, Altman Z-Score, Beneish M-Score (earnings manipulation)
- Accounting Red Flags (11 signals, 4 categories)
- Value Trap detection

**Fundamentals & Trends**
- Economic Moat scoring, ROIC vs WACC (economic profit), Capital Allocation quality
- DuPont ROE decomposition (3-step & 5-step)
- Peer Comparison, Implied Growth Rate (Reverse DCF/PEG/Gordon/Earnings Yield)
- **Trend & Growth-Signal Analysis**: multi-year quarterly series (revenue, margins, fcf yield, CCC) via stockanalysis (US default) / FMP / tushare, with growth-signal scoring and visualization

**Cash Flow & Shareholders**
- Free Cash Flow analysis (quality, SBC impact, True FCF)
- Buyback analysis (shareholder yield)
- Insider trading tracking (A-share & US)

**Context**
- Cyclical stock analysis (cycle position, cyclical-adjusted valuation)
- News & sentiment (keyword / LLM / agent-based), analyst guidance
- Industry analysis, stock screener

## Installation

```bash
# From PyPI
pip install valueinvest                         # Core (no data sources)

# With data sources / extras
pip install "valueinvest[fetch]"                # All data sources
pip install "valueinvest[us]"                   # US stocks (yfinance)
pip install "valueinvest[ashare]"               # A-shares (AKShare, free)
pip install "valueinvest[tushare]"              # A-shares with Tushare (token)
pip install "valueinvest[plot]"                 # Trend chart visualization (matplotlib)
```

For development:

```bash
git clone https://github.com/wangzhe3224/valueinvest.git
cd valueinvest
uv venv --python 3.11
source .venv/bin/activate
pip install -e ".[fetch,plot]"
```

## Quick Start

### Python API

```python
from valueinvest import Stock, ValuationEngine

stock = Stock.from_api("AAPL")          # auto-detects market (A-share or US)
engine = ValuationEngine()
results = engine.run_all(stock)          # all applicable methods
for r in results:
    print(f"{r.method}: fair value {r.fair_value:.2f} ({r.assessment})")

# Category-specific
engine.run_dividend(stock)               # dividend stocks
engine.run_bank(stock)                   # banks
engine.run_growth(stock)                 # growth stocks
```

### Command Line

```bash
python scripts/stock_analyzer.py 600887            # A-share (伊利股份)
python scripts/stock_analyzer.py AAPL               # US stock
python scripts/stock_analyzer.py 601398 --bank      # force bank analysis
python scripts/stock_analyzer.py AAPL --buyback --fcf   # shareholder return
python scripts/stock_analyzer.py 600887 --news      # with news sentiment
```

## Key Modules

### Valuation

```python
engine = ValuationEngine()
engine.run_single(stock, "graham_number")           # single method
engine.run_recommended(stock)                        # recommended for the stock type
engine.analyze_batch(['AAPL', 'MSFT', 'GOOGL'])      # compare multiple
```

### Trend & Growth-Signal Analysis (new)

```python
from valueinvest import fetch_quarterly_trends, analyze_trend_signals

fr = fetch_quarterly_trends("AAPL", years=5)         # ~20 quarters via stockanalysis
result = analyze_trend_signals(fr.series)            # composite rating + signals
print(result.rating.value, result.composite_score)   # e.g. "stable 55.9"
for s in result.signals:
    if s.is_available:
        print(f"  {s.metric.value:11s} {s.name:20s} {s.score:5.1f}")
```

### Free Cash Flow

```python
from valueinvest import CashFlowRegistry
result = CashFlowRegistry.get_fetcher("AAPL").fetch_cashflow("AAPL", years=5)
print(result.summary.fcf_quality.value, result.summary.fcf_yield, result.summary.fcf_trend.value)
```

### Quality Scores

```python
from valueinvest import calculate_f_score, calculate_m_score
fscore = calculate_f_score(stock, prior_roa=..., prior_gross_margin=...)   # Piotroski 0-9
mscore = calculate_m_score(stock, prior_revenue=..., prior_gross_margin=...)  # Beneish
```

### Red Flags, Moat, DuPont, Peers

```python
from valueinvest import AccountingRedFlagsEngine, MoatAnalysisEngine, DuPontAnalysisEngine, PeerComparisonEngine
redflags = AccountingRedFlagsEngine().analyze(stock)     # 11 signals / 4 categories
moat = MoatAnalysisEngine().analyze(stock)
dupont = DuPontAnalysisEngine().analyze(stock)           # 3-step & 5-step ROE
peers = PeerComparisonEngine().analyze(stock)            # vs industry peers
```

### Buyback & Insider

```python
from valueinvest import BuybackRegistry, InsiderRegistry
buyback = BuybackRegistry.get_fetcher("AAPL").fetch_buyback("AAPL", days=365)
insider = InsiderRegistry.get_fetcher("AAPL").fetch_insider_trades("AAPL", days=180)
```

### News & Sentiment

```python
from valueinvest import NewsRegistry
from valueinvest.news.analyzer.keyword_analyzer import KeywordSentimentAnalyzer
news = NewsRegistry.get_fetcher("AAPL").fetch_all("AAPL", days=30)
analysis = KeywordSentimentAnalyzer().analyze_batch(news.news, "AAPL")
print(analysis.sentiment_label, analysis.sentiment_score)   # positive/negative/neutral, -1..1
# LLM analyzer (OpenAI) and agent-based analyzer also available
```

### Cyclical Stocks

```python
from valueinvest import CyclicalAnalysisEngine, CyclicalStock
stock = CyclicalStock(ticker="601919", market=MarketType.A_SHARE, cycle_type=CycleType.SHIPPING, ...)
result = CyclicalAnalysisEngine().analyze(stock)   # cycle phase, rating, strategy
```

## Data Sources

| Source | Markets | Auth | Install |
|--------|---------|------|---------|
| AKShare | A-shares | Free | `pip install valueinvest[ashare]` |
| yfinance | US/Intl | Free | `pip install valueinvest[us]` |
| Tushare | A-shares | Token | `pip install valueinvest[tushare]` |
| stockanalysis.com | US (trend) | Free (scrape) | bundled |
| FMP | US (trend) | API key | optional |

Auto-detection by ticker: 6 digits (600887) → A-share, letters (AAPL) → US.

**Trend data**: US default is stockanalysis.com (free, ~5y quarterly); FMP free is capped at ~5 quarters (paid for full history); A-shares use Tushare. Switch via `TrendRegistry.register_fetcher(...)`.

## Available Valuation Methods

| Method | Best For |
|--------|----------|
| Graham Number / Formula / NCAV | Defensive / deep value |
| DCF / Reverse DCF | Growth companies |
| Earnings Power Value (EPV) | Mature companies |
| DDM / Two-Stage DDM | Dividend stocks |
| PEG / GARP / Rule of 40 | Profitable growth / SaaS |
| P/B / Residual Income | Banks, financials |
| **SOTP** | **Conglomerates (sum-of-the-parts)** |
| PE Relative / PB Relative | Peer & historical comparison |
| Piotroski F-Score / Altman Z-Score | Quality & bankruptcy risk |
| Beneish M-Score | Earnings manipulation |
| Cyclical PB / PE / FCF / Dividend | Cyclical stocks |

## Project Structure

```
valueinvest/
├── stock.py                 # Stock dataclass, StockHistory
├── exceptions.py
├── valuation/               # 20+ valuation methods + engine
│   ├── engine.py  base.py  graham.py  dcf.py  epv.py  ddm.py
│   ├── growth.py  bank.py  relative.py  sotp.py
│   ├── quality.py  mscore.py  value_trap.py  magic_formula.py  sbc.py
├── trend/                   # Quarterly trend & growth-signal analysis (v1.6.0)
│   ├── base.py  engine.py  signals.py  registry.py  plotting.py
│   └── fetcher/             # stockanalysis, fmp, yfinance, tushare
├── moat/                    # Economic moat scoring
├── roic/                    # ROIC vs WACC (economic profit)
├── capital/                 # Capital allocation quality
├── dupont/                  # DuPont ROE decomposition (3 & 5 step)
├── peer_comparison/         # Peer comparison engine
├── implied_growth/          # Market-implied growth rate
├── redflags/                # Accounting red flags (11 signals)
├── screener/                # Stock screener (filters, scorers, strategies)
├── industry/                # Industry analysis
├── cyclical/                # Cyclical stock analysis
│   ├── valuation/  strategy/
├── cashflow/                # Free Cash Flow analysis
├── buyback/                 # Buyback / shareholder yield
├── insider/                 # Insider trading
├── news/                    # News, sentiment, guidance
│   ├── fetcher/  analyzer/  (keyword / llm / agent)
├── data/
│   ├── fetcher/             # akshare, yfinance, tushare, peers
│   ├── patch.py             # Earnings patch
│   ├── freshness.py  presets.py
└── reports/                 # Report formatting & export

scripts/stock_analyzer.py    # CLI entry point
```

## License

MIT License
