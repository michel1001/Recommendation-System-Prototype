# Data Sources and Feature Usage

This document describes how data is transformed into machine-learning inputs for the sector ETF outperformance model.

## Market Data

Market prices come from yfinance or the local SQLite database.

Tracked fields include OHLCV and adjusted close values. They are cleaned and transformed into indicators used by the ML model.

## ML Market Features

| Feature | Definition | Usage |
|---|---|---|
| `momentum_21` | close / close 21 trading days ago - 1 | ML input |
| `momentum_63` | close / close 63 trading days ago - 1 | ML input |
| `momentum_126` | close / close 126 trading days ago - 1 | ML input |
| `volatility_20` | 20-day rolling daily-return standard deviation annualized by `sqrt(252)` | ML input |
| `downside_volatility_20` | 20-day rolling standard deviation of negative daily returns, annualized | ML input |
| `drawdown_current` | close / historical max close - 1 | ML input |
| `distance_to_ma_200` | close / 200-day moving average - 1 | ML input |
| `risk_adjusted_return_63` | 63-day momentum / 20-day volatility | ML input |
| `volume_momentum_20` | recent volume compared with trailing volume | ML input |
| `relative_strength_vs_spy_63` | 63-day sector return minus 63-day SPY return | ML input |
| `relative_strength_vs_spy_126` | 126-day sector return minus 126-day SPY return | ML input |

## Fundamental Data

ETF fundamentals are retained when available:

- `trailingPE`
- `forwardPE`
- `priceToBook`
- `dividendYield`
- `beta`
- `marketCap`

Availability can be incomplete for ETFs. Missing values are handled by the model pipeline through imputation where the selected feature set uses those fields.

## Optional Alternative Data

Google Trends features are prepared for full-mode research experiments:

- `trend_latest`
- `trend_momentum_4w`
- `trend_momentum_12w`
- `trend_z_score_12w`
- `trend_z_score_52w`
- `trend_spike`
- `trend_acceleration`
- `trend_percentile_52w`

Sentiment features can also be attached when a provider is configured. These are optional and are not required for the current stable market/fundamental model.

## Final Output

The final dashboard input is:

- `data/processed/ml_sector_ranking.csv`

It contains sector, ETF, date, ML outperformance probability versus SPY, model confidence, data readiness status, and model input features for traceability.
