"""Debug live Google Trends access without running the full pipeline.

This script is intentionally small and read-only by default. It helps the team
separate pytrends/Google rate-limit problems from pipeline/scoring problems.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEFAULT_TREND_GEO, DEFAULT_TREND_TIMEFRAME, TREND_KEYWORDS
from src.trend_providers import PytrendsTrendProvider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Debug a direct pytrends Google Trends request.")
    parser.add_argument("--sector", default="Technology", help="Sector name from TREND_KEYWORDS, for example Technology.")
    parser.add_argument("--keywords", nargs="*", default=None, help="Optional explicit keywords. Defaults to configured sector keywords.")
    parser.add_argument("--timeframe", default=DEFAULT_TREND_TIMEFRAME, help="Google Trends timeframe, for example 'today 5-y'.")
    parser.add_argument("--geo", default=DEFAULT_TREND_GEO, help="Google Trends geo, for example US.")
    parser.add_argument("--sleep-min", type=float, default=0.0, help="Minimum pre-request sleep in seconds.")
    parser.add_argument("--sleep-max", type=float, default=0.0, help="Maximum pre-request sleep in seconds.")
    parser.add_argument("--save", action="store_true", help="Save returned rows to data/raw/debug_google_trends_<sector>.csv.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    keywords = args.keywords or TREND_KEYWORDS.get(args.sector, [])
    if not keywords:
        print(f"[ERROR] No keywords configured for sector '{args.sector}'. Pass --keywords explicitly.")
        return 1

    print("[INFO] Google Trends debug request")
    print(f"sector: {args.sector}")
    print(f"keywords: {', '.join(keywords)}")
    print(f"timeframe: {args.timeframe}")
    print(f"geo: {args.geo}")

    provider = PytrendsTrendProvider(sleep_min_seconds=args.sleep_min, sleep_max_seconds=args.sleep_max)
    data, metadata = provider.fetch_sector_trends(args.sector, keywords, timeframe=args.timeframe, geo=args.geo)

    print(f"status: {metadata.get('trend_data_status')}")
    print(f"provider: {metadata.get('provider')}")
    print(f"source_detail: {metadata.get('trend_source_detail')}")
    if metadata.get("error"):
        print(f"error: {metadata.get('error')}")
    print(f"rows: {len(data)}")
    if not data.empty:
        print(f"first_date: {data['date'].min()}")
        print(f"last_date: {data['date'].max()}")
        print("tail:")
        print(data.tail().to_string(index=False))
        if args.save:
            output = PROJECT_ROOT / "data" / "raw" / f"debug_google_trends_{args.sector.lower().replace(' ', '_')}.csv"
            output.parent.mkdir(parents=True, exist_ok=True)
            data.to_csv(output, index=False)
            print(f"[OK] Saved: {output.relative_to(PROJECT_ROOT)}")
    else:
        print("[WARN] No usable Google Trends rows returned. Common causes: HTTP 429 rate limit, pytrends compatibility, or Google blocking unofficial requests.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
