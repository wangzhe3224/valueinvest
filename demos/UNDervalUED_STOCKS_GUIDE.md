# A股价值股筛选指南

## 快速开始

### 1. 基本用法（推荐）

```bash
# 默认：市值>=100亿，使用价值策略
python find_undervalued_stocks.py
```

**默认筛选标准**：
- 市值 >= 100亿（排除小盘微盘）
- 安全边际 >= 20%
- ROE >= 10%
- Altman Z >= 2.99（财务安全）
- P/E <= 15

### 2. 更严格的市值要求

```bash
# 市值>=200亿（大盘股）
python find_undervalued_stocks.py --min-cap 200

# 市值>=500亿（超大盘）
python find_undervalued_stocks.py --min-cap 500
```

### 3. 使用不同策略

```bash
# 成长策略（高增长+合理估值）
python find_undervalued_stocks.py --strategy growth --min-cap 200

# 质量策略（优质企业）
python find_undervalued_stocks.py --strategy quality --min-cap 300

# 红利策略（稳定分红）
python find_undervalued_stocks.py --strategy dividend --min-cap 200

# GARP策略（合理价格成长）
python find_undervalued_stocks.py --strategy garp --min-cap 200
```

### 4. 自定义参数

```bash
# 更严格的价值标准
python find_undervalued_stocks.py \
  --min-cap 200 \
  --min-mos 25 \
  --min-roe 15 \
  --max-pe 12 \
  --max-pb 1.5
```

### 5. 包含情感分析

```bash
# 包含新闻情感（较慢）
python find_undervalued_stocks.py --news

# 包含内幕交易（较慢）
python find_undervalued_stocks.py --insider

# 完整分析（最慢）
python find_undervalued_stocks.py --news --insider --min-cap 200
```

## 筛选策略详解

### VALUE 策略（深度价值）

**适用**: 耐心投资者，寻找被低估的股票

**筛选标准**:
- 安全边际 >= 20%
- ROE >= 10%
- Altman Z >= 2.99
- P/E <= 15

**评分权重**:
- 估值: 50%
- 质量: 30%
- 情感: 15%
- 动量: 5%

### GROWTH 策略（成长股）

**适用**: 追求资本增值

**筛选标准**:
- 盈利增长 >= 15%
- PEG <= 1.5
- Rule of 40 >= 30
- ROE >= 12%

**评分权重**:
- 估值: 25%
- 质量: 25%
- 情感: 15%
- 动量: 35%

### QUALITY 策略（高质量）

**适用**: 长期复利投资者

**筛选标准**:
- ROE >= 15%
- FCF收益率 >= 3%
- Altman Z >= 3.0
- ROIC >= 12%

**评分权重**:
- 估值: 25%
- 质量: 50%
- 情感: 15%
- 动量: 10%

### DIVIDEND 策略（红利股）

**适用**: 收益型投资者

**筛选标准**:
- 股息率 >= 3%
- 分红率 <= 70%
- 分红增长 >= 5%
- 安全边际 >= 10%

**评分权重**:
- 估值: 30%
- 质量: 45%
- 情感: 20%
- 动量: 5%

### GARP 策略（合理价格成长）

**适用**: 平衡成长与估值

**筛选标准**:
- 盈利增长 >= 10%
- PEG <= 1.2
- ROE >= 12%
- 安全边际 >= 10%

**评分权重**:
- 估值: 35%
- 质量: 30%
- 情感: 15%
- 动量: 20%

## 输出解读

### 评级系统

| 分数范围 | 评级 | 说明 |
|---------|------|------|
| 85+ | A+ | 优秀 |
| 80-84 | A | 很好 |
| 75-79 | A- | 良好 |
| 70-74 | B+ | 中上 |
| 65-69 | B | 中等 |
| 60-64 | B- | 中下 |
| <60 | C/D | 较差 |

### 关键指标

**安全边际 (Margin of Safety)**:
- >= 20%: 被低估
- 10-20%: 轻微低估
- -10~10%: 合理
- -20~-10%: 轻微高估
- < -20%: 高估

**ROE (净资产收益率)**:
- >= 15%: 优秀
- 10-15%: 良好
- <10%: 一般

**Altman Z-Score**:
- >= 3.0: 安全区
- 2.7-3.0: 警戒区
- <2.7: 危险区

## 高级用法

### 分析所有大盘股

```bash
# 分析所有市值>=100亿的股票（约300只）
python find_undervalued_stocks.py --max-stocks 0 --min-cap 100
```

### 快速筛选（仅前50只）

```bash
# 仅分析前50只最大市值的股票
python find_undervalued_stocks.py --max-stocks 50
```

### 提高并发速度

```bash
# 使用20个并发线程
python find_undervalued_stocks.py --workers 20
```

### 显示详细进度

```bash
# 显示每只股票的处理进度
python find_undervalued_stocks.py --verbose
```

## 实战建议

### 1. 分层筛选

```bash
# 第一步：宽松筛选，获取候选池
python find_undervalued_stocks.py --min-cap 100 --min-mos 10

# 第二步：严格筛选，精挑细选
python find_undervalued_stocks.py --min-cap 200 --min-mos 25 --min-roe 15
```

### 2. 多策略组合

```bash
# 价值+质量双确认
python find_undervalued_stocks.py --strategy value --min-cap 200 > value.txt
python find_undervalued_stocks.py --strategy quality --min-cap 200 > quality.txt

# 找出同时在两个列表中的股票
```

### 3. 定期监控

```bash
# 每周运行一次，保存结果
python find_undervalued_stocks.py --min-cap 200 --save weekly_screening.json
```

## 常见问题

### Q: 为什么有些股票分析失败？

A: 可能原因：
- 新股数据不完整
- ST股票数据异常
- 网络问题
- 数据源暂时不可用

### Q: 如何避免价值陷阱？

A: 使用以下组合：
```bash
# 严格财务质量 + 估值
python find_undervalued_stocks.py \
  --strategy value \
  --min-cap 200 \
  --min-mos 25 \
  --min-roe 15
```

### Q: 分析速度慢怎么办？

A: 
- 减少分析数量：`--max-stocks 50`
- 不使用情感分析：去掉 `--news --insider`
- 提高并发：`--workers 20`

### Q: 如何查看所有可用选项？

A: 
```bash
python find_undervalued_stocks.py --help
```

## 示例输出

```
================================================================================
A股价值股筛选结果
================================================================================
总计分析: 100 只
符合条件: 12 只
未通过: 85 只
错误: 3 只
通过率: 12.0%
耗时: 45.2秒

排名前 20 只股票:
--------------------------------------------------------------------------------
排名 代码      名称        评级   综合分  估值分  安全边际     ROE   市值(亿)
--------------------------------------------------------------------------------
   1 600887   伊利股份    A-    78.5   82.3    +22.5%  18.3     1675.0
   2 600900   长江电力    B+    72.3   68.5    +15.2%  14.2     5200.0
   3 601398   工商银行    B     68.9   72.1    +18.7%  11.8     1800.0
================================================================================

排名前 5 详细信息:
================================================================================

【1. 600887 - 伊利股份】
  综合评级: A- (78.5分)
  当前价格: ¥26.48
  市值: ¥1675.0亿
  
  【估值】
    公允价值: ¥32.15
    安全边际: +22.5%
    评估: Undervalued
    P/E: 16.0, P/B: 2.97
  
  【质量】
    ROE: 18.3%
    FCF收益率: 5.23%
    Altman Z: 3.45
    评估: High Quality
...
```

## 下一步

找到候选股票后，建议：

1. **深度分析**: 使用 `stock_analyzer.py` 详细分析
   ```bash
   python stock_analyzer.py 600887 --news --insider
   ```

2. **行业对比**: 查看同行业公司
   ```bash
   python stock_analyzer.py 600887 --industry
   ```

3. **财务健康**: 检查财务报表
   ```bash
   python stock_analyzer.py 600887 --fcf
   ```

4. **跟踪观察**: 加入观察名单，定期检查
