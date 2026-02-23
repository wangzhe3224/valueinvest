"""
Enhanced report generator with news analysis.

Generates comprehensive reports combining valuation and news sentiment.
"""
from typing import List, Optional
from datetime import datetime

from ..stock import Stock
from ..stock import StockHistory
from ..valuation.base import ValuationResult
from ..news.base import NewsAnalysisResult, Guidance, AnalystRating


class EnhancedReporter:
    """Generate enhanced reports with news sentiment analysis."""
    
    def render(
        self,
        stock: Stock,
        history: Optional[StockHistory],
        valuation_results: List[ValuationResult],
        news_analysis: Optional[NewsAnalysisResult] = None,
        company_type: str = "general",
        history_period: str = "5y",
    ) -> str:
        """Generate comprehensive analysis report."""
        lines = []
        
        valid_results = [
            r for r in valuation_results 
            if r.fair_value and r.fair_value > 0 and "Error" not in r.assessment
        ]
        
        lines.append("=" * 70)
        lines.append(f"{stock.name} ({stock.ticker}) - 投资分析报告")
        lines.append("=" * 70)
        
        lines.extend(self._company_overview(stock, company_type))
        lines.extend(self._financial_data(stock))
        
        if history and history.prices:
            lines.extend(self._historical_performance(history, history_period))
        
        if news_analysis and news_analysis.news:
            lines.extend(self._news_analysis_section(news_analysis))
        
        if news_analysis and news_analysis.has_guidance:
            lines.extend(self._guidance_section(news_analysis))
        
        lines.extend(self._valuation_section(valid_results, stock))
        lines.extend(self._conclusion_section(valid_results, stock, news_analysis))
        
        return "\n".join(lines)
    
    def _company_overview(self, stock: Stock, company_type: str) -> List[str]:
        lines = []
        lines.append("")
        lines.append("【公司概况】")
        lines.append(f"  公司: {stock.name}")
        lines.append(f"  代码: {stock.ticker}")
        lines.append(f"  类型: {self._get_type_label(company_type)}")
        lines.append(f"  当前股价: ¥{stock.current_price:.2f}")
        
        if stock.shares_outstanding:
            market_cap = stock.current_price * stock.shares_outstanding / 1e8
            lines.append(f"  总市值: ¥{market_cap:.0f}亿")
        
        return lines
    
    def _financial_data(self, stock: Stock) -> List[str]:
        lines = []
        lines.append("")
        lines.append("【最新财务数据】")
        
        if stock.revenue:
            lines.append(f"  营业收入: ¥{stock.revenue/1e8:.0f}亿")
        if stock.net_income:
            lines.append(f"  净利润: ¥{stock.net_income/1e8:.0f}亿")
        
        lines.append(f"  每股收益 (EPS): ¥{stock.eps:.2f}")
        lines.append(f"  每股净资产 (BVPS): ¥{stock.bvps:.2f}")
        lines.append(f"  市盈率 (PE): {stock.pe_ratio:.1f}倍")
        lines.append(f"  市净率 (PB): {stock.pb_ratio:.2f}倍")
        
        if stock.dividend_yield and stock.dividend_yield > 0:
            lines.append(f"  股息率: {stock.dividend_yield:.2f}%")
        
        if stock.roe:
            lines.append(f"  ROE: {stock.roe:.1f}%")
        
        return lines
    
    def _historical_performance(
        self, 
        history: StockHistory, 
        period: str
    ) -> List[str]:
        lines = []
        lines.append("")
        lines.append(f"【历史表现 ({period})】")
        lines.append(f"  股价CAGR (qfq): {history.cagr:.2f}%")
        
        if history.cagr_hfq != 0:
            lines.append(f"  真实回报 (hfq): {history.cagr_hfq:.2f}%")
        
        lines.append(f"  年化波动率: {history.volatility:.2f}%")
        lines.append(f"  最大回撤: {history.max_drawdown:.2f}%")
        
        stats = history.get_price_stats(days=30, adjust="qfq")
        if stats:
            lines.append("")
            lines.append("【近30日价格 (QFQ)】")
            lines.append(f"  最高: ¥{stats['high']:.2f}")
            lines.append(f"  最低: ¥{stats['low']:.2f}")
            lines.append(f"  均价: ¥{stats['avg']:.2f}")
            lines.append(f"  最新: ¥{stats['latest']:.2f}")
            lines.append(f"  涨跌幅: {stats['change_pct']:+.2f}%")
        
        return lines
    
    def _news_analysis_section(
        self, 
        analysis: NewsAnalysisResult
    ) -> List[str]:
        lines = []
        lines.append("")
        lines.append("=" * 70)
        lines.append("【新闻情感分析】")
        lines.append("=" * 70)
        lines.append("")
        
        sentiment_emoji = {
            "positive": "📈",
            "slightly_positive": "↗️",
            "neutral": "➡️",
            "slightly_negative": "↘️",
            "negative": "📉",
        }
        
        emoji = sentiment_emoji.get(analysis.sentiment_label, "➡️")
        lines.append(f"  情感得分: {emoji} {analysis.sentiment_score:+.2f} ({analysis.sentiment_label})")
        lines.append(f"  分析新闻数: {len(analysis.news)} 条 (7日内: {analysis.news_count_7d})")
        lines.append(f"  正面/负面/中性: {analysis.positive_count}/{analysis.negative_count}/{analysis.neutral_count}")
        lines.append(f"  置信度: {analysis.confidence:.0%}")
        lines.append(f"  趋势: {self._get_trend_label(analysis.sentiment_trend)}")
        
        if analysis.key_themes:
            lines.append("")
            lines.append("【关键主题】")
            for theme in analysis.key_themes[:5]:
                lines.append(f"  • {theme}")
        
        if analysis.risks:
            lines.append("")
            lines.append("【风险提示】")
            for risk in analysis.risks[:5]:
                lines.append(f"  ⚠️ {risk}")
        
        if analysis.catalysts:
            lines.append("")
            lines.append("【潜在催化剂】")
            for catalyst in analysis.catalysts[:5]:
                lines.append(f"  ✅ {catalyst}")
        
        recent_news = sorted(
            analysis.news, 
            key=lambda n: n.publish_date, 
            reverse=True
        )[:5]
        
        if recent_news:
            lines.append("")
            lines.append("【近期重要新闻】")
            for news in recent_news:
                sentiment_mark = "+" if news.is_positive else ("-" if news.is_negative else " ")
                date_str = news.publish_date.strftime("%m-%d")
                lines.append(f"  [{sentiment_mark}] {date_str} {news.title[:40]}...")
        
        return lines
    
    def _guidance_section(self, analysis: NewsAnalysisResult) -> List[str]:
        lines = []
        lines.append("")
        lines.append("【业绩指引与分析师预期】")
        lines.append("")
        
        guidance = analysis.latest_guidance
        
        if guidance:
            header = "| 指标 | 公司指引 | 分析师均值 | 差异 |"
            lines.append(header)
            lines.append("|------|----------|------------|------|")
            
            if guidance.has_company_guidance or guidance.has_analyst_data:
                if guidance.company_eps_low or guidance.analyst_eps_mean:
                    company_eps = self._format_range(
                        guidance.company_eps_low, 
                        guidance.company_eps_high
                    )
                    analyst_eps = f"{guidance.analyst_eps_mean:.2f}" if guidance.analyst_eps_mean else "-"
                    diff = guidance.guidance_vs_consensus
                    diff_label = self._get_diff_label(diff)
                    lines.append(f"| EPS | {company_eps} | {analyst_eps} | {diff_label} |")
                
                if guidance.company_revenue_low or guidance.analyst_revenue_mean:
                    company_rev = self._format_range(
                        guidance.company_revenue_low,
                        guidance.company_revenue_high,
                        suffix="亿"
                    )
                    analyst_rev = f"{guidance.analyst_revenue_mean:.0f}亿" if guidance.analyst_revenue_mean else "-"
                    lines.append(f"| 营收 | {company_rev} | {analyst_rev} | - |")
            
            if guidance.analyst_rating:
                lines.append("")
                lines.append(f"  分析师评级: {self._get_rating_label(guidance.analyst_rating)}")
                
                if guidance.analyst_rating_distribution:
                    dist = guidance.analyst_rating_distribution
                    lines.append(f"  买入/持有/卖出: {dist.get('buy', 0)}/{dist.get('hold', 0)}/{dist.get('sell', 0)}")
            
            if guidance.price_target_mean:
                lines.append(f"  目标价: ¥{guidance.price_target_mean:.2f} (区间: ¥{guidance.price_target_low:.2f}-¥{guidance.price_target_high:.2f})")
        
        return lines
    
    def _valuation_section(
        self,
        results: List[ValuationResult],
        stock: Stock
    ) -> List[str]:
        lines = []
        lines.append("")
        lines.append("=" * 70)
        lines.append("【估值汇总】")
        lines.append("=" * 70)
        lines.append("")
        
        if not results:
            lines.append("  (无有效估值结果)")
            return lines
        
        sorted_results = sorted(results, key=lambda x: x.fair_value)
        
        lines.append("| 方法 | 公允价值 | 溢价/折价 | 评估 |")
        lines.append("|------|----------|-----------|------|")
        
        for r in sorted_results:
            name = r.method[:18]
            lines.append(f"| {name:18} | ¥{r.fair_value:>7.2f} | {r.premium_discount:>+7.1f}% | {r.assessment[:10]:10} |")
        
        fair_values = [r.fair_value for r in results]
        avg_value = sum(fair_values) / len(fair_values)
        median_value = sorted(fair_values)[len(fair_values)//2]
        
        lines.append("")
        lines.append("【统计汇总】")
        lines.append(f"  公允价值范围: ¥{min(fair_values):.2f} - ¥{max(fair_values):.2f}")
        lines.append(f"  平均公允价值: ¥{avg_value:.2f}")
        lines.append(f"  中位数公允价值: ¥{median_value:.2f}")
        
        return lines
    
    def _conclusion_section(
        self,
        results: List[ValuationResult],
        stock: Stock,
        news_analysis: Optional[NewsAnalysisResult] = None,
    ) -> List[str]:
        lines = []
        lines.append("")
        lines.append("=" * 70)
        lines.append("【综合结论】")
        lines.append("=" * 70)
        lines.append("")
        
        if not results:
            lines.append("  (数据不足，无法给出结论)")
            return lines
        
        fair_values = [r.fair_value for r in results]
        avg_value = sum(fair_values) / len(fair_values)
        median_value = sorted(fair_values)[len(fair_values)//2]
        
        conservative = sorted(fair_values)[:max(1, len(fair_values)//3)]
        optimistic = sorted(fair_values)[-max(1, len(fair_values)//3):]
        
        cons_avg = sum(conservative) / len(conservative)
        opt_avg = sum(optimistic) / len(optimistic)
        
        lines.append(f"估值区间: ¥{cons_avg:.0f}-{median_value:.0f} (保守) / ¥{stock.current_price:.0f} (现价) / ¥{opt_avg:.0f}+ (乐观)")
        lines.append("")
        
        avg_premium = ((avg_value - stock.current_price) / stock.current_price) * 100
        
        if avg_premium < -15:
            rating = "低估"
            color = "🟢"
        elif avg_premium > 15:
            rating = "高估"
            color = "🔴"
        else:
            rating = "合理"
            color = "🟡"
        
        sentiment_boost = ""
        if news_analysis:
            if news_analysis.sentiment_score > 0.3:
                sentiment_boost = " + 正面消息"
            elif news_analysis.sentiment_score < -0.3:
                sentiment_boost = " - 负面消息"
        
        lines.append(f"【综合评级】: {color} {rating}{sentiment_boost}")
        lines.append("")
        lines.append("投资建议:")
        
        target_price = median_value * 0.85
        stop_loss = cons_avg * 0.9
        
        lines.append(f"  1. 目标买入价: ¥{target_price:.0f} (15%安全边际)")
        lines.append(f"  2. 止损位: ¥{stop_loss:.0f}")
        
        if news_analysis:
            if news_analysis.sentiment_score > 0.2:
                lines.append(f"  3. 情绪面: 近期消息偏正面，可积极关注")
            elif news_analysis.sentiment_score < -0.2:
                lines.append(f"  3. 情绪面: 近期存在负面消息，谨慎观望")
            else:
                lines.append(f"  3. 情绪面: 消息面中性，按估值操作")
        
        lines.append("")
        
        return lines
    
    def _get_type_label(self, company_type: str) -> str:
        labels = {
            "bank": "银行/金融",
            "dividend": "分红股",
            "growth": "成长股",
            "value": "价值股",
            "general": "一般",
        }
        return labels.get(company_type, "一般")
    
    def _get_trend_label(self, trend: str) -> str:
        labels = {
            "improving": "📈 改善中",
            "deteriorating": "📉 恶化中",
            "stable": "➡️ 稳定",
        }
        return labels.get(trend, trend)
    
    def _get_diff_label(self, diff: str) -> str:
        labels = {
            "above_consensus": "高于预期",
            "below_consensus": "低于预期",
            "in_line": "符合预期",
            "insufficient_data": "-",
        }
        return labels.get(diff, diff)
    
    def _get_rating_label(self, rating: AnalystRating) -> str:
        labels = {
            AnalystRating.STRONG_BUY: "强力买入",
            AnalystRating.BUY: "买入",
            AnalystRating.HOLD: "持有",
            AnalystRating.SELL: "卖出",
            AnalystRating.STRONG_SELL: "强力卖出",
        }
        return labels.get(rating, str(rating.value))
    
    def _format_range(
        self, 
        low: Optional[float], 
        high: Optional[float],
        suffix: str = ""
    ) -> str:
        if low is None and high is None:
            return "-"
        if low is None:
            return f"≤{high:.2f}{suffix}"
        if high is None:
            return f"≥{low:.2f}{suffix}"
        if low == high:
            return f"{low:.2f}{suffix}"
        return f"{low:.2f}-{high:.2f}{suffix}"
