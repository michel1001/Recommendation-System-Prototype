"""Refresh local SQLite market and fundamentals data from yfinance."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_loader import get_sector_etfs, load_fundamentals, load_market_data
from src.db_loader import save_fundamentals, save_market_indicators, save_market_prices, upsert_sectors
from src.db_schema import create_database_schema
from src.indicators import enrich_market_indicators
from src.preprocessing import clean_market_data


def _add_relative_strength(market: pd.DataFrame, benchmark: pd.DataFrame) -> pd.DataFrame:
    data = market.copy()
    if data.empty or benchmark.empty or "close" not in data or "close" not in benchmark:
        data["relative_strength_vs_spy_63"] = pd.NA
        data["relative_strength_vs_spy_126"] = pd.NA
        return data
    sector_close = pd.to_numeric(data["close"], errors="coerce")
    benchmark_close = pd.to_numeric(benchmark["close"], errors="coerce").reindex(data.index).ffill()
    for window in (63, 126):
        data[f"relative_strength_vs_spy_{window}"] = sector_close.pct_change(window) - benchmark_close.pct_change(window)
    return data


def refresh_market_database(period: str = "5y", force: bool = False) -> None:
    create_database_schema()
    print("[OK] Database schema created")
    sector_etfs = get_sector_etfs()
    upsert_sectors(sector_etfs)

    benchmark_prices = clean_market_data(load_market_data("SPY", period))
    benchmark_indicators = enrich_market_indicators(benchmark_prices)
    if not benchmark_prices.empty:
        save_market_prices(benchmark_prices, "Benchmark", "SPY")
        save_market_indicators(benchmark_indicators, "Benchmark", "SPY")
        print("[OK] Benchmark data saved: SPY")
    else:
        print("[WARN] Benchmark data unavailable: SPY")

    for sector, ticker in sector_etfs.items():
        prices = clean_market_data(load_market_data(ticker, period))
        if prices.empty:
            print(f"[WARN] Market data unavailable: {sector} / {ticker}")
            continue
        indicators = _add_relative_strength(enrich_market_indicators(prices), benchmark_indicators)
        save_market_prices(prices, sector, ticker)
        save_market_indicators(indicators, sector, ticker)
        print(f"[OK] Market data saved: {sector} / {ticker}")

        fundamentals = load_fundamentals(ticker)
        save_fundamentals(fundamentals, sector, ticker)
        print(f"[OK] Fundamentals saved: {sector} / {ticker}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh local SQLite market data.")
    parser.add_argument("--period", default="5y", help="yfinance download period, default: 5y.")
    parser.add_argument("--force", action="store_true", help="Refresh and upsert all rows even when data exists.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    refresh_market_database(period=args.period, force=args.force)
