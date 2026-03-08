#!/usr/bin/env python3
"""
SP100 简单数据提取器 - 从现有报告中提取关键数据
"""
import os
import re
import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# SP100 tickers
SP100_TICKERS = [
    "AAPL",
    "ABBV",
    "ABT",
    "ACN",
    "ADBE",
    "AIG",
    "AMD",
    "AMGN",
    "AMT",
    "AMZN",
    "AVGO",
    "AXP",
    "BA",
    "BAC",
    "BK",
    "BKNG",
    "BLK",
    "BMY",
    "BRK.B",
    "C",
    "CAT",
    "CL",
    "CMCSA",
    "COF",
    "COP",
    "COST",
    "CRM",
    "CSCO",
    "CVS",
    "CVX",
    "DE",
    "DHR",
    "DIS",
    "DUK",
    "EMR",
    "FDX",
    "GD",
    "GE",
    "GILD",
    "GM",
    "GOOG",
    "GOOGL",
    "GS",
    "HD",
    "HON",
    "IBM",
    "INTC",
    "INTU",
    "ISRG",
    "JNJ",
    "JPM",
    "KO",
    "LIN",
    "LLY",
    "LMT",
    "LOW",
    "MA",
    "MCD",
    "MDLZ",
    "MDT",
    "MET",
    "META",
    "MMM",
    "MO",
    "MRK",
    "MS",
    "MSFT",
    "NEE",
    "NFLX",
    "NKE",
    "NOW",
    "NVDA",
    "ORCL",
    "PEP",
    "PFE",
    "PG",
    "PLTR",
    "PM",
    "PYPL",
    "QCOM",
    "RTX",
    "SBUX",
    "SCHW",
    "SO",
    "SPG",
    "T",
    "TGT",
    "TMO",
    "TMUS",
    "TSLA",
    "TXN",
    "UBER",
    "UNH",
    "UNP",
    "UPS",
    "USB",
    "V",
    "VZ",
    "WFC",
    "WMT",
    "XOM",
]

# Sector mapping
SECTOR_MAP = {
    "AAPL": "Information Technology",
    "ABBV": "Health Care",
    "ABT": "Health Care",
    "ACN": "Information Technology",
    "ADBE": "Information Technology",
    "AIG": "Financials",
    "AMD": "Information Technology",
    "AMGN": "Health Care",
    "AMT": "Real Estate",
    "AMZN": "Consumer Discretionary",
    "AVGO": "Information Technology",
    "AXP": "Financials",
    "BA": "Industrials",
    "BAC": "Financials",
    "BK": "Financials",
    "BKNG": "Consumer Discretionary",
    "BLK": "Financials",
    "BMY": "Health Care",
    "BRK.B": "Financials",
    "C": "Financials",
    "CAT": "Industrials",
    "CL": "Consumer Staples",
    "CMCSA": "Communication Services",
    "COF": "Financials",
    "COP": "Energy",
    "COST": "Consumer Staples",
    "CRM": "Information Technology",
    "CSCO": "Information Technology",
    "CVS": "Health Care",
    "CVX": "Energy",
    "DE": "Industrials",
    "DHR": "Health Care",
    "DIS": "Communication Services",
    "DUK": "Utilities",
    "EMR": "Industrials",
    "FDX": "Industrials",
    "GD": "Industrials",
    "GE": "Industrials",
    "GILD": "Health Care",
    "GM": "Consumer Discretionary",
    "GOOG": "Communication Services",
    "GOOGL": "Communication Services",
    "GS": "Financials",
    "HD": "Consumer Discretionary",
    "HON": "Industrials",
    "IBM": "Information Technology",
    "INTC": "Information Technology",
    "INTU": "Information Technology",
    "ISRG": "Health Care",
    "JNJ": "Health Care",
    "JPM": "Financials",
    "KO": "Consumer Staples",
    "LIN": "Materials",
    "LLY": "Health Care",
    "LMT": "Industrials",
    "LOW": "Consumer Discretionary",
    "MA": "Information Technology",
    "MCD": "Consumer Discretionary",
    "MDLZ": "Consumer Staples",
    "MDT": "Health Care",
    "MET": "Financials",
    "META": "Communication Services",
    "MMM": "Industrials",
    "MO": "Consumer Staples",
    "MRK": "Health Care",
    "MS": "Financials",
    "MSFT": "Information Technology",
    "NEE": "Utilities",
    "NFLX": "Communication Services",
    "NKE": "Consumer Discretionary",
    "NOW": "Information Technology",
    "NVDA": "Information Technology",
    "ORCL": "Information Technology",
    "PEP": "Consumer Staples",
    "PFE": "Health Care",
    "PG": "Consumer Staples",
    "PLTR": "Information Technology",
    "PM": "Consumer Staples",
    "PYPL": "Financials",
    "QCOM": "Information Technology",
    "RTX": "Industrials",
    "SBUX": "Consumer Discretionary",
    "SCHW": "Financials",
    "SO": "Utilities",
    "SPG": "Real Estate",
    "T": "Communication Services",
    "TGT": "Consumer Discretionary",
    "TMO": "Health Care",
    "TMUS": "Communication Services",
    "TSLA": "Consumer Discretionary",
    "TXN": "Information Technology",
    "UBER": "Industrials",
    "UNH": "Health Care",
    "UNP": "Industrials",
    "UPS": "Industrials",
    "USB": "Financials",
    "V": "Information Technology",
    "VZ": "Communication Services",
    "WFC": "Financials",
    "WMT": "Consumer Staples",
    "XOM": "Energy",
}


def find_latest_report(ticker, reports_dir="reports"):
    """Find the latest report file for a given ticker"""
    ticker_folder = os.path.join(reports_dir, ticker)
    if not os.path.exists(ticker_folder):
        return None
    files = [f for f in os.listdir(ticker_folder) if f.endswith("_analysis.md")]
    if files:
        files.sort(key=lambda x: os.path.getmtime(os.path.join(ticker_folder, x)), reverse=True)
        return os.path.join(ticker_folder, files[0])
    return None


def extract_key_data(ticker, file_path):
    """Extract key metrics from a report file"""
    print(f"  Processing {ticker}...")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    result = {
        "ticker": ticker,
        "name": "",
        "sector": SECTOR_MAP.get(ticker, "Unknown"),
        "report_date": "",
        "price": 0,
        "pe": 0,
        "pb": 0,
        "cagr_5y": 0,
        "dividend_yield": 0,
        "market_cap": 0,
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
        "critical_issues": [],
        "warnings": [],
    }

    try:
        # Extract name
        name_match = re.search(r"## ([^(]+?)\s*\((\w+)\)", content)
        if name_match:
            result["name"] = name_match.group(1).strip()

        # Extract report date
        date_match = re.search(r"时间戳: (\d{4}-\d{2}-\d{2})", content)
        if date_match:
            result["report_date"] = date_match.group(1)

        # Extract current price
        price_match = re.search(r"当前股价.*?\$?([\d,.]+)", content)
        if price_match:
            try:
                result["price"] = float(price_match.group(1).replace(",", "").replace("$", ""))
            except:
                pass

        # Extract PE
        pe_match = re.search(r"市盈率 \(PE\).*?([\d.]+)x", content)
        if pe_match:
            try:
                result["pe"] = float(pe_match.group(1))
            except:
                pass

        # Extract PB
        pb_match = re.search(r"市净率 \(PB\).*?([\d.]+)x", content)
        if pb_match:
            try:
                result["pb"] = float(pb_match.group(1))
            except:
                pass

        # Extract valuation section
        valuation_section = re.search(r"## [五六、]估值分析(.*?)## 统计汇总", content, re.DOTALL)
        if valuation_section:
            valuation_content = valuation_section.group(1)

            # Extract fair values from table
            fair_values = []
            undervalued_count = 0
            overvalued_count = 0

            lines = valuation_content.split("\n")
            for line in lines:
                if "| ¥" in line:
                    parts = line.split("|")
                    if len(parts) >= 4:
                        try:
                            fv_str = parts[2].strip().replace("¥", "").replace(",", "")
                            fv = float(fv_str)
                            fair_values.append(fv)

                            # Check rating
                            rating = parts[4].strip().lower() if len(parts) > 4 else ""
                            if "undervalued" in rating:
                                undervalued_count += 1
                            elif "overvalued" in rating:
                                overvalued_count += 1
                        except:
                            continue

            if fair_values:
                result["fair_value_avg"] = sum(fair_values) / len(fair_values)
                result["fair_value_median"] = sorted(fair_values)[len(fair_values) // 2]
                result["undervalued_count"] = undervalued_count
                result["overvalued_count"] = overvalued_count

                # Determine rating
                if undervalued_count > overvalued_count:
                    result["rating"] = "undervalued"
                elif overvalued_count > undervalued_count:
                    result["rating"] = "overvalued"
                else:
                    result["rating"] = "fair"

        # Calculate premium/discount
        if result["price"] > 0 and result["fair_value_avg"] > 0:
            result["premium_discount"] = (
                (result["price"] - result["fair_value_avg"]) / result["fair_value_avg"]
            ) * 100

        # Extract value trap score
        trap_match = re.search(r"陷阱评分.*?(\d+)", content)
        if trap_match:
            result["value_trap_score"] = int(trap_match.group(1))

        # Extract FCF yield
        fcf_match = re.search(r"FCF收益率.*?([\d.]+)%", content)
        if fcf_match:
            try:
                result["fcf_yield"] = float(fcf_match.group(1))
            except:
                pass

        # Extract total yield
        total_yield_match = re.search(r"总股东收益率.*?([\d.]+)%", content)
        if total_yield_match:
            try:
                result["total_yield"] = float(total_yield_match.group(1))
            except:
                pass

        # Extract buyback yield
        buyback_match = re.search(r"回购收益率.*?([\d.]+)%", content)
        if buyback_match:
            try:
                result["buyback_yield"] = float(buyback_match.group(1))
            except:
                pass

    except Exception as e:
        print(f"    Error: {e}")

    return result


def generate_comprehensive_report(data):
    """Generate comprehensive markdown report"""

    # Calculate summary statistics
    undervalued = [d for d in data if d["rating"] == "undervalued"]
    fair = [d for d in data if d["rating"] == "fair"]
    overvalued = [d for d in data if d["rating"] == "overvalued"]

    # Calculate sector breakdown
    sector_data = defaultdict(list)
    for result in data:
        sector = result.get("sector", "Unknown")
        sector_data[sector].append(result)

    report_lines = []
    report_lines.append("# SP100 估值与投资价值综合分析报告\n")
    report_lines.append("")
    report_lines.append(f"**报告日期**: {datetime.now().strftime('%Y年%m月%d日')}\n")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    report_lines.append("## 一、SP100 整体估值水平\n")
    report_lines.append("")
    report_lines.append(
        f"截至 {datetime.now().strftime('%Y年%m月%d日')}, S&P 100 指数成分股的整体估值状态如下:\n"
    )
    report_lines.append("")
    report_lines.append("| 评级 | 公司数 | 平均溢价/折价 |")
    report_lines.append("|------|------|------------|")

    # Calculate averages
    if undervalued:
        avg_discount_undervalued = sum(r["premium_discount"] for r in undervalued) / len(
            undervalued
        )
    else:
        avg_discount_undervalued = 0

    if overvalued:
        avg_premium_overvalued = sum(r["premium_discount"] for r in overvalued) / len(overvalued)
    else:
        avg_premium_overvalued = 0

    report_lines.append(f"| 🟢 低估 | {len(undervalued)} | {avg_discount_undervalued:.1f}% |")
    report_lines.append(f"| 🟡 合理 | {len(fair)} | - |")
    report_lines.append(f"| 🔴 高估 | {len(overvalued)} | +{avg_premium_overvalued:.1f}% |")

    # Top undervalued companies
    sorted_undervalued = sorted(undervalued, key=lambda x: x["premium_discount"])
    report_lines.append("")
    report_lines.append("### 关键发现\n")
    report_lines.append("")
    report_lines.append("**最被低估的10 家公司** (按折价程度排序):\n")
    report_lines.append("")

    for i, result in enumerate(sorted_undervalued[:10], 1):
        report_lines.append(f"{i}. **{result['name']} ({result['ticker']})**\n")
        report_lines.append(f"   - 行业: {result.get('sector', 'N/A')}\n")
        report_lines.append(f"   - 当前股价: {result.get('price', 'N/A')}\n")
        report_lines.append(f"   - 公允价值均值: {result.get('fair_value_avg', 'N/A')}\n")
        report_lines.append(f"   - 折价程度: {result.get('premium_discount', 0):.1f}%\n")
        report_lines.append(f"   - 价值陷阱评分: {result.get('value_trap_score', 0)}/100\n")
        report_lines.append(f"   - FCF收益率: {result.get('fcf_yield', 0):.2f}%\n")
        report_lines.append(f"   - 总股东收益率: {result.get('total_yield', 0):.2f}%\n")
        report_lines.append("")

    # Top overvalued companies
    sorted_overvalued = sorted(overvalued, key=lambda x: x["premium_discount"], reverse=True)
    report_lines.append("")
    report_lines.append("**最被高估的10 家公司** (按溢价程度排序):\n")
    report_lines.append("")

    for i, result in enumerate(sorted_overvalued[:10], 1):
        report_lines.append(f"{i}. **{result['name']} ({result['ticker']})**\n")
        report_lines.append(f"   - 行业: {result.get('sector', 'N/A')}\n")
        report_lines.append(f"   - 当前股价: {result.get('price', 'N/A')}\n")
        report_lines.append(f"   - 公允价值均值: {result.get('fair_value_avg', 'N/A')}\n")
        report_lines.append(f"   - 溢价程度: +{result.get('premium_discount', 0):.1f}%\n")
        report_lines.append(f"   - PE: {result.get('pe', 0):.1f}x\n")
        report_lines.append(f"   - 5年CAGR: {result.get('cagr_5y', 0):.1f}%\n")
        report_lines.append("")

    # Sector breakdown
    report_lines.append("")
    report_lines.append("### 按行业分类的估值分布\n")
    report_lines.append("")
    report_lines.append("| 行业 | 低估 | 合理 | 高估 | 平均折价 |")
    report_lines.append("|------|------|------|------|------------|")

    for sector in sorted(sector_data.keys()):
        companies = sector_data[sector]
        undervalued_in_sector = [c for c in companies if c["rating"] == "undervalued"]
        fair_in_sector = [c for c in companies if c["rating"] == "fair"]
        overvalued_in_sector = [c for c in companies if c["rating"] == "overvalued"]

        avg_discount = sum(c["premium_discount"] for c in companies) / len(companies)

        report_lines.append(
            f"| {sector} | {len(undervalued_in_sector)} | {len(fair_in_sector)} | {len(overvalued_in_sector)} | {avg_discount:.1f}% |"
        )

    # Investment recommendations
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    report_lines.append("## 三、投资建议\n")
    report_lines.append("")
    report_lines.append("### 买入建议\n")
    report_lines.append("")
    report_lines.append(
        "基于估值分析,以下公司具有**低估值 + 低价值陷阱风险**的特征,适合考虑买入:\n"
    )
    report_lines.append("")

    # Find good investment candidates
    good_investments = [
        r
        for r in undervalued
        if r.get("value_trap_score", 0) < 40 and r.get("overall_risk", "low") == "low"
    ]
    sorted_good = sorted(good_investments, key=lambda x: x["premium_discount"])

    for result in sorted_good[:10]:
        report_lines.append(f"- **{result['name']} ({result['ticker']})**\n")
        report_lines.append(f"  - 行业: {result.get('sector', 'N/A')}\n")
        report_lines.append(f"  - 当前股价: {result.get('price', 'N/A')}\n")
        report_lines.append(f"  - 公允价值: {result.get('fair_value_avg', 'N/A')}\n")
        report_lines.append(f"  - 折价程度: {result.get('premium_discount', 0):.1f}%\n")
        target_price = result.get("fair_value_avg", 0) * 0.85
        report_lines.append(f"  - 目标买入价: {target_price:.2f} (15%安全边际)\n")
        report_lines.append(f"  - 价值陷阱评分: {result.get('value_trap_score', 0)}/100\n")
        report_lines.append(f"  - FCF收益率: {result.get('fcf_yield', 0):.2f}%\n")
        report_lines.append(f"  - 总股东收益率: {result.get('total_yield', 0):.2f}%\n")
        report_lines.append("")

    # Risk warnings
    report_lines.append("### 风险提示\n")
    report_lines.append("")
    report_lines.append("以下公司存在**高价值陷阱风险**,需要谨慎:\n")
    report_lines.append("")

    risky = [
        r
        for r in data
        if r.get("value_trap_score", 0) >= 40 or r.get("overall_risk", "low") == "high"
    ]
    sorted_risky = sorted(risky, key=lambda x: x.get("value_trap_score", 0), reverse=True)

    for result in sorted_risky[:5]:
        report_lines.append(f"- **{result['name']} ({result['ticker']})**\n")
        report_lines.append(f"  - 行业: {result.get('sector', 'N/A')}\n")
        report_lines.append(f"  - 价值陷阱评分: {result.get('value_trap_score', 0)}/100\n")
        report_lines.append(f"  - 风险等级: {result.get('overall_risk', 'N/A')}\n")
        report_lines.append("")

    # Detailed data table
    report_lines.append("---")
    report_lines.append("")
    report_lines.append("## 四、详细数据表\n")
    report_lines.append("")
    report_lines.append("| 代码 | 名称 | 行业 | 评级 | 折价% | 价值陷阱 | FCF收益率 | 总收益率 |")
    report_lines.append("|------|------|------|------|--------|----------|----------|----------|")

    for result in sorted(data, key=lambda x: x["premium_discount"]):
        report_lines.append(
            f"| {result['ticker']} | {result['name'][:12]} | {result.get('sector', 'N/A')[:15]} | {result.get('rating', 'N/A')[:10]} | {result.get('premium_discount', 0):+.1f}% | {result.get('value_trap_score', 0):.0f} | {result.get('fcf_yield', 0):.2f}% | {result.get('total_yield', 0):.2f}% |"
        )

    # Footer
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    report_lines.append("## 五、方法论说明\n")
    report_lines.append("")
    report_lines.append("### 估值方法\n")
    report_lines.append("- **DCF (现金流折现)**: 预测未来10年自由现金流, 终值计算终值\n")
    report_lines.append("- **G估值法**: 结合盈利增长和价值股特征\n")
    report_lines.append("- **DDM (股息折现)**: 适用于稳定分红股\n")
    report_lines.append("- **GARP (合理价格增长)**: 寻找成长股的合理买入价\n")
    report_lines.append("- **Reverse DCF**: 反向计算当前价格隐含的增长预期\n")
    report_lines.append(
        "- **价值陷阱检测**: 5维度评估(财务健康、业务恶化, 护城河侵蚀, AI风险, 分红信号)\n"
    )
    report_lines.append("")
    report_lines.append("### 评级标准\n")
    report_lines.append("- **低估 (Undervalued)**: 当前价格低于公允价值均值15%\n")
    report_lines.append("- **合理 (Fair)**: 当前价格在公允价值均值±15%以内\n")
    report_lines.append("- **高估 (Overvalued)**: 当前价格高于公允价值均值15%\n")
    report_lines.append("")
    report_lines.append("### 数据来源\n")
    report_lines.append("- **价格数据**: yfinance\n")
    report_lines.append("- **财务数据**: yfinance\n")
    report_lines.append(f"- **分析时间**: {datetime.now().strftime('%Y年%m月%d日')}\n")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    report_lines.append(
        "**免责声明**: 本报告仅供参考,不构成投资建议。投资有风险,入市需谨慎。所有数据均来自公开来源,可能存在误差。\n"
    )

    # Write to file
    output_path = "reports/sp100_summary_report.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f"✅ 报告已保存到: {output_path}")


if __name__ == "__main__":
    # Process all tickers
    all_results = []
    print(f"\n正在提取 {len(SP100_TICKERS)} 个公司的数据...")

    for ticker in SP100_TICKERS:
        latest_file = find_latest_report(ticker)
        if latest_file:
            data = extract_key_data(ticker, latest_file)
            if data:
                all_results.append(data)
                print(f"  ✓ {ticker}: {data['name']}")
            else:
                print(f"  ✗ {ticker}: 提取失败")
        else:
            print(f"  ○ {ticker}: 无报告文件")

    if not all_results:
        print("错误: 未能提取任何数据")
        exit(1)

    # Generate final report
    generate_comprehensive_report(all_results)

    # Save all data to JSON
    output_json = "reports/sp100_comprehensive_summary.json"
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 完成!")
    print(f"  - 共处理 {len(all_results)} 家公司")
    print(f"  - 报告已保存到: reports/sp100_summary_report.md")
    print(f"  - 数据已保存到: {output_json}")
