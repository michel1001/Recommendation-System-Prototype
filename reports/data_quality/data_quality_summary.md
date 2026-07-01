# Data Quality Summary Report

## 1. Database Overview
- Database path: `C:\Users\miche\Recommendation-System-Prototype\data\database\sector_monitoring.db`
- Generated timestamp: 2026-07-01 18:54:56

| table_name | row_count | status |
| --- | --- | --- |
| sectors | 11 | OK |
| market_prices | 15060 | OK |
| market_indicators | 15060 | OK |
| fundamentals | 11 | OK |
| google_trends | 0 | EMPTY |
| trend_features | 0 | EMPTY |
| recommendation_scores | 21 | OK |
| pipeline_runs | 2 | OK |

## 2. Sector Coverage
- Expected sector count: 11
- Actual sector count: 11
- Missing sectors: none
- Communication Services / XLC status: OK

| expected_sector | expected_ticker | present_in_db | ticker_in_db | status |
| --- | --- | --- | --- | --- |
| Technology | XLK | True | XLK | OK |
| Healthcare | XLV | True | XLV | OK |
| Financials | XLF | True | XLF | OK |
| Energy | XLE | True | XLE | OK |
| Consumer Discretionary | XLY | True | XLY | OK |
| Industrials | XLI | True | XLI | OK |
| Utilities | XLU | True | XLU | OK |
| Materials | XLB | True | XLB | OK |
| Real Estate | XLRE | True | XLRE | OK |
| Consumer Staples | XLP | True | XLP | OK |
| Communication Services | XLC | True | XLC | OK |

## 3. Market Data Coverage
- SPY benchmark status: OK
- Market price rows: 15060

| sector | ticker | row_count | min_date | max_date | number_of_missing_close | number_of_missing_adj_close | number_of_missing_volume | duplicate_date_rows | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Benchmark | SPY | 1255 | 2021-07-01 | 2026-07-01 | 0 | 0 | 0 | 0 | OK |
| Communication Services | XLC | 1255 | 2021-07-01 | 2026-07-01 | 0 | 0 | 0 | 0 | OK |
| Consumer Discretionary | XLY | 1255 | 2021-07-01 | 2026-07-01 | 0 | 0 | 0 | 0 | OK |
| Consumer Staples | XLP | 1255 | 2021-07-01 | 2026-07-01 | 0 | 0 | 0 | 0 | OK |
| Energy | XLE | 1255 | 2021-07-01 | 2026-07-01 | 0 | 0 | 0 | 0 | OK |
| Financials | XLF | 1255 | 2021-07-01 | 2026-07-01 | 0 | 0 | 0 | 0 | OK |
| Healthcare | XLV | 1255 | 2021-07-01 | 2026-07-01 | 0 | 0 | 0 | 0 | OK |
| Industrials | XLI | 1255 | 2021-07-01 | 2026-07-01 | 0 | 0 | 0 | 0 | OK |
| Materials | XLB | 1255 | 2021-07-01 | 2026-07-01 | 0 | 0 | 0 | 0 | OK |
| Real Estate | XLRE | 1255 | 2021-07-01 | 2026-07-01 | 0 | 0 | 0 | 0 | OK |
| Technology | XLK | 1255 | 2021-07-01 | 2026-07-01 | 0 | 0 | 0 | 0 | OK |
| Utilities | XLU | 1255 | 2021-07-01 | 2026-07-01 | 0 | 0 | 0 | 0 | OK |

## 4. Market Indicator Quality
Rolling indicators naturally contain NULL values in early rows because they require historical windows. The status below focuses on recent rows, defined as the latest 30 available dates per ticker.

| sector | ticker | row_count | min_date | max_date | missing_momentum_21_pct | missing_momentum_63_pct | missing_momentum_126_pct | missing_volatility_20_pct | missing_drawdown_current_pct | missing_relative_strength_vs_spy_63_pct | missing_relative_strength_vs_spy_126_pct | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Benchmark | SPY | 1255 | 2021-07-01 | 2026-07-01 | 1.67 | 5.02 | 10.04 | 1.59 | 0.0 | 100.0 | 100.0 | OK |
| Communication Services | XLC | 1255 | 2021-07-01 | 2026-07-01 | 1.67 | 5.02 | 10.04 | 1.59 | 0.0 | 5.02 | 10.04 | OK |
| Consumer Discretionary | XLY | 1255 | 2021-07-01 | 2026-07-01 | 1.67 | 5.02 | 10.04 | 1.59 | 0.0 | 5.02 | 10.04 | OK |
| Consumer Staples | XLP | 1255 | 2021-07-01 | 2026-07-01 | 1.67 | 5.02 | 10.04 | 1.59 | 0.0 | 5.02 | 10.04 | OK |
| Energy | XLE | 1255 | 2021-07-01 | 2026-07-01 | 1.67 | 5.02 | 10.04 | 1.59 | 0.0 | 5.02 | 10.04 | OK |
| Financials | XLF | 1255 | 2021-07-01 | 2026-07-01 | 1.67 | 5.02 | 10.04 | 1.59 | 0.0 | 5.02 | 10.04 | OK |
| Healthcare | XLV | 1255 | 2021-07-01 | 2026-07-01 | 1.67 | 5.02 | 10.04 | 1.59 | 0.0 | 5.02 | 10.04 | OK |
| Industrials | XLI | 1255 | 2021-07-01 | 2026-07-01 | 1.67 | 5.02 | 10.04 | 1.59 | 0.0 | 5.02 | 10.04 | OK |
| Materials | XLB | 1255 | 2021-07-01 | 2026-07-01 | 1.67 | 5.02 | 10.04 | 1.59 | 0.0 | 5.02 | 10.04 | OK |
| Real Estate | XLRE | 1255 | 2021-07-01 | 2026-07-01 | 1.67 | 5.02 | 10.04 | 1.59 | 0.0 | 5.02 | 10.04 | OK |
| Technology | XLK | 1255 | 2021-07-01 | 2026-07-01 | 1.67 | 5.02 | 10.04 | 1.59 | 0.0 | 5.02 | 10.04 | OK |
| Utilities | XLU | 1255 | 2021-07-01 | 2026-07-01 | 1.67 | 5.02 | 10.04 | 1.59 | 0.0 | 5.02 | 10.04 | OK |

## 5. Fundamental Data Quality
ETF fundamentals from yfinance may be incomplete, especially forward valuation and market-cap fields. OK means at least 3 of 6 tracked fields are available.

| sector | ticker | trailing_pe_available | forward_pe_available | price_to_book_available | dividend_yield_available | beta_available | market_cap_available | missing_field_count | available_field_count | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Communication Services | XLC | True | False | False | True | False | False | 4 | 2 | PARTIAL |
| Consumer Discretionary | XLY | True | False | True | True | False | False | 3 | 3 | OK |
| Consumer Staples | XLP | True | False | True | True | False | False | 3 | 3 | OK |
| Energy | XLE | True | False | True | True | False | False | 3 | 3 | OK |
| Financials | XLF | True | False | True | True | False | False | 3 | 3 | OK |
| Healthcare | XLV | True | False | True | True | False | False | 3 | 3 | OK |
| Industrials | XLI | True | False | True | True | False | False | 3 | 3 | OK |
| Materials | XLB | True | False | True | True | False | False | 3 | 3 | OK |
| Real Estate | XLRE | True | False | False | True | False | False | 4 | 2 | PARTIAL |
| Technology | XLK | True | False | True | True | False | False | 3 | 3 | OK |
| Utilities | XLU | True | False | True | True | False | False | 3 | 3 | OK |

## 6. Google Trends Data Quality
Google Trends data is optional in market/fundamental mode. If raw trends are missing, import manual CSV exports with `src/import_trends_csv.py`.

| sector | has_raw_trends | raw_trend_rows | number_of_keywords | min_trend_date | max_trend_date | has_trend_features | trend_feature_rows | latest_trend_feature_date | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Technology | False | 0 | 0 |  |  | False | 0 |  | NOT_USED |
| Healthcare | False | 0 | 0 |  |  | False | 0 |  | NOT_USED |
| Financials | False | 0 | 0 |  |  | False | 0 |  | NOT_USED |
| Energy | False | 0 | 0 |  |  | False | 0 |  | NOT_USED |
| Consumer Discretionary | False | 0 | 0 |  |  | False | 0 |  | NOT_USED |
| Industrials | False | 0 | 0 |  |  | False | 0 |  | NOT_USED |
| Utilities | False | 0 | 0 |  |  | False | 0 |  | NOT_USED |
| Materials | False | 0 | 0 |  |  | False | 0 |  | NOT_USED |
| Real Estate | False | 0 | 0 |  |  | False | 0 |  | NOT_USED |
| Consumer Staples | False | 0 | 0 |  |  | False | 0 |  | NOT_USED |
| Communication Services | False | 0 | 0 |  |  | False | 0 |  | NOT_USED |

## 7. Recommendation Output Quality
- Latest run id: run-20260701160825-d5a38343
- Latest run timestamp: 2026-07-01T16:08:25.628448+00:00
- Number of sectors in latest run: 11
- Operating mode: market_fundamental
- Scoring profile: market_fundamental_only
- Missing total_score: 0
- Missing recommendation: 0
- Missing data_quality_status: 0
- Missing actionability_status: 0
- Missing ML predictions: 0
- Status: OK

## 8. Pipeline Run History
- Number of runs: 2
- Latest run timestamp: 2026-07-01T16:08:25.628448+00:00
- Latest operating mode: market_fundamental
- Latest trend mode: auto
- Latest use_ml: 1
- Latest use_sentiment: 0
- Latest status: completed

## 9. Key Data Quality Issues
- google_trends table is empty; import manual Google Trends CSVs for full mode.
- trend_features table is empty; trend feature scoring cannot use DB trend inputs yet.
- fundamentals beta is missing for most ETFs.
- fundamentals market_cap is missing for most ETFs.
- ETF fundamentals are partially incomplete; this is common for yfinance ETF fields.

## 10. Recommended Next Steps
- Import manual Google Trends CSVs with src/import_trends_csv.py.
- Review missing ETF fundamental fields and document yfinance limitations.
- Re-run python src/verify_database.py.
- Re-run python src/pipeline.py --mode market_fundamental --data-source db.
