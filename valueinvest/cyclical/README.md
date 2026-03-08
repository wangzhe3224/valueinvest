# ValueInvest - Cyclical Stock Analysis Module

## Overview

The cyclical stock analysis module provides comprehensive tools for analyzing cyclical stocks with different strategies for A-share and US markets.

## Key Features

- **Cycle Position Scoring System**: Multi-dimensional scoring (valuation, financial, industry, sentiment) to determine where a stock is in its cycle
- **Cyclical-Adjusted Valuation Methods**:
  - **Cyclical PB Valuation**: Dynamic PB thresholds based on cycle phase
  - **Cyclical PE Valuation**: Normalized earnings using 3-5 year averages to avoid cycle traps
  - **Cyclical FCF Valuation**: Free cash flow yield analysis
  - **Cyclical Dividend Valuation**: Dividend sustainability assessment
- **Differentiated Strategies**:
  - **A-Share Strategy**: Trading-oriented (1-3 year holding, +50-200% target return)
  - **US Strategy**: Dividend-defensive (5-10 year holding, 6-10% annual return)
- **Cyclical Analysis Engine**: Complete end-to-end analysis workflow

## Quick Start

### Using the Analysis Engine (Recommended)

The easiest way to analyze a cyclical stock:

```python
from valueinvest.cyclical import (
    CyclicalAnalysisEngine,
    CyclicalStock,
    CycleType,
    MarketType,
)

# 1. Create stock data
stock = CyclicalStock(
    ticker="601919",
    name="中远海控",
    market=MarketType.A_SHARE,
    current_price=15.79,
    cycle_type=CycleType.SHIPPING,
    pb=1.09,
    bvps=14.5,
    eps=1.73,
    pe=9.1,
    fcf_yield=7.9,
    fcf_per_share=1.25,
    fcf_to_net_income=1.1,
    dividend_yield=5.0,
    debt_ratio=0.35,
    roe=12.0,
    historical_pb=[1.5, 2.0, 1.8, 2.5, 1.2],
)

# 2. Create engine
engine = CyclicalAnalysisEngine()

# 3. Run complete analysis
result = engine.analyze(stock)

# 4. View results
print(f"=== 周期股分析结果 ===")
print(f"股票: {result.stock.name} ({result.stock.ticker})")
print(f"周期阶段: {result.cycle_analysis.phase_display}")
print(f"周期得分: {result.cycle_analysis.total_score:.2f}/5.0")
print(f"综合评分: {result.overall_score}/100")
print(f"投资评级: {result.investment_rating}")
print(f"\n【策略建议】")
print(f"投资行动: {result.strategy_recommendation.action_display}")
print(f"建议仓位: {result.strategy_recommendation.target_allocation:.1%}")
print(f"目标价格: ¥{result.strategy_recommendation.target_price:.2f}")
```

### Manual Analysis (Step by Step)

For more control, you can perform each step manually:

```python
from valueinvest.cyclical import (
    CyclicalStock,
    CyclePositionScorer,
    CycleType,
    MarketType,
    IndicatorCategory,
    CycleIndicator,
    CyclicalPBValuation,
    AShareCyclicalStrategy,
)

# 1. Create stock data
stock = CyclicalStock(
    ticker="601919",
    name="中远海控",
    market=MarketType.A_SHARE,
    current_price=15.79,
    cycle_type=CycleType.SHIPPING,
    pb=1.09,
    bvps=14.5,
    eps=1.73,
    dividend_yield=5.0,
    historical_pb=[1.5, 2.0, 1.8, 2.5, 1.2],
)

# 2. Score cycle position
scorer = CyclePositionScorer(market=MarketType.A_SHARE)

# Add indicators
scorer.add_indicator(CycleIndicator(
    name="PB估值",
    value=stock.pb,
    category=IndicatorCategory.VALUATION,
    percentile=20.0,
))

scorer.add_indicator(CycleIndicator(
    name="BDI指数",
    value=1500,
    category=IndicatorCategory.INDUSTRY,
    percentile=25.0,
))

cycle_score = scorer.calculate_score()
print(f"Cycle Phase: {cycle_score.phase_display}")
print(f"Total Score: {cycle_score.total_score:.2f}/5.0")

# 3. Run valuation
valuation = CyclicalPBValuation()
result = valuation.calculate(stock)
print(f"Fair Value: ¥{result.fair_value:.2f}")
print(f"Action: {result.action}")

# 4. Get strategy recommendation
from valueinvest.cyclical.base import CyclicalAnalysisResult

analysis = CyclicalAnalysisResult(
    stock=stock,
    cycle_analysis=cycle_score,
    valuation_results={"pb": result}
)

strategy = AShareCyclicalStrategy()
recommendation = strategy.generate_recommendation(stock, analysis)

print(f"Recommendation: {recommendation.action_display}")
print(f"Target Allocation: {recommendation.target_allocation:.1%}")
print(f"Target Price: ¥{recommendation.target_price:.2f}")
```

## Module Components

### Analysis Engine (`cyclical/engine.py`)
- **CyclicalAnalysisEngine**: Complete analysis workflow
  - Automatic cycle type detection
  - Cycle position scoring
  - Multiple valuation methods
  - Market-specific strategies
  - Risk and catalyst identification
  - Overall scoring (0-100)
  - Investment rating (强烈推荐/推荐/中性/谨慎/不推荐)

### Enums (`cyclical/enums.py`)
- `CycleType`: COMMODITY, CAPACITY, FINANCIAL, REAL_ESTATE, SHIPPING, INVENTORY, ENERGY
- `CyclePhase`: BOTTOM, EARLY_UPSIDE, MID_UPSIDE, LATE_UPSIDE, TOP, EARLY_DOWNSIDE, MID_DOWNSIDE, LATE_DOWNSIDE
- `CycleStrength`: STRONG, MODERATE, WEAK
- `MarketType`: A_SHARE, US, HK
- `InvestmentAction`: STRONG_BUY, BUY, HOLD, REDUCE, SELL, WATCH
- `InvestmentStrategy`: CYCLICAL_TRADING, DIVIDEND_DEFENSIVE, BALANCED

### Base Classes (`cyclical/base.py`)
- `CycleIndicator`: Individual cycle indicator with scoring
- `CycleScore`: Cycle position assessment result
- `CyclicalStock`: Cyclical stock data model
- `ValuationResult`: Valuation calculation result
- `StrategyRecommendation`: Investment strategy recommendation
- `Checklist`: Buy/sell checklist
- `CyclicalAnalysisResult`: Complete analysis result

### Position Scorer (`cyclical/position_scorer.py`)
Multi-dimensional cycle position scoring system:
- **Valuation indicators**: PB, PE, dividend yield
- **Financial indicators**: ROE, debt ratio, FCF quality
- **Industry indicators**: BDI, CCFI, steel prices, etc.
- **Sentiment indicators**: Market attention, analyst ratings

Different weight configurations for A-share vs US markets.

### Valuation Methods (`cyclical/valuation/`)

#### Cyclical PB Valuation (`cyclical_pb.py`)
- Dynamic PB thresholds based on cycle phase
- A-share: Buy < 1.0-1.2x, Sell > 2.0-3.0x
- US: Buy < 1.0-1.4x, Sell > 1.5-2.0x
- Uses historical PB median as fair PB

#### Cyclical PE Valuation (`cyclical_pe.py`)
- Normalizes earnings using 3-5 year average ROE
- Avoids "cycle top low PE trap" (PE 5x but profits about to crash)
- A-share: Buy < 12x, Fair 15x, Sell > 20x
- US: Buy < 10x, Fair 13x, Sell > 16x

#### Cyclical FCF Valuation (`cyclical_fcf.py`)
- Free cash flow yield analysis
- A-share: Buy > 10%, Fair 7%, Sell < 5%
- US: Buy > 12%, Fair 8%, Sell < 6%

#### Cyclical Dividend Valuation (`cyclical_dividend.py`)
- Dividend sustainability assessment (payout ratio, FCF coverage)
- Total shareholder yield (dividend + buyback)
- US-focused: 5-10 year holding, 3-5% dividend yield target

### Strategies (`cyclical/strategy/`)

#### A-Share Strategy (`ashare_strategy.py`)
- **Objective**: Cycle trading, high returns
- **Holding Period**: 1-3 years
- **Target Return**: +50-200%
- **Max Position**: 10% single stock, 35% total cyclical
- **Decision Matrix**: Based on cycle phase and PB valuation
- **Buy Checklist**: Cycle position, valuation, financial quality, dividends

#### US Strategy (`us_strategy.py`)
- **Objective**: Dividend defensive, stable income
- **Holding Period**: 5-10 years
- **Target Return**: 6-10%/year (dividend + growth)
- **Max Position**: 8% single stock, 25% total cyclical
- **Decision Matrix**: Based on dividend sustainability and FCF yield
- **Buy Checklist**: Dividend history, sustainability, FCF coverage, valuation

## Testing

Run tests:
```bash
python -m pytest tests/test_cyclical.py -v
```

All tests should pass:
- Enum properties and display names
- Cycle indicator scoring
- Cycle position scorer
- Cyclical PB valuation (bottom, top, error handling)
- A-share strategy (bottom buy, top sell)
- Buy/sell checklists
- Full integration workflow

## Examples

See `examples/cyclical_example.py` for a complete workflow example analyzing 中远海控 (601919).

## Current Status

**Completed**:
- ✅ Enums and base classes
- ✅ Cycle position scoring system
- ✅ Four valuation methods (PB, PE, FCF, Dividend)
- ✅ A-share and US strategies
- ✅ **Cyclical Analysis Engine** - Complete end-to-end analysis
- ✅ Comprehensive tests (13 passing)
- ✅ Documentation and examples

**Optional Enhancements**:
- ⏳ Industry indicator fetchers (shipping, steel, metals, chemicals)
- ⏳ Integration with main ValuationEngine
- ⏳ CLI interface

## Code Statistics
- **Total Lines**: ~3,500 lines
- **Test Coverage**: 13 tests, all passing
- **Modules**: 10 core modules + 4 valuation methods + 2 strategies + 1 engine
