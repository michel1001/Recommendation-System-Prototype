"""Verify that the prototype outputs exist and contain the expected columns."""

from __future__ import annotations

from pathlib import Path
import os
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import FINNHUB_API_KEY_ENV, MODEL_PATH, TREND_CACHE_MAX_AGE_HOURS
from src.database import get_connection, get_database_path, table_exists

CSV_PATH = PROJECT_ROOT / "data" / "processed" / "recommendation_scores.csv"
HTML_REPORT_PATH = PROJECT_ROOT / "reports" / "html" / "sector_monitoring_report.html"
DASHBOARD_PATH = PROJECT_ROOT / "app" / "app.py"
BACKTEST_RESULTS_PATH = PROJECT_ROOT / "data" / "processed" / "backtest_results.csv"
BACKTEST_METRICS_PATH = PROJECT_ROOT / "data" / "processed" / "backtest_metrics.csv"

REQUIRED_COLUMNS = [
    "sector",
    "ticker",
    "trend_score",
    "trend_signal",
    "trend_data_status",
    "trend_refresh_mode",
    "trend_cache_age_hours",
    "trend_provider",
    "trend_source_detail",
    "operating_mode",
    "scoring_profile",
    "price_data_status",
    "market_last_date",
    "data_quality_status",
    "actionability_status",
    "trend_keywords",
    "trend_observations",
    "trend_last_date",
    "momentum_score",
    "risk_score",
    "fundamental_score",
    "synergy_score",
    "synergy_label",
    "total_score",
    "confidence_score",
    "recommendation",
    "short_explanation",
    "ml_predicted_outperform_probability",
    "ml_predicted_excess_return_4w",
    "ml_model_status",
]
REQUIRED_MARKET_FEATURES = ["momentum_21", "momentum_63", "momentum_126", "volatility_20", "drawdown_current"]
OPTIONAL_SENTIMENT_COLUMNS = [
    "sentiment_score_component",
    "sentiment_data_status",
    "sentiment_provider",
    "sentiment_article_count",
    "sentiment_bullish_percent",
    "sentiment_bearish_percent",
    "sentiment_buzz",
]


def verify_outputs() -> bool:
    missing_files: list[str] = []
    if not CSV_PATH.exists():
        missing_files.append(str(CSV_PATH.relative_to(PROJECT_ROOT)))
    if not HTML_REPORT_PATH.exists():
        missing_files.append(str(HTML_REPORT_PATH.relative_to(PROJECT_ROOT)))
    if not DASHBOARD_PATH.exists():
        missing_files.append(str(DASHBOARD_PATH.relative_to(PROJECT_ROOT)))

    missing_columns: list[str] = []
    trend_status_fail = False
    demo_only = False
    demo_refresh_mode = False
    stale_cache_sectors: list[str] = []
    ml_statuses: list[str] = []
    market_feature_fail = False
    score_fail = False
    all_research_prototype = False
    operating_modes: list[str] = []
    sentiment_missing_columns: list[str] = []
    sentiment_statuses: list[str] = []
    database_fail = False
    database_warnings: list[str] = []
    if CSV_PATH.exists():
        ranking = pd.read_csv(CSV_PATH)
        for column in REQUIRED_COLUMNS:
            if column not in ranking.columns:
                missing_columns.append(column)
        if ranking.empty:
            missing_columns.append("non-empty ranking rows")
        else:
            market_values = ranking[REQUIRED_MARKET_FEATURES].apply(pd.to_numeric, errors="coerce")
            market_feature_fail = market_values.isna().all().any()
            trend_statuses = ranking["trend_data_status"].fillna("fallback").astype(str).str.lower()
            operating_modes = sorted(ranking.get("operating_mode", pd.Series("unknown", index=ranking.index)).fillna("unknown").astype(str).str.lower().unique())
            valid_trend_statuses = {"live", "live_pytrends", "manual_csv", "external_api", "cache", "demo", "not_used", "missing_from_db"}
            trend_status_fail = not trend_statuses.isin(valid_trend_statuses).any() or trend_statuses.eq("fallback").all()
            score_fail = pd.to_numeric(ranking["total_score"], errors="coerce").isna().all()
            all_research_prototype = ranking["recommendation"].fillna("").astype(str).eq("Research Prototype").all()
            demo_only = trend_statuses.eq("demo").all()
            if "ml_model_status" in ranking.columns:
                ml_statuses = sorted(ranking["ml_model_status"].fillna("not_trained").astype(str).unique())
            sentiment_present = any(column in ranking.columns for column in OPTIONAL_SENTIMENT_COLUMNS)
            if sentiment_present:
                sentiment_missing_columns = [column for column in OPTIONAL_SENTIMENT_COLUMNS if column not in ranking.columns]
                if not sentiment_missing_columns:
                    sentiment_statuses = sorted(ranking["sentiment_data_status"].fillna("not_used").astype(str).str.lower().unique())
            if "trend_refresh_mode" in ranking.columns:
                demo_refresh_mode = ranking["trend_refresh_mode"].fillna("").astype(str).str.lower().eq("demo_only").any()
            if {"trend_data_status", "trend_cache_age_hours"}.issubset(ranking.columns):
                cache_ages = pd.to_numeric(ranking["trend_cache_age_hours"], errors="coerce")
                stale_cache_mask = trend_statuses.eq("cache") & cache_ages.gt(TREND_CACHE_MAX_AGE_HOURS)
                stale_cache_sectors = ranking.loc[stale_cache_mask, "sector"].astype(str).tolist()
            if ranking.get("price_data_status", pd.Series("", index=ranking.index)).fillna("").astype(str).str.lower().eq("db").any():
                db_path = get_database_path()
                if not db_path.exists():
                    database_fail = True
                    database_warnings.append(f"Database file not found: {db_path}")
                else:
                    required_tables = ("market_prices", "market_indicators", "fundamentals", "sectors")
                    for table in required_tables:
                        if not table_exists(table):
                            database_fail = True
                            database_warnings.append(f"Missing database table: {table}")
                    if table_exists("google_trends"):
                        with get_connection() as connection:
                            trend_count = int(connection.execute("SELECT COUNT(*) FROM google_trends").fetchone()[0])
                        if trend_count == 0:
                            database_warnings.append("google_trends table is empty. This is OK for market_fundamental mode.")

    if missing_files or missing_columns or sentiment_missing_columns or market_feature_fail or trend_status_fail or score_fail or database_fail or ("market_fundamental" in operating_modes and all_research_prototype):
        if missing_files:
            print("[ERROR] Missing files:")
            for item in missing_files:
                print(f" - {item}")
        if missing_columns:
            print("[ERROR] Missing columns:")
            for column in missing_columns:
                print(f" - {column}")
        if sentiment_missing_columns:
            print("[ERROR] Incomplete optional sentiment columns:")
            for column in sentiment_missing_columns:
                print(f" - {column}")
        if market_feature_fail:
            print("[FAIL] Important market features are still empty.")
        if trend_status_fail:
            print("[FAIL] All sectors use neutral trend fallback. Google Trends component is not demonstrable.")
        if score_fail:
            print("[FAIL] All total scores are empty.")
        if database_fail:
            print("[FAIL] Database checks failed.")
            for warning in database_warnings:
                print(f" - {warning}")
        if "market_fundamental" in operating_modes and all_research_prototype:
            print("[FAIL] Market/fundamental mode should not cap all rows to Research Prototype.")
        return False

    if demo_only:
        print("[WARN] Trend signals are demo-only. Outputs are prototype-only and not actionable.")
    if demo_refresh_mode:
        print("[WARN] Running in demo-only trend mode. Outputs are prototype-only.")
    if stale_cache_sectors:
        print(f"[WARN] Cached trend data is older than {TREND_CACHE_MAX_AGE_HOURS} hours for: {', '.join(stale_cache_sectors)}")
    for warning in database_warnings:
        print(f"[WARN] {warning}")
    if not MODEL_PATH.exists() or ml_statuses == ["not_trained"]:
        print("[WARN] ML model is not trained or not used. Run python src/ml_dataset.py and python src/ml_model.py, then rerun pipeline with --use-ml.")
    else:
        print(f"[OK] ML output status: {', '.join(ml_statuses)}")
    if sentiment_statuses:
        print(f"[OK] Sentiment status: {', '.join(sentiment_statuses)}")
        if "disabled_no_api_key" in sentiment_statuses and not os.getenv(FINNHUB_API_KEY_ENV):
            print(f"[WARN] Sentiment was requested but {FINNHUB_API_KEY_ENV} is not set.")
    if not BACKTEST_RESULTS_PATH.exists() or not BACKTEST_METRICS_PATH.exists():
        print("[WARN] Backtest outputs not found. Run python src/backtesting.py.")
    else:
        print("[OK] Backtest outputs found.")
    print("[OK] Prototype outputs verified successfully.")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if verify_outputs() else 1)
