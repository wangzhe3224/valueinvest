# ValueInvest Agent 使用指南

本文档为 AI Agent 提供库的快速参考和常用模式。

---

## 1. 快速开始

### 模式一：单只股票快速估值

```python
from valueinvest import Stock, ValuationEngine

stock = Stock.from_api("AAPL")
engine = ValuationEngine()
results = engine.run_recommended(stock)

for r in results:
    if r.is_reliable:
        print(r.to_summary())
```

### 模式二：完整分析（含推荐 + 汇总）

```python
from valueinvest import Stock, ValuationEngine

stock = Stock.from_api("600519")
engine = ValuationEngine()

# 查看推荐的方法列表
recs = engine.get_recommended_methods(stock)
print("主要方法:", recs["primary"])
print("次要方法:", recs["secondary"])

# 运行推荐方法
results = engine.run_recommended(stock)

# 获取汇总统计
summary = engine.summary(results)
print(f"中位数公允价值: ${summary['median_value']:.2f}")
print(f"可靠结果数: {summary['reliable_count']}/{summary['total_methods']}")
print(f"低估: {summary['undervalued_count']}, 高估: {summary['overvalued_count']}")
```

### 模式三：批量筛选

```python
from valueinvest import Stock, ValuationEngine

tickers = ["AAPL", "MSFT", "GOOG", "AMZN"]
engine = ValuationEngine()

for ticker in tickers:
    stock = Stock.from_api(ticker)
    results = engine.run_recommended(stock)
    summary = engine.summary(results)
    if summary["reliable_count"] > 0:
        median = summary["median_value"]
        price = stock.current_price
        discount = (median - price) / price * 100
        print(f"{ticker}: 中位价 ${median:.2f} | 现价 ${price:.2f} | 折价 {discount:+.1f}%")
```

---

## 2. 关键决策点

### run_recommended() vs run_all()

**优先使用 `run_recommended()`**。它会根据股票特征自动选择最合适的方法：

- 银行股 -> PB、剩余收益、DDM
- 高股息股 -> DDM、Graham、EPV
- 成长股 -> DCF、PEG、GARP
- 价值股 -> Graham、NCAV、EPV
- 其他 -> Graham公式、EPV

`run_all()` 运行所有 20+ 种方法，会产生大量不适用的结果，仅在全量分析时使用。

### 按公司类型选择预设方法

```python
engine = ValuationEngine()

# 银行股
results = engine.run_bank(stock)          # pb, residual_income, ddm, altman_z

# 高股息股
results = engine.run_dividend(stock)      # ddm, two_stage_ddm, graham_number, epv, owner_earnings

# 成长股
results = engine.run_growth(stock)        # dcf, reverse_dcf, peg, garp, rule_of_40, magic_formula

# 价值股
results = engine.run_value(stock)         # graham_number, ncav, epv, altman_z, value_trap, piotroski_f

# 周期股
results = engine.run_cyclical(stock)      # cyclical_pb, cyclical_pe, cyclical_fcf, cyclical_dividend
```

### 自定义参数使用 run_single()

当需要调整估值假设时使用：

```python
# 自定义 DCF 参数
result = engine.run_single(stock, "dcf",
    growth_1_5=12.0,      # 1-5年增长率
    growth_6_10=5.0,      # 6-10年增长率
    terminal_growth=3.0,  # 永续增长率
    discount_rate=9.0,    # 折现率
)

# 自定义两阶段 DDM
result = engine.run_single(stock, "two_stage_ddm",
    growth_stage1=8.0,    # 第一阶段增长率
    stage1_years=5,       # 第一阶段年数
    growth_stage2=3.0,    # 第二阶段增长率
    required_return=10.0, # 要求回报率
)

# 自定义 EPV
result = engine.run_single(stock, "epv",
    maintenance_capex_pct=0.6,
    cost_of_capital=9.0,
)
```

---

## 3. 数据质量检查

**使用估值结果前，务必检查数据质量。**

### is_reliable — 第一道防线

```python
for r in results:
    if not r.is_reliable:
        continue  # 跳过不可靠的结果
    print(f"{r.method}: ${r.fair_value:.2f}")
```

`is_reliable` 在 `missing_fields` 为空且 `fair_value > 0` 时返回 True。

### missing_fields — 了解缺失了什么

```python
for r in results:
    if r.missing_fields:
        print(f"{r.method} 缺失: {', '.join(r.missing_fields)}")
```

### applicability — 判断方法是否适用

```python
# applicability 取值: "Applicable", "Limited", "Not Applicable"
for r in results:
    if r.applicability == "Not Applicable":
        continue
    if r.applicability == "Limited":
        print(f"注意: {r.method} 适用性有限")
```

### confidence — 置信度

```python
# confidence 取值: "High", "Medium", "Low", "N/A"
reliable = [r for r in results if r.is_reliable and r.confidence in ("High", "Medium")]
```

### ValuationResult 关键字段速查

| 字段 | 类型 | 说明 |
|------|------|------|
| `method` | str | 估值方法名 |
| `fair_value` | float | 计算出的公允价值 |
| `current_price` | float | 当前股价 |
| `premium_discount` | float | 溢价/折价百分比（正=低估） |
| `assessment` | str | 评估结论（Undervalued/Overvalued/Fair） |
| `confidence` | str | 置信度（High/Medium/Low/N/A） |
| `applicability` | str | 适用性（Applicable/Limited/Not Applicable） |
| `missing_fields` | list[str] | 缺失的关键字段 |
| `is_reliable` | bool | 是否可靠（无缺失且 fair_value > 0） |
| `fair_value_range` | ValuationRange | 敏感性分析区间（low/base/high） |
| `details` | dict | 估值计算详情 |
| `analysis` | list[str] | 分析要点列表 |
| `margin_of_safety` | float | 安全边际百分比 |

---

## 4. 常见陷阱

### from_api() 数据新鲜度警告

`from_api()` 会自动检查价格和基本面数据的新鲜度，过期时将警告存入 `stock.warnings` 列表：

```python
from valueinvest import Stock

stock = Stock.from_api("AAPL")
if stock.warnings:
    print(f"数据警告: {'; '.join(stock.warnings)}")
```

### Stock.to_dict() 基本模式只返回核心字段

`to_dict()` 默认返回 13 个核心字段。使用 `to_dict(full=True)` 获取完整数据，或直接访问属性：

```python
# 完整数据
data = stock.to_dict(full=True)

# 或直接访问
stock.growth_rate        # 增长率
stock.dividend_yield     # 股息率
stock.ebitda             # EBITDA
stock.warnings           # 数据警告列表
stock.extra              # 额外数据字典
```

### 部分方法对不适用的股票返回 fair_value=0

例如对没有股息的股票调用 DDM，或对银行股调用 DCF。**先检查 `applicability`**：

```python
for r in results:
    if r.applicability == "Not Applicable":
        print(f"{r.method} 不适用于此股票，跳过")
        continue
    if r.fair_value == 0:
        print(f"{r.method} 无法计算公允价值")
```

### DCF 和增长方法需要正 FCF / growth_rate

```python
if stock.fcf <= 0:
    print("警告: FCF 非正，DCF 方法结果不可靠")
if not stock.growth_rate or stock.growth_rate <= 0:
    print("警告: 缺少增长率，PEG/GARP 方法结果不可靠")
```

---

## 5. 扩展模块

### 新闻分析

```python
from valueinvest.news.registry import NewsRegistry

fetcher = NewsRegistry.get_fetcher("AAPL")
result = fetcher.fetch_all("AAPL", days=30)

for news in result.news:
    print(f"[{news.sentiment.value}] {news.title}")

for guidance in result.guidance:
    print(f"指引: {guidance.content}")
```

### 内部人交易

```python
from valueinvest.insider.registry import InsiderRegistry

fetcher = InsiderRegistry.get_fetcher("AAPL")
result = fetcher.fetch_insider_trades("AAPL", days=90)

for trade in result.trades:
    print(f"{trade.insider_name}: {trade.transaction_type} {trade.shares}股")

if result.summary:
    print(f"总买入: {result.summary.total_buy}, 总卖出: {result.summary.total_sell}")
```

### 回购分析

```python
from valueinvest.buyback.registry import BuybackRegistry

fetcher = BuybackRegistry.get_fetcher("AAPL")
result = fetcher.fetch_buyback("AAPL", days=365)

if result.summary:
    print(f"回购金额: {result.summary.total_amount}")
    print(f"回购股数: {result.summary.total_shares}")
```

### 现金流分析

```python
from valueinvest.cashflow.registry import CashFlowRegistry

fetcher = CashFlowRegistry.get_fetcher("AAPL")
result = fetcher.fetch_cashflow("AAPL", years=5)

for record in result.records:
    print(f"{record.year}: 经营={record.operating_cf}, 自由={record.free_cf}")
```

### 周期股分析

```python
from valueinvest.cyclical.engine import CyclicalAnalysisEngine
from valueinvest.cyclical.base import CyclicalStock
from valueinvest.cyclical.enums import CycleType, MarketType

engine = CyclicalAnalysisEngine()
stock = CyclicalStock(
    ticker="601919",
    name="中远海控",
    market=MarketType.A_SHARE,
    current_price=15.79,
    cycle_type=CycleType.SHIPPING,
    pb=1.09,
    bvps=14.5,
)

result = engine.analyze(stock)
print(f"周期阶段: {result.cycle_analysis.phase_display}")
print(f"操作建议: {result.strategy_recommendation.action_display}")
```

### 便捷函数

```python
from valueinvest import calculate_f_score, calculate_m_score

# Piotroski F-Score (0-9，越高越好)
f_score = calculate_f_score(stock)
print(f"F-Score: {f_score.score}/9")

# Beneish M-Score (> -1.78 可能有财务造假)
m_score = calculate_m_score(stock)
print(f"M-Score: {m_score.score:.2f}")
```

---

## 6. 市场自动检测

所有 Registry 自动根据 ticker 检测市场：
- 纯数字（如 `600519`）-> A 股
- 字母（如 `AAPL`）-> 美股
- 支持 A 股和美股

```python
from valueinvest.news.registry import NewsRegistry

market = NewsRegistry.detect_market("600519")  # Market.A_SHARE
market = NewsRegistry.detect_market("AAPL")     # Market.US

print(f"支持的市场: {NewsRegistry.get_supported_markets()}")
```

---

## 7. 估值方法完整列表

| 方法名 | 方法类 | 说明 |
|--------|--------|------|
| `graham_number` | GrahamNumber | Graham 数值（EPS * BVPS 的开方） |
| `graham_formula` | GrahamFormula | Graham 增长公式 |
| `ncav` | NCAV | 净流动资产价值法 |
| `dcf` | DCF | 折现现金流 |
| `reverse_dcf` | ReverseDCF | 反向 DCF（推算隐含增长率） |
| `epv` | EPV | 盈利能力价值法 |
| `ddm` | DDM | 股息折现模型 |
| `two_stage_ddm` | TwoStageDDM | 两阶段 DDM |
| `peg` | PEG | PEG 估值 |
| `garp` | GARP | 合理价格成长 |
| `rule_of_40` | RuleOf40 | 40 法则 |
| `magic_formula` | MagicFormula | 神奇公式 |
| `owner_earnings` | OwnerEarnings | 巴菲特所有者收益 |
| `ev_ebitda` | EVEBITDA | EV/EBITDA 估值 |
| `pb` | PBValuation | PB 估值（适用于银行） |
| `residual_income` | ResidualIncome | 剩余收益模型（适用于银行） |
| `altman_z` | AltmanZScore | Altman Z 破产风险 |
| `value_trap` | ValueTrapDetector | 价值陷阱检测 |
| `sbc_analysis` | SBCAnalysis | 股权激励分析 |
| `piotroski_f` | PiotroskiFScore | Piotroski F-Score |
| `pe_relative` | PERelativeValuation | 相对 PE 估值 |
| `pb_relative` | PBRelativeValuation | 相对 PB 估值 |
| `beneish_m` | BeneishMScore | Beneish M-Score 造假检测 |
| `cyclical_pb` | CyclicalPBValuation | 周期 PB |
| `cyclical_pe` | CyclicalPEValuation | 周期 PE |
| `cyclical_fcf` | CyclicalFCFValuation | 周期 FCF |
| `cyclical_dividend` | CyclicalDividendValuation | 周期股息 |

---

## 8. 经济分析模块

### ROIC vs WACC — 经济利润分析

判断公司是否在创造或毁灭经济价值。ROIC > WACC = 创造价值。

```python
from valueinvest.roic import analyze_economic_profit

ep = analyze_economic_profit(stock)
print(ep.to_summary())
# EP(AAPL): ROIC=25.3% | WACC=9.5% | Spread=+15.8pp | VALUE CREATED

# 提供 beta 获取更精确的 WACC（CAPM 方法）
ep = analyze_economic_profit(stock, beta=1.2)
```

关键输出字段：
- `roic_result.roic` — ROIC 百分比
- `wacc_result.wacc` — WACC 百分比
- `roic_wacc_spread` — 利差（正=创造价值）
- `economic_profit` — 经济利润绝对值
- `value_created` — 是否创造价值

### 经济护城河评分

系统评估竞争优势强度，基于 11 个财务信号和 5 个维度。

```python
from valueinvest.moat import analyze_moat

moat = analyze_moat(stock)
print(moat.to_summary())
# Moat(AAPL): Score=72/100 | Type=WIDE | Signals=10/11

# 组合使用：传入预计算的 ROIC/WACC 提高准确性
ep = analyze_economic_profit(stock)
moat = analyze_moat(stock, roic=ep.roic_result.roic, wacc=ep.wacc_result.wacc)
```

护城河类型（`moat_type`）：
- `VERY_WIDE` (≥75) — 极强护城河
- `WIDE` (≥55) — 强护城河
- `NARROW` (≥35) — 窄护城河
- `NONE` (<35) — 无明显护城河

5 个评分维度：盈利能力(30%)、效率(20%)、增长(20%)、市场地位(15%)、财务堡垒(15%)

### 资本配置质量评分

评估管理层资本配置效率：分红、回购、再投资、资产负债表管理。

```python
from valueinvest.capital import analyze_capital_allocation

cap = analyze_capital_allocation(stock)
print(cap.to_summary())
# CapitalAlloc(AAPL): Score=68/100 | Rating=GOOD | ShareholderYield=4.5%

# 组合使用：传入 ROIC 提高再投资效率评估
ep = analyze_economic_profit(stock)
cap = analyze_capital_allocation(stock, roic=ep.roic_result.roic)
```

评级（`rating`）：
- `EXCELLENT` (≥80) — 卓越的资本配置
- `GOOD` (≥60) — 股东友好
- `ADEQUATE` (≥40) — 中规中矩
- `POOR` (≥25) — 令人担忧
- `DESTRUCTIVE` (<25) — 破坏价值

4 个评分维度：股东回报(35%)、再投资(25%)、资产负债表(20%)、稀释(20%)

### 三模块组合使用

```python
from valueinvest import Stock
from valueinvest.roic import analyze_economic_profit
from valueinvest.moat import analyze_moat
from valueinvest.capital import analyze_capital_allocation

stock = Stock.from_api("AAPL")

# 1. 先算经济利润（其他模块可以引用）
ep = analyze_economic_profit(stock)

# 2. 护城河分析（传入 ROIC/WACC 提高准确性）
moat = analyze_moat(stock, roic=ep.roic_result.roic, wacc=ep.wacc_result.wacc)

# 3. 资本配置分析（传入 ROIC 提高再投资评估）
cap = analyze_capital_allocation(stock, roic=ep.roic_result.roic)

# 综合判断
print(f"护城河: {moat.moat_type.value} ({moat.moat_score:.0f}/100)")
print(f"经济价值: {'创造' if ep.value_created else '毁灭'} (利差 {ep.roic_wacc_spread:+.1f}pp)")
print(f"资本配置: {cap.rating.value} ({cap.overall_score:.0f}/100)")
```

### 同行对比分析

将股票核心财务指标与同行业公司进行横向对比，评估相对估值、盈利能力和成长性。

```python
from valueinvest.peer_comparison import PeerComparisonEngine

engine = PeerComparisonEngine()
result = engine.analyze(stock)

print(result.to_summary())
# PeerComparison(600519): Score=55/100 | Rating=ABOVE_AVERAGE | Peers=15 | Industry=白酒

# 查看各指标百分位
for mc in result.metric_comparisons:
    if mc.is_available:
        print(f"  {mc.metric_name}: P{mc.percentile:.0f} ({mc.assessment})")

# 分类评分
print(f"估值评分: {result.valuation_score:.0f}")
print(f"盈利评分: {result.profitability_score:.0f}")
print(f"增长评分: {result.growth_score:.0f}")
```

美股无自动同行数据，需手动传入：

```python
from valueinvest.industry.base import PeerCompany
from valueinvest.peer_comparison import PeerComparisonEngine

peers = [
    PeerCompany(ticker="MSFT", name="Microsoft", market_cap=2800e9,
                pe_ratio=35, pb_ratio=12, roe=40, revenue=211e9, net_income=72e9),
    PeerCompany(ticker="GOOGL", name="Alphabet", market_cap=1700e9,
                pe_ratio=25, pb_ratio=6, roe=25, revenue=307e9, net_income=60e9),
]
engine = PeerComparisonEngine(peers=peers)
result = engine.analyze(stock)
```

CLI 使用：`python scripts/stock_analyzer.py 600887 --peers`
