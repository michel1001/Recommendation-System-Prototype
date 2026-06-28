# Recommendation-System-Prototype: Project Status Summary

## 1. Current Status

* The pipeline works in `market_fundamental` mode.
* Google Trends is currently not used in the default validated run.
* ML model training works.
* The Streamlit dashboard and HTML report work.
* Tests pass: `29 passed, 1 warning`.

## 2. Current Operating Mode

The default operating mode is `market_fundamental`.

This mode uses ETF market data, risk indicators, relative strength versus SPY, and available fundamental data. Google Trends is disabled in this mode and is shown in the output as:

```text
trend_data_status = not_used
```

This gives the project a stable research baseline even when reliable Google Trends data is unavailable.

## 3. AI / ML Component

The project now includes a supervised machine learning layer.

The ML model predicts:

* the probability that a sector outperforms SPY over the next 4 weeks
* the expected 4-week excess return versus SPY

This is the actual AI component of the prototype.

The rule-based sector score remains in place as an explainable baseline. It helps analysts understand why sectors rank highly before interpreting the ML predictions.

## 4. Google Trends Status

Google Trends integration exists and is technically prepared, but real Google Trends data is not currently used in the default validated run.

The system supports:

* manual CSV Google Trends files
* `pytrends` / live Google Trends loading
* external API placeholder
* cache
* demo data

The current usable run uses:

```text
trend_data_status = not_used
```

This means the current output is a market/fundamental research baseline. A full Google Trends run can be tested later once reliable real trend data is available.

## 5. Current Results

| Sector           | Total Score | Recommendation | Data Quality                       | Actionability | ML Status | ML Probability | ML Excess Return |
| ---------------- | ----------: | -------------- | ---------------------------------- | ------------- | --------- | -------------: | ---------------: |
| Utilities        |      63.666 | Watch          | Market/fundamental research signal | Research only | trained   |       0.506938 |        -0.006119 |
| Healthcare       |      61.157 | Watch          | Market/fundamental research signal | Research only | trained   |       0.504291 |        -0.007258 |
| Materials        |      59.269 | Neutral        | Market/fundamental research signal | Research only | trained   |       0.713467 |        -0.003957 |
| Financials       |      56.420 | Neutral        | Market/fundamental research signal | Research only | trained   |       0.396416 |        -0.004466 |
| Consumer Staples |      55.131 | Neutral        | Market/fundamental research signal | Research only | trained   |       0.456211 |        -0.005075 |

## 6. Validation

The current workflow was validated with:

```bash
python src/pipeline.py --mode market_fundamental
python src/ml_dataset.py --feature-set market_fundamental
python src/ml_model.py
python src/ml_evaluation.py
python src/pipeline.py --mode market_fundamental --use-ml
python src/verify_outputs.py
python -m pytest
```

Result:

```text
29 passed, 1 warning
```

## 7. Interpretation

The current outputs are not stock purchase recommendations.

They are research-only sector signals intended for analyst review. The prototype is designed for decision support, not autonomous trading or direct investment execution.

The current ML layer demonstrates that historical feature generation, supervised model training, prediction, and validation can be integrated into the research workflow. However, the model requires real Google Trends data, stronger historical validation, and more robust backtesting before it could be considered for any investment use.

## 8. Next Steps

* Add real Google Trends manual CSV files.
* Re-run full mode with real trend data.
* Compare `market_fundamental` mode versus full Google Trends mode.
* Improve ML evaluation.
* Add more robust backtesting.
* Prepare dashboard screenshots.
* Use the HTML report in the presentation.
