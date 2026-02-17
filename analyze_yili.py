"""
伊利股份 (600887.SH) 价值分析
使用 ValueInvest 框架进行多维度估值分析

数据来源: 2024年年报及2025年一季报
"""

from valueinvest import Stock, ValuationEngine
from valueinvest.reports.reporter import format_report, format_summary


def create_yili_stock() -> Stock:
    """
    创建伊利股份的股票数据对象
    
    关键财务数据 (2024年年报):
    - 营收: 1157.8亿元
    - 归母净利润: 84.53亿元 (剔除商誉减值后115.39亿元)
    - 经营现金流: 217.4亿元
    - 分红: 77.26亿元, 分红比例91.4%
    - ROE: 15.89%
    - 毛利率: 34.03%
    """
    return Stock(
        # 基本信息
        ticker="600887.SH",
        name="伊利股份 / Yili Group",
        exchange="SH",
        currency="CNY",
        
        # 价格和股本
        current_price=26.48,  # 2025年2月13日收盘价
        shares_outstanding=63.25e9,  # 63.25亿股
        
        # 盈利指标 (使用剔除商誉减值后的数据更能反映真实经营能力)
        eps=1.33,  # 摊薄每股收益
        bvps=8.32,  # 每股净资产
        
        # 收入和利润
        revenue=1157.80e9,  # 1157.8亿元
        net_income=84.53e9,  # 84.53亿元
        fcf=180e9,  # 自由现金流估算 (经营现金流217亿 - 资本开支约37亿)
        
        # 资产负债表
        current_assets=42.0e9,  # 流动资产估算
        total_liabilities=75.0e9,  # 总负债估算
        total_assets=119.0e9,  # 总资产估算
        net_debt=15.0e9,  # 净债务估算
        
        # 运营指标
        depreciation=8.0e9,  # 折旧估算
        capex=37.0e9,  # 资本开支估算
        net_working_capital=-5.0e9,  # 营运资本 (负数表示运营效率高)
        operating_margin=9.5,  # 营业利润率 (净利率)
        tax_rate=25.0,  # 企业所得税率
        roe=15.89,  # 净资产收益率
        
        # 增长预期 (成熟企业,低速增长)
        growth_rate=5.0,  # 预期增长率
        growth_rate_1_5=5.0,  # 1-5年增长率
        growth_rate_6_10=3.0,  # 6-10年增长率
        
        # 分红数据 (伊利是高分红股票)
        dividend_per_share=1.22,  # 每股分红 (77.26亿/63.25亿股)
        dividend_yield=4.61,  # 股息率 (1.22/26.48)
        dividend_growth_rate=3.0,  # 分红增长率
        
        # 折现率和资本成本
        china_10y_yield=1.80,  # 中国10年期国债收益率
        aaa_corporate_yield=2.28,  # AAA企业债收益率
        cost_of_capital=9.0,  # 股权成本 (考虑风险溢价)
        discount_rate=9.0,  # 折现率
        terminal_growth=2.5,  # 永续增长率
        
        # 行业分类
        sectors=["Consumer Staples", "Food & Beverage", "Dairy"],
    )


def run_yili_analysis():
    """运行伊利股份的完整估值分析"""
    
    # 创建股票对象
    yili = create_yili_stock()
    
    # 创建估值引擎
    engine = ValuationEngine()
    
    print("=" * 70)
    print("伊利股份 (600887.SH) 价值投资分析报告")
    print("=" * 70)
    print()
    
    # 打印基本信息
    print("【基本信息】")
    print(f"  股票代码: {yili.ticker}")
    print(f"  公司名称: {yili.name}")
    print(f"  当前股价: ¥{yili.current_price:.2f}")
    print(f"  总股本: {yili.shares_outstanding/1e9:.2f}亿股")
    print(f"  总市值: ¥{yili.market_cap/1e9:.2f}亿元")
    print()
    
    print("【财务数据 (2024年)】")
    print(f"  营业收入: ¥{yili.revenue/1e9:.2f}亿元")
    print(f"  净利润: ¥{yili.net_income/1e9:.2f}亿元")
    print(f"  每股收益(EPS): ¥{yili.eps:.2f}")
    print(f"  每股净资产(BVPS): ¥{yili.bvps:.2f}")
    print(f"  净资产收益率(ROE): {yili.roe:.2f}%")
    print(f"  市盈率(P/E): {yili.pe_ratio:.2f}倍")
    print(f"  市净率(P/B): {yili.pb_ratio:.2f}倍")
    print()
    
    print("【分红数据】")
    print(f"  每股分红: ¥{yili.dividend_per_share:.2f}")
    print(f"  股息率: {yili.dividend_yield:.2f}%")
    print(f"  分红比例: {yili.payout_ratio:.1f}%")
    print()
    
    # 运行分红股票估值方法 (伊利是成熟的分红股)
    print("=" * 70)
    print("【估值分析 - 分红股模型】")
    print("=" * 70)
    
    dividend_results = engine.run_dividend(yili)
    print(format_report(dividend_results, "伊利股份 - 分红股估值"))
    
    # 运行成长股估值方法
    print()
    print("=" * 70)
    print("【估值分析 - 成长股模型】")
    print("=" * 70)
    
    growth_results = engine.run_growth(yili)
    print(format_report(growth_results, "伊利股份 - 成长股估值"))
    
    # 运行所有方法
    print()
    print("=" * 70)
    print("【综合估值汇总】")
    print("=" * 70)
    
    all_results = engine.run_all(yili)
    print(format_report(all_results, "伊利股份 - 全方法估值"))
    print(format_summary(all_results))
    
    # 输出汇总统计
    summary = engine.summary(all_results)
    print()
    print("=" * 70)
    print("【投资建议】")
    print("=" * 70)
    print(f"  估值方法数量: {len([r for r in all_results if r.fair_value > 0])}种有效")
    print(f"  公允价值均值: ¥{summary['average_value']:.2f}")
    print(f"  公允价值中位数: ¥{summary['median_value']:.2f}")
    print(f"  估值区间: ¥{summary['min_value']:.2f} - ¥{summary['max_value']:.2f}")
    print(f"  当前价格: ¥{yili.current_price:.2f}")
    print(f"  潜在上涨空间: {summary['average_premium_discount']:+.1f}%")
    print(f"  低估方法数: {summary['undervalued_count']}/{len([r for r in all_results if r.fair_value > 0])}")
    print()
    
    # 投资评级
    if summary['average_value'] > yili.current_price * 1.15:
        rating = "低估 (买入机会)"
    elif summary['average_value'] > yili.current_price * 1.05:
        rating = "合理偏低 (可考虑买入)"
    elif summary['average_value'] < yili.current_price * 0.85:
        rating = "高估 (谨慎)"
    else:
        rating = "合理估值 (持有)"
    
    print(f"  综合评级: {rating}")
    print()
    
    # 适合的投资策略
    print("=" * 70)
    print("【适合的投资策略】")
    print("=" * 70)
    print("""
  1. 股息策略: 伊利承诺70%+分红比例，股息率4%+，适合追求稳定现金流的投资者
  
  2. 价值投资: 作为行业龙头，具有护城河，当前估值合理偏低
  
  3. 防御性配置: 消费必需品，受经济周期影响较小，适合作为防御性持仓
  
  4. 长期持有: 乳制品行业长久期资产，适合长期持有获取分红+温和增长
""")
    
    return all_results


if __name__ == "__main__":
    results = run_yili_analysis()
