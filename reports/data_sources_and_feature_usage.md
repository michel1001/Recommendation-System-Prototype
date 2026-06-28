# Data Sources and Feature Usage

This document describes the data currently used by the Recommendation-System-Prototype and how each data type is transformed into research signals. The system is decision-support only and does not execute trades.

## 1. Sector Universe

The prototype ranks 10 sector ETFs:

| Sector | ETF |
|---|---|
| Technology | XLK |
| Healthcare | XLV |
| Financials | XLF |
| Energy | XLE |
| Consumer Discretionary | XLY |
| Industrials | XLI |
| Utilities | XLU |
| Materials | XLB |
| Real Estate | XLRE |
| Consumer Staples | XLP |

SPY is used as the broad-market benchmark for relative-strength and ML target construction.

## 2. Market Data

Source: `yfinance`

Function: `load_market_data()` in `src/data_loader.py`

The pipeline downloads OHLCV data for each sector ETF:

- Open
- High
- Low
- Close
- Adj Close
- Volume

The default market period is `5y`.

## 3. Market-Derived Indicators

Module: `src/indicators.py`

The raw OHLCV data is transformed into these features:

| Feature | Calculation | Usage |
|---|---|---|
| `daily_return` | close price percentage change | intermediate return series |
| `cumulative_return` | compounded daily returns | intermediate performance series |
| `ma_20`, `ma_50`, `ma_200` | rolling close-price moving averages | trend context |
| `volatility_20` | 20-day rolling daily-return standard deviation annualized by `sqrt(252)` | risk score |
| `downside_volatility_20` | 20-day rolling standard deviation of negative daily returns, annualized | risk score |
| `momentum_21` | close / close 21 trading days ago - 1 | momentum score and ML feature |
| `momentum_63` | close / close 63 trading days ago - 1 | momentum score and ML feature |
| `momentum_126` | close / close 126 trading days ago - 1 | momentum score and ML feature |
| `drawdown_current` | close / historical max close - 1 | risk score and data-quality checks |
| `distance_to_ma_200` | close / 200-day moving average - 1 | momentum score and ML feature |
| `volume_momentum_20` | current volume / 20-day average volume | ML feature |
| `risk_adjusted_return_63` | 63-day momentum / 20-day volatility | momentum score and ML feature |

## 4. Relative Strength vs SPY

Used in the current pipeline and ML feature set.

| Feature | Calculation |
|---|---|
| `relative_strength_vs_spy_63` | sector ETF 63-day return minus SPY 63-day return |
| `relative_strength_vs_spy_126` | sector ETF 126-day return minus SPY 126-day return |

These features compare each sector ETF against the broad market rather than only measuring absolute performance.

## 5. Fundamental Data

Source: `yfinance.Ticker(ticker).info`

Function: `load_fundamentals()` in `src/data_loader.py`

The prototype currently uses a deliberately small ETF-compatible fundamental set:

| Field | Meaning | Usage |
|---|---|---|
| `trailingPE` | trailing price/earnings ratio if available | fundamental score; lower is better |
| `forwardPE` | forward price/earnings ratio if available | fundamental score; lower is better |
| `priceToBook` | price/book ratio if available | fundamental score; lower is better |
| `dividendYield` | dividend yield if available | fundamental score; higher is better |
| `beta` | market beta if available | risk score via distance from 1 |
| `marketCap` | market capitalization if available | fundamental score; higher is better |

Important limitation: ETF fundamentals from `yfinance` can be sparse, delayed, or inconsistently populated. Missing values remain `NaN`; the system does not invent missing fundamentals.

## 6. How Fundamental Data Is Scored

Function: `calculate_fundamental_score()` in `src/scoring.py`

The score is sector-relative:

- each available field is min-max normalized across sectors;
- lower valuation metrics are treated as better for `trailingPE`, `forwardPE`, and `priceToBook`;
- higher values are treated as better for `dividendYield` and `marketCap`;
- at least two usable fundamental fields are required, otherwise the fundamental score defaults to neutral `50`.

`beta` is not part of the fundamental score. It is used in the risk score as `abs(beta - 1)`, where a value closer to 1 is treated as lower risk.

## 7. Google Trends Data

Status: optional; not used in the stable default `market_fundamental` mode.

Supported providers:

- manual CSV export from Google Trends
- `pytrends` live request
- external API placeholder
- local cache
- deterministic synthetic demo data

Trend output status is stored in `trend_data_status`.

Current stable mode:

```text
trend_data_status = not_used
```

When trend data is used, the following features can be created:

| Feature | Meaning |
|---|---|
| `trend_latest` | latest Google Trends value |
| `trend_momentum_4w` | 4-week trend change |
| `trend_momentum_12w` | 12-week trend change |
| `trend_z_score_12w` | latest value relative to 12-week trend history |
| `trend_z_score_52w` | latest value relative to 52-week trend history |
| `trend_spike` | boolean spike flag |
| `trend_acceleration` | short-term momentum change |
| `trend_volatility` | trend volatility |
| `trend_percentile_52w` | latest value percentile in 52-week window |
| `trend_observations` | number of trend observations |
| `trend_last_date` | latest trend date |

Demo trend values are synthetic and must not be interpreted as real search interest.

## 8. Optional Finnhub News/Social Sentiment

Status: optional; disabled by default.

Source: Finnhub news sentiment endpoint.

Current local testing showed Finnhub returned HTTP 403 for the news-sentiment endpoint, so this source is currently not reliably available. The module handles this safely by marking sentiment status as invalid or unavailable instead of crashing.

Representative company tickers are mapped to each sector, for example:

- Technology: AAPL, MSFT, NVDA, AMD, AVGO
- Healthcare: UNH, JNJ, LLY, PFE, MRK
- Financials: JPM, BAC, WFC, GS, MS

Potential sentiment fields:

| Field | Meaning |
|---|---|
| `sentiment_score` | aggregated company sentiment score |
| `sentiment_score_component` | sentiment score scaled to 0-100 |
| `sentiment_bullish_percent` | average/weighted bullish percentage |
| `sentiment_bearish_percent` | average/weighted bearish percentage |
| `sentiment_buzz` | Finnhub buzz measure |
| `sentiment_article_count` | total article count used for aggregation |
| `sentiment_coverage_count` | number of companies with usable sentiment |
| `sentiment_data_status` | data status such as `live`, `cache`, `invalid_api_key`, `no_data`, or `not_used` |
| `sentiment_provider` | provider name |

Finnhub sentiment is treated as external black-box alternative data. It is not fully explainable and is never used as standalone investment advice.

## 9. Main Output Files

| File | Purpose |
|---|---|
| `data/processed/recommendation_scores.csv` | main dashboard input and sector ranking |
| `data/reports/recommendation_scores.csv` | report copy of the ranking |
| `reports/html/sector_monitoring_report.html` | generated HTML report |
| `data/processed/ml_training_dataset.csv` | historical ML dataset |
| `data/processed/ml_predictions.csv` | ML predictions on test data |
| `data/processed/ml_evaluation_metrics.csv` | model evaluation metrics |
| `data/processed/ml_feature_importance.csv` | feature importance for tree-based classifier |
| `models/sector_model.pkl` | trained ML model bundle |
| `models/feature_columns.json` | exact feature columns used by the trained model |

## 10. Current Stable Data Interpretation

The stable run is:

```bash
python src/pipeline.py --mode market_fundamental
```

It uses:

- ETF market data;
- market-derived indicators;
- SPY-relative strength;
- available yfinance fundamentals;
- no Google Trends;
- no Finnhub sentiment.

This is a research baseline, not a financial recommendation system.
