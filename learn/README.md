# Learning Notebooks

这个文件夹包含使用 `valueinvest` 库进行股票估值学习的 Jupyter Notebooks。

## 📚 可用教程

### 1. [DCF 估值模型教程](./dcf_valuation_tutorial.ipynb)

学习如何使用现金流折现 (DCF) 方法进行股票估值。

**学习内容：**
- DCF 的核心原理和公式
- 关键参数设定（增长率、折现率、终值增长率）
- 使用真实数据（美股、A股）进行 DCF 估值
- 手动计算 DCF 的每一步
- 可视化现金流预测
- 敏感性分析
- Reverse DCF（市场预期分析）
- DCF 的局限性和最佳实践

**运行方法：**
```bash
# 进入项目根目录
cd /Users/zhewang/Projects/2026/valueinvest

# 激活虚拟环境
source .venv/bin/activate

# 启动 Jupyter
jupyter notebook learn/dcf_valuation_tutorial.ipynb
```

## 🔧 环境要求

- Python 3.11+
- Jupyter Notebook 或 JupyterLab
- valueinvest 库及其依赖

安装依赖：
```bash
# 推荐方式：安装 learn + 数据源
pip install -e ".[learn,fetch]"

# 或分别安装
pip install -e ".[fetch]"  # 数据源
pip install -e ".[learn]"  # Jupyter + matplotlib + seaborn

# 最小安装（仅美股 + 可视化）
pip install -e ".[us,learn]"

# 最小安装（仅A股 + 可视化）
pip install -e ".[ashare,learn]"
```

### 可选依赖组

| 依赖组 | 包含内容 |
|--------|----------|
| `fetch` | 所有数据源 (yfinance, akshare, tushare) |
| `us` | 仅美股数据 (yfinance) |
| `ashare` | 仅A股数据 (akshare) |
| `learn` | **Jupyter + matplotlib + seaborn** ✨ |
| `dev` | 开发工具 (pytest, mypy, ruff) |
| `all` | 所有依赖 |

## 📊 数据源

教程使用真实股票数据：
- **美股**：通过 yfinance（免费，无需 API key）
- **A股**：通过 AKShare（免费，无需 API key）

## 🎯 学习路径

1. **DCF 基础** → 理解估值的核心原理
2. **参数设定** → 掌握关键参数的选择
3. **敏感性分析** → 理解参数对估值的影响
4. **实践应用** → 在真实股票上应用 DCF
5. **综合分析** → 结合多种估值方法

## 📖 参考资料

- [ValueInvest GitHub](https://github.com/wangzhe3224/valueinvest)
- 《证券分析》- Benjamin Graham
- 《估值》- McKinsey
- [Investopedia: DCF](https://www.investopedia.com/terms/d/dcf.asp)

## 🤝 贡献

欢迎添加更多学习 notebook！建议主题：
- Graham 估值方法
- 股息贴现模型 (DDM)
- 相对估值 (PE/PB)
- 周期股分析
- 质量评分 (Piotroski F-Score)

---

> 使用 [ValueInvest](https://github.com/wangzhe3224/valueinvest) 库创建
