"""Command-line entry point for the educational AI sector-monitoring prototype."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np

from src.config import ALLOWED_OPERATING_MODES, DEFAULT_MARKET_PERIOD, DISCLAIMER, OPERATING_MODE, RANKING_PATH, SCORING_MODE, SCORING_PROFILE_BY_MODE, SECTOR_REPRESENTATIVE_TICKERS, SENTIMENT_ENABLED, TREND_KEYWORDS, TREND_REFRESH_MODE, ensure_directories
from src.data_loader import get_sector_etfs, load_fundamentals, load_market_data
from src.indicators import enrich_market_indicators
from src.ml_model import load_model, predict_current_signals
from src.preprocessing import clean_market_data
from src.report_generator import generate_html_report, save_report_csv
from src.scoring import calculate_relative_scores, collect_latest_features
from src.sentiment_provider import aggregate_sector_sentiment, sentiment_not_used_features
from src.trends_loader import ALLOWED_TREND_REFRESH_MODES, calculate_trend_features, get_trends_with_cache_or_demo


def _add_ml_outputs(ranking: pd.DataFrame, use_ml: bool = False) -> pd.DataFrame:
    model = load_model() if use_ml else None
    if use_ml and model is None:
        print("[WARN] --use-ml requested, but no trained model was found. Run python src/ml_model.py.")
    result = predict_current_signals(ranking, model_bundle=model) if use_ml and model is not None else ranking.copy()
    if "ml_model_status" not in result:
        result["ml_predicted_outperform_probability"] = pd.NA
        result["ml_predicted_excess_return_4w"] = pd.NA
        result["ml_model_status"] = "not_trained"
        result["ml_model_confidence"] = 0.0
    if "ml_classifier_model" not in result:
        result["ml_classifier_model"] = ""
    if "ml_regression_model" not in result:
        result["ml_regression_model"] = ""
    if "ml_feature_set" not in result:
        result["ml_feature_set"] = ""
    if "ml_feature_mismatch_detail" not in result:
        result["ml_feature_mismatch_detail"] = ""
    return result


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


def run_pipeline(period: str = DEFAULT_MARKET_PERIOD, trend_mode: str = TREND_REFRESH_MODE, use_ml: bool = False, operating_mode: str = OPERATING_MODE, use_sentiment: bool | None = None) -> pd.DataFrame:
    """Build the ranking, HTML report, and dashboard input CSV without trading."""
    ensure_directories()
    rows, statuses = [], {}
    if operating_mode not in ALLOWED_OPERATING_MODES:
        raise ValueError(f"Invalid operating mode '{operating_mode}'. Allowed: {sorted(ALLOWED_OPERATING_MODES)}")
    if operating_mode == "demo":
        trend_mode = "demo_only"
    use_trends = operating_mode in {"full", "demo"}
    sentiment_enabled = operating_mode == "full" and (SENTIMENT_ENABLED if use_sentiment is None else use_sentiment)
    print(DISCLAIMER)
    print(f"Scoring mode: {SCORING_MODE}")
    print(f"Operating mode: {operating_mode}")
    print(f"Trend refresh mode: {trend_mode}")
    print(f"Sentiment module: {'enabled' if sentiment_enabled else 'disabled'}")
    benchmark_market = enrich_market_indicators(clean_market_data(load_market_data("SPY", period)))
    print("[OK] Benchmark data loaded: SPY" if not benchmark_market.empty else "[WARN] Benchmark data unavailable: SPY")
    sentiment_statuses: dict[str, list[str]] = {}
    for sector, ticker in get_sector_etfs().items():
        market = enrich_market_indicators(clean_market_data(load_market_data(ticker, period)))
        print(f"[OK] Market data loaded: {sector}" if not market.empty else f"[WARN] Market data unavailable: {sector}")
        if use_trends:
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
        row = collect_latest_features(sector, ticker, market, load_fundamentals(ticker), trend_features)
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
            "price_data_status": "live" if not market.empty else "missing",
            "scoring_mode": SCORING_MODE,
            "operating_mode": operating_mode,
            "scoring_profile": SCORING_PROFILE_BY_MODE[operating_mode],
        })
        rows.append(row)
    ranking = calculate_relative_scores(pd.DataFrame(rows), operating_mode=operating_mode).sort_values("total_score", ascending=False).reset_index(drop=True)
    ranking = _add_ml_outputs(ranking, use_ml=use_ml)
    ranking.to_csv(RANKING_PATH, index=False)
    save_report_csv(ranking)
    html_path = generate_html_report(ranking)
    print("[OK] Scores calculated")
    print(f"[OK] CSV exported: {RANKING_PATH.relative_to(PROJECT_ROOT)}")
    print(f"[OK] HTML report exported: {html_path.relative_to(PROJECT_ROOT)}")
    print("[OK] Dashboard entrypoint available: python -m streamlit run app/app.py")
    print("Data status counts: " + ", ".join(f"{key}={len(value)}" for key, value in sorted(statuses.items())))
    print("Sentiment status counts: " + ", ".join(f"{key}={len(value)}" for key, value in sorted(sentiment_statuses.items())))
    print("Top 5 sectors:")
    print(ranking[["sector", "ticker", "total_score", "recommendation", "synergy_label"]].head().to_string(index=False))
    print("Management summary: Scores combine investor-attention signals with market, risk, and fundamental validation for analyst review.")
    print("Dashboard command: python -m streamlit run app/app.py")
    return ranking


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the educational sector-monitoring pipeline.")
    parser.add_argument("--mode", choices=sorted(ALLOWED_OPERATING_MODES), default=OPERATING_MODE, help="Operating mode: market_fundamental, full, or demo.")
    parser.add_argument("--trend-mode", choices=sorted(ALLOWED_TREND_REFRESH_MODES), default=TREND_REFRESH_MODE, help="Google Trends refresh strategy.")
    parser.add_argument("--skip-live-trends", action="store_true", help="Equivalent to --trend-mode cache_only.")
    parser.add_argument("--period", default=DEFAULT_MARKET_PERIOD, help="Market-data period passed to yfinance.")
    parser.add_argument("--use-ml", action="store_true", help="Add current ML predictions if a trained model exists.")
    parser.add_argument("--no-ml", action="store_true", help="Disable ML predictions and mark outputs as not_trained.")
    parser.add_argument("--use-sentiment", action="store_true", help="Enable optional Finnhub news/social sentiment in full mode.")
    parser.add_argument("--no-sentiment", action="store_true", help="Disable optional news/social sentiment.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    selected_trend_mode = "cache_only" if args.skip_live_trends else args.trend_mode
    selected_sentiment = True if args.use_sentiment else False if args.no_sentiment else None
    run_pipeline(period=args.period, trend_mode=selected_trend_mode, use_ml=args.use_ml and not args.no_ml, operating_mode=args.mode, use_sentiment=selected_sentiment)
