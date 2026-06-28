"""Train and use supervised ML models for sector outperformance research."""

from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, mean_squared_error, precision_score, r2_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import FEATURE_COLUMNS_PATH, ML_EVALUATION_METRICS_PATH, ML_PREDICTIONS_PATH, ML_TRAINING_DATASET_PATH, MODEL_METADATA_PATH, MODEL_PATH, ensure_directories
from src.ml_dataset import MARKET_FEATURE_COLUMNS, SENTIMENT_FEATURE_COLUMNS, TREND_FEATURE_COLUMNS


TARGET_CLASSIFICATION = "target_outperform_spy_4w"
TARGET_REGRESSION = "target_excess_return_4w"
DEFAULT_FEATURE_COLUMNS = MARKET_FEATURE_COLUMNS + TREND_FEATURE_COLUMNS + SENTIMENT_FEATURE_COLUMNS
NON_FEATURE_COLUMNS = {
    "date",
    "sector",
    "ticker",
    "trend_data_status",
    "sentiment_data_status",
    "ml_data_quality",
    "sector_forward_return_4w",
    "spy_forward_return_4w",
    TARGET_CLASSIFICATION,
    TARGET_REGRESSION,
}


def load_ml_dataset(path=ML_TRAINING_DATASET_PATH) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["date"]) if path.exists() else pd.DataFrame()


def select_feature_columns(df: pd.DataFrame) -> list[str]:
    feature_set = str(df["feature_set"].dropna().iloc[0]) if "feature_set" in df.columns and df["feature_set"].notna().any() else "market_fundamental"
    allowed = MARKET_FEATURE_COLUMNS if feature_set == "market_fundamental" else DEFAULT_FEATURE_COLUMNS
    candidates = [column for column in allowed if column in df.columns]
    if candidates:
        return candidates
    return [column for column in df.columns if column not in NON_FEATURE_COLUMNS and pd.api.types.is_numeric_dtype(df[column])]


def time_based_train_test_split(df: pd.DataFrame, train_ratio: float = 0.7) -> tuple[pd.DataFrame, pd.DataFrame]:
    data = df.sort_values("date").reset_index(drop=True)
    split_index = max(1, min(len(data) - 1, int(len(data) * train_ratio)))
    return data.iloc[:split_index].copy(), data.iloc[split_index:].copy()


def _classification_metrics(y_true: pd.Series, probabilities: np.ndarray, labels: np.ndarray) -> dict[str, float]:
    metrics = {
        "accuracy": accuracy_score(y_true, labels),
        "precision": precision_score(y_true, labels, zero_division=0),
        "recall": recall_score(y_true, labels, zero_division=0),
        "f1": f1_score(y_true, labels, zero_division=0),
    }
    try:
        metrics["roc_auc"] = roc_auc_score(y_true, probabilities) if y_true.nunique() > 1 else np.nan
    except ValueError:
        metrics["roc_auc"] = np.nan
    return {key: float(value) if pd.notna(value) else np.nan for key, value in metrics.items()}


def _predict_probability(model, X: pd.DataFrame) -> np.ndarray:
    if hasattr(model[-1], "predict_proba"):
        probabilities = model.predict_proba(X)
        if probabilities.shape[1] == 1:
            klass = int(model[-1].classes_[0]) if hasattr(model[-1], "classes_") else 0
            return np.ones(len(X)) if klass == 1 else np.zeros(len(X))
        return probabilities[:, 1]
    return np.asarray(model.predict(X), dtype=float)


def _regression_metrics(y_true: pd.Series, predictions: np.ndarray) -> dict[str, float]:
    rmse = float(np.sqrt(mean_squared_error(y_true, predictions)))
    directional_accuracy = float((np.sign(y_true) == np.sign(predictions)).mean())
    return {
        "mae": float(mean_absolute_error(y_true, predictions)),
        "rmse": rmse,
        "r2": float(r2_score(y_true, predictions)) if len(y_true) > 1 else np.nan,
        "directional_accuracy": directional_accuracy,
    }


def train_classification_models(df: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    feature_columns = select_feature_columns(df)
    train, test = time_based_train_test_split(df)
    X_train, y_train = train[feature_columns], train[TARGET_CLASSIFICATION]
    X_test, y_test = test[feature_columns], test[TARGET_CLASSIFICATION]
    models = {
        "LogisticRegression": Pipeline([("imputer", SimpleImputer()), ("scaler", StandardScaler()), ("model", LogisticRegression(max_iter=1000))]),
        "RandomForestClassifier": Pipeline([("imputer", SimpleImputer()), ("model", RandomForestClassifier(n_estimators=120, min_samples_leaf=5, random_state=42))]),
    }
    if y_train.nunique() < 2:
        models = {"DummyClassifier": Pipeline([("imputer", SimpleImputer()), ("model", DummyClassifier(strategy="most_frequent"))])}
    rows = []
    fitted = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        probabilities = _predict_probability(model, X_test) if y_train.nunique() > 1 else np.full(len(X_test), float(y_train.mean()))
        labels = (probabilities >= 0.5).astype(int)
        rows.append({"task": "classification", "model": name, **_classification_metrics(y_test, probabilities, labels)})
        fitted[name] = model
    return fitted, pd.DataFrame(rows)


def train_regression_models(df: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    feature_columns = select_feature_columns(df)
    train, test = time_based_train_test_split(df)
    X_train, y_train = train[feature_columns], train[TARGET_REGRESSION]
    X_test, y_test = test[feature_columns], test[TARGET_REGRESSION]
    models = {
        "Ridge": Pipeline([("imputer", SimpleImputer()), ("scaler", StandardScaler()), ("model", Ridge(alpha=1.0))]),
        "RandomForestRegressor": Pipeline([("imputer", SimpleImputer()), ("model", RandomForestRegressor(n_estimators=120, min_samples_leaf=5, random_state=42))]),
    }
    rows = []
    fitted = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)
        rows.append({"task": "regression", "model": name, **_regression_metrics(y_test, predictions)})
        fitted[name] = model
    return fitted, pd.DataFrame(rows)


def evaluate_models(df: pd.DataFrame) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    feature_columns = select_feature_columns(df)
    classifiers, classification_metrics = train_classification_models(df)
    regressors, regression_metrics = train_regression_models(df)
    if classification_metrics.empty or regression_metrics.empty:
        raise ValueError("Not enough data variation to train ML models.")

    best_classifier_name = classification_metrics.sort_values(["f1", "accuracy"], ascending=False).iloc[0]["model"]
    best_regressor_name = regression_metrics.sort_values("rmse", ascending=True).iloc[0]["model"]
    bundle = {
        "classifier": classifiers[best_classifier_name],
        "regressor": regressors[best_regressor_name],
        "classifier_name": best_classifier_name,
        "regressor_name": best_regressor_name,
        "feature_columns": feature_columns,
        "feature_set": str(df["feature_set"].dropna().iloc[0]) if "feature_set" in df.columns and df["feature_set"].notna().any() else "market_fundamental",
        "trained_on_demo_trends": bool(df.get("trend_data_status", pd.Series(dtype=str)).astype(str).str.lower().eq("demo").any()),
        "number_of_rows": int(len(df)),
        "train_start": str(pd.to_datetime(time_based_train_test_split(df)[0]["date"]).min().date()),
        "train_end": str(pd.to_datetime(time_based_train_test_split(df)[0]["date"]).max().date()),
        "test_start": str(pd.to_datetime(time_based_train_test_split(df)[1]["date"]).min().date()),
        "test_end": str(pd.to_datetime(time_based_train_test_split(df)[1]["date"]).max().date()),
    }

    test = time_based_train_test_split(df)[1].copy()
    probabilities = _predict_probability(bundle["classifier"], test[feature_columns])
    excess_return = bundle["regressor"].predict(test[feature_columns])
    keep_columns = ["date", "sector", "ticker", TARGET_CLASSIFICATION, TARGET_REGRESSION, "trend_data_status", "ml_data_quality", "feature_set"]
    predictions = test[[column for column in keep_columns if column in test.columns]].copy()
    predictions["ml_predicted_outperform_probability"] = probabilities
    predictions["ml_predicted_excess_return_4w"] = excess_return
    predictions["ml_model_status"] = "trained"
    predictions["ml_model_confidence"] = (np.abs(probabilities - 0.5) * 2 * 100).clip(0, 100)
    metrics = pd.concat([classification_metrics, regression_metrics], ignore_index=True)
    return bundle, metrics, predictions


def save_best_model(bundle: dict, metrics: pd.DataFrame, predictions: pd.DataFrame, model_path=MODEL_PATH) -> object:
    ensure_directories()
    model_path.parent.mkdir(parents=True, exist_ok=True)
    with model_path.open("wb") as handle:
        pickle.dump(bundle, handle)
    FEATURE_COLUMNS_PATH.write_text(json.dumps(bundle["feature_columns"], indent=2), encoding="utf-8")
    MODEL_METADATA_PATH.write_text(json.dumps({
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "feature_set": bundle.get("feature_set", "market_fundamental"),
        "target": {"classification": TARGET_CLASSIFICATION, "regression": TARGET_REGRESSION},
        "number_of_rows": bundle.get("number_of_rows"),
        "train_start": bundle.get("train_start"),
        "train_end": bundle.get("train_end"),
        "test_start": bundle.get("test_start"),
        "test_end": bundle.get("test_end"),
        "classification_model": bundle.get("classifier_name"),
        "regression_model": bundle.get("regressor_name"),
        "trained_on_demo_trends": bundle.get("trained_on_demo_trends"),
    }, indent=2), encoding="utf-8")
    metrics.to_csv(ML_EVALUATION_METRICS_PATH, index=False)
    predictions.to_csv(ML_PREDICTIONS_PATH, index=False)
    return model_path


def load_model(model_path=MODEL_PATH) -> dict | None:
    if not model_path.exists():
        return None
    with model_path.open("rb") as handle:
        return pickle.load(handle)


def predict_current_signals(current_feature_df: pd.DataFrame, model_bundle: dict | None = None) -> pd.DataFrame:
    result = current_feature_df.copy()
    if model_bundle is None:
        model_bundle = load_model()
    if model_bundle is None:
        result["ml_predicted_outperform_probability"] = np.nan
        result["ml_predicted_excess_return_4w"] = np.nan
        result["ml_model_status"] = "not_trained"
        result["ml_model_confidence"] = 0.0
        return result
    feature_columns = model_bundle["feature_columns"]
    missing_features = [column for column in feature_columns if column not in result.columns]
    if missing_features:
        result["ml_predicted_outperform_probability"] = np.nan
        result["ml_predicted_excess_return_4w"] = np.nan
        result["ml_model_status"] = "feature_mismatch"
        result["ml_model_confidence"] = 0.0
        result["ml_feature_mismatch_detail"] = ", ".join(missing_features)
        return result
    for column in feature_columns:
        if column not in result.columns:
            result[column] = np.nan
    probabilities = _predict_probability(model_bundle["classifier"], result[feature_columns])
    result["ml_predicted_outperform_probability"] = probabilities
    result["ml_predicted_excess_return_4w"] = model_bundle["regressor"].predict(result[feature_columns])
    result["ml_model_status"] = "trained_demo_trends" if model_bundle.get("trained_on_demo_trends") else "trained"
    result["ml_model_confidence"] = (np.abs(probabilities - 0.5) * 2 * 100).clip(0, 100)
    result["ml_classifier_model"] = model_bundle.get("classifier_name", "")
    result["ml_regression_model"] = model_bundle.get("regressor_name", "")
    result["ml_feature_set"] = model_bundle.get("feature_set", "")
    return result


def main() -> int:
    dataset = load_ml_dataset()
    if dataset.empty:
        raise SystemExit("ML dataset not found or empty. Run python src/ml_dataset.py first.")
    bundle, metrics, predictions = evaluate_models(dataset)
    path = save_best_model(bundle, metrics, predictions)
    print(f"[OK] ML model exported: {path.relative_to(PROJECT_ROOT)}")
    print(f"[OK] Metrics exported: {ML_EVALUATION_METRICS_PATH.relative_to(PROJECT_ROOT)}")
    print(metrics.to_string(index=False))
    if bundle.get("trained_on_demo_trends"):
        print("[WARN] Model trained with demo trend data. ML outputs are prototype-only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
