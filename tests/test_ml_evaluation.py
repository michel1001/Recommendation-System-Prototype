import numpy as np
import pandas as pd

from src.ml_evaluation import calculate_ml_backtest


def test_ml_backtest_calculates_metrics_from_predictions():
    rows = []
    for month in pd.date_range("2024-01-31", periods=6, freq="ME"):
        for idx, sector in enumerate(["Technology", "Energy", "Utilities"]):
            rows.append({
                "date": month,
                "sector": sector,
                "ticker": sector[:3],
                "ml_predicted_outperform_probability": .8 - idx * .2,
                "target_excess_return_4w": .02 - idx * .01,
            })
    predictions = pd.DataFrame(rows)

    results, metrics = calculate_ml_backtest(predictions, top_n=2)

    assert len(results) == 6
    assert {"ml_portfolio_excess_return", "ml_cumulative_excess_return"}.issubset(results.columns)
    assert not metrics.empty
    assert metrics["strategy"].str.contains("ML top sectors").any()
