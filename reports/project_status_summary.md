# Project Status Summary

The prototype now focuses exclusively on supervised machine learning for sector ETF outperformance prediction.

## Active Model

- Productive model: `RandomForestClassifier`
- Target: sector ETF outperformance versus SPY over the next 4 weeks
- Ranking basis: `ml_predicted_outperform_probability`
- Validation: time-based train/test split

## Active Pipeline

```text
SQLite data
-> Data Cleaning
-> Feature Engineering
-> time-based Train/Test Split
-> RandomForestClassifier
-> Outperformance Probability
-> Ranking/Dashboard
```

## Active Outputs

- `data/processed/ml_sector_ranking.csv`
- `data/processed/ml_predictions.csv`
- `data/processed/ml_evaluation_metrics.csv`
- `data/processed/ml_feature_importance.csv`
- `models/sector_model.pkl`
- `reports/html/sector_monitoring_report.html`

## Notes

Google Trends remains an optional prepared feature source. The current stable model can operate on market/fundamental features without active trend inputs.

The output is a research signal for analyst review and is not investment advice or a trading instruction.
