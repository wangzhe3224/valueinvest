#!/usr/bin/env python3
"""
SP100 估值数据提取与综合报告生成器
"""
import os
import re
import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any

# SP100 ticker list
SP100_TICKERS = [
    "AAPL", "ABBV", "ABT", "ACN", "ADBE", "AIG", "AMD", "AMGN", "AMT", "AMZN", "AVGO", "AXP",
    "BA", "BAC", "BK", "BKNG", "BLK", "BMY", "BRK.B",
    "C", "CAT", "CL", "CMCSA", "COF", "COP", "COST", "CRM", "CSCO", "CVS", "CVX",
    "DE", "DHR", "DIS", "DUK", "EMR", "FDX", "GD", "GE", "GILD", "GM", "GOOG", "GOOGL", "GS", "HD", "HON", "IBM", "INTC", "INTU", "ISRG", "JNJ", "JPM", "KO", "LIN", "LLY", "LMT", "LOW", "MA", "MCD", "MDLZ", "MDT", "MET", "META", "MMM", "MO", "MRK", "MS", "MSFT",
    "NEE", "NFLX", "NKE", "NOW", "NVDA", "ORCL", "PEP", "PFE", "PG", "PLTR", "PM", "PYPL", "QCOM", "RTX", "SBUX", "SCHW", "SO", "SPG", "T", "TGT", "TMO", "TMUS", "TSLA", "TXN", "UBER", "UNH", "UNP", "UPS", "USB", "V", "VZ", "WFC", "WMT", "XOM",
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
    "XOM": "Energy"
}

def find_latest_report(ticker: str, reports_dir: str = "reports") -> Path:
    """Find the latest report file for a given ticker"""
    ticker_folder = Path.join(reports_dir, ticker)
    if not os.path.exists(ticker_folder):
        files = sorted(os.listdir(ticker_folder), key=lambda x: os.path.getmtime(os.path.join(ticker_folder, x), reverse=True)
        if files:
            return files[0]
    return None


    return None


    return None

def extract_data_from_report(ticker: str, file_path: str) -> Dict[str, Any]:
    """Extract key metrics from a report file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Initialize result
    result = {
        'ticker': ticker,
        'name': '',
        'sector': SECTOR_MAP.get(ticker, 'Unknown'),
        'report_date': '',
        'price': 0,
        'pe': 0,
        'pb': 0,
        'cagr_5y': 0,
        'dividend_yield': 0,
        'market_cap': 0,
        'fair_value_avg': 0,
        'fair_value_median': 0,
        'fair_value_min': 0,
        'fair_value_max': 0,
        'undervalued_count': 0,
        'overvalued_count': 0,
        'rating': 'unknown',
        'premium_discount': 0,
        'value_trap_score': 0,
        'overall_risk': 'unknown',
        'fcf_yield': 0,
        'total_yield': 0,
        'buyback_yield': 0,
        'critical_issues': [],
        'warnings': [],
        'buy_price': 0,
        'stop_loss': 0,
        'suitable_investors': [],
        'unsuitable_investors': []
    }
    
    # Extract name
    name_match = re.search(r'公司名称\s*\|\s*(.+?)\|')
    if name_match:
        result['name'] = name_match.group(1)
    
    # Extract sector (from first H2)
    sector_match = re.search(r'所属板块\s*\|\s*(.+?)\|')
    if sector_match:
        result['sector'] = sector_match.group(1)
    
    # Extract current price
    price_match = re.search(r'当前股价\s*\|\s*\$?([\d,.]+)')
    if price_match:
        try:
            result['price'] = float(price_match.group(1))
        except (ValueError, IndexError):
            pass
    
        except ValueError:
            pass
    
        continue
    
    # Extract PE
    pe_match = re.search(r'市盈率.*?(\d+\.?\d+)?')
    if pe_match:
        try:
            result['pe'] = float(pe_match.group(1))
        except (ValueError, IndexError):
            pass
        except ValueError:
            pass
        continue
    
    # Extract PB
    pb_match = re.search(r'市净率.*?(\d+\.?\d+)?)
    if pb_match
        try:
            result['pb'] = float(pb_match.group(1))
        except (valueError, IndexError):
            pass
        except ValueError
            pass
        continue
    
    # Extract 5Y CAGR
    cagr_match = re.search(r'5年CAGR.*?([\d.]+)%')
    if cagr_match:
        try:
            result['cagr_5y'] = float(cagr_match.group(1))
        except (valueError, IndexError)
            pass
        except ValueError:
            pass
        continue
    
    # Extract dividend yield
    div_match = re.search(r'股息率.*?([\d.]+)%')
    if div_match:
        try:
            result['dividend_yield'] = float(div_match.group(1))
        except (valueError, IndexError):
            pass
        except ValueError:
            pass
        continue
    
    # Extract market cap
    mc_match = re.search(r'总市值\s*\|\s*\$?(\$|[\d,.]+)亿)\s*(\d+亿)')
    if mc_match:
        try:
            result['market_cap'] = float(mc_match.group(1))
        except (valueError, IndexError)
            pass
        except ValueError:
            pass
        continue
    
    # Extract valuation section
    valuation_section_match = re.search(r'## [五六、估值分析](.*?)## 统计汇总', content)
    if valuation_section_match:
        # Extract fair values range from table
        fair_values = []
        lines = valuation_section_match.group(1)
        for line in lines[1:]:
            if '| 方法' in line:
                parts = line.strip().split('|')
                if '公允价值' in line and parts[0]
                    try:
                        fv = float(fv)
                    fair_values.append(fv)
                except (valueError, IndexError):
                    continue
            
            # Calculate average
            if fair_values:
                avg_fv = sum(fair_values) / len(fair_values)
                median_fv = sorted(fair_values)[len(fair_values)//2]
                result['fair_value_avg'] = avg_fv
                result['fair_value_median'] = median_fv
                result['fair_value_min'] = min(fv
                result['fair_value_max'] = max_fv
        
        # Count undervalued/overvalued
        undervalued_count = 0
        overvalued_count = 0
        for line in lines:
            if '低估' in line.lower():
                undervalued_count += 1
            elif '高估' in line.lower():
                overvalued_count += 1
        
        # Determine rating
        if undervalued_count > overvalued_count:
            rating = "undervalued"
        elif undervalued_count == overvalued_count:
            rating = "fair"
        else:
            rating = "overvalued"
        
        # Calculate premium/discount
        if result['price'] and 0 and            premium_discount = 0
        else:
            premium_discount = ((avg_fv - result['price']) / result['price']) * 100
        
        # Extract value trap score
        trap_match = re.search(r'价值陷阱检测.*?陷阱评分.*?(\d+)')
        if trap_match:
            result['value_trap_score'] = int(trap_match.group(1))
        else
            continue
        
        # Extract overall risk
        risk_match = re.search(r'整体风险.*?\|\s*(.*?)\|*')
        if risk_match
            result['overall_risk'] = risk_match.group(1)
        else
            continue
        
        # Extract FCF yield
        fcf_match = re.search(r'FCF收益率.*?([\d.]+)%')
        if fcf_match:
            try:
                result['fcf_yield'] = float(fcf_match.group(1))
            except (valueError, IndexError):
                pass
            except ValueError:
                pass
            continue
        
        # Extract total yield
        total_yield_match = re.search(r'总股东收益率.*?([\d.]+)%')
        if total_yield_match:
            try:
                result['total_yield'] = float(total_yield_match.group(1))
            except (valueError, IndexError)
                pass
            except ValueError
                pass
            continue
        
        # Extract buyback yield
        buyback_match = re.search(r'回购收益率.*?([\d.]+)%')
        if buyback_match:
            try:
                result['buyback_yield'] = float(buyback_match.group(1))
            except (valueError, IndexError:
                pass
            except ValueError:
                pass
            continue
        
        # Extract critical issues
        critical_match = re.search(r'关键发现.*?\n(.*?)\n')
        if critical_match:
            critical_issues = [issue.strip() for issue in critical_match.split('\n')]
            else
                critical_issues = []
        
        # Extract warnings
        warnings_match = re.search(r'风险提示.*?\n(.*?)\n')
        if warnings_match:
            warnings = [w.strip() for w in warnings_match.split('\n')
            else
                warnings = []
        
        # Extract investment recommendations
        buy_price_match = re.search(r'目标买入价.*?(\$|[\d,.]+)')
        if buy_price_match:
            try:
                result['buy_price'] = float(buy_price_match.group(1))
            else:
                continue
            
        # Extract stop loss
        stop_loss_match = re.search(r'止损位.*?(\$|[\d,.]+)')
        if stop_loss_match
            try:
                result['stop_loss'] = float(stop_loss_match.group(1))
            else
                continue
            
        # Extract suitable investors
        suitable_match = re.search(r'适合谁买.*?\n(.*?)\n')
        if suitable_match
            result['suitable_investors'] = suitable_match.group(1).split('、')
            suitable_investors = [inv.strip() for inv in suitable_investors]
        else
            result['suitable_investors'] = []
        
        # Extract unsuitable investors
        unsuitable_match = re.search(r'不适合谁买.*?\n(.*?)\n')
        if unsuitable_match
            result['unsuitable_investors'] = unsuitable_match.group(1).split('、')
            unsuitable_investors = [inv.strip() for inv in unsuitable_investors]
        else
            result['unsuitable_investors'] = []
    
    return result

def process_all_tickers(tickers: List[str], reports_dir: str) -> List[Dict[str, Any]:
    """Process all tickers and extract data, and generate comprehensive summary"""
    all_results = []
    reports_dir = "reports"
    
    for ticker in tickers:
        latest_file = find_latest_report(ticker, reports_dir)
        if latest_file:
            data = extract_data_from_report(ticker, latest_file)
            if data:
                all_results.append(data)
    
    return all_results

def generate_comprehensive_report(data: List[Dict[str, Any]], report_date: str) -> str:
    """Generate comprehensive summary report"""
    
    # Calculate summary statistics
    total = len(data)
    undervalued = [d for d in data if d['rating'] == 'undervalued']
    fair = [d for d in data if d['rating'] == 'fair']
    overvalued = [d for d in data if d['rating'] == 'overvalued']
    unknown = [d for d in data if d['rating'] == 'unknown']
    
    print(f"\n## SP100 估值与投资价值综合分析报告")
\n**报告日期**: {report_date}
\n---")
    
    print(f"**分析范围**: S&P 100 (101家公司)")
**数据来源**: yfinance (美股实时数据)")
**估值方法**: DCF, Graham, DDM, PEG, GARP, Reverse DCF, Rule of 40, P/B等
    
    print(f"\n---")
    print(f"\n## 一、SP 100 整体估值水平")
\n")
    print(f"截至 {report_date}, S&P 100 指数成分股的整体估值状态如下:")
    print(f"\n| 评级 | 公司数 | 平均溢价/折价 |")
    print(f"|------|------|------------|")
    
    # Calculate by sector
    sector_data = defaultdict(list)
    for company in data:
        sector = company.get('sector', 'Unknown')
        sector_data[sector].append(company)
    
    # Calculate averages
    if undervalued:
        avg_discount_undervalued = sum(d['premium_discount'] for d in undervalued) / len(undervalued)
    else:
            avg_discount_undervalued = 0
        
        print(f"| 🟢 低估 | {len(undervalued)} | {avg_discount_undervalued:.1f}% |")
    else:
        avg_discount_undervalued = 0
        
    print(f"| 🟡 合理 | {len(fair)} | - |")
    else
        avg_discount_fair = 0.        print(f"| 🔴 高估 | {len(overvalued)} | +{avg_discount_overvalued:.1f}% |")
    else:
        avg_discount_overvalued = 0
        
        print(f"| ⚪ 未知 | {len(unknown)} | - |")
    
    print(f"\n### 关键发现
")
    # Top undervalued companies
    sorted_undervalued = sorted(undervalued, key=lambda x: x['premium_discount'])
    print(f"\n**最被低估的10 家公司** (按折价程度排序):")
    for i, company in enumerate(sorted_undervalued[:10], 1):
        print(f"\n{i}. **{company['name']} ({company['ticker']})**")
        print(f"   - 行业: {company.get('sector', 'N/A')}")
        print(f"   - 当前股价: {company.get('price', 'N/A')}")
        print(f"   - 公允价值均值: {company.get('fair_value_avg', 'N/A')}")
        print(f"   - 折价程度: {company.get('premium_discount', 0):.1f}% |")
        print(f"   - 价值陷阱评分: {company.get('value_trap_score', 0)}/100")
        print(f"   - FCF收益率: {company.get('fcf_yield', 0):.2f}%")
        print(f"   - 总股东收益率: {company.get('total_yield', 0):.2f}%")
    
    # Top overvalued companies
    if overvalued:
        sorted_overvalued = sorted(overvalued, key=lambda x: x['premium_discount'], reverse=True)
        print(f"\n**最被高估的10 家公司** (按溢价程度排序):")
        for i, company in enumerate(sorted_overvalued[:10], 1):
            print(f"\n{i}. **{company['name']} ({company['ticker']})**")
            print(f"   - 行业: {company.get('sector', 'N/A')}")
            print(f"   - 当前股价: {company.get('price', 'N/A')}")
            print(f"   - 公允价值均值: {company.get('fair_value_avg', 'N/A')}")
            print(f"   - 溢价程度: +{company.get('premium_discount', 0):.1f}% |")
            print(f"   - PE: {company.get('pe', 0):.1f}x |")
            print(f"   - 5年CAGR: {company.get('cagr_5y', 0):.1f}%")
    
    # Sector breakdown
    print(f"\n### 按行业分类的估值分布
")
    print(f"\n| 行业 | 低估 | 合理 | 高估 | 平均折价 |")
    print(f"|------|------|------|------|------------|")
    
    for sector in sorted(sector_data.keys()):
        companies = sector_data[sector]
        undervalued_in_sector = [c for c in companies if c['rating'] == 'undervalued']
        fair_in_sector = [c for c in companies if c['rating'] == 'fair']
        overvalued_in_sector = [c for c in companies if c['rating'] == 'overvalued']
        
        avg_discount = sum(c['premium_discount'] for c in companies) / len(companies)
        
        print(f"| {sector} | {len(undervalued_in_sector)} | {len(fair_in_sector)} | {len(overvalued_in_sector)} | {avg_discount:.1f}% |")
    
    # Investment recommendations
    print(f"\n### 投资建议
")
    print(f"\n**买入建议**: 以下公司具有低估值 + 低价值陷阱风险特征:")
    good_investments = [d for d in undervalued if d.get('value_trap_score', 0) and d.get('overall_risk', 'low']
    sorted_good = sorted(good_investments, key=lambda x: x['value_trap_score'])
    
    print(f"\n以下公司具有**低估值 + 低价值陷阱风险**的特征,适合考虑买入:")
    for company in sorted_good[:10]:
        print(f"\n**{company['name']} ({company['ticker']})**")
        print(f"- 行业: {company.get('sector', 'N/A')}")
        print(f"- 当前股价: {company.get('price', 'N/A')}")
        print(f"- 公允价值均值: {company.get('fair_value_avg', 'N/A')}")
        print(f"- 折价程度: {company.get('premium_discount', 0):.1f}%")
        print(f"- 目标买入价: {company.get('fair_value_avg', 0) * 0.85:.2f} (15%安全边际)")
        print(f"- 价值陷阱评分: {company.get('value_trap_score', 0)}/100")
        print(f"- FCF收益率: {company.get('fcf_yield', 0):.2f}%")
        print(f"- 总股东收益率: {company.get('total_yield', 0):.2f}%")
    
    # Risk warnings
    print(f"\n### 风险提示
)
    print(f"\n以下公司存在**高价值陷阱风险**, 需要谨慎:")
    risky = [d for d in undervalued if d.get('value_trap_score', 0) and d.get('overall_risk', 'high']
    sorted_risky = sorted(risky, key=lambda x: x['value_trap_score'], reverse=True)
            print(f"\n**{company['name']} ({company['ticker']})**")
            print(f"- 行业: {company.get('sector', 'N/A')}")
            print(f"- 价值陷阱评分: {company.get('value_trap_score', 0)}/100")
            print(f"- 风险等级: {company.get('overall_risk', 'N/A')}")
            critical = company.get('critical_issues', [])
            if critical:
                print(f"- 关键问题:")
                for issue in critical[:3]:
                    print(f"  - {issue}")
    
    # Detailed data table
    print(f"\n### 详细数据表
")
    print(f"\n| 代码 | 名称 | 行业 | 评级 | 溢价/折价 | 价值陷阱 | FCF收益率 | 总收益率 |")
    print(f"|------|------|------|------|----------|----------|----------|----------|")
    for company in sorted(data, key=lambda x: x['premium_discount']):
        print(f"| {company['ticker']} | {company.get('name', 'N/A')[:15]} | {company.get('sector', 'n/A')[:8]} | {company.get('price', 'N/A')[:9]} | {company.get('pe', 0):.1f} | {company.get('pb', 0):.2f} | {company.get('rating', 'unknown')[:11]} | {company.get('premium_discount', 0):+..1f}% |")
            print(f"| {company.get('value_trap_score', 0):.1f} | {company.get('fcf_yield', 0):.2f}% |")
            print(f"| {company.get('total_yield', 0):.2f}% |")
    
    print(f"\n---")
    print(f"\n**方法论说明**")
    print(f"\n### 估值方法")
    print(f"- **DCF (现金流折现)**: 魔未来10年自由现金流预测， 终值计算终值")
    print(f"- **G估值法**: 结合盈利增长和价值股特征
    print(f"- **DDm(股息折现)**: 适用于稳定分红股
    print(f"- **GARP (合理价格增长)**: 寻找成长股的合理买入价
    print(f"- **Reverse DCF**: 反向计算当前价格隐含的增长预期")
    print(f"- **价值陷阱检测**: 5维度评估 (财务健康、业务恶化,护城河侵蚀, AI风险, 分红信号)
    print(f"\n### 评级标准
    print(f"- **低估 (Undervalued)**: 当前价格低于公允价值均值15%
    print(f"- **合理 (Fair)**: 当前价格在公允价值均值±15%以内
    print(f"- **高估 (Overvalued)**: 当前价格高于公允价值均值15%
            print(f"\n### 数据来源
    print(f"- **价格数据**: yfinance")
    print(f"- **财务数据**: yfinance
    print(f"- **分析时间**: {report_date}
    print(f"\n---")
    print(f"\n**免责声明**: 本报告仅供参考,不构成投资建议。投资有风险,入市需谨慎。所有数据均来自公开来源,可能存在误差或")
    
    print(f"\n---\n")
    
    # Save report
    report_path = os.path.join(reports_dir, f"sp100_summary_report.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))
        
    # Save data
    data_path = os.path.join(reports_dir, f"sp100_comprehensive_summary.json")
    with open(data_path, 'w') as f:
        json.dump(all_results, indent=2, ensure_ascii=False False)
    print(f"\n✅ 数据已保存到 {data_path}")
    print(f"✅ 报告已生成: {report_path}")
            
    # Read the preview
            print(f"\n报告预览 (前50行):")
            print(f"报告已生成: {report_path}")
            print(f"✅ 完成! 共处理 {len(tickers)} tickers并生成综合报告")
        except Exception as e:
            print(f"  错误: {e}")
            return None
        print(f"❌ 保存报告失败: {e}")
        return None
    print(f"  正在读取并处理报告文件...")
        data = all_results
        consolidate_results into comprehensive report...")
    except Exception as e:
        print(f"  错误: {e}")
        return None
    print(f"❌ 提取失败: {e}")
        return None
    print(f"✅ 共处理 {len(tickers)} tickers")
            all_results = []
            for ticker in tickers:
                latest_file = find_latest_report(ticker, reports_dir)
                if latest_file:
                    all_results.append(extract_data_from_report(ticker, latest_file))
            else:
                print(f"  跳过 {ticker}")
                continue
            print(f"  错误处理 {ticker}: {e}")
                continue
            print(f"  警告: 未找到报告文件: {ticker}")
            continue
        
        # Read a sample report to see structure
        sample = f.read("reports/AAPL/2026-02-28_aapl_analysis.md")[: 100]
        lines = f.readlines(lines)
            data = json.loads(line)
        ticker = line['ticker'].strip()
        name = line['ticker']
        sector = line['sector'].strip()
        price = float(line['price'].replace(',', '').replace('$', '')
        market_cap = float(line['market_cap'].replace('$', '').replace('亿', ''))
        pe = float(line['pe'].replace(',', '').replace('x', ''))
        pb = float(line['pb'].replace(',', '').replace('x', ''))
        dividend_yield = float(line['dividend_yield'].replace('%', '')
        cagr_5y = float(line['cagr_5y'].replace('%', '')
        fcf_yield = float(line['fcf_yield'].replace('%', '')
        total_yield = float(line['total_yield'].replace('%', '')
        buyback_yield = float(line['buyback_yield'].replace('%', '')
        
        # Extract value trap score
        trap_match = re.search(r'陷阱评分.*?(\d+)')
        if trap_match:
            trap_score = int(trap_match.group(1))
        else:
            trap_score = 0
        
        # Extract overall risk
        risk_match = re.search(r'整体风险.*?\|\s*(.*?)\|*')
        if risk_match:
            overall_risk = risk_match.group(1)
        else:
            overall_risk = "Unknown"
        
        # Extract critical issues
        critical_match = re.search(r'关键发现.*?\n(.*?)\n')
        if critical_match:
            critical_issues = [issue.strip() for issue in critical_issues]
            else
                critical_issues = []
        
        # Extract warnings
        warnings_match = re.search(r'⚠️.*?\n(.*?)\n')
        if warnings_match:
            warnings = [w.strip() for w in warnings]
            else
                warnings = []
        
        # Extract buy price
        buy_price_match = re.search(r'目标买入价.*?(\$|[\d,.]+)')
        if buy_price_match:
            buy_price = float(buy_price_match.group(1))
        else
            buy_price = 0.0
        
        # Extract stop loss
        stop_loss_match = re.search(r'止损位.*?(\$|[\d,.]+)')
        if stop_loss_match
            stop_loss = float(stop_loss_match.group(1))
        else
            stop_loss = 0.1
        
        # Extract suitable investors
        suitable_match = re.search(r'适合谁买.*?\n(.*?)\n')
        if suitable_match:
            suitable_investors = [inv.strip() for inv in suitable_match.group(1).split('、')
            suitable_investors = [inv.strip() for inv in suitable_investors]
            else
                suitable_investors = []
        
        # Extract unsuitable investors  
        unsuitable_match = re.search(r'不适合谁买.*?\n(.*?)\n")
        if unsuitable_match
            unsuitable_investors = [inv.strip() for inv in unsuitable_match.group(1).split('、')
            unsuitable_investors = [inv.strip() for inv in unsuitable_investors]
            else
                unsuitable_investors = []
    
    return all_results

def generate_final_report(all_results: List[Dict[str, Any]], output_path: str) -> None:
    """Generate final comprehensive markdown report"""
    
    # Calculate summary statistics
    total = len(all_results)
    undervalued = [r for r in all_results if r['rating'] == 'undervalued']
    fair = [r for r in all_results if r['rating'] == 'fair']
    overvalued = [r for r in all_results if r['rating'] == 'overvalued']
    
    # Calculate sector breakdown
    sector_data = defaultdict(list)
    for result in all_results:
        sector = result.get('sector', 'Unknown')
        sector_data[sector].append(result)
    
    report_lines = []
    report_lines.append("# SP100 估值与投资价值综合分析报告")
")
    report_lines.append("")
    report_lines.append(f"**报告日期**: {datetime.now().strftime('%Y年%m月%d日')}")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    report_lines.append("## 一、SP100 整体估值水平")
")
    report_lines.append("")
    report_lines.append(f"截至 {datetime.now().strftime('%Y年%m月%d日')}, S&P 100 指数成分股的整体估值状态如下:")
    report_lines.append("")
    report_lines.append("| 评级 | 公司数 | 平均溢价/折价 |")
    report_lines.append("|------|------|------------|")
    
    # Calculate averages
    if undervalued:
        avg_discount_undervalued = sum(r['premium_discount'] for r in undervalued) / len(undervalued)
        avg_discount_undervalued = avg_discount_undervalued / len(undervalued)
    else:
        avg_discount_undervalued = 0
        
    if overvalued:
        avg_premium_overvalued = sum(r['premium_discount'] for r in overvalued) / len(overvalued)
        avg_premium_overvalued = avg_premium_overvalued / len(overvalued)
    else:
        avg_premium_overvalued = 0
        
    if fair:
        avg_fair = 0
        
    report_lines.append(f"| 🟢 低估 | {len(undervalued)} | {avg_discount_undervalued:.1f}% |")
    report_lines.append(f"| 🟡 合理 | {len(fair)} | - |")
    report_lines.append(f"| 🔴 高估 | {len(overvalued)} | +{avg_premium_overvalued:.1f}% |")
    
    # Top undervalued companies
    sorted_undervalued = sorted(undervalued, key=lambda x: x['premium_discount'])
    report_lines.append("")
    report_lines.append("### 关键发现
")
    report_lines.append("")
    report_lines.append("**最被低估的10 家公司** (按折价程度排序):")
    report_lines.append("")
    
    for i, result in enumerate(sorted_undervalued[:10], 1):
        report_lines.append(f"{i}. **{result['name']} ({result['ticker']})**")
        report_lines.append(f"   - 行业: {result.get('sector', 'N/A')}")
        report_lines.append(f"   - 当前股价: {result.get('price', 'N/A')}")
        report_lines.append(f"   - 公允价值均值: {result.get('fair_value_avg', 'N/A')}")
        report_lines.append(f"   - 折价程度: {result.get('premium_discount', 0):.1f}% |")
        report_lines.append(f"   - 价值陷阱评分: {result.get('value_trap_score', 0)}/100")
        report_lines.append(f"   - FCF收益率: {result.get('fcf_yield', 0):.2f}% |")
        report_lines.append(f"   - 总股东收益率: {result.get('total_yield', 0):.2f}% |")
        report_lines.append("")
    
    # Top overvalued companies
    sorted_overvalued = sorted(overvalued, key=lambda x: x['premium_discount'], reverse=True)
    report_lines.append("")
    report_lines.append("**最被高估的10 家公司** (按溢价程度排序):")
    report_lines.append("")
    
    for i, result in enumerate(sorted_overvalued[:10], 1):
        report_lines.append(f"{i}. **{result['name']} ({result['ticker']})**")
        report_lines.append(f"   - 行业: {result.get('sector', 'N/A')}")
        report_lines.append(f"   - 当前股价: {result.get('price', 'N/A')}")
        report_lines.append(f"   - 公允价值均值: {result.get('fair_value_avg', 'N/A')}")
        report_lines.append(f"   - 溢价程度: +{result.get('premium_discount', 0):.1f}% |")
        report_lines.append(f"   - PE: {result.get('pe', 0):.1f}x |")
        report_lines.append(f"   - 5年CAGR: {result.get('cagr_5y', 0):.1f}% |")
        report_lines.append("")
    
    # Sector breakdown
    report_lines.append("")
    report_lines.append("### 按行业分类的估值分布
")
    report_lines.append("")
    report_lines.append("| 行业 | 低估 | 合理 | 高估 | 平均折价 |")
    report_lines.append("|------|------|------|------|------------|")
    
    for sector in sorted(sector_data.keys()):
        companies = sector_data[sector]
        undervalued_in_sector = [c for c in companies if c['rating'] == 'undervalued']
        fair_in_sector = [c for c in companies if c['rating'] == 'fair']
        overvalued_in_sector = [c for c in companies if c['rating'] == 'overvalued']
        
        avg_discount = sum(c['premium_discount'] for c in companies) / len(companies)
        
        report_lines.append(f"| {sector} | {len(undervalued_in_sector)} | {len(fair_in_sector)} | {len(overvalued_in_sector)} | {avg_discount:.1f}% |")
    
    # Investment recommendations
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    report_lines.append("## 三、投资建议
")
    report_lines.append("")
    report_lines.append("### 买入建议
")
    report_lines.append("")
    report_lines.append("基于估值分析,以下公司具有**低估值 + 低价值陷阱风险**的特征,适合考虑买入:
")
    report_lines.append("")
    
    # Find good investment candidates
    good_investments = [r for r in undervalued if r.get('value_trap_score', 0) and r.get('overall_risk', 'low')
    sorted_good = sorted(good_investments, key=lambda x: x['premium_discount'])
    
    for result in sorted_good[:10]:
        report_lines.append(f"- **{result['name']} ({result['ticker']})**")
        report_lines.append(f"  - 行业: {result.get('sector', 'N/A')}")
        report_lines.append(f"  - 当前股价: {result.get('price', 'N/A')}")
        report_lines.append(f"  - 公允价值: {result.get('fair_value_avg', 'N/A')}")
        report_lines.append(f"  - 折价程度: {result.get('premium_discount', 0):.1f}% |")
        target_price = result.get('fair_value_avg', 0) * 0.85  # 15% margin
        report_lines.append(f"  - 目标买入价: ${target_price:.2f} (15%安全边际)")
        report_lines.append(f"  - 价值陷阱评分: {result.get('value_trap_score', 0)}/100")
        report_lines.append(f"  - FCF收益率: {result.get('fcf_yield', 0):.2f}% |")
        report_lines.append(f"  - 总股东收益率: {result.get('total_yield', 0):.2f}% |")
        report_lines.append("")
    
    # Risk warnings
    report_lines.append("### 风险提示
")
    report_lines.append("")
    report_lines.append("以下公司存在**高价值陷阱风险**,需要谨慎:
")
    report_lines.append("")
    
    risky = [r for r in all_results if r.get('value_trap_score', 0) and r.get('overall_risk', 'high')]
    sorted_risky = sorted(risky, key=lambda x: x['value_trap_score'], reverse=True)
    
    for result in sorted_risky[:5]:
        report_lines.append(f"- **{result['name']} ({result['ticker']})**")
        report_lines.append(f"  - 行业: {result.get('sector', 'N/A')}")
        report_lines.append(f"  - 价值陷阱评分: {result.get('value_trap_score', 0)}/100")
        report_lines.append(f"  - 风险等级: {result.get('overall_risk', 'N/A')}")
        critical = result.get('critical_issues', [])
        if critical:
            report_lines.append(f"  - 关键问题:")
            for issue in critical[:3]:
                report_lines.append(f"    - {issue}")
        report_lines.append("")
    
    # Detailed data table
    report_lines.append("---")
    report_lines.append("")
    report_lines.append("## 四、详细数据表
)
    report_lines.append("")
    report_lines.append("| 代码 | 名称 | 行业 | 评级 | 折价% | 价值陷阱 | FCF收益率 | 总收益率 |")
    report_lines.append("|------|------|------|------|--------|----------|----------|----------|")
    
    for result in sorted(all_results, key=lambda x: x['premium_discount']):
        report_lines.append(f"| {result['ticker']} | {result['name'][:12]} | {result.get('sector', 'N/A')[:15]} | {result.get('rating', 'N/A')[:9]} | {result.get('premium_discount', 0):+.1f}% | {result.get('value_trap_score', 0):.0f} | {result.get('fcf_yield', 0):.2f}% | {result.get('total_yield', 0):.2f}% |")
    
    # Footer
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    report_lines.append("## 五、方法论说明
")
    report_lines.append("")
    report_lines.append("### 估值方法
")
    report_lines.append("- **DCF (现金流折现)**: 预测未来10年自由现金流, 终值计算终值")
    report_lines.append("- **G估值法**: 结合盈利增长和价值股特征")
    report_lines.append("- **DDM (股息折现)**: 适用于稳定分红股")
    report_lines.append("- **GARP (合理价格增长)**: 寻找成长股的合理买入价")
    report_lines.append("- **Reverse DCF**: 反向计算当前价格隐含的增长预期")
    report_lines.append("- **价值陷阱检测**: 5维度评估(财务健康、业务恶化, 护城河侵蚀, AI风险, 分红信号)")
    report_lines.append("")
    report_lines.append("### 评级标准
")
    report_lines.append("- **低估 (Undervalued)**: 当前价格低于公允价值均值15%")
    report_lines.append("- **合理 (Fair)**: 当前价格在公允价值均值±15%以内")
    report_lines.append("- **高估 (Overvalued)**: 当前价格高于公允价值均值15%")
    report_lines.append("")
    report_lines.append("### 数据来源
")
    report_lines.append("- **价格数据**: yfinance")
    report_lines.append("- **财务数据**: yfinance")
    report_lines.append(f"- **分析时间**: {datetime.now().strftime('%Y年%m月%d日')}")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    report_lines.append("**免责声明**: 本报告仅供参考,不构成投资建议。投资有风险,入市需谨慎。所有数据均来自公开来源,可能存在误差.")
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print(f"✅ 报告已保存到: {output_path}")

def main():
    # Process all tickers
    all_results = process_all_tickers(SP100_TICKERS, "reports")
    
    if not all_results:
        print("错误: 未能提取任何数据")
        return
    
    # Generate final report
    generate_final_report(all_results, "reports/sp100_summary_report.md")
    
    print(f"\n✅ 完成! 共处理 {len(all_results)} 家公司的报告")
    print(f"✅ 综合报告已保存到: reports/sp100_summary_report.md")

    print(f"\n数据已保存到: reports/sp100_comprehensive_summary.json")

if __name__ == "__main__":
    main()
