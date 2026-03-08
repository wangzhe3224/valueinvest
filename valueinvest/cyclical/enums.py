"""
Enum definitions for cyclical stock analysis.
"""
from enum import Enum


class CycleType(Enum):
    """周期类型"""

    COMMODITY = "commodity"  # 商品价格周期（石油、有色）
    CAPACITY = "capacity"  # 产能周期（钢铁、水泥、化工）
    FINANCIAL = "financial"  # 金融周期（银行、证券）
    REAL_ESTATE = "real_estate"  # 地产周期
    SHIPPING = "shipping"  # 航运周期
    INVENTORY = "inventory"  # 库存周期（半导体、汽车）
    ENERGY = "energy"  # 能源周期（石油、天然气、煤炭）


class CyclePhase(Enum):
    """周期阶段"""

    BOTTOM = "bottom"  # 周期底部
    EARLY_UPSIDE = "early_upside"  # 上行初期
    MID_UPSIDE = "mid_upside"  # 上行中期
    LATE_UPSIDE = "late_upside"  # 上行后期
    TOP = "top"  # 周期顶点
    EARLY_DOWNSIDE = "early_downside"  # 下行初期
    MID_DOWNSIDE = "mid_downside"  # 下行中期
    LATE_DOWNSIDE = "late_downside"  # 下行后期

    @property
    def display_name(self) -> str:
        """Chinese display name"""
        names = {
            "bottom": "周期底部",
            "early_upside": "上行初期",
            "mid_upside": "上行中期",
            "late_upside": "上行后期",
            "top": "周期顶点",
            "early_downside": "下行初期",
            "mid_downside": "下行中期",
            "late_downside": "下行后期",
        }
        return names.get(self.value, self.value)

    @property
    def is_upside(self) -> bool:
        """是否处于上行阶段"""
        return self in [CyclePhase.EARLY_UPSIDE, CyclePhase.MID_UPSIDE, CyclePhase.LATE_UPSIDE]

    @property
    def is_downside(self) -> bool:
        """是否处于下行阶段"""
        return self in [
            CyclePhase.EARLY_DOWNSIDE,
            CyclePhase.MID_DOWNSIDE,
            CyclePhase.LATE_DOWNSIDE,
        ]

    @property
    def is_buyable(self) -> bool:
        """是否适合买入"""
        return self in [CyclePhase.BOTTOM, CyclePhase.EARLY_UPSIDE, CyclePhase.LATE_DOWNSIDE]

    @property
    def is_sellable(self) -> bool:
        """是否适合卖出"""
        return self in [CyclePhase.TOP, CyclePhase.EARLY_DOWNSIDE, CyclePhase.LATE_UPSIDE]


class CycleStrength(Enum):
    """周期强度"""

    STRONG = "strong"  # 强周期（利润波动 > 50%/年）
    MODERATE = "moderate"  # 中等周期（利润波动 20-50%/年）
    WEAK = "weak"  # 弱周期（利润波动 < 20%/年）

    @property
    def display_name(self) -> str:
        names = {
            "strong": "强周期",
            "moderate": "中等周期",
            "weak": "弱周期",
        }
        return names.get(self.value, self.value)


class MarketType(Enum):
    """市场类型"""

    A_SHARE = "a_share"  # A股
    US = "us"  # 美股
    HK = "hk"  # 港股

    @property
    def display_name(self) -> str:
        names = {
            "a_share": "A股",
            "us": "美股",
            "hk": "港股",
        }
        return names.get(self.value, self.value)


class InvestmentAction(Enum):
    """投资行动"""

    STRONG_BUY = "strong_buy"  # 强烈买入
    BUY = "buy"  # 买入
    HOLD = "hold"  # 持有
    REDUCE = "reduce"  # 减仓
    SELL = "sell"  # 卖出
    WATCH = "watch"  # 观望

    @property
    def display_name(self) -> str:
        names = {
            "strong_buy": "强烈买入",
            "buy": "买入",
            "hold": "持有",
            "reduce": "减仓",
            "sell": "卖出",
            "watch": "观望",
        }
        return names.get(self.value, self.value)

    @property
    def signal(self) -> str:
        """信号标识"""
        signals = {
            "strong_buy": "🟢🟢",
            "buy": "🟢",
            "hold": "🟡",
            "reduce": "🟠",
            "sell": "🔴",
            "watch": "⚪",
        }
        return signals.get(self.value, "⚪")


class InvestmentStrategy(Enum):
    """投资策略"""

    CYCLICAL_TRADING = "cyclical_trading"  # A股：周期博弈（1-3年，高赔率）
    DIVIDEND_DEFENSIVE = "dividend_defensive"  # 美股：收息防御（5-10年，稳定回报）
    BALANCED = "balanced"  # 平衡策略

    @property
    def display_name(self) -> str:
        names = {
            "cyclical_trading": "周期博弈",
            "dividend_defensive": "收息防御",
            "balanced": "平衡策略",
        }
        return names.get(self.value, self.value)


class IndicatorCategory(Enum):
    """指标类别"""

    VALUATION = "valuation"  # 估值指标（PB, PE等）
    FINANCIAL = "financial"  # 财务指标（ROE, 负债率等）
    INDUSTRY = "industry"  # 行业指标（价格、运价等）
    SENTIMENT = "sentiment"  # 情绪指标（市场关注度等）
    TECHNICAL = "technical"  # 技术指标（均线、成交量等）
