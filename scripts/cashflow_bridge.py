#!/usr/bin/env python3
"""收入 → 净利润 → 自由现金流 桥接分析 (Cash Flow Bridge)

把一家公司"钱怎么赚、钱去哪了"拆成两张桥接图 + 两组趋势图:

1. 利润桥 (P&L waterfall):   收入 → COGS → 毛利 → 费用 → 营业利润 → 利息/其他 → 税 → 净利润
2. 现金桥 (Cash waterfall):  净利润 → +D&A → +SBC → ±营运资本及其他 → OCF → -CapEx → FCF
3. 季度趋势:                 收入柱 + 毛利率/营业利润率/净利率三线 (上下两面板, 各一根轴)
4. 年度现金流质量:           净利润/OCF/FCF 分组柱 + SBC 线

用法:
    source valueinvest/.venv/bin/activate
    python valueinvest/scripts/cashflow_bridge.py AVGO                    # 默认 FY 口径
    python valueinvest/scripts/cashflow_bridge.py AVGO --period ttm       # TTM 口径瀑布图
    python valueinvest/scripts/cashflow_bridge.py AVGO --quarters 12 --years 6
    python valueinvest/scripts/cashflow_bridge.py AVGO --out-dir valueinvest-reports/reports/AVGO
    python valueinvest/scripts/cashflow_bridge.py AVGO --debug            # 打印报表可用行项目

输出:
    - JSON 摘要 (桥接表 / 序列 / 质量信号 / 图表路径)
    - 4 张 PNG: pl_bridge / cash_bridge / trend / cash_quality

配色遵循 dataviz 规范 (已通过 validate_palette.js):
    增加=蓝 #2a78d6 · 减少=红 #e34948 · 小计=炭 #52514e · 序列槽位 1-4
"""

import argparse
import datetime
import json
import os
import sys

import numpy as np
import pandas as pd
import yfinance as yf

# ---------------------------------------------------------------- dataviz 规范色板
SURFACE = "#fcfcfb"
INK = "#0b0b0b"          # 主文字
INK_2 = "#52514e"        # 次文字 / 小计柱
MUTED = "#898781"        # 轴标签
GRID = "#e1e0d9"         # 网格 hairline
BASELINE = "#c3c2b7"     # 轴线
BLUE = "#2a78d6"         # 槽位1 / 增加
ORANGE = "#eb6834"       # 槽位2
AQUA = "#1baf7a"         # 槽位3
YELLOW = "#eda100"       # 槽位4
RED = "#e34948"          # 槽位8 / 减少 (diverging 暖极, 已过 validator)

CJK_FONTS = [
    "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei",
    "Noto Sans CJK SC", "Source Han Sans SC", "WenQuanYi Micro Hei",
]


def style_fig(fig, ax_list):
    """统一 chrome: 表面色 / 去边框 / hairline 网格 / muted 轴字。"""
    import matplotlib.pyplot as plt
    for ax in ax_list:
        ax.set_facecolor(SURFACE)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(BASELINE)
        ax.spines["bottom"].set_linewidth(0.8)
        ax.tick_params(colors=MUTED, labelsize=9, length=0)
        ax.yaxis.grid(True, color=GRID, linewidth=0.8)
        ax.xaxis.grid(False)
        ax.set_axisbelow(True)
    fig.set_facecolor(SURFACE)


def setup_fonts():
    import matplotlib
    import matplotlib.font_manager as fm
    available = {f.name for f in fm.fontManager.ttflist}
    picked = [f for f in CJK_FONTS if f in available]
    matplotlib.rcParams["font.family"] = ["sans-serif"]
    matplotlib.rcParams["font.sans-serif"] = picked + ["DejaVu Sans", "Arial"]
    matplotlib.rcParams["axes.unicode_minus"] = False


# ---------------------------------------------------------------- 取数工具
def grab(df: pd.DataFrame, col, names, default=np.nan) -> float:
    """按候选行名依次取值 (十亿级原币), 全部缺失返回 default。"""
    for nm in names:
        if nm in df.index and col in df.columns:
            v = df.loc[nm, col]
            if v == v and v is not None:
                return float(v)
    return default


def col_label(col) -> str:
    d = getattr(col, "date", None)
    if callable(d):
        try:
            return str(d())[:10]
        except TypeError:
            pass
    return str(col)[:10]


# ---------------------------------------------------------------- 桥接构建
def build_pl_bridge(inc: pd.DataFrame, col) -> list:
    """利润桥: 收入 → 净利润。返回 [{label, value(原币), kind, note}]"""
    rev = grab(inc, col, ["Total Revenue"])
    if not np.isfinite(rev):
        return []
    gp = grab(inc, col, ["Gross Profit"])
    cogs = grab(inc, col, ["Cost Of Revenue"])
    op_inc = grab(inc, col, ["Operating Income", "EBIT"])
    pretax = grab(inc, col, ["Pretax Income", "Income Before Tax"])
    tax = grab(inc, col, ["Tax Provision", "Income Tax Expense"])
    ni = grab(inc, col, ["Net Income", "Net Income Common Stockholders"])

    steps = []
    if np.isfinite(gp):
        cogs_v = cogs if np.isfinite(cogs) else rev - gp
        steps += [
            dict(label="营业收入", value=rev, kind="total"),
            dict(label="营业成本", value=-abs(cogs_v), kind="decrease"),
            dict(label="毛利润", value=gp, kind="total"),
        ]
        if np.isfinite(op_inc):
            opex = gp - op_inc  # 插值: 全部经营费用 (研发/销售管理/其他)
            steps += [
                dict(label="经营费用*", value=-abs(opex), kind="decrease",
                     note="研发+销售管理+其他 (插值)"),
            ]
    else:
        # 金融机构等无毛利结构: 退化桥
        steps.append(dict(label="营业收入", value=rev, kind="total"))
        if np.isfinite(op_inc):
            steps.append(dict(label="经营费用", value=-(rev - op_inc), kind="decrease"))
        gp = None

    if np.isfinite(op_inc):
        steps.append(dict(label="营业利润", value=op_inc, kind="total"))
        if np.isfinite(pretax):
            interest_other = pretax - op_inc
            if abs(interest_other) > 1:  # <1 (原币单位亿级阈值) 忽略
                steps.append(dict(label="利息及其他", value=interest_other,
                                  kind="increase" if interest_other > 0 else "decrease"))
        else:
            pretax = op_inc
    if np.isfinite(tax) and tax != 0:
        steps.append(dict(label="所得税", value=-abs(tax), kind="decrease"))
    if np.isfinite(ni):
        steps.append(dict(label="净利润", value=ni, kind="total"))
    return steps


def build_cash_bridge(cf: pd.DataFrame, col, ni: float) -> list:
    """现金桥: 净利润 → FCF。营运资本及其他 = 插值残差, 保证闭合。"""
    ocf = grab(cf, col, ["Operating Cash Flow"])
    if not np.isfinite(ocf):
        return []
    dna = grab(cf, col, ["Depreciation And Amortization", "Reconciled Depreciation"])
    sbc = grab(cf, col, ["Stock Based Compensation"])
    deferred = grab(cf, col, ["Deferred Income Tax", "Deferred Tax"])
    other_nc = grab(cf, col, ["Other Non Cash Items"])
    capex = grab(cf, col, ["Capital Expenditure"])
    fcf = grab(cf, col, ["Free Cash Flow"])
    if not np.isfinite(fcf) and np.isfinite(capex):
        fcf = ocf + capex  # yfinance CapEx 为负值
    capex = -abs(capex) if np.isfinite(capex) else np.nan

    identified = sum(v for v in [dna, sbc, deferred, other_nc] if np.isfinite(v))
    wc_other = ocf - (ni if np.isfinite(ni) else 0) - identified

    steps = []
    if np.isfinite(ni):
        steps.append(dict(label="净利润", value=ni, kind="total"))
    else:
        steps.append(dict(label="经营现金流", value=ocf, kind="total"))
    if np.isfinite(dna) and dna != 0:
        steps.append(dict(label="折旧摊销", value=dna, kind="increase"))
    if np.isfinite(sbc) and sbc != 0:
        steps.append(dict(label="股权激励 SBC", value=sbc, kind="increase"))
    noncash_other = sum(v for v in [deferred, other_nc] if np.isfinite(v))
    if abs(noncash_other) > 1:
        steps.append(dict(label="其他非现金项", value=noncash_other,
                          kind="increase" if noncash_other > 0 else "decrease"))
    if abs(wc_other) > 1:
        steps.append(dict(label="营运资本及其他*", value=wc_other,
                          kind="increase" if wc_other > 0 else "decrease",
                          note="插值: OCF-净利润-已列非现金项"))
    steps.append(dict(label="经营现金流 OCF", value=ocf, kind="total"))
    if np.isfinite(capex) and capex != 0:
        steps.append(dict(label="资本开支 CapEx", value=capex, kind="decrease"))
    if np.isfinite(fcf):
        steps.append(dict(label="自由现金流 FCF", value=fcf, kind="total"))
    return steps


def waterfall_totals(steps: list):
    """为瀑布图计算每步的 (bottom, height) 与累计校验。"""
    out, cum = [], 0.0
    for s in steps:
        if s["kind"] == "total":
            out.append((s["label"], 0.0, s["value"], s))
            cum = s["value"]
        else:
            bottom = cum if s["value"] >= 0 else cum + s["value"]
            out.append((s["label"], bottom, abs(s["value"]), s))
            cum += s["value"]
    return out


# ---------------------------------------------------------------- 序列与信号
def build_series(inc: pd.DataFrame, cf: pd.DataFrame, cols, label_fn) -> list:
    rows = []
    cols = list(cols)[::-1]  # yfinance 列序新在前 → 统一转为时间正序 (旧→新)
    for col in cols:
        rev = grab(inc, col, ["Total Revenue"])
        if not (np.isfinite(rev) and rev):  # 跳过空列 (yfinance 末列常为占位)
            continue
        gp = grab(inc, col, ["Gross Profit"])
        op = grab(inc, col, ["Operating Income", "EBIT"])
        ni = grab(inc, col, ["Net Income", "Net Income Common Stockholders"])
        ocf = grab(cf, col, ["Operating Cash Flow"])
        capex = grab(cf, col, ["Capital Expenditure"])
        sbc = grab(cf, col, ["Stock Based Compensation"])
        fcf = ocf + capex if np.isfinite(ocf) and np.isfinite(capex) else grab(cf, col, ["Free Cash Flow"])
        rows.append(dict(
            period=label_fn(col),
            revenue=rev, gross_profit=gp, operating_income=op, net_income=ni,
            ocf=ocf, capex=(-capex if np.isfinite(capex) else np.nan), fcf=fcf, sbc=sbc,
            gross_margin=gp / rev * 100 if np.isfinite(gp) and rev else np.nan,
            operating_margin=op / rev * 100 if np.isfinite(op) and rev else np.nan,
            net_margin=ni / rev * 100 if np.isfinite(ni) and rev else np.nan,
            ocf_to_ni=ocf / ni * 100 if np.isfinite(ocf) and np.isfinite(ni) and ni else np.nan,
            fcf_to_ni=fcf / ni * 100 if np.isfinite(fcf) and np.isfinite(ni) and ni else np.nan,
            sbc_to_rev=sbc / rev * 100 if np.isfinite(sbc) and rev else np.nan,
        ))
    return rows


def quality_signals(annual_rows: list, q_rows: list) -> list:
    """自动生成质量信号 (中文, 供报告引用)。返回 [{name, value, grade, text}]"""
    sig = []
    if not annual_rows:
        return sig
    latest, prev = annual_rows[-1], annual_rows[-2] if len(annual_rows) > 1 else None

    def grade_ocf_ni(x):
        return "优秀" if x >= 110 else "良好" if x >= 100 else "关注" if x >= 80 else "警报"

    vals = [r["ocf_to_ni"] for r in annual_rows if np.isfinite(r["ocf_to_ni"])]
    if vals:
        x = vals[-1]
        sig.append(dict(name="盈利含金量 OCF/净利润", value=f"{x:.0f}%",
                        grade=grade_ocf_ni(x),
                        text=f"经营现金流为净利润的 {x:.0f}%（5 年区间 {min(vals):.0f}%~{max(vals):.0f}%）。"
                             f"{'净利润完全转化为现金' if x >= 100 else '净利润高于经营现金流，需检查应收/存货/递延项'}"))
    vals = [r["fcf_to_ni"] for r in annual_rows if np.isfinite(r["fcf_to_ni"])]
    if vals:
        x = vals[-1]
        g = "优秀" if x >= 80 else "良好" if x >= 50 else "警惕"
        sig.append(dict(name="FCF/净利润", value=f"{x:.0f}%", grade=g,
                        text=f"自由现金流覆盖净利润 {x:.0f}%，{'利润几乎全部落袋' if x >= 80 else '资本开支或营运资本吞噬了部分利润'}"))
    if np.isfinite(latest.get("sbc_to_rev", np.nan)):
        x = latest["sbc_to_rev"]
        g = "健康" if x < 5 else "关注" if x < 10 else "高" if x < 20 else "严重"
        sig.append(dict(name="SBC/营收", value=f"{x:.1f}%", grade=g,
                        text=f"股权激励占营收 {x:.1f}%，{'稀释压力小' if x < 5 else 'SBC 是隐性费用，True FCF 需扣除'}"))
    vals = [(r["revenue"], r["ocf"], r["capex"]) for r in annual_rows
            if np.isfinite(r["revenue"]) and np.isfinite(r["capex"])]
    if vals:
        capex_ratio = vals[-1][2] / vals[-1][0] * 100
        g = "轻资产" if capex_ratio < 5 else "中等" if capex_ratio < 15 else "重资产"
        sig.append(dict(name="CapEx/营收", value=f"{capex_ratio:.1f}%", grade=g,
                        text=f"资本开支强度 {capex_ratio:.1f}%（{g}模式），重资产模式需更多关注再投资回报"))
    if len(q_rows) >= 6:
        half = len(q_rows) // 2
        for key, cname in [("gross_margin", "毛利率"), ("net_margin", "净利率")]:
            a = [r[key] for r in q_rows[:half] if np.isfinite(r[key])]
            b = [r[key] for r in q_rows[half:] if np.isfinite(r[key])]
            if a and b:
                d = np.mean(b) - np.mean(a)
                direction = "改善" if d > 0.5 else "恶化" if d < -0.5 else "平稳"
                sig.append(dict(name=f"{cname}趋势(近{len(q_rows)}季)", value=f"{d:+.1f}pp", grade=direction,
                                text=f"后 {half} 季均值较前 {half} 季 {direction} {abs(d):.1f}pp"))
        # 背离检测: 最近季 NI YoY vs OCF YoY
        def yoy(rows, key):
            if len(rows) >= 5 and np.isfinite(rows[-1][key]) and np.isfinite(rows[-5][key]) and rows[-5][key]:
                return (rows[-1][key] / abs(rows[-5][key]) - 1) * 100
            return None
        ni_g, ocf_g = yoy(q_rows, "net_income"), yoy(q_rows, "ocf")
        if ni_g is not None and ocf_g is not None and abs(ni_g - ocf_g) > 20:
            worse = ocf_g < ni_g
            sig.append(dict(name="利润-现金流背离", value=f"NI {ni_g:+.0f}% vs OCF {ocf_g:+.0f}%",
                            grade="警报" if worse else "备注",
                            text=f"近 4 季净利润同比 {ni_g:+.0f}% vs 经营现金流 {ocf_g:+.0f}%，"
                                 f"{'现金流跟不上利润，警惕应收/预收/存货质量' if worse else '现金流领先于利润，多为质量正面信号'}"))
    return sig


# ---------------------------------------------------------------- 图表
def plot_waterfall(steps, title, subtitle, path, currency="USD"):
    import matplotlib.pyplot as plt
    setup_fonts()
    bars = waterfall_totals(steps)
    n = len(bars)
    fig, ax = plt.subplots(figsize=(max(7.0, 0.95 * n), 4.6), dpi=150)
    scale = 1e8  # → 亿
    xs = np.arange(n)
    for i, (label, bottom, height, s) in enumerate(bars):
        color = INK_2 if s["kind"] == "total" else (BLUE if s["value"] > 0 else RED)
        ax.bar(i, height / scale, bottom=bottom / scale, width=0.62, color=color,
               edgecolor=SURFACE, linewidth=1.5, zorder=3)
        top = (bottom + height) / scale
        v = s["value"] / scale
        if s["kind"] == "total":
            ax.annotate(f"{v:,.0f}", (i, top), ha="center", va="bottom", fontsize=9,
                        color=INK, fontweight="bold")
        else:
            ax.annotate(f"{v:+,.0f}", (i, top), ha="center", va="bottom", fontsize=8.5,
                        color=color, fontweight="bold")
        pct = s.get("note")
        rev0 = bars[0][2] / scale
        if rev0 and s["kind"] != "total":
            ax.annotate(f"{s['value'] / scale / rev0 * 100:+.1f}%", (i, bottom / scale),
                        ha="center", va="top", fontsize=7.5, color=MUTED)
    # 连接线 (hairline)
    cum = 0.0
    tops = []
    for label, bottom, height, s in bars:
        cum = (bottom + height) if s["kind"] == "total" else bottom + height
        tops.append(cum / scale)
    for i in range(n - 1):
        ax.plot([i + 0.31, i + 1 - 0.31], [tops[i], tops[i]],
                color=BASELINE, linewidth=0.8, zorder=2)
    ax.set_xticks(xs)
    ax.set_xticklabels([b[0] for b in bars], fontsize=9, color=INK_2,
                       rotation=20, ha="right", rotation_mode="anchor")
    ax.axhline(0, color=BASELINE, linewidth=0.8)
    ax.set_ylabel(f"{currency} 亿", fontsize=9, color=MUTED)
    ax.set_title(title, fontsize=12.5, color=INK, fontweight="bold", loc="left", pad=14)
    ax.text(0, 1.015, subtitle, transform=ax.transAxes, fontsize=8.5, color=MUTED)
    style_fig(fig, [ax])
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def plot_trend(q_rows, title, path, currency="USD"):
    import matplotlib.pyplot as plt
    setup_fonts()
    labels = [r["period"][2:] for r in q_rows]  # '26-05-03' 风格缩短
    x = np.arange(len(q_rows))
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9.2, 6.2), dpi=150, sharex=True,
                                   gridspec_kw=dict(height_ratios=[1.15, 1], hspace=0.16))
    scale = 1e8
    rev = [r["revenue"] / scale for r in q_rows]
    ax1.bar(x, rev, width=0.58, color=BLUE, edgecolor=SURFACE, linewidth=1, zorder=3)
    for i, v in enumerate(rev):
        ax1.annotate(f"{v:,.0f}", (i, v), ha="center", va="bottom", fontsize=7.8, color=INK_2)
    ax1.set_ylabel(f"{currency} 亿", fontsize=9, color=MUTED)
    ax1.set_title(title, fontsize=12.5, color=INK, fontweight="bold", loc="left", pad=10)
    series = [("毛利率", "gross_margin", BLUE), ("营业利润率", "operating_margin", ORANGE),
              ("净利率", "net_margin", AQUA)]
    for name, key, color in series:
        ys = [r[key] if np.isfinite(r[key]) else np.nan for r in q_rows]
        ax2.plot(x, ys, color=color, linewidth=2, marker="o", markersize=4.5,
                 markerfacecolor=color, markeredgecolor=SURFACE, markeredgewidth=1,
                 solid_capstyle="round", label=name, zorder=3)
        if ys and np.isfinite(ys[-1]):
            ax2.annotate(f"{ys[-1]:.1f}%", (x[-1], ys[-1]), xytext=(6, 0),
                         textcoords="offset points", va="center", fontsize=8.5,
                         color=color, fontweight="bold")
    ax2.set_ylabel("利润率 %", fontsize=9, color=MUTED)
    ax2.legend(loc="lower right", frameon=False, fontsize=8.5, ncol=3,
               labelcolor=INK_2, handlelength=1.6)
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, fontsize=8.5, color=MUTED)
    style_fig(fig, [ax1, ax2])
    fig.savefig(path, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def plot_cash_quality(annual_rows, path, currency="USD"):
    import matplotlib.pyplot as plt
    setup_fonts()
    labels = [str(r["period"]) for r in annual_rows]
    x = np.arange(len(annual_rows))
    w = 0.26
    fig, ax = plt.subplots(figsize=(8.6, 4.6), dpi=150)
    scale = 1e8
    for off, (name, key, color) in enumerate([
            ("净利润", "net_income", BLUE), ("经营现金流", "ocf", ORANGE), ("自由现金流", "fcf", AQUA)]):
        ys = [r[key] / scale if np.isfinite(r[key]) else np.nan for r in annual_rows]
        ax.bar(x + (off - 1) * w, ys, width=w * 0.92, color=color, edgecolor=SURFACE,
               linewidth=1, label=name, zorder=3)
    sbc = [r["sbc"] / scale if np.isfinite(r["sbc"]) else np.nan for r in annual_rows]
    ax.plot(x, sbc, color=YELLOW, linewidth=2, marker="o", markersize=5,
            markerfacecolor=YELLOW, markeredgecolor=SURFACE, markeredgewidth=1,
            label="SBC", zorder=4)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9, color=MUTED)
    ax.set_ylabel(f"{currency} 亿", fontsize=9, color=MUTED)
    ax.legend(loc="upper left", frameon=False, fontsize=8.5, ncol=4, labelcolor=INK_2)
    style_fig(fig, [ax])
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- 主流程
def fmt_bridge(steps, currency):
    rev = steps[0]["value"] if steps else np.nan
    return [dict(label=s["label"], value_yi=round(s["value"] / 1e8, 1),
                 pct_of_revenue=round(s["value"] / rev * 100, 1)
                 if np.isfinite(rev) and rev and s["kind"] != "total" else None,
                 kind=s["kind"], note=s.get("note")) for s in steps]


def main():
    ap = argparse.ArgumentParser(description="收入→净利润→FCF 桥接分析")
    ap.add_argument("ticker")
    ap.add_argument("--period", choices=["fy", "ttm"], default="fy", help="瀑布图口径")
    ap.add_argument("--quarters", type=int, default=8, help="季度趋势期数")
    ap.add_argument("--years", type=int, default=5, help="年度期数")
    ap.add_argument("--out-dir", default=None, help="PNG 输出目录 (默认 /tmp)")
    ap.add_argument("--json-out", default=None, help="JSON 输出路径 (默认 /tmp)")
    ap.add_argument("--debug", action="store_true", help="打印报表可用行项目")
    args = ap.parse_args()

    t = yf.Ticker(args.ticker)
    ai, acf = t.income_stmt, t.cashflow
    qi, qcf = t.quarterly_income_stmt, t.quarterly_cashflow
    if ai.empty or acf.empty or qi.empty or qcf.empty:
        sys.exit(f"[cashflow_bridge] {args.ticker}: 报表数据不可用")
    if args.debug:
        print("income:", list(ai.index)[:40], file=sys.stderr)
        print("cashflow:", list(acf.index)[:40], file=sys.stderr)

    currency = (t.info or {}).get("financialCurrency", "USD") or "USD"

    # ---- 瀑布图口径
    if args.period == "ttm":
        cols = list(qi.columns[:4])
        cf_cols = list(qcf.columns[:4])
        # TTM: 4 个季度逐项求和后合成桥接
        ni = _ttm_sum(qi, ["Net Income", "Net Income Common Stockholders"], cols)
        pl_steps = _ttm_pl_bridge(qi, cols)
        cash_steps = _ttm_cash_bridge(qcf, cf_cols, ni)
        period_label = f"TTM ({col_label(cols[-1])} ~ {col_label(cols[0])})"
    else:
        col = ai.columns[0]
        cf_col = acf.columns[0]
        pl_steps = build_pl_bridge(ai, col)
        ni = grab(ai, col, ["Net Income", "Net Income Common Stockholders"])
        cash_steps = build_cash_bridge(acf, cf_col, ni)
        fy_end = col_label(col)
        period_label = f"FY 截至 {fy_end}"

    if not pl_steps or not cash_steps:
        sys.exit(f"[cashflow_bridge] {args.ticker}: 桥接构建失败 (试 --debug 查看行项目)")

    # ---- 序列
    q_rows = build_series(qi, qcf, list(qi.columns[:args.quarters]), col_label)
    a_rows = build_series(ai, acf, list(ai.columns[:args.years]), lambda c: getattr(c, "year", str(c)))
    signals = quality_signals(a_rows, q_rows)

    # ---- 图表
    out_dir = args.out_dir or "/tmp"
    os.makedirs(out_dir, exist_ok=True)
    tk = args.ticker.lower().replace(".", "_")
    date_tag = datetime.date.today().strftime("%Y%m%d")
    paths = {
        "pl_bridge": os.path.join(out_dir, f"{tk}_pl_bridge_{date_tag}.png"),
        "cash_bridge": os.path.join(out_dir, f"{tk}_cash_bridge_{date_tag}.png"),
        "trend": os.path.join(out_dir, f"{tk}_cashflow_trend_{date_tag}.png"),
        "cash_quality": os.path.join(out_dir, f"{tk}_cash_quality_{date_tag}.png"),
    }
    plot_waterfall(pl_steps, f"{args.ticker} 利润桥：收入 → 净利润",
                   f"{period_label} · 蓝色=增加 · 红色=减少 · 炭色=小计 · 单位 {currency} 亿",
                   paths["pl_bridge"], currency)
    plot_waterfall(cash_steps, f"{args.ticker} 现金桥：净利润 → 自由现金流",
                   f"{period_label} · 蓝色=非现金加回/现金流入 · 红色=流出 · 单位 {currency} 亿",
                   paths["cash_bridge"], currency)
    plot_trend(q_rows, f"{args.ticker} 季度收入与三级利润率", paths["trend"], currency)
    plot_cash_quality(a_rows, paths["cash_quality"], currency)

    # ---- JSON 摘要
    summary = dict(
        ticker=args.ticker, currency=currency, period=period_label,
        generated=datetime.date.today().isoformat(),
        pl_bridge=fmt_bridge(pl_steps, currency),
        cash_bridge=fmt_bridge(cash_steps, currency),
        quarterly=q_rows, annual=a_rows, signals=signals, charts=paths,
    )
    json_path = args.json_out or f"/tmp/{tk}_cashflow_bridge.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1, default=str)
    print(json.dumps(summary, ensure_ascii=False, indent=1, default=str))
    print(f"\n[cashflow_bridge] 图表: {paths}\n[cashflow_bridge] JSON: {json_path}",
          file=sys.stderr)


# ---- TTM 合成桥 (对 4 个季度逐项求和后复用单期逻辑)
def _ttm_sum(df, names, cols):
    tot, ok = 0.0, False
    for col in cols:
        v = grab(df, col, names)
        if np.isfinite(v):
            tot += v
            ok = True
    return tot if ok else np.nan


def _ttm_pl_bridge(qi, cols):
    rev = _ttm_sum(qi, ["Total Revenue"], cols)
    gp = _ttm_sum(qi, ["Gross Profit"], cols)
    cogs = _ttm_sum(qi, ["Cost Of Revenue"], cols)
    op = _ttm_sum(qi, ["Operating Income", "EBIT"], cols)
    pretax = _ttm_sum(qi, ["Pretax Income", "Income Before Tax"], cols)
    tax = _ttm_sum(qi, ["Tax Provision", "Income Tax Expense"], cols)
    ni = _ttm_sum(qi, ["Net Income", "Net Income Common Stockholders"], cols)
    if not np.isfinite(rev):
        return []
    steps = [dict(label="营业收入", value=rev, kind="total")]
    if np.isfinite(gp):
        steps.append(dict(label="营业成本", value=-(cogs if np.isfinite(cogs) else rev - gp),
                          kind="decrease"))
        steps.append(dict(label="毛利润", value=gp, kind="total"))
        if np.isfinite(op):
            steps.append(dict(label="经营费用*", value=-(gp - op), kind="decrease",
                              note="研发+销售管理+其他 (插值)"))
    elif np.isfinite(op):
        steps.append(dict(label="经营费用", value=-(rev - op), kind="decrease"))
    if np.isfinite(op):
        steps.append(dict(label="营业利润", value=op, kind="total"))
        if np.isfinite(pretax):
            io = pretax - op
            if abs(io) > 1:
                steps.append(dict(label="利息及其他", value=io,
                                  kind="increase" if io > 0 else "decrease"))
    if np.isfinite(tax) and tax != 0:
        steps.append(dict(label="所得税", value=-abs(tax), kind="decrease"))
    if np.isfinite(ni):
        steps.append(dict(label="净利润", value=ni, kind="total"))
    return steps


def _ttm_cash_bridge(qcf, cols, ni):
    ocf = _ttm_sum(qcf, ["Operating Cash Flow"], cols)
    if not np.isfinite(ocf):
        return []
    dna = _ttm_sum(qcf, ["Depreciation And Amortization", "Reconciled Depreciation"], cols)
    sbc = _ttm_sum(qcf, ["Stock Based Compensation"], cols)
    capex = _ttm_sum(qcf, ["Capital Expenditure"], cols)
    identified = sum(v for v in [dna, sbc] if np.isfinite(v))
    wc_other = ocf - (ni if np.isfinite(ni) else 0) - identified
    steps = []
    if np.isfinite(ni):
        steps.append(dict(label="净利润", value=ni, kind="total"))
    if np.isfinite(dna) and dna != 0:
        steps.append(dict(label="折旧摊销", value=dna, kind="increase"))
    if np.isfinite(sbc) and sbc != 0:
        steps.append(dict(label="股权激励 SBC", value=sbc, kind="increase"))
    if abs(wc_other) > 1:
        steps.append(dict(label="营运资本及其他*", value=wc_other,
                          kind="increase" if wc_other > 0 else "decrease",
                          note="插值: OCF-净利润-已列非现金项"))
    steps.append(dict(label="经营现金流 OCF", value=ocf, kind="total"))
    if np.isfinite(capex) and capex != 0:
        steps.append(dict(label="资本开支 CapEx", value=-abs(capex), kind="decrease"))
        fcf = ocf - abs(capex)
        steps.append(dict(label="自由现金流 FCF", value=fcf, kind="total"))
    return steps


if __name__ == "__main__":
    main()
