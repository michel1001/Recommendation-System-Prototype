# ML Methodology

This document describes the current modelling approach in the Recommendation-System-Prototype.

The project is a research and decision-support prototype. It does not generate buy/sell orders and does not provide financial advice.

## 1. Modelling Approach

The project now uses one productive modelling approach:

- a supervised machine-learning classifier;
- target: whether a sector ETF outperforms SPY over the next 4 weeks;
- main model: `RandomForestClassifier`;
- final ranking: sorted by `ml_predicted_outperform_probability`.

The previous rule-based ranking layer has been removed from the active pipeline, dashboard, database export, and final output contract.

## 2. Pipeline

```text
SQLite data
-> Data Cleaning
-> Feature Engineering
-> time-based Train/Test Split
-> RandomForestClassifier
-> Outperformance Probability
-> Ranking/Dashboard
```

## 3. Feature Set

The model keeps the engineered features that describe current sector state:

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

The full research feature set can additionally include Google Trends and sentiment fields when reliable historical inputs are available. The current stable model can run without active Google Trends inputs.

## 4. Target Definition

The prediction horizon is 21 trading days, approximately 4 weeks.

```text
target_outperform_spy_4w = 1 if sector_forward_return_4w > spy_forward_return_4w else 0
```

The model therefore predicts sector ETF outperformance against the benchmark ETF SPY, not an absolute return and not a trading action.

## 5. Training and Validation

The dataset is split chronologically:

- earlier rows are used for training;
- later rows are used for testing.

This time-based split avoids random leakage across the time series and reduces look-ahead bias.

Classification metrics:

- accuracy;
- precision;
- recall;
- F1;
- ROC AUC.

## 6. Output Contract

The final ML ranking contains:

- rank;
- date;
- sector;
- ETF ticker;
- ML outperformance probability versus SPY;
- model confidence;
- model status;
- data readiness status;
- short ML interpretation;
- model input features used for traceability.

Feature importance is generated from the Random Forest classifier when available.

## 7. Interpretation

The output is a research signal for analyst review. It is not investment advice, not a buy/sell recommendation, and not autonomous trading logic.
