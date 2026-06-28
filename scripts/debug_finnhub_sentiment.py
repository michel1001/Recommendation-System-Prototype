"""Debug Finnhub news-sentiment access without running the full pipeline.

The script never prints the API key. It only prints whether a key is loaded,
its length, and a short hash fingerprint so team members can compare setups.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import FINNHUB_API_KEY_ENV, RAW_SENTIMENT_DIR, SECTOR_REPRESENTATIVE_TICKERS
from src.sentiment_provider import FinnhubSentimentProvider, aggregate_sector_sentiment


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:12] if value else ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Debug Finnhub company news sentiment.")
    parser.add_argument("--ticker", default="AAPL", help="Company ticker to test, for example AAPL.")
    parser.add_argument("--sector", default=None, help="Optional sector aggregation test, for example Technology.")
    parser.add_argument("--clear-cache", action="store_true", help="Delete cached Finnhub sentiment JSON files before testing.")
    return parser.parse_args()


def _clear_cache() -> None:
    RAW_SENTIMENT_DIR.mkdir(parents=True, exist_ok=True)
    removed = 0
    for path in RAW_SENTIMENT_DIR.glob("finnhub_news_sentiment_*.json"):
        path.unlink()
        removed += 1
    print(f"[OK] Removed {removed} cached Finnhub sentiment file(s).")


def _print_company_result(result: dict) -> None:
    fields = [
        "ticker",
        "sentiment_data_status",
        "sentiment_provider",
        "companyNewsScore",
        "bullishPercent",
        "bearishPercent",
        "articlesInLastWeek",
        "buzz",
        "error",
    ]
    print({field: result.get(field) for field in fields})


def _print_sector_result(result: dict) -> None:
    fields = [
        "sentiment_data_status",
        "sentiment_provider",
        "sentiment_score",
        "sentiment_score_component",
        "sentiment_bullish_percent",
        "sentiment_bearish_percent",
        "sentiment_article_count",
        "sentiment_buzz",
        "sentiment_coverage_count",
    ]
    print({field: result.get(field) for field in fields})


def main() -> int:
    args = parse_args()
    if args.clear_cache:
        _clear_cache()

    key = os.getenv(FINNHUB_API_KEY_ENV, "")
    print("[INFO] Finnhub sentiment debug request")
    print(f"key_loaded: {bool(key)}")
    print(f"key_length: {len(key)}")
    print(f"key_too_short: {len(key) < 20}")
    print(f"key_fingerprint: {_fingerprint(key)}")

    provider = FinnhubSentimentProvider()
    print(f"\n[INFO] Company test: {args.ticker.upper()}")
    company_result = provider.fetch_company_sentiment(args.ticker)
    _print_company_result(company_result)

    if args.sector:
        tickers = SECTOR_REPRESENTATIVE_TICKERS.get(args.sector)
        if not tickers:
            print(f"\n[ERROR] Unknown sector '{args.sector}'. Known sectors: {', '.join(sorted(SECTOR_REPRESENTATIVE_TICKERS))}")
            return 1
        print(f"\n[INFO] Sector aggregation test: {args.sector} ({', '.join(tickers)})")
        sector_result = aggregate_sector_sentiment(args.sector, tickers, provider=provider)
        _print_sector_result(sector_result)

    status = str(company_result.get("sentiment_data_status", "missing"))
    if status in {"invalid_api_key", "error", "rate_limited"}:
        print("\n[WARN] Finnhub did not return usable sentiment. If the quote endpoint works but this endpoint returns HTTP 403, the news-sentiment endpoint may not be available for the account/plan.")
    elif status in {"no_data", "missing"}:
        print("\n[WARN] Finnhub responded but no usable sentiment fields were available for this ticker.")
    else:
        print("\n[OK] Finnhub returned a usable company sentiment response or cache entry.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
