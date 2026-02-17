# ValueInvest

A modular Python library for comprehensive stock valuation using multiple methodologies.

## Features

- **Graham Valuation**: Graham Number, Graham Formula, NCAV (Net-Net)
- **Discounted Cash Flow**: DCF (10-year projection), Reverse DCF
- **Earnings Power Value**: Zero-growth intrinsic value
- **Dividend Models**: Gordon Growth, Two-Stage DDM
- **Growth Valuation**: PEG Ratio, GARP, Rule of 40
- **Bank Valuation**: P/B Valuation, Residual Income Model

## Installation

```bash
cd valueinvest
pip install -e .
```

## Quick Start

### Command Line

```bash
# Analyze preset stocks
python analyze.py google
python analyze.py icbc
python analyze.py yangtze

# Use specific methods
python analyze.py google --methods dcf,peg,garp
```

### Python API

```python
from valueinvest import Stock, ValuationEngine
from valueinvest.data.presets import get_preset

# Use a preset
stock = get_preset("icbc")

# Or create your own
stock = Stock(
    ticker="AAPL",
    name="Apple Inc.",
    current_price=180.0,
    shares_outstanding=15.5e9,
    eps=6.0,
    bvps=3.5,
    revenue=383e9,
    net_income=97e9,
    fcf=100e9,
    growth_rate=8.0,
    dividend_per_share=0.96,
    dividend_yield=0.53,
    dividend_growth_rate=5.0,
    cost_of_capital=10.0,
    discount_rate=10.0,
    terminal_growth=2.5,
)

# Run valuation
engine = ValuationEngine()

# All methods
results = engine.run_all(stock)

# Category-specific methods
results = engine.run_growth(stock)      # Growth companies
results = engine.run_dividend(stock)    # Dividend stocks
results = engine.run_bank(stock)        # Banks

# Specific methods
results = engine.run_multiple(stock, ["dcf", "ddm", "peg"])

# Custom parameters
result = engine.run_single(stock, "dcf", 
    growth_1_5=15.0, 
    growth_6_10=8.0, 
    discount_rate=9.0
)

# Summary statistics
summary = engine.summary(results)
print(f"Average Fair Value: ${summary['average_value']:.2f}")
print(f"Undervalued: {summary['undervalued_count']}/{len(results)}")
```

## Available Methods

| Method | Best For | Key Formula |
|--------|----------|-------------|
| Graham Number | Defensive investors | √(22.5 × EPS × BVPS) |
| Graham Formula | Moderate growth | V = (EPS × (8.5 + 2g) × 4.4) / Y |
| NCAV | Deep value | (Assets - Liabilities) / Shares |
| DCF | Growth companies | PV(Free Cash Flows) + Terminal Value |
| Reverse DCF | Any | What growth is priced in? |
| EPV | Mature companies | Distributable CF / Cost of Capital |
| DDM | Dividend stocks | D / (r - g) |
| Two-Stage DDM | Dividend growth | Stage 1 + Terminal perpetuity |
| PEG | Profitable growth | P/E ÷ Growth Rate |
| GARP | Growth at reasonable price | Future EPS × Target P/E, discounted |
| Rule of 40 | SaaS/Subscription | Growth % + Margin % ≥ 40 |
| P/B Valuation | Banks | Fair P/B = (ROE - g) / (COE - g) |
| Residual Income | Banks | Book Value + PV(Excess Returns) |

## Project Structure

```
valueinvest/
├── __init__.py
├── stock.py                 # Stock data container
├── valuation/
│   ├── base.py              # Base classes
│   ├── graham.py            # Graham methods
│   ├── dcf.py               # DCF methods
│   ├── epv.py               # Earnings Power Value
│   ├── ddm.py               # Dividend models
│   ├── growth.py            # Growth valuation
│   ├── bank.py              # Bank valuation
│   └── engine.py            # Unified engine
├── data/
│   └── presets.py           # Pre-configured stocks
└── reports/
    └── reporter.py          # Report formatting

analyze.py                   # CLI entry point
```

## Extending the Library

Add a custom valuation method:

```python
from valueinvest.valuation.base import BaseValuation, ValuationResult

class MyValuation(BaseValuation):
    method_name = "My Custom Method"
    
    def calculate(self, stock) -> ValuationResult:
        # Your valuation logic
        fair_value = stock.eps * 15  # example
        
        return ValuationResult(
            method=self.method_name,
            fair_value=round(fair_value, 2),
            current_price=stock.current_price,
            premium_discount=round(
                ((fair_value - stock.current_price) / stock.current_price) * 100, 1
            ),
            assessment=self._assess(fair_value, stock.current_price),
            analysis=["Custom analysis notes"],
        )

# Register in engine.py
engine._methods["my_method"] = MyValuation()
```

## Example Output

```
╔════════════════════════════════════════════════════════════════════╗
║                  工商银行 / ICBC - Valuation Analysis              ║
╚════════════════════════════════════════════════════════════════════╝

┌────────────────────────────────────────────────────────────────────┐
│ VALUATION SUMMARY                                                  │
├────────────────────────────────────────────────────────────────────┤
│ Method                           Fair Value       Margin Assessment│
├────────────────────────────────────────────────────────────────────┤
│ P/B Valuation                         $9.64       +32.0% Undervalued│
│ Residual Income                       $8.64       +18.3% Undervalued│
│ Graham Number                        $15.35      +110.2% Undervalued│
├────────────────────────────────────────────────────────────────────┤
│ AVERAGE                             $10.99       +50.5%            │
│ CURRENT PRICE                        $7.30           --            │
└────────────────────────────────────────────────────────────────────┘
```

## License

MIT License
