"""Command-line entry point for the educational AI sector-monitoring prototype."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import sys
from pathlib import Path
import uuid
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np

from src.config import ALLOWED_OPERATING_MODES, DEFAULT_MARKET_PERIOD, DISCLAIMER, OPERATING_MODE, RANKING_PATH, SECTOR_REPRESENTATIVE_TICKERS, SENTIMENT_ENABLED, TREND_KEYWORDS, TREND_REFRESH_MODE, ensure_directories
from src.data_loader import get_sector_etfs, load_fundamentals, load_market_data
from src.database import get_database_path, table_exists
from src.db_loader import (
    load_google_trends,
    load_latest_fundamentals,
    load_latest_trend_features,
    load_market_indicators,
    load_market_prices,
    save_fundamentals,
    save_market_indicators,
    save_market_prices,
    save_pipeline_run,
    save_ml_sector_rankings,
    save_trend_features,
    upsert_sectors,
)
from src.db_schema import create_database_schema
from src.features import assess_data_readiness, collect_latest_features, ml_explanation, ml_signal_label
from src.indicators import enrich_market_indicators
from src.ml_model import load_model, predict_current_signals
from src.preprocessing import clean_market_data
from src.report_generator import generate_html_report, save_report_csv
from src.sentiment_provider import aggregate_sector_sentiment, sentiment_not_used_features
from src.trends_loader import ALLOWED_TREND_REFRESH_MODES, calculate_trend_features, get_trends_with_cache_or_demo


def _add_ml_outputs(features: pd.DataFrame) -> pd.DataFrame:
    model = load_model()
    if model is None:
        print("[WARN] No trained model was found. Run python src/ml_dataset.py and python src/ml_model.py.")
    result = predict_current_signals(features, model_bundle=model) if model is not None else features.copy()
    if "ml_model_status" not in result:
        result["ml_predicted_outperform_probability"] = pd.NA
        result["ml_model_status"] = "not_trained"
        result["ml_model_confidence"] = 0.0
    if "ml_classifier_model" not in result:
        result["ml_classifier_model"] = ""
    if "ml_feature_set" not in result:
        result["ml_feature_set"] = ""
    if "ml_feature_mismatch_detail" not in result:
        result["ml_feature_mismatch_detail"] = ""
    return result


def _finalize_ml_ranking(features: pd.DataFrame) -> pd.DataFrame:
    ranking = _add_ml_outputs(features)
    ranking["data_readiness_status"] = ranking.apply(assess_data_readiness, axis=1)
    ranking["ml_signal_label"] = ranking["ml_predicted_outperform_probability"].map(ml_signal_label)
    ranking["short_explanation"] = ranking.apply(ml_explanation, axis=1)
    ranking = ranking.sort_values("ml_predicted_outperform_probability", ascending=False, na_position="last").reset_index(drop=True)
    ranking.insert(0, "rank", range(1, len(ranking) + 1))
    output_columns = [
        "rank",
        "date",
        "sector",
        "ticker",
        "ml_predicted_outperform_probability",
        "ml_model_confidence",
        "ml_signal_label",
        "ml_model_status",
        "ml_classifier_model",
        "ml_feature_set",
        "data_readiness_status",
        "short_explanation",
        "market_last_date",
        "price_data_status",
        "trend_data_status",
        "trend_refresh_mode",
        "trend_provider",
        "trend_source_detail",
        "sentiment_data_status",
        "momentum_21",
        "momentum_63",
        "momentum_126",
        "volatility_20",
        "downside_volatility_20",
        "drawdown_current",
        "distance_to_ma_200",
        "risk_adjusted_return_63",
        "volume_momentum_20",
        "relative_strength_vs_spy_63",
        "relative_strength_vs_spy_126",
        "trailingPE",
        "forwardPE",
        "priceToBook",
        "dividendYield",
        "beta",
        "marketCap",
    ]
    return ranking[[column for column in output_columns if column in ranking.columns]]


def _trend_not_used_features() -> dict:
    return {
        "trend_mean": np.nan, "trend_latest": np.nan, "trend_momentum_4w": np.nan, "trend_momentum_12w": np.nan,
        "trend_z_score_12w": np.nan, "trend_z_score_52w": np.nan, "trend_spike": False, "trend_acceleration": np.nan,
        "trend_volatility": np.nan, "trend_percentile_52w": np.nan, "trend_observations": 0, "trend_last_date": "",
    }


def _relative_strength_features(market: pd.DataFrame, benchmark: pd.DataFrame) -> dict[str, float]:
    """Calculate current relative strength versus SPY for ML feature alignment."""
    result = {"relative_strength_vs_spy_63": np.nan, "relative_strength_vs_spy_126": np.nan}
    if market.empty or benchmark.empty or "close" not in market or "close" not in benchmark:
        return result
    sector_close = pd.to_numeric(market["close"], errors="coerce")
    benchmark_close = pd.to_numeric(benchmark["close"], errors="coerce").reindex(market.index).ffill()
    for window in (63, 126):
        if len(sector_close.dropna()) > window and len(benchmark_close.dropna()) > window:
            result[f"relative_strength_vs_spy_{window}"] = float(sector_close.pct_change(window).iloc[-1] - benchmark_close.pct_change(window).iloc[-1])
    return result


def _load_market_from_db(ticker: str) -> pd.DataFrame:
    prices = load_market_prices(ticker)
    indicators = load_market_indicators(ticker)
    if prices.empty and indicators.empty:
        return pd.DataFrame()
    if indicators.empty:
        return prices
    return prices.join(indicators, how="outer").sort_index() if not prices.empty else indicators


def _database_has_required_data(sector_etfs: dict[str, str]) -> bool:
    if not get_database_path().exists():
        return False
    if not all(table_exists(table) for table in ("market_prices", "market_indicators", "fundamentals", "sectors")):
        return False
    return bool(sector_etfs and not _load_market_from_db(next(iter(sector_etfs.values()))).empty)


def _trend_features_from_db(sector: str) -> tuple[dict, str, dict]:
    features = load_latest_trend_features(sector)
    if features:
        features["trend_data_status"] = features.get("trend_data_status") or "manual_csv"
        return features, str(features["trend_data_status"]), {"trend_refresh_mode": "db", "trend_cache_age_hours": pd.NA, "trend_provider": "sqlite", "trend_source_detail": "SQLite trend_features table"}
    trends = load_google_trends(sector)
    if not trends.empty:
        features = calculate_trend_features(trends)
        features["trend_data_status"] = "manual_csv"
        save_trend_features(features, sector)
        return features, "manual_csv", {"trend_refresh_mode": "db", "trend_cache_age_hours": pd.NA, "trend_provider": "sqlite", "trend_source_detail": "SQLite google_trends table"}
    print("No Google Trends data found in DB. Import manual CSVs with src/import_trends_csv.py.")
    features = _trend_not_used_features()
    features["trend_data_status"] = "missing_from_db"
    return features, "missing_from_db", {"trend_refresh_mode": "db", "trend_cache_age_hours": pd.NA, "trend_provider": "sqlite", "trend_source_detail": "No Google Trends data found in DB. Import manual CSVs with src/import_trends_csv.py."}


def run_pipeline(period: str = DEFAULT_MARKET_PERIOD, trend_mode: str = TREND_REFRESH_MODE, use_ml: bool = True, operating_mode: str = OPERATING_MODE, use_sentiment: bool | None = None, data_source: str = "db", save_to_db: bool = False) -> pd.DataFrame:
    """Build the ML ranking, HTML report, and dashboard input CSV without trading."""
    ensure_directories()
    rows, statuses = [], {}
    if operating_mode not in ALLOWED_OPERATING_MODES:
        raise ValueError(f"Invalid operating mode '{operating_mode}'. Allowed: {sorted(ALLOWED_OPERATING_MODES)}")
    if operating_mode == "demo":
        trend_mode = "demo_only"
    use_trends = operating_mode in {"full", "demo"}
    sentiment_enabled = operating_mode == "full" and (SENTIMENT_ENABLED if use_sentiment is None else use_sentiment)
    print(DISCLAIMER)
    print(f"Operating mode: {operating_mode}")
    print(f"Trend refresh mode: {trend_mode}")
    print(f"Data source: {data_source}")
    print(f"Sentiment module: {'enabled' if sentiment_enabled else 'disabled'}")
    sector_etfs = get_sector_etfs()
    if data_source == "db" and not _database_has_required_data(sector_etfs):
        raise SystemExit("Database is empty. Run python src/refresh_market_data.py first.")
    if save_to_db:
        create_database_schema()
        upsert_sectors(sector_etfs)
    if data_source == "db":
        benchmark_market = _load_market_from_db("SPY")
    else:
        benchmark_prices = clean_market_data(load_market_data("SPY", period))
        benchmark_market = enrich_market_indicators(benchmark_prices)
        if save_to_db and not benchmark_prices.empty:
            save_market_prices(benchmark_prices, "Benchmark", "SPY")
            save_market_indicators(benchmark_market, "Benchmark", "SPY")
    print("[OK] Benchmark data loaded: SPY" if not benchmark_market.empty else "[WARN] Benchmark data unavailable: SPY")
    sentiment_statuses: dict[str, list[str]] = {}
    for sector, ticker in sector_etfs.items():
        if data_source == "db":
            market = _load_market_from_db(ticker)
            fundamentals = load_latest_fundamentals(ticker)
        else:
            market_prices = clean_market_data(load_market_data(ticker, period))
            market = enrich_market_indicators(market_prices)
            fundamentals = load_fundamentals(ticker)
            if save_to_db and not market_prices.empty:
                save_market_prices(market_prices, sector, ticker)
                enriched_for_db = market.copy()
                enriched_for_db.update(pd.DataFrame([_relative_strength_features(market, benchmark_market)], index=[market.index[-1]]) if not market.empty else pd.DataFrame())
                save_market_indicators(market, sector, ticker)
                save_fundamentals(fundamentals, sector, ticker)
        print(f"[OK] Market data loaded: {sector}" if not market.empty else f"[WARN] Market data unavailable: {sector}")
        if use_trends:
            if data_source == "db":
                trend_features, status, trend_metadata = _trend_features_from_db(sector)
            else:
                trends, status, trend_metadata = get_trends_with_cache_or_demo(
                    sector,
                    TREND_KEYWORDS[sector],
                    return_status=True,
                    return_metadata=True,
                    refresh_mode=trend_mode,
                )
                trend_features = calculate_trend_features(trends)
        else:
            status = "not_used"
            trend_metadata = {"trend_refresh_mode": trend_mode, "trend_cache_age_hours": pd.NA, "trend_provider": "disabled_by_mode", "trend_source_detail": "Google Trends disabled in market/fundamental mode"}
            trend_features = _trend_not_used_features()
        statuses.setdefault(status, []).append(sector)
        print(f"[OK] Google Trends status {status}: {sector}")
        row = collect_latest_features(sector, ticker, market, fundamentals, trend_features)
        if "relative_strength_vs_spy_63" not in row or pd.isna(row.get("relative_strength_vs_spy_63")):
            row.update(_relative_strength_features(market, benchmark_market))
        if sentiment_enabled:
            sentiment_features = aggregate_sector_sentiment(sector, SECTOR_REPRESENTATIVE_TICKERS.get(sector, []))
        else:
            sentiment_features = sentiment_not_used_features()
        row.update(sentiment_features)
        sentiment_status = str(sentiment_features.get("sentiment_data_status", "missing"))
        sentiment_statuses.setdefault(sentiment_status, []).append(sector)
        if sentiment_status == "disabled_no_api_key":
            print(f"[WARN] Sentiment disabled for {sector}: FINNHUB_API_KEY is not set.")
        else:
            print(f"[OK] Sentiment status {sentiment_status}: {sector}")
        market_last_date = market.index.max().strftime("%Y-%m-%d") if not market.empty else ""
        row.update({
            "trend_data_status": status,
            "trend_refresh_mode": trend_metadata.get("trend_refresh_mode", trend_mode),
            "trend_cache_age_hours": trend_metadata.get("trend_cache_age_hours", pd.NA),
            "trend_provider": trend_metadata.get("trend_provider", status),
            "trend_source_detail": trend_metadata.get("trend_source_detail", ""),
            "trend_keywords": ", ".join(TREND_KEYWORDS[sector]),
            "market_last_date": market_last_date,
            "price_data_status": data_source if not market.empty else "missing",
            "operating_mode": operating_mode,
            "date": market_last_date,
        })
        rows.append(row)
    ranking = _finalize_ml_ranking(pd.DataFrame(rows))
    ranking.to_csv(RANKING_PATH, index=False)
    save_report_csv(ranking)
    html_path = generate_html_report(ranking)
    if data_source == "db" or save_to_db:
        create_database_schema()
        run_timestamp = datetime.now(timezone.utc).isoformat()
        run_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
        save_ml_sector_rankings(ranking, run_id, run_timestamp)
        save_pipeline_run(run_id, {"run_timestamp": run_timestamp, "operating_mode": operating_mode, "trend_mode": trend_mode, "use_ml": use_ml, "use_sentiment": sentiment_enabled, "status": "completed", "notes": f"data_source={data_source}"})
    print("[OK] ML outperformance probabilities calculated")
    print(f"[OK] CSV exported: {RANKING_PATH.relative_to(PROJECT_ROOT)}")
    print(f"[OK] HTML report exported: {html_path.relative_to(PROJECT_ROOT)}")
    print("[OK] Dashboard entrypoint available: python -m streamlit run app/app.py")
    print("Data status counts: " + ", ".join(f"{key}={len(value)}" for key, value in sorted(statuses.items())))
    print("Sentiment status counts: " + ", ".join(f"{key}={len(value)}" for key, value in sorted(sentiment_statuses.items())))
    print("Top 5 sectors:")
    print(ranking[["rank", "sector", "ticker", "ml_predicted_outperform_probability", "ml_signal_label"]].head().to_string(index=False))
    print("Management summary: Ranking is derived only from the supervised ML outperformance probability versus SPY.")
    print("Dashboard command: python -m streamlit run app/app.py")
    return ranking


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the educational sector-monitoring pipeline.")
    parser.add_argument("--mode", choices=sorted(ALLOWED_OPERATING_MODES), default=OPERATING_MODE, help="Operating mode: market_fundamental, full, or demo.")
    parser.add_argument("--trend-mode", choices=sorted(ALLOWED_TREND_REFRESH_MODES), default=TREND_REFRESH_MODE, help="Google Trends refresh strategy.")
    parser.add_argument("--skip-live-trends", action="store_true", help="Equivalent to --trend-mode cache_only.")
    parser.add_argument("--period", default=DEFAULT_MARKET_PERIOD, help="Market-data period passed to yfinance.")
    parser.add_argument("--use-ml", action="store_true", help="Deprecated: ML is always used for the final ranking.")
    parser.add_argument("--no-ml", action="store_true", help="Deprecated: retained for CLI compatibility; final ranking still expects an ML model.")
    parser.add_argument("--use-sentiment", action="store_true", help="Enable optional Finnhub news/social sentiment in full mode.")
    parser.add_argument("--no-sentiment", action="store_true", help="Disable optional news/social sentiment.")
    parser.add_argument("--data-source", choices=["db", "live"], default="db", help="Read input data from SQLite or live yfinance/providers.")
    parser.add_argument("--save-to-db", action="store_true", help="When using --data-source live, also save loaded market/fundamental data and ML ranking to SQLite.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    selected_trend_mode = "cache_only" if args.skip_live_trends else args.trend_mode
    selected_sentiment = True if args.use_sentiment else False if args.no_sentiment else None
    run_pipeline(period=args.period, trend_mode=selected_trend_mode, use_ml=True, operating_mode=args.mode, use_sentiment=selected_sentiment, data_source=args.data_source, save_to_db=args.save_to_db)
