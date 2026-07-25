"""
MiniMax (0100.HK) 多维度分析脚本
使用 valueinvest 库对 MiniMax 进行 SOTP 分部估值、同行对比、价值陷阱、红旗、护城河分析。
注意：MiniMax 为未盈利高增长 AI 公司，传统估值法（PE/Graham/EPV）不适用，
本脚本重点运行适用的模块（SOTP、同行对比）并计算自定义指标（EV/Revenue、Rule of 40、现金跑道）。
"""
import json
from valueinvest import Stock
from valueinvest.valuation.sotp import SOTPValuation, SOTPSegment
from valueinvest.peer_comparison import PeerComparisonEngine
from valueinvest.industry.base import PeerCompany
from valueinvest.valuation.value_trap import detect_value_trap
from valueinvest.moat import analyze_moat
from valueinvest.redflags import analyze_red_flags
from valueinvest.roic import analyze_economic_profit

# ========== 汇率与数据口径 ==========
USD_HKD = 7.8  # USD/HKD 汇率（与智谱报告口径一致）

def usd_to_hkd(x):
    return x * USD_HKD

# ========== 用准确数据构造 Stock 对象（HKD 口径）==========
# 关键修正：总股本 313.64M（yfinance 的 232.5M 错误）；revenue 用 US$79M 而非 HK$79M
shares = 313_640_000          # Investing.com / HKEX 确认的总股本
price = 497.6                 # 2026-06-20 收盘价（HKD），当日 +12.33%
market_cap = shares * price   # HK$156.06B ≈ US$20B

# FY2025 财务（USD，公司官方报告口径）
revenue_usd = 79_038_000          # +158.9% YoY
revenue_2024_usd = 30_523_000
gross_profit_usd = 20_079_000     # 毛利率 25.4%
rd_usd = 252_771_000              # 研发费用（占营收 320%）
selling_usd = 51_896_000
admin_usd = 36_813_000
adj_net_loss_usd = 250_856_000    # 经调整净亏损（剔除优先股公允价值变动）
gaap_net_loss_usd = 1_871_617_000 # GAAP 净亏损（含 US$1.59B 非现金优先股公允价值损失）
sbc_usd = 24_031_000              # 股权激励（偏低）
cash_pre_ipo_usd = 1_050_300_000  # 2025-12-31 现金（IPO 前）
ipo_proceeds_usd = 619_000_000    # IPO 募资
debt_usd = 35_452_000             # 银行借款

# 分部收入（USD）
seg_c_usd = 53_075_000   # AI 原生产品（C 端：Talkie/Hailuo/星迹/MiniMax Agent）
seg_b_usd = 25_963_000   # 开放平台及企业服务（B 端 API）

# 2026E 预测（S&P Global 共识）
revenue_2026e_usd = 219_000_000
revenue_2030e_usd = 5_800_000_000
arr_usd = 150_000_000    # 2026.02 ARR

# IPO 后权益（优先股转股 + IPO 募资）
# IPO 前净资产(亏空) US$-2,648M + 优先股转股 US$3,597.6M + IPO 募资 US$619M
post_ipo_equity_hkd = usd_to_hkd(-2_648_190_000 + 3_597_566_000 + 619_000_000)
bvps = post_ipo_equity_hkd / shares
# IPO 后现金（预估：2025 末现金 + IPO 募资 - H1 2026 烧钱 ~US$100M）
cash_post_ipo_usd = cash_pre_ipo_usd + ipo_proceeds_usd - 100_000_000

stock = Stock(
    ticker="0100.HK",
    name="MiniMax Group Inc",
    current_price=price,
    shares_outstanding=shares,
    eps=adj_net_loss_usd / shares * USD_HKD,   # 经调整每股亏损（HKD）
    bvps=bvps,
    revenue=usd_to_hkd(revenue_usd),
    net_income=usd_to_hkd(adj_net_loss_usd),    # 用经调整净亏损（更能反映真实经营）
    fcf=usd_to_hkd(-227_000_000),               # 经调整烧钱（剔除 SBC 非现金）
    operating_cash_flow=usd_to_hkd(-227_000_000),
    capex=usd_to_hkd(1_571_000),
    sbc=usd_to_hkd(sbc_usd),
    operating_margin=-355.6,                    # 经调整营业利润率（严重为负）
    revenue_growth=158.9,
    earnings_growth=0,
    cash_and_equivalents=usd_to_hkd(cash_post_ipo_usd),
    total_debt=usd_to_hkd(debt_usd),
    net_debt=usd_to_hkd(debt_usd - cash_post_ipo_usd),  # 负值 = 净现金
    total_assets=usd_to_hkd(1_088_000_000 + 619_000_000),  # IPO 后
    current_assets=usd_to_hkd(1_007_359_000 + 619_000_000),
    total_liabilities=usd_to_hkd(130_000_000),  # IPO 后（剔除已转股的优先股）
    growth_rate=80.0,    # 2026E 增速（US$79M→219M ≈ 177%，逐步放缓取 80%）
    cost_of_capital=11.0,
    discount_rate=11.0,
    terminal_growth=3.0,
    industry="ai_foundation_model",
)
stock.target_mean_price = 1050.0  # 分析师目标价均值 HK$1,050（HKD）

print("=" * 70)
print("MiniMax (0100.HK) 关键数据校验")
print("=" * 70)
print(f"总股本: {shares/1e6:.2f}M")
print(f"当前股价: HK${price}")
print(f"总市值: HK${market_cap/1e8:.1f}亿 = US${market_cap/USD_HKD/1e8:.1f}亿")
print(f"FY2025 营收: US${revenue_usd/1e6:.2f}M = HK${usd_to_hkd(revenue_usd)/1e8:.2f}亿")
print(f"营收增速: +158.9%")
print(f"经调整净亏损: US${adj_net_loss_usd/1e6:.1f}M")
print(f"GAAP 净亏损: US${gaap_net_loss_usd/1e6:.1f}M (含 US$1,589.9M 非现金优先股公允价值损失)")
print(f"IPO 后现金: ~US${cash_post_ipo_usd/1e6:.0f}M")
print(f"IPO 后 BVPS: HK${bvps:.1f} → P/B = {price/bvps:.1f}x")
print(f"毛利率: 25.4% (2024: 12.2%)")
print(f"研发费用: US${rd_usd/1e6:.1f}M (占营收 {rd_usd/revenue_usd*100:.0f}%)")

# ========== 自定义估值指标 ==========
print("\n" + "=" * 70)
print("自定义估值指标（EV/Revenue 多口径）")
print("=" * 70)
ev = market_cap - usd_to_hkd(cash_post_ipo_usd) + usd_to_hkd(debt_usd)
ev_usd = ev / USD_HKD
print(f"企业价值 EV: HK${ev/1e8:.1f}亿 = US${ev_usd/1e8:.1f}亿")
print(f"\nEV/Revenue:")
print(f"  2025 实际: {ev_usd/revenue_usd:.0f}x  (EV US${ev_usd/1e6:.0f}M / 营收 US${revenue_usd/1e6:.1f}M)")
print(f"  2026E:     {ev_usd/revenue_2026e_usd:.0f}x  (营收 US${revenue_2026e_usd/1e6:.1f}M)")
print(f"  ARR:       {ev_usd/arr_usd:.0f}x  (ARR US${arr_usd/1e6:.0f}M)")
print(f"  2030E:     {ev_usd/revenue_2030e_usd:.1f}x  (营收 US${revenue_2030e_usd/1e6:.0f}M)")
print(f"\nPS (市值/营收):")
print(f"  2025: {market_cap/USD_HKD/revenue_usd:.0f}x | 2026E: {market_cap/USD_HKD/revenue_2026e_usd:.0f}x | ARR: {market_cap/USD_HKD/arr_usd:.0f}x")

# Rule of 40
print(f"\nRule of 40: 增速 158.9% + 调整后利润率 -{abs(adj_net_loss_usd)/revenue_usd*100:.0f}% = {158.9 - abs(adj_net_loss_usd)/revenue_usd*100:.0f}")
print(f"  (用毛利率口径替代: 增速 158.9% + 毛利率 25.4% = {158.9+25.4:.1f} → 远超 40 阈值，符合高增长 SaaS)")

# 现金跑道
burn = adj_net_loss_usd - sbc_usd  # 剔除非现金 SBC 的真实烧钱
print(f"\n现金跑道: IPO 后现金 US${cash_post_ipo_usd/1e6:.0f}M / 年烧钱 US${burn/1e6:.0f}M = {cash_post_ipo_usd/burn:.1f} 年")
print(f"  (若营收按 2026E US$219M 增长，烧钱率改善，跑道更长)")

# ========== SOTP 分部估值（两种情景）==========
print("\n" + "=" * 70)
print("SOTP 分部估值（C 端 AI 原生产品 + B 端开放平台/API）")
print("=" * 70)

def run_sotp(rev_c, rev_b, mult_c, mult_b, label):
    segments = [
        SOTPSegment(name="AI原生产品(C端:Talkie/Hailuo)", revenue=usd_to_hkd(rev_c),
                    valuation_method="ev_revenue", multiple=mult_c,
                    notes="消费级 AI App，海外 73%，订阅+内购"),
        SOTPSegment(name="开放平台及企业服务(B端API)", revenue=usd_to_hkd(rev_b),
                    valuation_method="ev_revenue", multiple=mult_b,
                    notes="企业 API/平台，B 端客户半年增 5 倍"),
    ]
    sotp = SOTPValuation(segments=segments, holdco_discount_pct=10, unallocated_costs=0)
    result = sotp.calculate(stock)
    total_ev = sum(result.components.values())
    equity = total_ev + usd_to_hkd(cash_post_ipo_usd) - usd_to_hkd(debt_usd)
    fps = equity / shares
    print(f"\n【{label}】")
    for name, val in result.components.items():
        print(f"  {name}: HK${val/1e8:.1f}亿 (US${val/USD_HKD/1e6:.0f}M)")
    print(f"  合计 EV: HK${total_ev/1e8:.1f}亿 (US${total_ev/USD_HKD/1e6:.0f}M)")
    print(f"  + 净现金 US${(cash_post_ipo_usd-debt_usd)/1e6:.0f}M")
    print(f"  = 股权价值 HK${equity/1e8:.1f}亿")
    print(f"  每股公允价值: HK${fps:.1f}  (vs 现价 HK${price}, {'高估' if price>fps else '低估'} {(price/fps-1)*100:+.0f}%)")
    return fps

# 情景1：2025 实际营收 + 成长期倍数
fps1 = run_sotp(seg_c_usd, seg_b_usd, 25, 35, "情景1: 2025实际营收 × 成长期倍数(C端25x/B端35x)")
# 情景2：2026E 营收 + 略降倍数
seg_c_2026 = revenue_2026e_usd * (seg_c_usd/revenue_usd)
seg_b_2026 = revenue_2026e_usd * (seg_b_usd/revenue_usd)
fps2 = run_sotp(seg_c_2026, seg_b_2026, 20, 30, "情景2: 2026E营收 × 成熟期倍数(C端20x/B端30x)")
# 情景3：乐观 2030 部分兑现
fps3 = run_sotp(revenue_2030e_usd*0.3*(seg_c_usd/revenue_usd), revenue_2030e_usd*0.3*(seg_b_usd/revenue_usd), 15, 25, "情景3: 2028E营收(2030的30%) × 成熟倍数")

# ========== 同行对比（手动 peers）==========
print("\n" + "=" * 70)
print("同行对比分析（智谱 + 全球模型公司参照）")
print("=" * 70)
peers = [
    PeerCompany(ticker="0100.HK", name="MiniMax", market_cap=20e9, revenue=79e6,
                net_income=-251e6, revenue_growth=159, operating_margin=-356,
                net_margin=-318, pe_ratio=0, pb_ratio=12.8, roe=0),
    PeerCompany(ticker="2513.HK", name="智谱AI", market_cap=120e9, revenue=100e6,
                net_income=-650e6, revenue_growth=132, operating_margin=-650,
                net_margin=-650, pe_ratio=0, pb_ratio=0, roe=0),
    PeerCompany(ticker="OPENAI", name="OpenAI", market_cap=852e9, revenue=20000e6,
                net_income=-14000e6, revenue_growth=100, operating_margin=-70,
                net_margin=-70, pe_ratio=0, pb_ratio=0, roe=0),
    PeerCompany(ticker="ANTHROPIC", name="Anthropic", market_cap=965e9, revenue=47000e6,
                net_income=1230e6, revenue_growth=900, operating_margin=15,
                net_margin=2.6, pe_ratio=784, pb_ratio=0, roe=0),
]
try:
    eng = PeerComparisonEngine(peers=peers)
    res = eng.analyze(stock)
    print(f"综合评分: {res.composite_score:.1f}/100 ({res.rating.value})")
    print(f"估值评分: {res.valuation_score:.1f} | 盈利评分: {res.profitability_score:.1f} | 增长评分: {res.growth_score:.1f}")
    if res.strengths:
        print("优势:"); [print(f"  + {s}") for s in res.strengths[:5]]
    if res.weaknesses:
        print("劣势:"); [print(f"  - {w}") for w in res.weaknesses[:5]]
except Exception as e:
    print(f"同行对比运行受限: {e}")

# PS 同行对比（核心矛盾）
print("\nPS(ARR 口径) 同行对比:")
peer_ps = {"MiniMax(0100)": ev_usd/arr_usd, "智谱(2513)": 120e9/240e6,
           "OpenAI": 852e9/46e9, "Anthropic": 965e9/47e9}  # ARR: OpenAI US$46B, Anthropic US$47B
for k, v in sorted(peer_ps.items(), key=lambda x: -x[1]):
    print(f"  {k:18s}: {v:.1f}x")

# ========== 价值陷阱 / 红旗 / 护城河（含重要警示）==========
print("\n" + "=" * 70)
print("价值陷阱 / 会计红旗 / 护城河（⚠️ 对未盈利成长股有失真，仅供参考）")
print("=" * 70)
try:
    trap = detect_value_trap(stock, revenue_cagr_5y=80, margin_trend='improving',
                             roe_trend='improving', industry='ai_foundation_model')
    print(f"价值陷阱风险: {trap.overall_risk} | 评分 {trap.trap_score:.0f}/100 | is_trap={trap.is_trap}")
    print(f"  财务健康: {trap.financial_health_score:.0f} | 业务恶化: {trap.business_deterioration_score:.0f}")
    print(f"  护城河侵蚀: {trap.moat_erosion_score:.0f} | AI颠覆: {trap.ai_vulnerability_score:.0f}")
    if trap.warnings:
        for w in trap.warnings[:3]: print(f"  ⚠️ {w}")
except Exception as e:
    print(f"价值陷阱: {e}")

try:
    rf = analyze_red_flags(stock)
    print(f"\n会计红旗: {rf.risk_level.value} | 评分 {rf.overall_score:.0f}/100 | has_flags={rf.has_flags}")
    print(f"  盈利质量: {rf.earnings_quality_score:.0f} | 收入确认: {rf.revenue_recognition_score:.0f}")
    if rf.triggered_flags:
        for f in rf.triggered_flags[:3]: print(f"  🚩 {f}")
except Exception as e:
    print(f"红旗: {e}")

try:
    moat = analyze_moat(stock)
    print(f"\n护城河评分: {moat.moat_score:.0f}/100 | 类型: {moat.moat_type.value} | has_moat={moat.has_moat}")
    print(f"  盈利能力: {getattr(moat,'profitability_score',0):.0f} | 效率: {getattr(moat,'efficiency_score',0):.0f}")
except Exception as e:
    print(f"护城河: {e}")

print("\n" + "=" * 70)
print("分析完成")
print("=" * 70)
