# Changelog

All notable changes to this project will be documented in this file.

## [1.3.2] - 2026-05-02

### Fixed
- **YFinanceFetcher FCF**: Prefer cashflow statement "Free Cash Flow" line over `info['freeCashflow']` which can be significantly inaccurate (e.g. META FY2025: info reported \$25B vs actual \$46B). Falls back to OCF + CapEx calculation if "Free Cash Flow" line is unavailable.

## [1.3.1] - 2026-04-23

### Fixed
- **CyclicalStock.from_stock**: Fixed `fcf_yield` calculation — was dividing total FCF by price instead of FCF per share by price, resulting in inflated values.
- **CyclicalStock.from_stock**: Added missing `fcf_per_share` field mapping, causing FCF valuation to return near-zero values.

## [1.3.0] - 2026-04-20

### Added
- **Accounting Red Flags Detection**: New `redflags` module with `AccountingRedFlagsEngine` for detecting accounting manipulation risks across 11 signals in 4 categories (earnings quality 30%, revenue recognition 25%, asset & working capital 25%, capital structure 20%). Higher score = more red flags. Includes risk level classification (CLEAN through SEVERE_FLAGS).

## [1.2.1] - 2026-04-11

### Added
- **Implied Growth Rate Analysis**: New `implied_growth` module with `ImpliedGrowthEngine` for deriving market-implied growth rates from current stock price using multiple methods (Reverse DCF, PEG, Gordon Growth, Earnings Yield), comparing with historical growth rates, and assessing reasonableness (0-100 score).

## [1.2.0] - 2026-04-11

### Added
- **Peer Comparison Analysis**: New `peer_comparison` module with `PeerComparisonEngine` for comparing a stock's financial metrics (PE, PB, ROE, margins, growth, market cap) against industry peers. Includes percentile ranking, composite scoring (0-100), and strengths/weaknesses identification.
- **PeerCompany enrichment**: Added `operating_margin`, `net_margin`, `revenue_growth`, `ebitda`, `debt_ratio` fields and `effective_net_margin` property to `PeerCompany`.
- **`--peers` CLI flag**: `stock_analyzer.py` now supports `--peers` for peer comparison output.
- **Roadmap**: Added `roadmap.md` with planned features organized by category.

### Changed
- Updated `.venv` to Python 3.14.3
- Minimum Python version requirement raised from 3.9 to 3.11 (`requires-python = ">=3.11"`)
- Updated tooling targets (mypy, ruff) to Python 3.11+

## [1.1.0] - 2026-03-28

### Added
- **Historical PE/PB data**: yfinance fetcher now computes 5-year historical PE and PB ratios (avg_price / EPS, avg_price / BVPS) with detailed `historical_pe_data`/`historical_pb_data` dicts for relative valuation.
- **Interest expense**: yfinance fetcher now extracts interest expense from income statement, handling NaN in latest year and falling back to net interest (expense - income).
- **TTM data priority**: `fcf` and `operating_cash_flow` now use TTM values from yfinance `info` dict as primary source; annual report cashflow data is fallback only.
- **Batch analysis**: `ValuationEngine.analyze_batch()` for comparing multiple stocks, with `StockAnalysis`/`BatchAnalysisResult` dataclasses and `format_batch_table()` helper.
- **Analyst target prices**: Added `target_mean_price`, `target_high_price`, `target_low_price`, `number_of_analysts`, `recommendation` fields to Stock (via yfinance info dict).
- **Peer comparison module**: New `valueinvest.data.fetcher.peers` with `fetch_peer_metrics()` to fetch valuation metrics for a list of peer tickers.
- **PE Relative Valuation**: Now includes analyst consensus target and upside % in analysis and details.
- **AGENTS.md**: Agent-oriented quick reference with common patterns, decision points, data quality checks, and pitfall warnings.
- **Stock.__repr__()**: Concise one-line string representation for quick debugging.
- **Stock.summary()**: Structured multi-line data summary with data quality hints.
- **Stock.warnings**: Warnings list populated by `from_api()` instead of printing to stdout.
- **Stock.to_dict(full=True)**: Full data export including all financial fields.
- **ValuationResult.to_summary()**: Concise one-line summary for agent consumption.
- **ValuationResult.__str__()**: Multi-line string with details and analysis points.
- **Custom exceptions**: `DataFetchError`, `InsufficientDataError`, `UnsupportedMarketError` in `valueinvest/exceptions.py`.

### Fixed
- **yfinance fetcher**: Compute `net_debt` from balance sheet (`total_debt - cash`) when yfinance `netDebt` is None.
- **yfinance fetcher**: Dividend growth rate now uses last 10 complete years (excludes partial current year).
- **yfinance fetcher**: `tax_rate` computed from income statement (`Tax Provision / Pretax Income`).
- **Stock**: Added missing `current_liabilities` field.
- **AAA corporate yield**: Updated default from 2.28% to 5.30% (current Moody's Aaa rate as of March 2026).
- **Currency symbols**: Changed hardcoded ¥ to $ in analysis strings across Graham, DDM, Bank, and Growth modules.
- **Altman Z-Score**: Fixed NaN handling when `retained_earnings` is missing.
- **Piotroski F-Score**: Use `operating_cash_flow` instead of `fcf` for criteria F2/F4.
- **Piotroski F-Score**: Fixed current ratio to use `current_liabilities` instead of `total_liabilities`.
- **Beneish M-Score**: Medium risk no longer flagged as `is_manipulator=True`.
- **Cyclical methods**: Return clear "Not Applicable" message when called with regular `Stock`.
- **Bank methods**: Removed Altman Z-Score from BANK_METHODS.
- **Value Trap**: Registered in `ValuationEngine._methods` (was imported but missing from dict).
- **Moat/Capital engines**: Fixed TypeError when passing optional kwargs to signal functions.

### Improved
- **ValuationEngine.run_multiple()**: Error results now include exception type name and proper confidence/applicability flags.
- **Stock.from_api()**: Freshness warnings stored in `stock.warnings` instead of printing to stdout.

## [1.0.4] - 2026-03-28

### Fixed
- **yfinance data mapping**: Fixed 12+ fields returning None/0 from `Stock.from_api()`:
  - `operating_cash_flow`, `ebitda`, `total_debt`, `cash_and_equivalents` now from financial statements
  - `sector`, `industry`, `earnings_growth`, `revenue_growth` now from `ticker.info`
  - `inventory`, `accounts_receivable`, `accounts_payable`, `retained_earnings` now from balance sheet
  - `short_term_debt`, `long_term_debt` now from balance sheet
- **capex sign convention**: Now stored as positive value (expenditure)
- **Prior year data**: `prior_roa`, `prior_debt_ratio`, `prior_current_ratio`, `prior_shares_outstanding`, `prior_gross_margin`, `prior_asset_turnover` computed from prior year financials
- **total_liabilities**: Now from balance sheet `Total Liabilities Net Minority Interest` instead of `info.totalDebt`
- **growth_rate**: Now defaults to `revenueGrowth` from API instead of 0
- **Graham Number**: Added BVPS threshold ($10) for asset-light companies (e.g., tech with massive buybacks)
- **Magic Formula**: Fixed invested capital always being $0 by populating `net_working_capital`/`net_fixed_assets` from balance sheet, with Equity + Debt fallback
- **Value Trap**: Fixed `revenue_cagr_5y` parameter not being used — CAGR input now auto-normalizes decimal vs percentage format

### Added
- New Stock fields: `sector`, `industry`, `earnings_growth`, `revenue_growth`, `operating_cash_flow`, `total_debt`, `cash_and_equivalents`
- Computed properties: `revenue_cagr_5y`, `earnings_cagr_5y`, `gross_margin`, `asset_turnover`, `current_ratio`, `roa`, `debt_ratio`

## [1.0.2] - 2026-03-12

### Added
- Learning notebooks: Added `learn/` folder with DCF valuation tutorial
  - Interactive Jupyter notebook for learning DCF basics
  - Real data examples (AAPL, 600887)
  - Sensitivity analysis and visualization
  - Reverse DCF for market expectations

## [1.0.1] - 2026-03-09

### Fixed
- A-share data fetching: Fixed column name matching, bank stock support, and variable scope issues
- Flexible period formats: `fetch_history()` now supports `5d`, `1m`, `3m`, `1y` formats

### Added
- Data freshness checking: Price data (strict, yesterday OK), fundamental data (tolerant, up to 6 months)
- Report date extraction from financial statements

### Improved
- Better error handling and user-friendly warnings

## [1.0.0] - 2025-12-XX

- Initial release

---

For details, see [GitHub Releases](https://github.com/wangzhe3224/valueinvest/releases)
