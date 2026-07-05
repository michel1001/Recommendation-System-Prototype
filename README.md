# Recommendation-System-Prototype

Machine-learning prototype for sector ETF monitoring. The project predicts whether a sector ETF is likely to outperform the benchmark ETF SPY over the next 4 weeks.

This project is for educational and research purposes only. It does not constitute financial advice, investment advice, or a recommendation to buy or sell any financial instrument.

## Current Modelling Focus

The active modelling approach is supervised machine learning:

```text
SQLite data
-> Data Cleaning
-> Feature Engineering
-> time-based Train/Test Split
-> RandomForestClassifier
-> Outperformance Probability
-> Ranking/Dashboard
```

The final sector ranking is derived only from `ml_predicted_outperform_probability`.

## Target

```text
target_outperform_spy_4w = 1
if sector_forward_return_4w > spy_forward_return_4w
else 0
```

The horizon is 21 trading days, approximately 4 weeks.

## Main Features

- Momentum 21 / 63 / 126 trading days
- 20-day volatility
- 20-day downside volatility
- Current drawdown
- Distance to 200-day moving average
- 63-day risk-adjusted return
- 20-day volume momentum
- Relative strength vs. SPY over 63 / 126 trading days
- ETF fundamentals where available

Google Trends and sentiment fields are prepared as optional research features. The current stable model can run without active trend inputs.

## Key Outputs

- `data/processed/ml_training_dataset.csv`
- `models/sector_model.pkl`
- `models/feature_columns.json`
- `models/model_metadata.json`
- `data/processed/ml_predictions.csv`
- `data/processed/ml_feature_importance.csv`
- `data/processed/ml_sector_ranking.csv`
- `reports/html/sector_monitoring_report.html`

## Common Commands

```powershell
python src/refresh_market_data.py
python src/ml_dataset.py
python src/ml_model.py
python src/ml_evaluation.py
python src/pipeline.py --mode market_fundamental --data-source db
python src/verify_outputs.py
python -m streamlit run app/app.py
```

## Validation

The model uses a chronological train/test split rather than a random split. This keeps later observations out of training and reduces look-ahead bias.

Classification metrics include accuracy, precision, recall, F1, and ROC AUC. Feature importance is exported from the Random Forest classifier when available.

## Project Status

The former rule-based ranking layer has been removed from the active pipeline, dashboard, output contract, and database export. Feature engineering remains in place because those fields are model inputs.
