"""Refresh Google Trends cache without running the ML ranking pipeline or reports."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    DEFAULT_TREND_GEO,
    DEFAULT_TREND_TIMEFRAME,
    GOOGLE_TRENDS_MAX_SLEEP_SECONDS,
    GOOGLE_TRENDS_MIN_SLEEP_SECONDS,
    TREND_KEYWORDS,
    ensure_directories,
)
from src.trends_loader import load_sector_trends_live, save_trends_cache


def refresh_sector(
    sector: str,
    sleep_min: float = GOOGLE_TRENDS_MIN_SLEEP_SECONDS,
    sleep_max: float = GOOGLE_TRENDS_MAX_SLEEP_SECONDS,
    timeframe: str = DEFAULT_TREND_TIMEFRAME,
    geo: str = DEFAULT_TREND_GEO,
) -> bool:
    """Attempt a live Google Trends refresh for one sector."""
    keywords = TREND_KEYWORDS[sector]
    trends = load_sector_trends_live(sector, keywords, timeframe=timeframe, geo=geo, sleep_min_seconds=sleep_min, sleep_max_seconds=sleep_max)
    if trends.empty:
        print(f"[WARN] Google Trends refresh failed for {sector}. If this is HTTP 429 rate limiting, wait and retry later.")
        return False

    path = save_trends_cache(trends, sector, keywords=keywords, timeframe=timeframe, geo=geo, source="live")
    print(f"[OK] Refreshed Google Trends cache for {sector}: {path.relative_to(PROJECT_ROOT)}")
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh Google Trends cache only; does not run ML ranking, dashboard, or report generation.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--sector", choices=sorted(TREND_KEYWORDS), help="Single sector to refresh.")
    group.add_argument("--all", action="store_true", help="Refresh all configured sectors.")
    parser.add_argument("--sleep-min", type=float, default=GOOGLE_TRENDS_MIN_SLEEP_SECONDS, help="Minimum seconds to wait before each live request.")
    parser.add_argument("--sleep-max", type=float, default=GOOGLE_TRENDS_MAX_SLEEP_SECONDS, help="Maximum seconds to wait before each live request.")
    parser.add_argument("--timeframe", default=DEFAULT_TREND_TIMEFRAME)
    parser.add_argument("--geo", default=DEFAULT_TREND_GEO)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_directories()
    sectors = sorted(TREND_KEYWORDS) if args.all else [args.sector]
    successes = 0
    for sector in sectors:
        successes += int(refresh_sector(sector, args.sleep_min, args.sleep_max, args.timeframe, args.geo))
    print(f"[INFO] Refresh complete: {successes}/{len(sectors)} sector cache files updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
