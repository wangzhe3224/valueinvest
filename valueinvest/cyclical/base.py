"""
Base data classes for cyclical stock analysis.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from datetime import date

if TYPE_CHECKING:
    from valueinvest.stock import Stock

from .enums import (
    CycleType,
    CyclePhase,
    CycleStrength,
    MarketType,
    InvestmentAction,
    InvestmentStrategy,
    IndicatorCategory,
)


@dataclass
class CycleIndicator:
    """周期指标"""

    name: str  # 指标名称
    value: float  # 当前值
    category: IndicatorCategory  # 指标类别
    historical_avg: float = 0.0  # 历史均值
    percentile: float = 50.0  # 历史分位（0-100）
    trend: str = "stable"  # 趋势（"up", "down", "stable"）
    weight: float = 1.0  # 权重
    unit: str = ""  # 单位
    description: str = ""  # 描述
    historical_values: List[float] = field(default_factory=list)  # 历史数据

    @property
    def score(self) -> float:
        """将指标值标准化为 1.0-5.0 分"""
        if self.percentile < 20:
            return 1.0  # 周期底部
        elif self.percentile < 40:
            return 2.0  # 上行初期
        elif self.percentile < 60:
            return 3.0  # 中期
        elif self.percentile < 80:
            return 4.0  # 上行后期
        else:
            return 5.0  # 周期顶点

    @property
    def status(self) -> str:
        """指标状态"""
        if self.percentile < 25:
            return "极低"
        elif self.percentile < 40:
            return "偏低"
        elif self.percentile < 60:
            return "中等"
        elif self.percentile < 75:
            return "偏高"
        else:
            return "极高"


@dataclass
class CycleScore:
    """周期位置评分"""

    total_score: float  # 总分（1.0-5.0）
    phase: CyclePhase  # 周期阶段
    confidence: str = "Medium"  # 置信度（High, Medium, Low）

    # 分维度得分
    valuation_score: float = 3.0  # 估值指标得分
    financial_score: float = 3.0  # 财务指标得分
    industry_score: float = 3.0  # 行业指标得分
    sentiment_score: float = 3.0  # 情绪指标得分

    # 指标列表
    indicators: List[CycleIndicator] = field(default_factory=list)
    rationale: List[str] = field(default_factory=list)

    @property
    def phase_display(self) -> str:
        """周期阶段显示名"""
        return self.phase.display_name

    @property
    def phase_emoji(self) -> str:
        """周期阶段emoji"""
        emojis = {
            CyclePhase.BOTTOM: "📉",
            CyclePhase.EARLY_UPSIDE: "↗️",
            CyclePhase.MID_UPSIDE: "⬆️",
            CyclePhase.LATE_UPSIDE: "↗️",
            CyclePhase.TOP: "📈",
            CyclePhase.EARLY_DOWNSIDE: "↘️",
            CyclePhase.MID_DOWNSIDE: "⬇️",
            CyclePhase.LATE_DOWNSIDE: "↘️",
        }
        return emojis.get(self.phase, "➡️")

    @property
    def assessment(self) -> str:
        """评估结论"""
        if self.total_score < 2.0:
            return "周期底部，买入机会"
        elif self.total_score < 3.0:
            return "上行初期，逐步建仓"
        elif self.total_score < 3.5:
            return "上行中期，持有为主"
        elif self.total_score < 4.0:
            return "上行后期，考虑减仓"
        elif self.total_score < 4.5:
            return "周期顶点，清仓离场"
        else:
            return "下行阶段，观望为主"


@dataclass
class CyclicalStock:
    """周期股数据"""

    # 基本信息
    ticker: str
    name: str
    market: MarketType
    current_price: float

    # 周期属性
    cycle_type: CycleType
    cycle_strength: CycleStrength = CycleStrength.MODERATE
    cycle_length_years: int = 5  # 周期长度（年）

    # 当前状态
    current_phase: CyclePhase = CyclePhase.MID_UPSIDE
    cycle_score: Optional[CycleScore] = None

    # 估值指标
    pb: float = 0.0
    pe: float = 0.0
    ps: float = 0.0  # 市销率
    cyclical_adjusted_pe: float = 0.0  # 周期调整PE
    fcf_yield: float = 0.0  # FCF收益率
    dividend_yield: float = 0.0  # 股息率
    ev_ebitda: float = 0.0  # EV/EBITDA

    # 每股指标
    bvps: float = 0.0  # 每股净资产
    eps: float = 0.0  # 每股收益
    fcf_per_share: float = 0.0  # 每股自由现金流

    # 财务质量
    debt_ratio: float = 0.0  # 资产负债率
    roe: float = 0.0  # 净资产收益率
    roa: float = 0.0  # 总资产收益率
    fcf_to_net_income: float = 0.0  # FCF/净利润
    gross_margin: float = 0.0  # 毛利率
    operating_margin: float = 0.0  # 营业利润率
    interest_coverage: float = 0.0  # 利息覆盖率

    # 分红相关
    payout_ratio: float = 0.0  # 分红比例
    dividend_growth_rate: float = 0.0  # 股息增长率
    consecutive_dividend_years: int = 0  # 连续分红年数

    # 历史数据
    historical_pb: List[float] = field(default_factory=list)
    historical_pe: List[float] = field(default_factory=list)
    historical_roe: List[float] = field(default_factory=list)
    historical_fcf_yield: List[float] = field(default_factory=list)

    # 规模
    market_cap: float = 0.0  # 市值
    revenue: float = 0.0  # 营业收入
    net_income: float = 0.0  # 净利润
    total_assets: float = 0.0  # 总资产

    # 策略建议
    investment_action: InvestmentAction = InvestmentAction.WATCH
    target_allocation: float = 0.0  # 建议仓位（%）
    target_price: float = 0.0  # 目标价
    stop_loss_price: float = 0.0  # 止损价
    expected_return: float = 0.0  # 预期收益（%）
    holding_period: str = ""  # 持有周期
    strategy_type: InvestmentStrategy = InvestmentStrategy.CYCLICAL_TRADING

    # 其他信息
    currency: str = "CNY"
    exchange: str = "SH"
    sectors: List[str] = field(default_factory=list)
    analysis_date: date = field(default_factory=date.today)

    @classmethod
    def from_stock(
        cls,
        stock: "Stock",
        cycle_type: CycleType,
        cycle_strength: CycleStrength = CycleStrength.MODERATE,
    ) -> "CyclicalStock":
        """从 Stock 对象创建 CyclicalStock"""
        # 判断市场类型
        if stock.ticker.isdigit() and len(stock.ticker) == 6:
            market = MarketType.A_SHARE
            currency = "CNY"
        else:
            market = MarketType.US
            currency = "USD"

        return cls(
            ticker=stock.ticker,
            name=stock.name,
            market=market,
            current_price=stock.current_price,
            cycle_type=cycle_type,
            cycle_strength=cycle_strength,
            # 估值指标
            pb=stock.pb_ratio if hasattr(stock, "pb_ratio") else 0.0,
            pe=stock.pe_ratio if hasattr(stock, "pe_ratio") else 0.0,
            bvps=stock.bvps,
            eps=stock.eps,
            fcf_yield=stock.fcf / stock.current_price
            if stock.current_price > 0 and stock.fcf > 0
            else 0.0,
            dividend_yield=stock.dividend_yield,
            # 财务质量
            debt_ratio=stock.total_liabilities / stock.total_assets
            if stock.total_assets > 0
            else 0.0,
            roe=stock.roe,
            fcf_to_net_income=stock.fcf / stock.net_income if stock.net_income > 0 else 0.0,
            gross_margin=stock.gross_margin if hasattr(stock, "gross_margin") else 0.0,
            operating_margin=stock.operating_margin,
            # 分红相关
            payout_ratio=stock.dividend_per_share / stock.eps if stock.eps > 0 else 0.0,
            dividend_growth_rate=stock.dividend_growth_rate,
            # 历史数据
            historical_pb=stock.historical_pb if hasattr(stock, "historical_pb") else [],
            historical_pe=stock.historical_pe if hasattr(stock, "historical_pe") else [],
            # 规模
            market_cap=stock.current_price * stock.shares_outstanding,
            revenue=stock.revenue,
            net_income=stock.net_income,
            total_assets=stock.total_assets,
            # 其他
            currency=currency,
            exchange=stock.exchange,
            sectors=stock.sectors if hasattr(stock, "sectors") else [],
        )

    @property
    def market_display(self) -> str:
        """市场显示名"""
        return self.market.display_name

    @property
    def is_buyable(self) -> bool:
        """是否适合买入"""
        return self.current_phase.is_buyable and self.investment_action in [
            InvestmentAction.STRONG_BUY,
            InvestmentAction.BUY,
        ]

    @property
    def is_sellable(self) -> bool:
        """是否适合卖出"""
        return self.current_phase.is_sellable or self.investment_action in [
            InvestmentAction.SELL,
            InvestmentAction.REDUCE,
        ]


@dataclass
class ValuationResult:
    """估值结果"""

    method: str  # 估值方法
    fair_value: float  # 公允价值
    current_value: float  # 当前价值
    premium_discount: float  # 溢价/折价（%）
    assessment: str  # 评估（Undervalued, Fair, Overvalued）
    action: str = "HOLD"  # 行动建议
    details: Dict[str, Any] = field(default_factory=dict)
    confidence: str = "Medium"  # 置信度

    @property
    def margin_of_safety(self) -> float:
        """安全边际"""
        if self.fair_value <= 0:
            return 0.0
        return ((self.fair_value - self.current_value) / self.fair_value) * 100


@dataclass
class StrategyRecommendation:
    """策略建议"""

    action: InvestmentAction  # 投资行动
    target_allocation: float  # 目标仓位（%）
    target_price: float  # 目标价
    stop_loss_price: float  # 止损价
    expected_return: float  # 预期收益（%）
    holding_period: str  # 持有周期
    strategy_type: InvestmentStrategy  # 策略类型

    # 额外信息
    dividend_yield: float = 0.0  # 股息率
    total_shareholder_yield: float = 0.0  # 总股东收益率（股息+回购）
    expected_annual_return: float = 0.0  # 预期年化收益

    # 理由
    rationale: List[str] = field(default_factory=list)

    @property
    def action_display(self) -> str:
        """行动显示名"""
        return self.action.display_name

    @property
    def action_signal(self) -> str:
        """行动信号"""
        return self.action.signal


@dataclass
class Checklist:
    """买入/卖出清单"""

    items: Dict[str, bool] = field(default_factory=dict)

    @property
    def passed_count(self) -> int:
        """通过项数"""
        return sum(1 for passed in self.items.values() if passed)

    @property
    def total_count(self) -> int:
        """总项数"""
        return len(self.items)

    @property
    def pass_rate(self) -> float:
        """通过率"""
        if self.total_count == 0:
            return 0.0
        return (self.passed_count / self.total_count) * 100

    @property
    def passed_items(self) -> List[str]:
        """通过的项目"""
        return [item for item, passed in self.items.items() if passed]

    @property
    def failed_items(self) -> List[str]:
        """未通过的项目"""
        return [item for item, passed in self.items.items() if not passed]


@dataclass
class CyclicalAnalysisResult:
    """周期股分析结果"""

    stock: CyclicalStock
    cycle_analysis: CycleScore
    valuation_results: Dict[str, ValuationResult] = field(default_factory=dict)
    strategy_recommendation: Optional[StrategyRecommendation] = None

    # 清单
    buy_checklist: Optional[Checklist] = None
    sell_checklist: Optional[Checklist] = None

    # 风险和催化剂
    risks: List[str] = field(default_factory=list)
    catalysts: List[str] = field(default_factory=list)

    # 综合评分
    overall_score: float = 0.0  # 综合评分（0-100）
    investment_rating: str = "Neutral"  # 投资评级

    @property
    def is_recommended(self) -> bool:
        """是否推荐"""
        return self.strategy_recommendation and self.strategy_recommendation.action in [
            InvestmentAction.STRONG_BUY,
            InvestmentAction.BUY,
        ]

    @property
    def risk_level(self) -> str:
        """风险等级"""
        if self.cycle_analysis.total_score < 2.5:
            return "低"
        elif self.cycle_analysis.total_score < 3.5:
            return "中"
        else:
            return "高"
