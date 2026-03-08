#!/usr/bin/env python3
"""
SP100 Comprehensive Data Extractor - Final Version
Extract key metrics from existing reports and generate summary
"""

import os
import re
import json
from datetime import datetime

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
    "AAPL": "IT",
    "ACN": "IT",
    "ADBE": "IT",
    "AMD": "IT",
    "AVGO": "IT",
    "CRM": "IT",
    "CSCO": "IT",
    "IBM": "IT",
    "INTC": "IT",
    "INTU": "IT",
    "MA": "IT",
    "MSFT": "IT",
    "NOW": "IT",
    "NVDA": "IT",
    "ORCL": "IT",
    "PLTR": "IT",
    "QCOM": "IT",
    "TXN": "IT",
    "V": "IT",
    "ABBV": "Health",
    "ABT": "Health",
    "AMGN": "Health",
    "BMY": "Health",
    "CVS": "Health",
    "DHR": "Health",
    "GILD": "Health",
    "ISRG": "Health",
    "JNJ": "Health",
    "LLY": "Health",
    "MDT": "Health",
    "MRK": "Health",
    "PFE": "Health",
    "TMO": "Health",
    "UNH": "Health",
    "AIG": "Fin",
    "AXP": "Fin",
    "BAC": "Fin",
    "BK": "Fin",
    "BLK": "Fin",
    "C": "Fin",
    "COF": "Fin",
    "GS": "Fin",
    "JPM": "Fin",
    "MET": "Fin",
    "MS": "Fin",
    "PYPL": "Fin",
    "SCHW": "Fin",
    "USB": "Fin",
    "WFC": "Fin",
    "AMZN": "Cons Disc",
    "BKNG": "Cons Disc",
    "GM": "Cons Disc",
    "HD": "Cons Disc",
    "LOW": "Cons Disc",
    "MCD": "Cons Disc",
    "NKE": "Cons Disc",
    "SBUX": "Cons Disc",
    "TGT": "Cons Disc",
    "TSLA": "Cons Disc",
    "CMCSA": "Comm",
    "DIS": "Comm",
    "GOOG": "Comm",
    "GOOGL": "Comm",
    "META": "Comm",
    "NFLX": "Comm",
    "T": "Comm",
    "TMUS": "Comm",
    "VZ": "Comm",
    "CL": "Cons Stap",
    "COST": "Cons Stap",
    "KO": "Cons Stap",
    "MDLZ": "Cons Stap",
    "PEP": "Cons Stap",
    "PG": "Cons Stap",
    "PM": "Cons Stap",
    "WMT": "Cons Stap",
    "BA": "Ind",
    "CAT": "Ind",
    "DE": "Ind",
    "EMR": "Ind",
    "FDX": "Ind",
    "GD": "Ind",
    "GE": "Ind",
    "HON": "Ind",
    "LMT": "Ind",
    "MMM": "Ind",
    "RTX": "Ind",
    "UBER": "Ind",
    "UNP": "Ind",
    "UPS": "Ind",
    "COP": "Energy",
    "CVX": "Energy",
    "XOM": "Energy",
    "DUK": "Util",
    "NEE": "Util",
    "SO": "Util",
    "LIN": "Materials",
    "AMT": "RE",
    "SPG": "RE",
}


def extract_from_report(filepath, ticker):
    """Extract key data from report file"""
    result = {
        "ticker": ticker,
        "name": "",
        "sector": SECTOR_MAP.get(ticker, "Other"),
        "report_date": "",
        "price": 0.0,
        "pe": 0.0,
        "pb": 0.0,
        "fair_value_avg": 0.0,
        "premium_discount": 0.0,
        "rating": "unknown",
        "value_trap_score": 0,
        "fcf_yield": 0.0,
        "total_yield": 0.0,
    }

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return result

    # Extract date from filename
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})_\w+_analysis\.md", filepath)
    if date_match:
        result["report_date"] = date_match.group(1)

    # Extract company name
    name_match = re.search(r"\|\s*公司名称\s*\|\s*([^|]+)\s*\|", content)
    if name_match:
        result["name"] = name_match.group(1).strip()

    # Extract price
    price_match = re.search(r"\|\s*当前股价\s*\|\s*\\?\$?([\d,.]+)\s*\|", content)
    if price_match:
        try:
            result["price"] = float(price_match.group(1).replace(",", ""))
        except:
            pass

    # Extract PE
    pe_match = re.search(r"\|\s*市盈率\s*\(PE\)\s*\|\s*([\d.]+)x?\s*\|", content)
    if pe_match:
        try:
            result["pe"] = float(pe_match.group(1))
        except:
            pass

    # Extract PB
    pb_match = re.search(r"\|\s*市净率\s*\(PB\)\s*\|\s*([\d,.]+)x?\s*\|", content)
    if pb_match:
        try:
            result["pb"] = float(pb_match.group(1).replace(",", ""))
        except:
            pass

    # Extract premium/discount
    premium_match = re.search(r"当前价格相对平均值:\s*([+-]?[\d.]+)%", content)
    if premium_match:
        try:
            result["premium_discount"] = float(premium_match.group(1))
        except:
            pass

    # Extract rating
    rating_match = re.search(r"\|\s*综合评级\s*\|\s*([^|]+)\s*\|", content)
    if rating_match:
        rating_text = rating_match.group(1).strip().lower()
        if "overvalued" in rating_text or "高估" in rating_text:
            result["rating"] = "overvalued"
        elif "undervalued" in rating_text or "低估" in rating_text:
            result["rating"] = "undervalued"
        elif "fair" in rating_text or "合理" in rating_text:
            result["rating"] = "fair"

    # Extract value trap score
    trap_match = re.search(r"\|\s*陷阱评分\s*\|\s*(\d+)/100\s*\|", content)
    if trap_match:
        try:
            result["value_trap_score"] = int(trap_match.group(1))
        except:
            pass

    # Extract FCF yield
    fcf_match = re.search(r"\|\s*FCF\s*收益率\s*\|\s*([\d.]+)%?\s*\|", content)
    if fcf_match:
        try:
            result["fcf_yield"] = float(fcf_match.group(1))
        except:
            pass

    # Extract total yield
    yield_match = re.search(
        r"\|\s*\*?\*?总股东收益率\*?\*?\s*\|\s*\*?\*?([\d.]+)%?\*?\*?\s*\|", content
    )
    if yield_match:
        try:
            result["total_yield"] = float(yield_match.group(1))
        except:
            pass

    return result


def find_latest_report(ticker, reports_dir):
    """Find the latest report file for a ticker"""
    ticker_dir = os.path.join(reports_dir, ticker)
    if not os.path.exists(ticker_dir):
        return None

    reports = [
        os.path.join(ticker_dir, f) for f in os.listdir(ticker_dir) if f.endswith("_analysis.md")
    ]
    if not reports:
        return None

    reports.sort(reverse=True)
    return reports[0]


def main():
    reports_dir = "reports"
    output_json = "reports/sp100_data.json"
    output_md = "reports/sp100_report.md"

    print("=" * 60)
    print("SP100 Data Extractor")
    print("=" * 60)

    all_data = []
    stats = {"total": 0, "found": 0, "undervalued": 0, "fair": 0, "overvalued": 0, "unknown": 0}

    for ticker in SP100_TICKERS:
        stats["total"] += 1
        report_path = find_latest_report(ticker, reports_dir)

        if report_path:
            stats["found"] += 1
            data = extract_from_report(report_path, ticker)
            all_data.append(data)

            if data["rating"] == "undervalued":
                stats["undervalued"] += 1
            elif data["rating"] == "fair":
                stats["fair"] += 1
            elif data["rating"] == "overvalued":
                stats["overvalued"] += 1
            else:
                stats["unknown"] += 1

            print(
                f"  OK {ticker}: PE={data['pe']:.1f} Rating={data['rating']} Trap={data['value_trap_score']}"
            )
        else:
            print(f"  -- {ticker}: No report")

    # Save JSON
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"\nSaved JSON to {output_json}")

    # Generate report
    generate_report(all_data, stats, output_md)
    print(f"Saved report to {output_md}")

    # Print stats
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total: {stats['total']}, Found: {stats['found']}")
    print(f"Undervalued: {stats['undervalued']}, Fair: {stats['fair']}")
    print(f"Overvalued: {stats['overvalued']}, Unknown: {stats['unknown']}")


def generate_report(data, stats, output_path):
    """Generate markdown report"""

    # Sort by rating
    undervalued = sorted(
        [d for d in data if d["rating"] == "undervalued"], key=lambda x: x["premium_discount"]
    )
    fair = [d for d in data if d["rating"] == "fair"]
    overvalued = sorted(
        [d for d in data if d["rating"] == "overvalued"],
        key=lambda x: x["premium_discount"],
        reverse=True,
    )
    unknown = [d for d in data if d["rating"] == "unknown"]

    # Safe undervalued (low trap risk)
    safe_undervalued = [d for d in undervalued if d["value_trap_score"] < 40]

    # High trap risk
    high_trap = sorted(
        [d for d in data if d["value_trap_score"] >= 50],
        key=lambda x: x["value_trap_score"],
        reverse=True,
    )

    date_str = datetime.now().strftime("%Y-%m-%d")

    md = f"""# SP100 Valuation Analysis Report

**Date**: {date_str}

---

## 1. Overall Valuation Status

| Rating | Count | Percentage |
|--------|-------|------------|
| Undervalued | {stats['undervalued']} | {stats['undervalued']/max(stats['found'],1)*100:.1f}% |
| Fair | {stats['fair']} | {stats['fair']/max(stats['found'],1)*100:.1f}% |
| Overvalued | {stats['overvalued']} | {stats['overvalued']/max(stats['found'],1)*100:.1f}% |
| Unknown | {stats['unknown']} | {stats['unknown']/max(stats['found'],1)*100:.1f}% |
| **Total** | **{stats['found']}** | **100%** |

"""

    if undervalued:
        md += "### Most Undervalued Companies\n\n"
        md += "| Ticker | Sector | Discount | PE | Trap Score | FCF Yield | Total Yield |\n"
        md += "|--------|--------|----------|-----|------------|-----------|-------------|\n"
        for d in undervalued[:15]:
            md += f"| {d['ticker']} | {d['sector']} | {d['premium_discount']:+.1f}% | {d['pe']:.1f} | {d['value_trap_score']}/100 | {d['fcf_yield']:.2f}% | {d['total_yield']:.2f}% |\n"
        md += "\n"

    if overvalued:
        md += "### Most Overvalued Companies\n\n"
        md += "| Ticker | Sector | Premium | PE | PB | Trap Score |\n"
        md += "|--------|--------|---------|-----|-----|------------|\n"
        for d in overvalued[:15]:
            md += f"| {d['ticker']} | {d['sector']} | {d['premium_discount']:+.1f}% | {d['pe']:.1f} | {d['pb']:.1f} | {d['value_trap_score']}/100 |\n"
        md += "\n"

    md += "---\n\n## 2. Investment Recommendations\n\n"

    if safe_undervalued:
        md += "### Buy Candidates (Undervalued + Low Trap Risk)\n\n"
        md += "| Ticker | Sector | Discount | Trap Score | FCF Yield | Total Yield |\n"
        md += "|--------|--------|----------|------------|-----------|-------------|\n"
        for d in safe_undervalued[:10]:
            md += f"| {d['ticker']} | {d['sector']} | {d['premium_discount']:+.1f}% | {d['value_trap_score']}/100 | {d['fcf_yield']:.2f}% | {d['total_yield']:.2f}% |\n"
        md += "\n"
    else:
        md += "*No companies currently meet the 'undervalued + low trap risk' criteria.*\n\n"

    if high_trap:
        md += "### Risk Warning: High Value Trap Risk\n\n"
        md += "| Ticker | Sector | Rating | Trap Score |\n"
        md += "|--------|--------|--------|------------|\n"
        for d in high_trap[:10]:
            md += (
                f"| {d['ticker']} | {d['sector']} | {d['rating']} | {d['value_trap_score']}/100 |\n"
            )
        md += "\n"

    md += "---\n\n## 3. Full Data Table\n\n"
    md += "| Ticker | Sector | Rating | Discount | PE | PB | Trap | FCF% | Yield% |\n"
    md += "|--------|--------|--------|----------|-----|-----|------|------|--------|\n"

    for d in undervalued + fair + overvalued + unknown:
        icon = {"undervalued": "G", "fair": "Y", "overvalued": "R", "unknown": "?"}.get(
            d["rating"], "?"
        )
        md += f"| {d['ticker']} | {d['sector']} | {icon} | {d['premium_discount']:+.1f}% | {d['pe']:.1f} | {d['pb']:.1f} | {d['value_trap_score']} | {d['fcf_yield']:.1f} | {d['total_yield']:.1f} |\n"

    md += """
---

## 4. Methodology

- **Undervalued**: Price < Fair Value - 15%
- **Fair**: Price within Fair Value +/- 15%
- **Overvalued**: Price > Fair Value + 15%

### Value Trap Detection (5 dimensions)
1. Financial Health (Altman Z-Score)
2. Business Deterioration (Revenue/Margin trends)
3. Moat Erosion (Competitive advantage)
4. AI Disruption Risk
5. Dividend Signal

### Data Source
- Price/Financial data: yfinance
- Analysis tool: ValueInvest valuation engine

---

*Disclaimer: This report is for reference only and does not constitute investment advice.*
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)


if __name__ == "__main__":
    main()
