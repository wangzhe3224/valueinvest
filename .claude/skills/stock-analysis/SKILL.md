# Stock Analysis Skill

快速分析任意股票的多维度估值报告。

## Usage

```
Use the stock-analysis skill to analyze [TICKER]
```

## Input Required

- **ticker**: 股票代码
  - A股: 6位数字 (如 600887, 000001)
  - 美股: 字母代码 (如 AAPL, GOOGL)

## Workflow

### Step 1: Fetch Data (Separate Calls)

```python
from valueinvest import Stock, StockHistory

# 1. 获取基本面数据
stock = Stock.from_api(ticker)

# 2. 获取价格历史 (包含QFQ和HFQ两种复权)
history = Stock.fetch_price_history(ticker, period='5y', include_hfq=True)

# 3. QFQ价格 (前复权 - 用于估值比较)
recent_prices = history.get_recent_prices(days=10, adjust="qfq")
stats_qfq = history.get_price_stats(days=30, adjust="qfq")

# 4. HFQ价格 (后复权 - 真实投资回报)
stats_hfq = history.get_price_stats(days=30, adjust="hfq")
cagr_real = history.cagr_hfq  # 含分红再投资的真实回报
```

获取数据包括:
- **基本面**: EPS, BVPS, Revenue, Net Income, PE, PB
- **QFQ价格 (前复权)**: 用于与当前估值比较
- **HFQ价格 (后复权)**: 反映真实含分红投资回报
- **统计指标**: CAGR, 波动率, 最大回撤

### Step 2: Set Valuation Parameters

根据公司类型设置合理参数:

```python
# 通用参数
stock.growth_rate = 3.0          # 长期增长率
stock.cost_of_capital = 9.0       # 资本成本/要求回报率
stock.discount_rate = 9.0         # 折现率
stock.terminal_growth = 2.5       # 永续增长率
stock.growth_rate_1_5 = 3.0       # 前5年增长
stock.growth_rate_6_10 = 2.0      # 后5年增长

# 分红股参数
stock.dividend_per_share = X      # 每股股息
stock.dividend_yield = Y          # 股息率
stock.dividend_growth_rate = Z    # 股息增长率

# 使用历史CAGR作为增长率参考
if history.cagr > 0:
    stock.growth_rate = min(history.cagr, 10)  # 上限10%
```

### Step 3: Run Multi-dimensional Valuation

```python
from valueinvest import ValuationEngine

engine = ValuationEngine()

# 运行所有方法
results = engine.run_all(stock)

# 或分类运行
dividend_results = engine.run_dividend(stock)  # 分红股
growth_results = engine.run_growth(stock)      # 成长股
bank_results = engine.run_bank(stock)          # 银行股
```

### Step 4: Generate Report

输出格式:

```
======================================================================
[公司名称] ([代码]) - 深度分析报告
======================================================================

【公司概况】
  公司: XXX
  代码: XXX
  类型: XXX (银行/分红/成长/价值)
  当前股价: ¥XX.XX
  总市值: ¥XXX亿

【最新财务数据】
  营业收入: ¥XXX亿
  净利润: ¥XXX亿
  每股收益 (EPS): ¥X.XX
  每股净资产 (BVPS): ¥X.XX
  市盈率 (PE): XX.X倍
  市净率 (PB): X.XX倍
  股息率: X.XX%

【历史表现 (5年)】
  股价CAGR: X.XX%
  年化波动率: XX.XX%
  最大回撤: -XX.XX%

【近30日价格统计】
  最高: ¥XX.XX
  最低: ¥XX.XX
  均价: ¥XX.XX
  最新: ¥XX.XX
  涨跌幅: ±X.XX%

【近10日收盘价】
  2024-XX-XX: ¥XX.XX
  2024-XX-XX: ¥XX.XX (+X.XX%)
  2024-XX-XX: ¥XX.XX (-X.XX%)
  ...

======================================================================
【估值汇总】
======================================================================

| 方法 | 公允价值 | 溢价/折价 | 评估 |
|------|----------|-----------|------|
| Graham Number | ¥XX.XX | -XX% | 高估 |
| DDM | ¥XX.XX | -XX% | 高估 |
| EPV | ¥XX.XX | -XX% | 高估 |
| Graham Formula | ¥XX.XX | +XX% | 低估 |

【统计汇总】
  有效估值方法数: X
  公允价值范围: ¥XX.XX - ¥XX.XX
  平均公允价值: ¥XX.XX
  中位数公允价值: ¥XX.XX
  
  相对平均值: ±XX%
  低估方法数: X/X
  高估方法数: X/X

======================================================================
【最终结论】
======================================================================

估值区间: ¥XX-XX (保守) / ¥XX (现价) / ¥XX+ (乐观)

【综合评级】: 低估/合理/高估

投资建议:
  1. 已持有者: ...
  2. 潜在买入: 等待回调至¥XX以下
  3. 目标价位: ¥XX (提供XX%安全边际)
  4. 止损位: ¥XX

预期回报:
  保守: 股息X% + 增长X% = X%/年
  中性: 股息X% + 增长X% = X%/年
  乐观: 股息X% + 增长X% = X%/年

风险提示:
  - ...
  - ...
```

## Company Type Detection

根据股票特征自动判断公司类型:

| 特征 | 类型 | 推荐方法 |
|------|------|----------|
| 高分红 (>3%) | 分红股 | DDM, Two-Stage DDM, Graham |
| 低增长 (<5%) | 价值股 | Graham Number, EPV |
| 高增长 (>10%) | 成长股 | DCF, PEG, GARP |
| 金融行业 | 银行/金融 | P/B, Residual Income |
| 科技/SaaS | 科技股 | Rule of 40, DCF |

## Key Metrics to Calculate

1. **估值汇总统计**
   - 有效方法数
   - 公允价值范围
   - 平均值/中位数

2. **溢价/折价分析**
   - 相对平均值
   - 相对中位数

3. **方法分布**
   - 低估方法数
   - 高估方法数
   - 合理方法数

4. **综合评级规则**
   - 平均溢价 < -15%: 低估
   - 平均溢价 > +15%: 高估
   - 其他: 合理

5. **价格统计**
   - 近30日: 高/低/均价/涨跌幅
   - 近10日: 每日收盘价及涨跌

## StockHistory Methods

```python
history = Stock.fetch_price_history(ticker, period='5y')

# 获取近期价格列表 (默认QFQ)
recent = history.get_recent_prices(days=10)
# 指定HFQ
recent_hfq = history.get_recent_prices(days=10, adjust="hfq")

# 获取价格统计 (默认QFQ)
stats = history.get_price_stats(days=30)
# 指定HFQ
stats_hfq = history.get_price_stats(days=30, adjust="hfq")
```

## QFQ vs HFQ 复权说明

| 类型 | 全称 | 用途 | 特点 |
|------|------|------|------|
| **QFQ** | 前复权 | 与估值比较 | 当前价格不变，历史价格调整 |
| **HFQ** | 后复权 | 计算真实回报 | 历史价格不变，累积分红到当前价格 |

**使用场景**:
- **估值比较**: 用QFQ价格，因为当前价格与市场一致
- **投资回报**: 用HFQ的CAGR，反映含分红再投资的真实收益

**示例**:
```
伊利股份 5年数据:
  QFQ CAGR: -8.24%  (仅股价变化)
  HFQ CAGR: -6.40%  (含分红再投资)
  差额 1.84% = 分红贡献
```

## Example Prompts

```
分析伊利股份 600887
Analyze AAPL stock
给我分析一下工商银行 601398
分析长江电力
```

## Notes

- **数据分离**: 基本面和价格历史分开获取，按需调用
- A股使用 AKShare 数据源 (免费)
- 美股使用 yfinance 数据源
- 历史数据默认5年，可调整
- 增长率等参数需要根据行业和公司情况合理假设
