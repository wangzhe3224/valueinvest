#!/usr/bin/env python3
"""
SP100 Comprehensive Data Extractor v2
从现有报告中提取关键指标，生成综合分析报告
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime

# SP100 公司列表（2026年2月）
SP100_TICKERS = [
    "AAPL", "ABBV", "ABT", "ACN", "ADBE", "AIG", "AMD", "AMGN", "AMT", "AMZN",
    "AVGO", "AXP", "BA", "BAC", "BK", "BKNG", "BLK", "BMY", "C", "CAT",
    "CL", "CMCSA", "COF", "COP", "COST", "CRM", "CSCO", "CVS", "CVX", "DE",
    "DHR", "DIS", "DUK", "EMR", "FDX", "GD", "GE", "GILD", "GM", "GOOG",
    "GOOGL", "GS", "HD", "HON", "IBM", "INTC", "INTU", "ISRG", "JNJ", "JPM",
    "KO", "LIN", "LLY", "LMT", "LOW", "MA", "MCD", "MDLZ", "MDT", "MET",
    "META", "MMM", "MO", "MRK", "MS", "MSFT", "NEE", "NFLX", "NKE", "NOW",
    "NVDA", "ORCL", "PEP", "PFE", "PG", "PLTR", "PM", "PYPL", "QCOM", "RTX",
    "SBUX", "SCHW", "SO", "SPG", "T", "TGT", "TMO", "TMUS", "TSLA", "TXN",
    "UBER", "UNH", "UNP", "UPS", "USB", "V", "VZ", "WFC", "WMT", "XOM",
]

# 行业映射
SECTOR_MAP = {
    # Information Technology
    "AAPL": "Information Technology", "ACN": "Information Technology", "ADBE": "Information Technology",
    "AMD": "Information Technology", "AVGO": "Information Technology", "CRM": "Information Technology",
    "CSCO": "Information Technology", "IBM": "Information Technology", "INTC": "Information Technology",
    "INTU": "Information Technology", "MA": "Information Technology", "MSFT": "Information Technology",
    "NOW": "Information Technology", "NVDA": "Information Technology", "ORCL": "Information Technology",
    "PLTR": "Information Technology", "QCOM": "Information Technology", "TXN": "Information Technology",
    "V": "Information Technology",
    
    # Health Care
    "ABBV": "Health Care", "ABT": "Health Care", "AMGN": "Health Care", "BMY": "Health Care",
    "CVS": "Health Care", "DHR": "Health Care", "GILD": "Health Care", "ISRG": "Health Care",
    "JNJ": "Health Care", "LLY": "Health Care", "MDT": "Health Care", "MRK": "Health Care",
    "PFE": "Health Care", "TMO": "Health Care", "UNH": "Health Care",
    
    # Financials
    "AIG": "Financials", "AXP": "Financials", "BAC": "Financials", "BK": "Financials",
    "BLK": "Financials", "C": "Financials", "COF": "Financials", "GS": "Financials",
    "JPM": "Financials", "MET": "Financials", "MS": "Financials", "PYPL": "Financials",
    "SCHW": "Financials", "USB": "Financials", "WFC": "Financials",
    
    # Consumer Discretionary
    "AMZN": "Consumer Discretionary", "BKNG": "Consumer Discretionary", "GM": "Consumer Discretionary",
    "HD": "Consumer Discretionary", "LOW": "Consumer Discretionary", "MCD": "Consumer Discretionary",
    "NKE": "Consumer Discretionary", "SBUX": "Consumer Discretionary", "TGT": "Consumer Discretionary",
    "TSLA": "Consumer Discretionary",
    
    # Communication Services
    "CMCSA": "Communication Services", "DIS": "Communication Services", "GOOG": "Communication Services",
    "GOOGL": "Communication Services", "META": "Communication Services", "NFLX": "Communication Services",
    "T": "Communication Services", "TMUS": "Communication Services", "VZ": "Communication Services",
    
    # Consumer Staples
    "CL": "Consumer Staples", "COST": "Consumer Staples", "KO": "Consumer Staples",
    "MDLZ": "Consumer Staples", "PEP": "Consumer Staples", "PG": "Consumer Staples",
    "PM": "Consumer Staples", "WMT": "Consumer Staples",
    
    # Industrials
    "BA": "Industrials", "CAT": "Industrials", "DE": "Industrials", "EMR": "Industrials",
    "FDX": "Industrials", "GD": "Industrials", "GE": "Industrials", "HON": "Industrials",
    "LMT": "Industrials", "MMM": "Industrials", "RTX": "Industrials", "UBER": "Industrials",
    "UNP": "Industrials", "UPS": "Industrials",
    
    # Energy
    "COP": "Energy", "CVX": "Energy", "XOM": "Energy",
    
    # Utilities
    "DUK": "Utilities", "NEE": "Utilities", "SO": "Utilities",
    
    # Materials
    "LIN": "Materials",
    
    # Real Estate
    "AMT": "Real Estate", "SPG": "Real Estate",
}


def extract_from_report(filepath: str, ticker: str) -> dict:
    """从报告文件中提取关键数据"""
    result = {
        "ticker": ticker,
        "name": "",
        "sector": SECTOR_MAP.get(ticker, "Unknown"),
        "report_date": "",
        "price": 0,
        "pe": 0,
        "pb": 0,
        "fair_value_avg": 0,
        "fair_value_median": 0,
        "undervalued_count": 0,
        "overvalued_count": 0,
        "rating": "unknown",
        "premium_discount": 0,
        "value_trap_score": 0,
        "overall_risk": "unknown",
        "fcf_yield": 0,
        "total_yield": 0,
        "buyback_yield": 0,
        "dividend_yield": 0,
    }
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"  Error reading {filepath}: {e}")
        return result
    
    # 提取报告日期
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})_\w+_analysis\.md", filepath)
    if date_match:
        result["report_date"] = date_match.group(1)
    
    # 提取公司名称
    name_match = re.search(r"\|\s*公司名称\s*\|\s*([^|]+)\s*\|", content)
    if name_match:
        result["name"] = name_match.group(1).strip()
    
    # 提取当前股价
    price_match = re.search(r"\|\s*当前股价\s*\|\s*\\?\$?([\d,.]+)\s*\|", content)
    if price_match:
        result["price"] = float(price_match.group(1).replace(",", ""))
    
    # 提取市盈率
    pe_match = re.search(r"\|\s*市盈率\s*\(PE\)\s*\|\s*([\d.]+)x?\s*\|", content)
    if pe_match:
        result["pe"] = float(pe_match.group(1))
    
    # 提取市净率
    pb_match = re.search(r"\|\s*市净率\s*\(PB\)\s*\|\s*([\d,.]+)x?\s*\|", content)
    if pb_match:
        result["pb"] = float(pb_match.group(1).replace(",", ""))
    
    # 提取股息率
    div_match = re.search(r"\|\s*股息率\s*\|\s*([\d.]+)%?\s*\|", content)
    if div_match:
        result["dividend_yield"] = float(div_match.group(1))
    
    # 提取估值汇总 (6.1 节)
    # 公允价值范围
    fv_range_match = re.search(r"公允价值范围:\s*\\?\$?([\d,.]+)\s*-\s*\\?\$?([\d,.]+)", content)
    
    # 平均公允价值
    fv_avg_match = re.search(r"平均公允价值:\s*\\?\$?([\d,.]+)", content)
    if fv_avg_match:
        result["fair_value_avg"] = float(fv_avg_match.group(1).replace(",", ""))
    
    # 中位数公允价值
    fv_median_match = re.search(r"中位数公允价值:\s*\\?\$?([\d,.]+)", content)
    if fv_median_match:
        result["fair_value_median"] = float(fv_median_match.group(1).replace(",", ""))
    
    # 当前价格相对平均值偏离
    premium_match = re.search(r"当前价格相对平均值:\s*([+-]?[\d.]+)%", content)
    if premium_match:
        result["premium_discount"] = float(premium_match.group(1))
    
    # 综合评级 (11.2 节)
    rating_match = re.search(r"\|\s*综合评级\s*\|\s*([^|]+)\s*\|", content)
    if rating_match:
        rating_text = rating_match.group(1).strip().lower()
        if "高估" in rating_text or "overvalued" in rating_text:
            result["rating"] = "overvalued"
        elif "低估" in rating_text or "undervalued" in rating_text:
            result["rating"] = "undervalued"
        elif "合理" in rating_text or "fair" in rating_text:
            result["rating"] = "fair"
        else:
            result["rating"] = "unknown"
    
    # 低估/高估方法数
    undervalued_match = re.search(r"低估方法数\s*\|\s*(\d+)/\d+", content)
    if undervalued_match:
        result["undervalued_count"] = int(undervalued_match.group(1))
    
    overvalued_match = re.search(r"高估方法数\s*\|\s*(\d+)/\d+", content)
    if overvalued_match:
        result["overvalued_count"] = int(overvalued_match.group(1))
    
    # 价值陷阱检测 (7.1 节)
    trap_score_match = re.search(r"\|\s*陷阱评分\s*\|\s*(\d+)/100\s*\|", content)
    if trap_score_match:
        result["value_trap_score"] = int(trap_score_match.group(1))
    
    # 整体风险等级
    risk_match = re.search(r"\|\s*整体风险等级\s*\|\s*\*\*(LOW|MODERATE|HIGH|CRITICAL)\*\*\s*\|", content)
    if risk_match:
        result["overall_risk"] = risk_match.group(1)
    else:
        # 另一种格式
        risk_match2 = re.search(r"整体风险等级\s*\|\s*\*\*(\w+)\*\*", content)
        if risk_match2:
            result["overall_risk"] = risk_match2.group(1)
    
    # FCF 收益率 (5.1 节或11.5节)
    fcf_yield_match = re.search(r"\|\s*FCF\s*收益率\s*\|\s*([\d.]+)%?\s*\|", content)
    if fcf_yield_match:
        result["fcf_yield"] = float(fcf_yield_match.group(1))
    
    # 总股东收益率 (8.1 节)
    total_yield_match = re.search(r"\|\s*\*?\*?总股东收益率\*?\*?\s*\|\s*\*?\*?([\d.]+)%?\*?\*?\s*\|", content)
    if total_yield_match:
        result["total_yield"] = float(total_yield_match.group(1))
    
    # 回购收益率
    buyback_match = re.search(r"\|\s*回购收益率\s*\|\s*\*?\*?([\d.]+)%?\*?\*?\s*\|", content)
    if buyback_match:
        result["buyback_yield"] = float(buyback_match.group(1))
    
    return result


def find_latest_report(ticker: str, reports_dir: str) -> str | None:
    """找到最新的报告文件"""
    ticker_dir = os.path.join(reports_dir, ticker)
    if not os.path.exists(ticker_dir):
        return None
    
    # 列出所有报告文件
    reports = []
    for f in os.listdir(ticker_dir):
        if f.endswith("_analysis.md"):
            reports.append(os.path.join(ticker_dir, f))
    
    if not reports:
        return None
    
    # 按日期排序，返回最新的
    reports.sort(reverse=True)
    return reports[0]


def main():
    reports_dir = "reports"
    output_json = "reports/sp100_comprehensive_summary_v2.json"
    output_md = "reports/sp100_summary_report_v2.md"
    
    print("=" * 60)
    print("SP100 Comprehensive Data Extractor v2")
    print("=" * 60)
    
    all_data = []
    stats = {
        "total": 0,
        "found": 0,
        "undervalued": 0,
        "fair": 0,
        "overvalued": 0,
        "unknown": 0,
    }
    
    for ticker in SP100_TICKERS:
        stats["total"] += 1
        report_path = find_latest_report(ticker, reports_dir)
        
        if report_path:
            stats["found"] += 1
            data = extract_from_report(report_path, ticker)
            all_data.append(data)
            
            # 统计评级
            if data["rating"] == "undervalued":
                stats["undervalued"] += 1
            elif data["rating"] == "fair":
                stats["fair"] += 1
            elif data["rating"] == "overvalued":
                stats["overvalued"] += 1
            else:
                stats["unknown"] += 1
            
            print(f"  ✓ {ticker}: {data['name'][:30] if data['name'] else 'N/A'} | "
                  f"PE={data['pe']:.1f} | Rating={data['rating']} | "
                  f"Trap={data['value_trap_score']}")
        else:
            print(f"  ✗ {ticker}: No report found")
    
    # 保存 JSON
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"\n✓ JSON saved to {output_json}")
    
    # 生成 Markdown 报告
    generate_report(all_data, stats, output_md)
    print(f"✓ Report saved to {output_md}")
    
    # 打印统计
    print("\n" + "=" * 60)
    print("Summary Statistics")
    print("=" * 60)
    print(f"Total tickers: {stats['total']}")
    print(f"Reports found: {stats['found']}")
    print(f"  - Undervalued: {stats['undervalued']}")
    print(f"  - Fair: {stats['fair']}")
    print(f"  - Overvalued: {stats['overvalued']}")
    print(f"  - Unknown: {stats['unknown']}")


def generate_report(data: list, stats: dict, output_path: str):
    """生成综合分析报告"""
    
    # 按评级分类
    undervalued = [d for d in data if d["rating"] == "undervalued"]
    fair = [d for d in data if d["rating"] == "fair"]
    overvalued = [d for d in data if d["rating"] == "overvalued"]
    unknown = [d for d in data if d["rating"] == "unknown"]
    
    # 按折价程度排序（负数最大优先）
    undervalued.sort(key=lambda x: x["premium_discount"])
    
    # 按溢价程度排序（正数最大优先）
    overvalued.sort(key=lambda x: x["premium_discount"], reverse=True)
    
    # 按行业分类
    sector_data = {}
    for d in data:
        sector = d["sector"]
        if sector not in sector_data:
            sector_data[sector] = {"undervalued": 0, "fair": 0, "overvalued": 0, "unknown": 0,
                                   "companies": [], "avg_premium": []}
        sector_data[sector]["companies"].append(d)
        if d["rating"] == "undervalued":
            sector_data[sector]["undervalued"] += 1
        elif d["rating"] == "fair":
            sector_data[sector]["fair"] += 1
        elif d["rating"] == "overvalued":
            sector_data[sector]["overvalued"] += 1
        else:
            sector_data[sector]["unknown"] += 1
        if d["premium_discount"] != 0:
            sector_data[sector]["avg_premium"].append(d["premium_discount"])
    
    # 计算各行业平均折价
    for sector in sector_data:
        premiums = sector_data[sector]["avg_premium"]
        if premiums:
            sector_data[sector]["avg_premium_val"] = sum(premiums) / len(premiums)
        else:
            sector_data[sector]["avg_premium_val"] = 0
    
    # 识别低价值陷阱风险的低估公司
    safe_undervalued = [d for d in undervalued if d["value_trap_score"] < 40]
    
    # 识别高价值陷阱风险的公司
    high_trap_risk = [d for d in data if d["value_trap_score"] >= 50]
    high_trap_risk.sort(key=lambda x: x["value_trap_score"], reverse=True)
    
    # 生成报告
    report_date = datetime.now().strftime("%Y年%m月%d日")
    
    md = f"""# SP100 估值与投资价值综合分析报告

**报告日期**: {report_date}

---

## 一、SP100 整体估值水平

截至 {report_date}, S&P 100 指数成分股的整体估值状态如下:

| 评级 | 公司数 | 占比 |
|------|--------|------|
| 🟢 低估 (Undervalued) | {stats['undervalued']} | {stats['undervalued']/stats['found']*100:.1f}% |
| 🟡 合理 (Fair) | {stats['fair']} | {stats['fair']/stats['found']*100:.1f}% |
| 🔴 高估 (Overvalued) | {stats['overvalued']} | {stats['overvalued']/stats['found']*100:.1f}% |
| ⚪ 待定 (Unknown) | {stats['unknown']} | {stats['unknown']/stats['found']*100:.1f}% |
| **总计** | **{stats['found']}** | **100%** |

### 关键发现

"""
    
    if undervalued:
        md += "**🟢 最被低估的公司** (按折价程度排序):\n\n"
        md += "| 代码 | 名称 | 行业 | 折价% | 价值陷阱 | FCF收益率 | 总收益率 |\n"
        md += "|------|------|------|-------|----------|-----------|----------|\n"
        for d in undervalued[:15]:
            name = d['name'][:20] if d['name'] else "N/A"
            md += f"| {d['ticker']} | {name} | {d['sector'][:15]} | {d['premium_discount']:+.1f}% | {d['value_trap_score']}/100 | {d['fcf_yield']:.2f}% | {d['total_yield']:.2f}% |\n"
        md += "\n"
    
    if overvalued:
        md += "**🔴 最被高估的公司** (按溢价程度排序):\n\n"
        md += "| 代码 | 名称 | 行业 | 溢价% | PE | PB | 总收益率 |\n"
        md += "|------|------|------|-------|-----|-----|----------|\n"
        for d in overvalued[:15]:
            name = d['name'][:20] if d['name'] else "N/A"
            md += f"| {d['ticker']} | {name} | {d['sector'][:15]} | {d['premium_discount']:+.1f}% | {d['pe']:.1f}x | {d['pb']:.1f}x | {d['total_yield']:.2f}% |\n"
        md += "\n"
    
    md += """---

## 二、按行业分类的估值分布

| 行业 | 低估 | 合理 | 高估 | 待定 | 平均溢价/折价 |
|------|------|------|------|------|---------------|
"""
    
    sector_order = ["Information Technology", "Health Care", "Financials", "Consumer Discretionary",
                    "Communication Services", "Consumer Staples", "Industrials", "Energy",
                    "Utilities", "Materials", "Real Estate"]
    
    for sector in sector_order:
        if sector in sector_data:
            s = sector_data[sector]
            md += f"| {sector[:20]} | {s['undervalued']} | {s['fair']} | {s['overvalued']} | {s['unknown']} | {s['avg_premium_val']:+.1f}% |\n"
    
    md += """
---

## 三、投资建议

### 🟢 买入建议

基于估值分析，以下公司具有**低估值 + 低价值陷阱风险**的特征，适合考虑买入:

"""
    
    if safe_undervalued:
        md += "| 代码 | 名称 | 行业 | 折价% | 价值陷阱 | FCF收益率 | 总收益率 |\n"
        md += "|------|------|------|-------|----------|-----------|----------|\n"
        for d in safe_undervalued[:10]:
            name = d['name'][:20] if d['name'] else "N/A"
            md += f"| {d['ticker']} | {name} | {d['sector'][:15]} | {d['premium_discount']:+.1f}% | {d['value_trap_score']}/100 | {d['fcf_yield']:.2f}% | {d['total_yield']:.2f}% |\n"
    else:
        md += "*当前未发现同时满足"低估+低价值陷阱风险"条件的公司。*\n"
    
    md += """
### ⚠️ 风险提示

以下公司存在**高价值陷阱风险** (评分≥50/100)，需要谨慎:

"""
    
    if high_trap_risk:
        md += "| 代码 | 名称 | 行业 | 评级 | 价值陷阱 | 主要风险 |\n"
        md += "|------|------|------|------|----------|----------|\n"
        for d in high_trap_risk[:10]:
            name = d['name'][:20] if d['name'] else "N/A"
            md += f"| {d['ticker']} | {name} | {d['sector'][:15]} | {d['rating']} | {d['value_trap_score']}/100 | - |\n"
    else:
        md += "*当前未发现高价值陷阱风险公司。*\n"
    
    md += f"""
---

## 四、详细数据表

| 代码 | 名称 | 行业 | 评级 | 折价% | PE | PB | 价值陷阱 | FCF收益率 | 总收益率 |
|------|------|------|------|-------|-----|-----|----------|-----------|----------|
"""
    
    # 按评级排序：低估 > 合理 > 高估 > 待定
    sorted_data = undervalued + fair + overvalued + unknown
    for d in sorted_data:
        name = d['name'][:15] if d['name'] else "N/A"
        rating_icon = {"undervalued": "🟢", "fair": "🟡", "overvalued": "🔴", "unknown": "⚪"}.get(d['rating'], "⚪")
        md += f"| {d['ticker']} | {name} | {d['sector'][:12]} | {rating_icon} {d['rating'][:3]} | {d['premium_discount']:+.1f}% | {d['pe']:.1f} | {d['pb']:.1f} | {d['value_trap_score']}/100 | {d['fcf_yield']:.2f}% | {d['total_yield']:.2f}% |\n"
    
    md += """
---

## 五、方法论说明

### 估值方法

- **DCF (现金流折现)**: 预测未来10年自由现金流，计算终值并折现
- **GARP (合理价格增长)**: 结合盈利增长和价值股特征
- **PEG Ratio**: PE / 增长率，寻找合理估值的成长股
- **EV/EBITDA**: 企业价值 / 息税折旧摊销前利润
- **Graham Formula**: 经典价值投资公式
- **Reverse DCF**: 反向计算当前价格隐含的增长预期
- **Rule of 40**: 增长率 + 利润率 ≥ 40% (SaaS/科技股)

### 评级标准

- **低估 (Undervalued)**: 当前价格低于公允价值均值15%以上
- **合理 (Fair)**: 当前价格在公允价值均值±15%以内
- **高估 (Overvalued)**: 当前价格高于公允价值均值15%以上

### 价值陷阱检测 (5维度)

1. **财务健康度**: Altman Z-Score 破产预警
2. **业务恶化**: 收入/毛利/ROE 趋势
3. **护城河侵蚀**: 竞争优势削弱
4. **AI 颠覆风险**: 行业被 AI 颠覆的可能性
5. **分红信号**: 分红可持续性

### 数据来源

- **价格数据**: yfinance
- **财务数据**: yfinance
- **分析工具**: ValueInvest 估值引擎

---

**免责声明**: 本报告仅供参考，不构成投资建议。投资有风险，入市需谨慎。所有数据均来自公开来源，可能存在误差。
"""
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)


if __name__ == "__main__":
    main()
