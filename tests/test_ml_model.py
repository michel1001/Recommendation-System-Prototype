import numpy as np
import pandas as pd

from src.ml_model import evaluate_models, predict_current_signals, time_based_train_test_split
from src.ml_dataset import MARKET_FEATURE_COLUMNS, TREND_FEATURE_COLUMNS


def _synthetic_ml_dataset(rows=160):
    rng = np.random.default_rng(42)
    dates = pd.date_range("2020-01-01", periods=rows, freq="B")
    frame = pd.DataFrame({"date": dates, "sector": ["Technology" if i % 2 else "Energy" for i in range(rows)], "ticker": ["XLK" if i % 2 else "XLE" for i in range(rows)]})
    for column in MARKET_FEATURE_COLUMNS + TREND_FEATURE_COLUMNS:
        frame[column] = rng.normal(0, 1, rows)
    signal = frame["momentum_21"] + frame["trend_momentum_4w"] * .5
    frame["target_excess_return_4w"] = signal * .01 + rng.normal(0, .01, rows)
    frame["target_outperform_spy_4w"] = frame["target_excess_return_4w"].gt(0).astype(int)
    frame["trend_data_status"] = "demo"
    frame["ml_data_quality"] = "prototype_only"
    frame["feature_set"] = "full"
    return frame


def test_time_based_split_preserves_chronology():
    data = _synthetic_ml_dataset()
    train, test = time_based_train_test_split(data, train_ratio=.7)

    assert train["date"].max() < test["date"].min()
    assert len(train) > len(test)


def test_model_training_and_current_predictions_on_synthetic_data():
    data = _synthetic_ml_dataset()
    bundle, metrics, predictions = evaluate_models(data)
    current = data.tail(5).drop(columns=["target_outperform_spy_4w", "target_excess_return_4w"])
    scored = predict_current_signals(current, model_bundle=bundle)

    assert not metrics.empty
    assert not predictions.empty
    assert {"ml_predicted_outperform_probability", "ml_model_status"}.issubset(scored.columns)
    assert scored["ml_model_status"].eq("trained_demo_trends").all()
