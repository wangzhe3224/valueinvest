# Changelog

All notable changes to this project will be documented in this file.

## [1.0.4] - 2026-03-28

### Fixed
- **Graham Number**: Added BVPS threshold ($10) for asset-light companies. Tech companies with low BVPS (due to buybacks/intangibles) now return N/A instead of absurdly inflated values.
- **Magic Formula**: Fixed invested capital always being $0 by populating `net_working_capital` and `net_fixed_assets` from yfinance balance sheet. Added fallback using Equity + Debt when Greenblatt's formula yields non-positive capital.

## [1.0.3] - 2026-03-28

### Fixed
- **yfinance data mapping**: Fixed 12 fields returning None/0 from `Stock.from_api()`:
  - `operating_cash_flow`, `ebitda`, `total_debt`, `cash_and_equivalents` now populated from financial statements
  - `sector`, `industry`, `earnings_growth`, `revenue_growth` now populated from `ticker.info`
  - `inventory`, `accounts_receivable`, `accounts_payable`, `retained_earnings` now populated from balance sheet
  - `short_term_debt`, `long_term_debt` now populated from balance sheet
- **capex sign convention**: Now stored as positive value (expenditure), matching intuitive expectation
- **Prior year data**: `prior_roa`, `prior_debt_ratio`, `prior_current_ratio`, `prior_shares_outstanding`, `prior_gross_margin`, `prior_asset_turnover` now computed from prior year financials for F-Score/M-Score
- **total_liabilities**: Now correctly mapped from balance sheet `Total Liabilities Net Minority Interest` instead of `info.totalDebt`

### Added
- New Stock fields: `sector`, `industry`, `earnings_growth`, `revenue_growth`, `operating_cash_flow`, `total_debt`, `cash_and_equivalents`
- Computed properties: `revenue_cagr_5y`, `earnings_cagr_5y`, `gross_margin`, `asset_turnover`, `current_ratio`, `roa`, `debt_ratio`
- 5-year CAGR for revenue and earnings computed from historical financials

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
