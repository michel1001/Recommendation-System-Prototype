"""Evaluate the ML layer and create simple research backtest artifacts."""

from __future__ import annotations

import sys
from pathlib import Path
import json

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    ML_BACKTEST_METRICS_PATH,
    ML_BACKTEST_RESULTS_PATH,
    ML_EVALUATION_METRICS_PATH,
    ML_FEATURE_IMPORTANCE_PATH,
    ML_PREDICTIONS_PATH,
    ML_TRAINING_DATASET_PATH,
    MODEL_METADATA_PATH,
    ensure_directories,
)
from src.ml_model import load_model


def calculate_feature_importance(model_bundle: dict | None = None) -> pd.DataFrame:
    model_bundle = model_bundle or load_model()
    if model_bundle is None:
        return pd.DataFrame(columns=["feature", "importance", "model"])
    model = model_bundle.get("classifier")
    feature_columns = model_bundle.get("feature_columns", [])
    estimator = model[-1] if model is not None else None
    if not hasattr(estimator, "feature_importances_"):
        return pd.DataFrame(columns=["feature", "importance", "model"])
    return pd.DataFrame({"feature": feature_columns, "importance": estimator.feature_importances_, "model": model_bundle.get("classifier_name", "")}).sort_values("importance", ascending=False)


def calculate_ml_backtest(predictions: pd.DataFrame, top_n: int = 3) -> tuple[pd.DataFrame, pd.DataFrame]:
    if predictions.empty:
        return pd.DataFrame(), pd.DataFrame()
    data = predictions.copy()
    data["date"] = pd.to_datetime(data["date"])
    data["rebalance_month"] = data["date"].dt.to_period("M").dt.to_timestamp()
    month_rows = []
    for month, group in data.sort_values("date").groupby("rebalance_month"):
        latest_date = group["date"].max()
        snapshot = group[group["date"].eq(latest_date)].sort_values("ml_predicted_outperform_probability", ascending=False)
        selected = snapshot.head(top_n)
        if selected.empty:
            continue
        portfolio_excess = selected["target_excess_return_4w"].mean()
        equal_weight_excess = snapshot["target_excess_return_4w"].mean()
        month_rows.append({
            "rebalance_date": latest_date,
            "selected_sectors": ", ".join(selected["sector"].astype(str)),
            "ml_portfolio_excess_return": portfolio_excess,
            "equal_weight_excess_return": equal_weight_excess,
        })
    results = pd.DataFrame(month_rows)
    if results.empty:
        return results, pd.DataFrame()
    results["ml_cumulative_excess_return"] = (1 + results["ml_portfolio_excess_return"]).cumprod() - 1
    results["equal_weight_cumulative_excess_return"] = (1 + results["equal_weight_excess_return"]).cumprod() - 1
    metrics = pd.DataFrame([
        _strategy_metrics(results["ml_portfolio_excess_return"], "ML top sectors", len(results)),
        _strategy_metrics(results["equal_weight_excess_return"], "Equal-weight sector excess", len(results)),
    ])
    return results, metrics


def _strategy_metrics(returns: pd.Series, strategy: str, periods: int) -> dict:
    returns = pd.to_numeric(returns, errors="coerce").dropna()
    if returns.empty:
        return {"strategy": strategy, "cumulative_excess_return": np.nan, "average_excess_return": np.nan, "volatility": np.nan, "hit_rate": np.nan, "periods": periods}
    return {
        "strategy": strategy,
        "cumulative_excess_return": float((1 + returns).prod() - 1),
        "average_excess_return": float(returns.mean()),
        "volatility": float(returns.std()),
        "hit_rate": float(returns.gt(0).mean()),
        "periods": periods,
    }


def evaluate_ml_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ensure_directories()
    predictions = pd.read_csv(ML_PREDICTIONS_PATH, parse_dates=["date"]) if ML_PREDICTIONS_PATH.exists() else pd.DataFrame()
    feature_importance = calculate_feature_importance()
    backtest_results, backtest_metrics = calculate_ml_backtest(predictions)
    feature_set = "unknown"
    if MODEL_METADATA_PATH.exists():
        feature_set = json.loads(MODEL_METADATA_PATH.read_text(encoding="utf-8")).get("feature_set", "unknown")
    for frame in (feature_importance, backtest_results, backtest_metrics):
        if not frame.empty:
            frame["feature_set"] = feature_set
    feature_importance.to_csv(ML_FEATURE_IMPORTANCE_PATH, index=False)
    backtest_results.to_csv(ML_BACKTEST_RESULTS_PATH, index=False)
    backtest_metrics.to_csv(ML_BACKTEST_METRICS_PATH, index=False)
    return feature_importance, backtest_results, backtest_metrics


def main() -> int:
    if not ML_EVALUATION_METRICS_PATH.exists():
        print("[WARN] ML model metrics not found. Run python src/ml_model.py first.")
    if not ML_TRAINING_DATASET_PATH.exists():
        print("[WARN] ML training dataset not found. Run python src/ml_dataset.py first.")
    feature_importance, backtest_results, backtest_metrics = evaluate_ml_outputs()
    print(f"[OK] ML feature importance exported: {ML_FEATURE_IMPORTANCE_PATH.relative_to(PROJECT_ROOT)} ({len(feature_importance)} rows)")
    print(f"[OK] ML backtest results exported: {ML_BACKTEST_RESULTS_PATH.relative_to(PROJECT_ROOT)} ({len(backtest_results)} rows)")
    print(f"[OK] ML backtest metrics exported: {ML_BACKTEST_METRICS_PATH.relative_to(PROJECT_ROOT)}")
    if ML_TRAINING_DATASET_PATH.exists():
        dataset = pd.read_csv(ML_TRAINING_DATASET_PATH)
        if dataset.get("trend_data_status", pd.Series(dtype=str)).astype(str).str.lower().eq("demo").any():
            print("[WARN] ML results are not investment-grade because trend inputs are synthetic.")
    if not backtest_metrics.empty:
        print(backtest_metrics.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
