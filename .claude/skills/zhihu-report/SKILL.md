# Zhihu Stock Report Skill

将股票分析结果生成知乎风格的深度文章。

## Usage

```
Use the zhihu-report skill to generate article for [TICKER]
```

## Input Required

- **ticker**: 股票代码
- **stock**: Stock 对象 (已获取基本面数据)
- **history**: StockHistory 对象 (已获取价格历史)
- **results**: ValuationResult 列表 (估值引擎结果)
- **company_type**: 公司类型 (growth/dividend/value/bank/general)

## Output Location

文章保存到 `reports/[TICKER]/YYYY-MM-DD_[ticker]_analysis.md`

## Markdown Format Rules (知乎兼容)

1. **表格**: 允许使用，格式标准
2. **禁止使用**:
3. **必须转义**: 美元符号 `$` -> `\$`
4. **加粗**: 仅在正文中使用 `**text**`

## Article Template

```markdown
# [股票名称]暴跌/上涨X%后，还值得买入吗？——用N种估值模型深度分析 [TICKER]

本文使用 ValueInvest 库对 [公司全称] ([TICKER]) 进行多维度估值分析，时间戳：YYYY-MM-DD

---

## 一、前言：[吸引眼球的引言]

[背景描述，2-3句话]

**核心问题：[关键投资问题]**

本文将通过 N 种专业估值模型进行深度分析。

---

## 二、公司概况：你应该知道的"基本面"

| 指标 | 数值 |
|------|------|
| 公司名称 | [name] |
| 股票代码 | [ticker] |
| 当前股价 | \$[price] |
| 总市值 | \$[market_cap]亿 |
| 营业收入 | \$[revenue]亿 |
| 净利润 | \$[net_income]亿 |
| 每股收益 (EPS) | \$[eps] |
| 每股净资产 (BVPS) | \$[bvps] |
| 市盈率 (PE) | [pe]x |
| 市净率 (PB) | [pb]x |

**一句话概括**：[核心投资亮点]

---

## 三、历史表现：[N]年[X]%的年化回报

### 3.1 关键指标

| 指标 | 数值 | 解读 |
|------|------|------|
| [N]年CAGR | [cagr]% | [解读] |
| 年化波动率 | [volatility]% | [解读] |
| 最大回撤 | [drawdown]% | [解读] |
| 近30日涨跌 | [change]% | [解读] |

### 3.2 近10日股价走势

| 日期 | 收盘价 | 日涨跌 |
|------|--------|--------|
| [date] | \$[price] | [change]% |
| ... | ... | ... |

**趋势判断**：[整体趋势描述]

---

## 四、多维度估值分析

### 4.1 估值结果汇总

| 估值方法 | 公允价值 | vs 现价 | 评估结论 |
|----------|----------|---------|----------|
| [method] | \$[value] | [premium]% | [assessment] |
| ... | ... | ... | ... |

### 4.2 统计汇总

公允价值范围: \$[min] - \$[max]

- 平均公允价值: \$[avg]
- 中位数公允价值: \$[median]
- 当前价格相对平均值: [diff]%

### 4.3 重点方法解读

**[方法名]：\$[value] ([评估])**

[方法解释，2-3句话]

[关键参数说明]

---

## 五、综合结论

### 5.1 估值区间

| 类型 | 价格区间 |
|------|----------|
| 保守 | \$[low] - \$[mid] |
| 中性 (现价) | \$[current] |
| 乐观 | \$[high]+ |

### 5.2 投资评级

| 项目 | 结果 |
|------|------|
| 综合评级 | [rating] |
| 相对均值偏离 | [diff]% |
| 低估方法数 | [n]/[total] |
| 高估方法数 | [n]/[total] |

### 5.3 操作建议

| 场景 | 建议 |
|------|------|
| 已持有 | [advice] |
| 潜在买入 | [advice] |
| 目标价位 | \$[target] (提供 [X]% 安全边际) |
| 止损位 | \$[stop_loss] |

---

## 六、风险提示

### 6.1 业务风险

1. **[风险1]**：[描述]
2. **[风险2]**：[描述]
3. ...

### 6.2 估值风险

1. **[风险1]**：[描述]
2. ...

---

## 七、预期回报分析

| 情景 | 年化回报假设 | 预期收益 |
|------|--------------|----------|
| 保守 | [assumption] | [return]/年 |
| 中性 | [assumption] | [return]/年 |
| 乐观 | [assumption] | [return]/年 |

---

## 八、总结

### 一句话结论

[核心投资结论，1-2句话]

### 适合谁买？

- [适合人群1]
- [适合人群2]
- [适合人群3]

### 不适合谁？

- [不适合人群1]
- [不适合人群2]
- [不适合人群3]

---

## 九、数据来源与方法论

- 数据源：[yfinance/AKShare]
- 估值引擎：ValueInvest 多维度估值库
- 分析方法：[方法列表]
- 历史周期：[N]年

---

免责声明：本文仅供学习交流，不构成任何投资建议。股市有风险，投资需谨慎。

**作者**：ValueInvest 估值引擎  
**时间**：YYYY-MM-DD
```

## Workflow

### Step 1: Run Analysis (if not done)

```bash
python stock_analyzer.py [TICKER] --growth --news --period 5y
```

或使用 API:

```python
from valueinvest import Stock, ValuationEngine

stock = Stock.from_api(ticker)
history = Stock.fetch_price_history(ticker, period="5y")

engine = ValuationEngine()
results = engine.run_growth(stock)  # 或 run_all/run_dividend/run_bank
```

### Step 2: Generate Article

根据模板填充数据，注意：

1. 提取关键数据点
2. 撰写解读性文字 (不是简单复制数字)
3. 添加投资建议和风险提示
4. 检查格式合规性

### Step 3: Escape Special Characters

```bash
sed -i '' 's/\$/\\$/g' [filename].md
```

### Step 4: Save File

```bash
# 创建目录
mkdir -p reports/[TICKER]

# 保存文件
# reports/[TICKER]/YYYY-MM-DD_[ticker]_analysis.md
```

## Data Extraction Guide

| 模板字段 | 数据来源 |
|----------|----------|
| name | stock.name |
| ticker | stock.ticker |
| price | stock.current_price |
| market_cap | stock.current_price * stock.shares_outstanding / 1e8 |
| revenue | stock.revenue / 1e8 |
| net_income | stock.net_income / 1e8 |
| eps | stock.eps |
| bvps | stock.bvps |
| pe | stock.pe_ratio |
| pb | stock.pb_ratio |
| cagr | history.cagr |
| volatility | history.volatility |
| drawdown | history.max_drawdown |
| fair_values | [r.fair_value for r in results] |
| assessments | [r.assessment for r in results] |

## Title Patterns

根据股价表现选择标题模式：

| 情况 | 标题模式 |
|------|----------|
| 近期大跌 (>5%) | [名称]暴跌X%后，还值得买入吗？ |
| 近期大涨 (>5%) | [名称]大涨X%，现在还能追吗？ |
| 横盘震荡 | [名称]深度分析：用N种估值模型看懂这只股票 |
| 创新高/新低 | [名称]创[X]年新高/新低，该怎么操作？ |

## Example

```
Use the zhihu-report skill to generate article for GOOGL
```

输出: `reports/GOOG/2026-02-18_google_analysis.md`
