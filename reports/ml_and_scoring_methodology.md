# ML, Statistical, and Heuristic Methodology

This document explains the machine learning, statistical, and rule-based methods used in the Recommendation-System-Prototype.

The project is a research and decision-support prototype. It does not generate buy/sell orders and does not provide financial advice.

## 1. Overall Design

The system has two parallel research layers:

1. an explainable rule-based scoring layer;
2. a supervised ML layer.

The rule-based score is the transparent baseline. The ML layer is the actual predictive AI component.

## 2. Operating Modes

### `market_fundamental`

Stable default mode.

Uses:

- market indicators;
- risk indicators;
- relative strength versus SPY;
- available fundamentals.

Does not use:

- Google Trends;
- Finnhub sentiment.

### `full`

Research mode that can include:

- Google Trends attention features;
- optional Finnhub sentiment features;
- market indicators;
- fundamentals;
- ML outputs.

This mode depends more heavily on external data availability.

### `demo`

Demonstration mode using synthetic Google Trends data. Outputs are prototype-only.

## 3. Statistical Transformations

### Returns

Daily returns are computed as:

```text
daily_return = close_t / close_t-1 - 1
```

Cumulative returns are computed by compounding daily returns.

### Volatility

20-day volatility is computed as:

```text
rolling_std(daily_return, 20) * sqrt(252)
```

This annualizes recent daily volatility.

### Downside Volatility

Downside volatility uses only negative daily returns:

```text
rolling_std(negative_daily_returns, 20) * sqrt(252)
```

Missing downside volatility is filled with `0.0` when no negative returns are present in the window.

### Momentum

Momentum is calculated over three windows:

```text
momentum_21  = close_t / close_t-21  - 1
momentum_63  = close_t / close_t-63  - 1
momentum_126 = close_t / close_t-126 - 1
```

These correspond approximately to 1 month, 3 months, and 6 months of trading days.

### Drawdown

Current drawdown is:

```text
drawdown_current = close_t / max(close_so_far) - 1
```

This measures how far the current ETF price is below its historical high in the selected period.

### Distance to 200-Day Moving Average

```text
distance_to_ma_200 = close_t / moving_average_200 - 1
```

Positive values indicate the ETF is trading above its 200-day moving average.

### Risk-Adjusted Return

```text
risk_adjusted_return_63 = momentum_63 / volatility_20
```

This is a simple momentum-per-risk heuristic.

### Relative Strength vs SPY

```text
relative_strength_vs_spy_63 = sector_return_63 - spy_return_63
relative_strength_vs_spy_126 = sector_return_126 - spy_return_126
```

These features compare sector ETF performance against the broad market.

## 4. Rule-Based Scoring

Module: `src/scoring.py`

The rule-based score uses sector-relative normalization. Most score components are min-max scaled across sectors to a 0-100 range.

If all values are missing or identical, the component defaults to neutral `50`.

### Momentum Score

Inputs:

- `momentum_21`
- `momentum_63`
- `momentum_126`
- `distance_to_ma_200`
- `risk_adjusted_return_63`

Higher values are better. The component is the average of available normalized inputs.

### Risk Score

Inputs:

- `volatility_20`
- `downside_volatility_20`
- absolute current drawdown magnitude
- beta distance from 1

Lower risk is better. Volatility, downside volatility, drawdown magnitude, and beta distance are reverse-scored.

### Fundamental Score

Inputs:

- `trailingPE`
- `forwardPE`
- `priceToBook`
- `dividendYield`
- `marketCap`

Rules:

- lower `trailingPE`, `forwardPE`, and `priceToBook` are better;
- higher `dividendYield` and `marketCap` are better;
- at least two usable fields are required;
- otherwise the score defaults to neutral `50`.

### Trend Score

Inputs, when Google Trends is active:

- trend z-scores;
- trend momentum;
- trend acceleration;
- trend percentile;
- spike flag;
- trend volatility.

Special handling:

- `trend_data_status = not_used` produces trend score `0` in market/fundamental mode;
- fallback trend data is neutralized;
- demo trend score is slightly penalized.

### Sentiment Score Component

Optional full-mode component.

Inputs:

- `sentiment_score_component`;
- fallback from `sentiment_score * 100`.

Only usable sentiment statuses are included:

- `live`
- `cache`
- `available`
- `demo`

Unavailable statuses such as `invalid_api_key`, `no_data`, `missing`, or `not_used` are not treated as real sentiment.

## 5. Total Score Weights

### Market/Fundamental Mode

```text
momentum_score     40%
fundamental_score  30%
risk_score         30%
trend_score         0%
```

Google Trends is intentionally excluded.

### Full Mode Without Usable Sentiment

When sentiment is missing, the sentiment weight is redistributed across the other non-sentiment components:

```text
trend_score        30.00%
momentum_score     31.82%
fundamental_score  25.45%
risk_score         12.73%
```

This avoids faking sentiment.

### Full Mode With Usable Sentiment

```text
trend_score                 30%
sentiment_score_component   15%
momentum_score              25%
fundamental_score           20%
risk_score                  10%
```

Sentiment is supporting alternative data only.

### Demo Mode

Demo mode uses the original full trend-market-fundamental weights but caps interpretation as prototype-only.

## 6. Synergy Labels

The system assigns heuristic labels to make the score easier to interpret:

| Label | Rule |
|---|---|
| Trend-confirmed opportunity | high trend, positive momentum, acceptable fundamentals |
| Early attention signal | high trend but weak momentum |
| Hype risk | high trend but weak fundamentals |
| Fundamental sleeper | low trend but strong fundamentals |
| Weak setup | weak trend and weak momentum |
| Balanced setup | mixed or moderate signals |

These labels are explanations, not trading instructions.

## 7. Data Quality and Actionability Gates

The system explicitly separates signal generation from actionability.

Examples:

- demo trend data -> `Prototype only`
- missing market data -> `Insufficient data`
- market/fundamental with valid market inputs -> `Market/fundamental research signal`
- unvalidated research signal -> `Research only`

The system intentionally avoids buy/sell language.

## 8. Supervised ML Dataset

Module: `src/ml_dataset.py`

The ML dataset is built as a sector-date supervised learning table.

For each sector ETF and date, it stores engineered features available at that time. The future return is used only as the target.

### ML Feature Sets

`market_fundamental` feature set:

- `momentum_21`
- `momentum_63`
- `momentum_126`
- `volatility_20`
- `downside_volatility_20`
- `drawdown_current`
- `distance_to_ma_200`
- `risk_adjusted_return_63`
- `volume_momentum_20`
- `relative_strength_vs_spy_63`
- `relative_strength_vs_spy_126`

`full` feature set additionally can include:

- Google Trends features;
- sentiment features.

When demo trend or demo sentiment data is used, `ml_data_quality` is marked as prototype-only.

## 9. ML Prediction Targets

The forward horizon is 21 trading days, approximately 4 weeks.

### Classification Target

```text
target_outperform_spy_4w = 1 if sector_forward_return_4w > spy_forward_return_4w else 0
```

This predicts whether the sector ETF outperforms SPY over the next 4 weeks.

### Regression Target

```text
target_excess_return_4w = sector_forward_return_4w - spy_forward_return_4w
```

This predicts expected 4-week excess return versus SPY.

## 10. ML Algorithms

Module: `src/ml_model.py`

### Classification Models

The classification task trains:

- Logistic Regression
- Random Forest Classifier

If the training target has only one class, a Dummy Classifier is used as a safe fallback.

### Regression Models

The regression task trains:

- Ridge Regression
- Random Forest Regressor

### Preprocessing

The linear models use:

- `SimpleImputer`
- `StandardScaler`

Tree models use:

- `SimpleImputer`

### Model Selection

Best classifier:

```text
sort by f1, then accuracy
```

Best regressor:

```text
lowest RMSE
```

The selected model bundle is saved to:

```text
models/sector_model.pkl
```

The exact training feature columns are saved to:

```text
models/feature_columns.json
```

## 11. ML Evaluation Metrics

Classification metrics:

- accuracy
- precision
- recall
- F1
- ROC AUC

Regression metrics:

- MAE
- RMSE
- R²
- directional accuracy

The model uses a time-based train/test split, not a random split, to reduce time-series leakage.

## 12. ML Backtest-Style Evaluation

Module: `src/ml_evaluation.py`

The ML evaluation creates a simple monthly research simulation:

1. take the latest sector prediction per month;
2. rank sectors by predicted outperformance probability;
3. select the top sectors;
4. calculate average realized 4-week excess return;
5. compare against an equal-weight sector excess-return baseline.

Metrics include:

- cumulative excess return;
- average excess return;
- volatility;
- hit rate;
- number of periods.

This is not a production-grade trading backtest. It is a research diagnostic.

## 13. Current Interpretation

The current stable model and scoring system should be interpreted as:

- educational;
- explainable;
- research-only;
- not investment advice;
- not autonomous trading.

The ML layer is the actual AI prediction component. The rule-based score is the transparent heuristic baseline.

Before any stronger conclusion, the project would need:

- reliable real Google Trends data;
- validated sentiment data or a different sentiment provider;
- stronger historical backtesting;
- better point-in-time fundamental data;
- human analyst review.
