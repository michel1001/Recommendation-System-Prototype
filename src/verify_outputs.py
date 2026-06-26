"""Verify that the prototype outputs exist and contain the expected columns."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import TREND_CACHE_MAX_AGE_HOURS

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
]
REQUIRED_MARKET_FEATURES = ["momentum_21", "momentum_63", "momentum_126", "volatility_20", "drawdown_current"]


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
    market_feature_fail = False
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
            trend_status_fail = not trend_statuses.isin({"live", "cache", "demo"}).any()
            demo_only = trend_statuses.eq("demo").all()
            if "trend_refresh_mode" in ranking.columns:
                demo_refresh_mode = ranking["trend_refresh_mode"].fillna("").astype(str).str.lower().eq("demo_only").any()
            if {"trend_data_status", "trend_cache_age_hours"}.issubset(ranking.columns):
                cache_ages = pd.to_numeric(ranking["trend_cache_age_hours"], errors="coerce")
                stale_cache_mask = trend_statuses.eq("cache") & cache_ages.gt(TREND_CACHE_MAX_AGE_HOURS)
                stale_cache_sectors = ranking.loc[stale_cache_mask, "sector"].astype(str).tolist()

    if missing_files or missing_columns or market_feature_fail or trend_status_fail:
        if missing_files:
            print("[ERROR] Missing files:")
            for item in missing_files:
                print(f" - {item}")
        if missing_columns:
            print("[ERROR] Missing columns:")
            for column in missing_columns:
                print(f" - {column}")
        if market_feature_fail:
            print("[FAIL] Important market features are still empty.")
        if trend_status_fail:
            print("[FAIL] All sectors use neutral trend fallback. Google Trends component is not demonstrable.")
        return False

    if demo_only:
        print("[WARN] Trend signals are demo-only. Outputs are prototype-only and not actionable.")
    if demo_refresh_mode:
        print("[WARN] Running in demo-only trend mode. Outputs are prototype-only.")
    if stale_cache_sectors:
        print(f"[WARN] Cached trend data is older than {TREND_CACHE_MAX_AGE_HOURS} hours for: {', '.join(stale_cache_sectors)}")
    if not BACKTEST_RESULTS_PATH.exists() or not BACKTEST_METRICS_PATH.exists():
        print("[WARN] Backtest outputs not found. Run python src/backtesting.py.")
    else:
        print("[OK] Backtest outputs found.")
    print("[OK] Prototype outputs verified successfully.")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if verify_outputs() else 1)
