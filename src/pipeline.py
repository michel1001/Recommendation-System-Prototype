"""Command-line entry point for the educational AI sector-monitoring prototype."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEFAULT_MARKET_PERIOD, DISCLAIMER, RANKING_PATH, SCORING_MODE, TREND_KEYWORDS, TREND_REFRESH_MODE, ensure_directories
from src.data_loader import get_sector_etfs, load_fundamentals, load_market_data
from src.indicators import enrich_market_indicators
from src.preprocessing import clean_market_data
from src.report_generator import generate_html_report, save_report_csv
from src.scoring import calculate_relative_scores, collect_latest_features
from src.trends_loader import ALLOWED_TREND_REFRESH_MODES, calculate_trend_features, get_trends_with_cache_or_demo


def run_pipeline(period: str = DEFAULT_MARKET_PERIOD, trend_mode: str = TREND_REFRESH_MODE) -> pd.DataFrame:
    """Build the ranking, HTML report, and dashboard input CSV without trading."""
    ensure_directories()
    rows, statuses = [], {status: [] for status in ("live", "cache", "demo", "fallback")}
    print(DISCLAIMER)
    print(f"Scoring mode: {SCORING_MODE}")
    print(f"Trend refresh mode: {trend_mode}")
    for sector, ticker in get_sector_etfs().items():
        market = enrich_market_indicators(clean_market_data(load_market_data(ticker, period)))
        print(f"[OK] Market data loaded: {sector}" if not market.empty else f"[WARN] Market data unavailable: {sector}")
        trends, status, trend_metadata = get_trends_with_cache_or_demo(
            sector,
            TREND_KEYWORDS[sector],
            return_status=True,
            return_metadata=True,
            refresh_mode=trend_mode,
        )
        statuses[status].append(sector)
        print(f"[OK] Google Trends loaded {status}: {sector}")
        row = collect_latest_features(sector, ticker, market, load_fundamentals(ticker), calculate_trend_features(trends))
        market_last_date = market.index.max().strftime("%Y-%m-%d") if not market.empty else ""
        row.update({
            "trend_data_status": status,
            "trend_refresh_mode": trend_metadata.get("trend_refresh_mode", trend_mode),
            "trend_cache_age_hours": trend_metadata.get("trend_cache_age_hours", pd.NA),
            "trend_keywords": ", ".join(TREND_KEYWORDS[sector]),
            "market_last_date": market_last_date,
            "price_data_status": "live" if not market.empty else "missing",
            "scoring_mode": SCORING_MODE,
        })
        rows.append(row)
    ranking = calculate_relative_scores(pd.DataFrame(rows)).sort_values("total_score", ascending=False).reset_index(drop=True)
    ranking.to_csv(RANKING_PATH, index=False)
    save_report_csv(ranking)
    html_path = generate_html_report(ranking)
    print("[OK] Scores calculated")
    print(f"[OK] CSV exported: {RANKING_PATH.relative_to(PROJECT_ROOT)}")
    print(f"[OK] HTML report exported: {html_path.relative_to(PROJECT_ROOT)}")
    print("[OK] Dashboard entrypoint available: python -m streamlit run app/app.py")
    print("Data status counts: " + ", ".join(f"{key}={len(value)}" for key, value in statuses.items()))
    print("Top 5 sectors:")
    print(ranking[["sector", "ticker", "total_score", "recommendation", "synergy_label"]].head().to_string(index=False))
    print("Management summary: Scores combine investor-attention signals with market, risk, and fundamental validation for analyst review.")
    print("Dashboard command: python -m streamlit run app/app.py")
    return ranking


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the educational sector-monitoring pipeline.")
    parser.add_argument("--trend-mode", choices=sorted(ALLOWED_TREND_REFRESH_MODES), default=TREND_REFRESH_MODE, help="Google Trends refresh strategy.")
    parser.add_argument("--skip-live-trends", action="store_true", help="Equivalent to --trend-mode cache_only.")
    parser.add_argument("--period", default=DEFAULT_MARKET_PERIOD, help="Market-data period passed to yfinance.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    selected_trend_mode = "cache_only" if args.skip_live_trends else args.trend_mode
    run_pipeline(period=args.period, trend_mode=selected_trend_mode)
