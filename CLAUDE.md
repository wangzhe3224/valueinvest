# ValueInvest

Python 股票估值库：多方法估值 + 实时数据 + 新闻情感分析 + 内幕交易

## Setup

```bash
uv venv --python 3.11 && source .venv/bin/activate
uv pip install --python .venv/bin/python -e ".[fetch]"  # 全部数据源
uv pip install --python .venv/bin/python -e ".[ashare]" # 仅A股
uv pip install --python .venv/bin/python -e ".[us]"     # 仅美股
```

## Architecture

```
valueinvest/
├── stock.py                    # Stock dataclass, StockHistory, from_api()
├── valuation/
│   ├── base.py                 # BaseValuation (ABC), ValuationResult
│   ├── engine.py               # ValuationEngine
│   ├── graham.py, dcf.py, epv.py, ddm.py, growth.py, bank.py, magic_formula.py
│   ├── quality.py              # OwnerEarnings, AltmanZScore
│   ├── value_trap.py           # ValueTrapDetector, detect_value_trap()
├── news/
│   ├── base.py, registry.py    # NewsItem, Guidance, NewsAnalysisResult
│   ├── fetcher/                # akshare_news.py, yfinance_news.py
│   └── analyzer/               # keyword_analyzer.py, llm_analyzer.py, agent_analyzer.py
├── insider/
│   ├── base.py, registry.py
│   └── fetcher/                # akshare_insider.py, yfinance_insider.py
├── data/fetcher/               # akshare.py, yfinance.py, tushare.py
└── reports/                    # reporter.py, enhanced_reporter.py
```

## Key APIs

```python
from valueinvest import Stock, ValuationEngine
from valueinvest.news.registry import NewsRegistry
from valueinvest.news.analyzer.keyword_analyzer import KeywordSentimentAnalyzer
from valueinvest.insider import InsiderRegistry

# 获取股票数据
stock = Stock.from_api("600887")  # A股 (6位数字)
stock = Stock.from_api("AAPL")    # 美股 (字母)
history = Stock.fetch_price_history("600887", period="5y")

# 运行估值
engine = ValuationEngine()
results = engine.run_all(stock)
results = engine.run_dividend(stock)  # 分红股
results = engine.run_bank(stock)      # 银行
results = engine.run_growth(stock)    # 成长股

# 价值陷阱检测
from valueinvest.valuation import ValueTrapDetector, detect_value_trap
detector = ValueTrapDetector(
    revenue_cagr_5y=-3.0,  # 5年收入CAGR
    margin_trend="compressing",  # 毛利率趋势
    industry="education",  # 行业 (AI风险评估)
)
trap_result = detector.detect(stock)
# trap_result.is_trap: True/False
# trap_result.trap_score: 0-100
# trap_result.overall_risk: LOW/MODERATE/HIGH/CRITICAL

# 快捷函数
result = detect_value_trap(stock, revenue_cagr_5y=5.0, industry="utilities")

# 新闻情感分析
fetcher = NewsRegistry.get_fetcher("600887")
news_result = fetcher.fetch_all("600887", days=30)
analyzer = KeywordSentimentAnalyzer()
analysis = analyzer.analyze_batch(news_result.news, "600887")
# analysis.sentiment_score: -1 到 +1

# 内幕交易
insider_fetcher = InsiderRegistry.get_fetcher("600887")
insider_result = insider_fetcher.fetch_insider_trades("600887", days=365)
# result.summary.sentiment: bullish/bearish/neutral
```

## CLI

```bash
python stock_analyzer.py 600887                    # A股分析
python stock_analyzer.py AAPL                      # 美股分析
python stock_analyzer.py 601398 --bank             # 强制银行分析
python stock_analyzer.py 600900 --dividend         # 强制分红分析
python stock_analyzer.py 600887 --period 3y        # 3年历史
python stock_analyzer.py 600887 --news             # 新闻情感
python stock_analyzer.py AAPL --news --llm         # LLM情感分析
python stock_analyzer.py 600887 --insider          # 内幕交易
```

## Data Sources

| Source | Markets | Auth | Ticker Format |
|--------|---------|------|---------------|
| AKShare | A-shares | Free | 6 digits (600887) |
| yfinance | US/Intl | Free | Letters (AAPL) |
| Tushare | A-shares | Token | 6 digits |

## QFQ vs HFQ

| Type | Use Case |
|------|----------|
| QFQ (前复权) | 估值比较，history.cagr |
| HFQ (后复权) | 真实收益，history.cagr_hfq |

## Company Type Detection

- Utilities (600900等) → Dividend
- Banks (601398等) → Bank
- 股息率 > 3% → Dividend
- HFQ CAGR > 10% → Growth
- HFQ CAGR < 5% → Value

## Value Trap Detection

价值陷阱检测维度：
- **Financial Health**: Altman Z-Score 破产预警
- **Business Deterioration**: 收入/毛利/ROE趋势
- **Moat Erosion**: 护城河侵蚀
- **AI Vulnerability**: AI颠覆风险 (教育/SaaS高危)
- **Dividend Signal**: 分红可持续性

```python
# 使用示例
detector = ValueTrapDetector(
    revenue_cagr_5y=-5.0,      # 收入下滑
    margin_trend="compressing", # 毛利压缩
    roe_trend="declining",      # ROE下降
    industry="education",       # AI高危行业
)
result = detector.detect(stock)

if result.is_trap:
    print(f"警告: {stock.ticker} 可能是价值陷阱!")
    for issue in result.critical_issues:
        print(f"  - {issue}")
```

AI高危行业列表 (见 `AI_VULNERABLE_INDUSTRIES`): education, edtech, saas, customer_service 等

## Conventions

- dataclasses 作为数据容器
- 所有公共 API 有类型提示
- `ValuationResult.fair_value` = 内在价值
- ±15% 为 "Fair"，否则 "Undervalued/Overvalued"
- 情感分数: -1 (最负面) 到 +1 (最正面)
- 情感标签: positive (>0.3), negative (<-0.3), neutral (中间)

## Adding New Valuation Method

1. 继承 `BaseValuation`，实现 `calculate(stock) -> ValuationResult`
2. 注册到 `ValuationEngine._methods` dict

## Adding New Market (News/Insider)

```python
from valueinvest.news.base import Market
from valueinvest.news.fetcher.base import BaseNewsFetcher
from valueinvest.news.registry import NewsRegistry

class HKNewsFetcher(BaseNewsFetcher):
    market = Market.HK
    # 实现 fetch_news(), fetch_guidance()

NewsRegistry.register_fetcher(Market.HK, HKNewsFetcher)
NewsRegistry.register_detector(lambda t: Market.HK if t.isdigit() and len(t) == 5 else None)
```
