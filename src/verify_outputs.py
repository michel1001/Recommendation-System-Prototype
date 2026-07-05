"""Verify that the ML prototype outputs exist and contain the expected columns."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import MODEL_PATH, RANKING_PATH, TREND_CACHE_MAX_AGE_HOURS
from src.database import get_connection, get_database_path, table_exists

CSV_PATH = RANKING_PATH
HTML_REPORT_PATH = PROJECT_ROOT / "reports" / "html" / "sector_monitoring_report.html"
DASHBOARD_PATH = PROJECT_ROOT / "app" / "app.py"

REQUIRED_COLUMNS = [
    "rank",
    "date",
    "sector",
    "ticker",
    "ml_predicted_outperform_probability",
    "ml_model_confidence",
    "ml_signal_label",
    "ml_model_status",
    "data_readiness_status",
    "short_explanation",
    "trend_data_status",
    "price_data_status",
    "market_last_date",
]
REQUIRED_MARKET_FEATURES = ["momentum_21", "momentum_63", "momentum_126", "volatility_20", "drawdown_current"]
REMOVED_OUTPUT_COLUMNS = {
    "total_score",
    "trend_score",
    "momentum_score",
    "risk_score",
    "fundamental_score",
    "synergy_score",
    "synergy_label",
    "confidence_score",
    "recommendation",
    "scoring_profile",
}


def verify_outputs() -> bool:
    missing_files: list[str] = []
    for path in (CSV_PATH, HTML_REPORT_PATH, DASHBOARD_PATH):
        if not path.exists():
            missing_files.append(str(path.relative_to(PROJECT_ROOT)))

    missing_columns: list[str] = []
    removed_columns_present: list[str] = []
    market_feature_fail = False
    probability_fail = False
    ranking_fail = False
    database_fail = False
    database_warnings: list[str] = []
    ml_statuses: list[str] = []
    stale_cache_sectors: list[str] = []

    if CSV_PATH.exists():
        ranking = pd.read_csv(CSV_PATH)
        missing_columns = [column for column in REQUIRED_COLUMNS if column not in ranking.columns]
        removed_columns_present = sorted(REMOVED_OUTPUT_COLUMNS.intersection(ranking.columns))
        if ranking.empty:
            missing_columns.append("non-empty ranking rows")
        elif not missing_columns:
            market_values = ranking[REQUIRED_MARKET_FEATURES].apply(pd.to_numeric, errors="coerce")
            market_feature_fail = market_values.isna().all().any()
            probabilities = pd.to_numeric(ranking["ml_predicted_outperform_probability"], errors="coerce")
            probability_fail = probabilities.isna().all()
            ranking_fail = not probabilities.fillna(-1).is_monotonic_decreasing
            ml_statuses = sorted(ranking["ml_model_status"].fillna("not_trained").astype(str).unique())
            trend_statuses = ranking["trend_data_status"].fillna("not_used").astype(str).str.lower()
            if {"trend_cache_age_hours", "sector"}.issubset(ranking.columns):
                cache_ages = pd.to_numeric(ranking["trend_cache_age_hours"], errors="coerce")
                stale_cache_mask = trend_statuses.eq("cache") & cache_ages.gt(TREND_CACHE_MAX_AGE_HOURS)
                stale_cache_sectors = ranking.loc[stale_cache_mask, "sector"].astype(str).tolist()
            if ranking.get("price_data_status", pd.Series("", index=ranking.index)).fillna("").astype(str).str.lower().eq("db").any():
                db_path = get_database_path()
                if not db_path.exists():
                    database_fail = True
                    database_warnings.append(f"Database file not found: {db_path}")
                else:
                    for table in ("market_prices", "market_indicators", "fundamentals", "sectors"):
                        if not table_exists(table):
                            database_fail = True
                            database_warnings.append(f"Missing database table: {table}")
                    if table_exists("google_trends"):
                        with get_connection() as connection:
                            trend_count = int(connection.execute("SELECT COUNT(*) FROM google_trends").fetchone()[0])
                        if trend_count == 0:
                            database_warnings.append("google_trends table is empty. This is OK when trends are not active.")

    if missing_files or missing_columns or removed_columns_present or market_feature_fail or probability_fail or ranking_fail or database_fail:
        if missing_files:
            print("[ERROR] Missing files:")
            for item in missing_files:
                print(f" - {item}")
        if missing_columns:
            print("[ERROR] Missing columns:")
            for column in missing_columns:
                print(f" - {column}")
        if removed_columns_present:
            print("[FAIL] Removed rule-based columns are still present:")
            for column in removed_columns_present:
                print(f" - {column}")
        if market_feature_fail:
            print("[FAIL] Important ML market features are empty.")
        if probability_fail:
            print("[FAIL] ML probabilities are empty.")
        if ranking_fail:
            print("[FAIL] Ranking is not sorted by ML outperformance probability.")
        if database_fail:
            print("[FAIL] Database checks failed.")
            for warning in database_warnings:
                print(f" - {warning}")
        return False

    for warning in database_warnings:
        print(f"[WARN] {warning}")
    if stale_cache_sectors:
        print(f"[WARN] Cached trend data is older than {TREND_CACHE_MAX_AGE_HOURS} hours for: {', '.join(stale_cache_sectors)}")
    if not MODEL_PATH.exists() or ml_statuses == ["not_trained"]:
        print("[WARN] ML model is not trained. Run python src/ml_dataset.py and python src/ml_model.py.")
    else:
        print(f"[OK] ML output status: {', '.join(ml_statuses)}")
    print("[OK] ML prototype outputs verified successfully.")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if verify_outputs() else 1)
