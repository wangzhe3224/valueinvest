# ValueInvest

Python library for stock valuation using multiple methodologies.

## Tech Stack
- Python 3.x, dataclasses, abc

## Architecture
```
valueinvest/
├── stock.py              # Stock dataclass (ticker, price, eps, bvps, fcf, etc.)
├── valuation/
│   ├── base.py           # BaseValuation (ABC), ValuationResult (dataclass)
│   ├── engine.py         # ValuationEngine (runs methods, aggregates results)
│   ├── graham.py         # Graham Number, Graham Formula, NCAV
│   ├── dcf.py            # DCF, Reverse DCF
│   ├── epv.py            # Earnings Power Value
│   ├── ddm.py            # Gordon Growth, Two-Stage DDM
│   ├── growth.py         # PEG, GARP, Rule of 40
│   ├── bank.py           # P/B Valuation, Residual Income
│   └── magic_formula.py  # Joel Greenblatt's Magic Formula (EY + ROC)
├── data/presets.py       # Pre-configured stock data
└── reports/reporter.py   # Format output tables
```

## Key Patterns
- **Add new method**: Extend `BaseValuation`, implement `calculate(stock) -> ValuationResult`
- **Register method**: Add to `ValuationEngine._methods` dict
- **Run valuations**: `engine.run_all(stock)`, `engine.run_multiple(stock, ["dcf", "ddm"])`

## Commands
```bash
python analyze.py google      # Growth stock methods
python analyze.py icbc        # Bank methods
python analyze.py yangtze     # Dividend methods
python analyze.py <name> --methods dcf,peg,garp
```

## Conventions
- Use dataclasses for data containers
- Type hints on all public APIs
- `ValuationResult.fair_value` is the intrinsic value estimate
- Assessment threshold: ±15% for "Fair", otherwise "Undervalued/Overvalued"
