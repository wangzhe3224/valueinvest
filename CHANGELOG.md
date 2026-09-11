# Changelog

All notable changes to this project will be documented in this file.

## [1.7.3] - 2026-09-11

### Added
- **stock_snapshot quick note for no-COGS vendors**: when reported gross margin is ≥ 99.5% (vendor P&L has no COGS row — e.g. Mastercard, ICE — so gross profit is imputed = revenue), the snapshot now emits an `[i]` note telling the analyst to use operating/net margin instead. Caught during the MA 2026-09-11 snapshot where the table showed a bogus 100% gross margin.

## [1.7.2] - 2026-09-11

### Fixed
- **stock_snapshot ROE/ROIC sourced from the wrong stockanalysis page**: the quarterly ratios page's `roe`/`roic` fields are single-quarter (ROIC) / YTD-basis (ROE) numbers, not TTM — IBM displayed ROE 14.8% / ROIC 2.2% instead of the true ~34.5% / ~14.0% (fiscal-year anchors and the latest-TTM column were both affected, which also skewed the four-quadrant ROIC delta). The script now also fetches the annual ratios page (whose newest column is TTM) and uses it for ROE/ROIC levels and deltas, with fallback to the old source if the annual page is unavailable.

## [1.7.1] - 2026-09-06

### Fixed
- **YFinanceInsiderFetcher returned 0 trades (silent failure)**: rewrote to use `Ticker.insider_transactions` (per-trade Form 4 records, ~2y history). The old code iterated `insider_purchases` — a 6-month aggregate table with no `Start Date` column, so every row was skipped — and read a non-existent `Shares` column from `insider_roster_holders`. Trade type is now parsed from the `Text` field (Sale/Buy/Gift/Exercise; empty text = grant → `OTHER`, no longer miscounted as buys), price falls back to `Value / Shares` when the text lacks one, and `Value` NaN is handled.

## [1.7.0] - 2026-09-04

### Added
- **Trend chart expansion**: `plot_trends()` now also renders **Net Income (TTM)** and **Operating Cash Flow (TTM)** history panels (humanized B/M y-axis) plus a combined **YoY Growth panel** overlaying revenue / net income / operating-cash-flow TTM growth with direct end-of-line labels and a ±200% display clip (tiny-base outliers can no longer flatten the panel). New `include_growth` flag to toggle the growth panel.
- **`TrendMetric.NET_INCOME` / `TrendMetric.OPERATING_CASH_FLOW`**: chart/extraction-only metrics (no signals, no score weight — composite ratings are unchanged); new `TrendSeries.ttm_yoy(metric)` returns TTM YoY % (`None` where the year-ago base is non-positive).

## [1.6.1] - 2026-08-20

### Fixed
- **PeerComparisonEngine crash on net_margin**: `_get_peer_values` referenced non-existent `Stock.effective_net_margin` when a peer's derived net margin was 0, raising `AttributeError` and killing the whole peer comparison. Now derives it via `_derive_net_margin(p)`.

## [1.6.0] - 2026-07-30

### Added
- **Trend & Growth-Signal Analysis**: New `trend` module for multi-year quarterly trend analysis. `fetch_quarterly_trends()` returns single-quarter + rolling-TTM series for revenue, gross margin, net margin, fcf yield, and CCC (cash conversion cycle) — via FMP (US, ~30y quarterly history) or Tushare (A-shares). `analyze_trend_signals()` scores growth signals (CAGR, YoY/QoQ acceleration, inflection, consecutive-streak, stability) into a composite trend rating with CCC industry-applicability gating. `plot_trends()` renders a multi-panel PNG (new `plot` optional dependency, matplotlib). Ships new `trend-analysis` skill.

## [1.5.1] - 2026-07-25

### Fixed
- **YFinanceFetcher fundamentals crash on net-interest-income companies**: `fetch_fundamentals` used invalid pandas API `financials.loc.get(...)` (a `_LocIndexer` has no `.get`), raising `AttributeError` for companies that report "Interest Income" but no "Interest Expense" line (e.g. GRMN and other debt-free / net-cash firms). The `AttributeError` escaped the narrow `except (KeyError, IndexError, TypeError)` and nuked the entire fetch, returning `data={}` — so downstream `fetch_stock_data.py` reported zero revenue/NI/EPS and only 2 valuation methods ran. Fixed to use guarded `.loc[...]` access, and broadened the income-statement / balance-sheet / cashflow `except` clauses to also catch `AttributeError` so one bad line can no longer wipe a whole fetch.

## [1.5.0] - 2026-06-12

### Added
- **Earnings Patch**: New `data.patch` module for patching Stock objects with manually collected quarterly earnings data when API data is delayed. Computes TTM metrics (full 4Q or partial NQ with `sum(NQ) + API_annual × (4-N)/4`), stores data provenance in `stock.extra`, and adds `is_patched` / `data_provenance` properties to Stock. CLI support via `--earnings-patch` flag on `fetch_stock_data.py`.

### Fixed
- **Earnings Patch**: Fixed `_sum_quarter_field` and `_has_any_data` to handle `None` field values (e.g., `depreciation=None`). Extracted `_get_quarter_field` helper that treats `None` as `0.0`.

## [1.4.0] - 2026-05-31

### Fixed
- **YFinanceNewsFetcher**: Fixed date parsing for yfinance news API format change. `pubDate` is now ISO 8601 string instead of Unix timestamp. Added `re` import and proper timezone handling.

### Added
- **DuPont ROE Decomposition**: New `dupont` module with `DuPontAnalysisEngine` for decomposing ROE into driving factors. Supports three-step (NPM × AT × EM) and five-step (Tax × Interest × OpMargin × AT × EM) decomposition. Identifies primary ROE driver, classifies quality, and flags leverage dependency.
- **SOTP Valuation**: New `sotp` module with `SOTPValuation` and `SOTPSegment` for Sum-of-the-Parts valuation of conglomerates and multi-segment companies. Supports per-segment valuation via EV/EBITDA, EV/Revenue, P/E, and Book Value methods, with holdco discount, minority interest, and unallocated cost adjustments. Registered in `ValuationEngine` with `CONGLOMERATE_METHODS` group and `run_conglomerate()` method.

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
