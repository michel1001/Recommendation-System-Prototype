"""Build a supervised historical ML dataset for sector outperformance research."""

from __future__ import annotations

import sys
from pathlib import Path
import argparse

import numpy as np
import pandas as pd
import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import ML_TRAINING_DATASET_PATH, SECTOR_ETFS, TREND_KEYWORDS, ensure_directories
from src.indicators import enrich_market_indicators
from src.preprocessing import clean_market_data
from src.sentiment_provider import DemoSentimentProvider, aggregate_sector_sentiment
from src.trend_providers import DemoTrendProvider


MARKET_FEATURE_COLUMNS = [
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
]
TREND_FEATURE_COLUMNS = [
    "trend_latest",
    "trend_momentum_4w",
    "trend_momentum_12w",
    "trend_z_score_12w",
    "trend_z_score_52w",
    "trend_spike",
    "trend_acceleration",
    "trend_percentile_52w",
]
SENTIMENT_FEATURE_COLUMNS = [
    "sentiment_score",
    "sentiment_bullish_percent",
    "sentiment_bearish_percent",
    "sentiment_buzz",
    "sentiment_article_count",
]


def _download_ohlcv(ticker: str, start: str = "2018-01-01", end: str | None = None) -> pd.DataFrame:
    try:
        data = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False)
    except Exception as exc:
        print(f"[WARN] Historical data unavailable for {ticker}: {exc}")
        return pd.DataFrame()
    if data is None or data.empty:
        return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [str(column[0]) for column in data.columns]
    data.index = pd.to_datetime(data.index)
    return data


def _demo_market_data(ticker: str, start: str = "2018-01-01", periods: int = 1300) -> pd.DataFrame:
    """Deterministic emergency fallback so the ML workflow remains demonstrable offline."""
    seed = sum((idx + 1) * ord(char) for idx, char in enumerate(ticker))
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start=start, periods=periods)
    returns = rng.normal(0.00025 + (seed % 7) / 100000, 0.012, periods)
    close = 100 * (1 + pd.Series(returns)).cumprod().to_numpy()
    volume = rng.integers(5_000_000, 30_000_000, periods)
    return pd.DataFrame({"Open": close * 0.998, "High": close * 1.01, "Low": close * 0.99, "Close": close, "Adj Close": close, "Volume": volume}, index=dates)


def _trend_history_features(sector: str, dates: pd.Series, status: str = "demo") -> pd.DataFrame:
    trend_data, metadata = DemoTrendProvider(periods=520).fetch_sector_trends(sector, TREND_KEYWORDS.get(sector, []))
    trend_data = trend_data.sort_values("date").copy()
    values = pd.to_numeric(trend_data["value"], errors="coerce")
    trend_data["trend_latest"] = values
    trend_data["trend_momentum_4w"] = values / values.shift(4) - 1
    trend_data["trend_momentum_12w"] = values / values.shift(12) - 1
    trend_data["trend_z_score_12w"] = (values - values.rolling(12).mean()) / values.rolling(12).std()
    trend_data["trend_z_score_52w"] = (values - values.rolling(52).mean()) / values.rolling(52).std()
    trend_data["trend_acceleration"] = trend_data["trend_momentum_4w"] - (values / values.shift(8) - 1)
    trend_data["trend_percentile_52w"] = values.rolling(52).rank(pct=True) * 100
    trend_data["trend_spike"] = trend_data["trend_z_score_12w"].gt(1.5)
    trend_data["date"] = pd.to_datetime(trend_data["date"], errors="coerce").astype("datetime64[ns]")
    trend_data = trend_data[["date", *TREND_FEATURE_COLUMNS]].dropna(subset=["date"])
    targets = pd.DataFrame({"date": pd.to_datetime(dates, errors="coerce").astype("datetime64[ns]").sort_values()})
    aligned = pd.merge_asof(targets, trend_data.sort_values("date"), on="date", direction="backward")
    aligned["sector"] = sector
    aligned["trend_data_status"] = metadata.get("trend_data_status", status)
    return aligned


def _sentiment_history_features(sector: str, dates: pd.Series) -> pd.DataFrame:
    """Attach deterministic demo sentiment features for full-mode ML experiments."""
    features = aggregate_sector_sentiment(sector, [sector], provider=DemoSentimentProvider())
    targets = pd.DataFrame({"date": pd.to_datetime(dates, errors="coerce").astype("datetime64[ns]").sort_values()})
    for column in SENTIMENT_FEATURE_COLUMNS:
        targets[column] = features.get(column, np.nan)
    targets["sector"] = sector
    targets["sentiment_data_status"] = features.get("sentiment_data_status", "demo")
    return targets


def calculate_historical_sector_features(sector: str, ticker: str, market_df: pd.DataFrame, spy_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate point-in-time market features for one sector."""
    if market_df.empty or spy_df.empty:
        return pd.DataFrame()
    market = enrich_market_indicators(clean_market_data(market_df))
    spy = clean_market_data(spy_df)
    if "close" not in market or "close" not in spy:
        return pd.DataFrame()

    result = market.copy()
    spy_close = pd.to_numeric(spy["close"], errors="coerce").reindex(result.index).ffill()
    close = pd.to_numeric(result["close"], errors="coerce")
    result["relative_strength_vs_spy_63"] = close.pct_change(63) - spy_close.pct_change(63)
    result["relative_strength_vs_spy_126"] = close.pct_change(126) - spy_close.pct_change(126)
    result["sector_forward_base_close"] = close
    result["spy_forward_base_close"] = spy_close
    result["date"] = result.index
    result["sector"] = sector
    result["ticker"] = ticker
    columns = ["date", "sector", "ticker", "sector_forward_base_close", "spy_forward_base_close", *MARKET_FEATURE_COLUMNS]
    return result[columns].reset_index(drop=True)


def add_forward_return_targets(df: pd.DataFrame, horizon_days: int = 21) -> pd.DataFrame:
    """Add 4-week forward excess-return targets without using future features."""
    data = df.sort_values(["sector", "date"]).copy()
    data["sector_forward_return_4w"] = data.groupby("sector")["sector_forward_base_close"].shift(-horizon_days) / data["sector_forward_base_close"] - 1
    data["spy_forward_return_4w"] = data.groupby("sector")["spy_forward_base_close"].shift(-horizon_days) / data["spy_forward_base_close"] - 1
    data["target_excess_return_4w"] = data["sector_forward_return_4w"] - data["spy_forward_return_4w"]
    data["target_outperform_spy_4w"] = data["target_excess_return_4w"].gt(0).astype(int)
    return data.dropna(subset=["target_excess_return_4w", "target_outperform_spy_4w"])


def build_historical_feature_dataset(start: str = "2018-01-01", end: str | None = None, horizon_days: int = 21, use_demo_market_fallback: bool = True, feature_set: str = "market_fundamental") -> pd.DataFrame:
    """Build a sector-date supervised learning table."""
    spy = _download_ohlcv("SPY", start=start, end=end)
    if spy.empty and use_demo_market_fallback:
        spy = _demo_market_data("SPY", start=start)

    rows = []
    for sector, ticker in SECTOR_ETFS.items():
        market = _download_ohlcv(ticker, start=start, end=end)
        if market.empty and use_demo_market_fallback:
            market = _demo_market_data(ticker, start=start)
        features = calculate_historical_sector_features(sector, ticker, market, spy)
        if features.empty:
            continue
        features = features.sort_values("date")
        features["date"] = pd.to_datetime(features["date"], errors="coerce").astype("datetime64[ns]")
        if feature_set == "full":
            trend_features = _trend_history_features(sector, features["date"])
            features = features.merge(trend_features.drop(columns=["sector"]), on="date", how="left")
            sentiment_features = _sentiment_history_features(sector, features["date"])
            features = features.merge(sentiment_features.drop(columns=["sector"]), on="date", how="left")
            features["ml_data_quality"] = np.where(features["trend_data_status"].eq("demo") | features["sentiment_data_status"].eq("demo"), "prototype_only", "research")
        else:
            features["trend_data_status"] = "not_used"
            features["ml_data_quality"] = "market_fundamental_only"
        features["feature_set"] = feature_set
        rows.append(features)

    if not rows:
        return pd.DataFrame()
    dataset = pd.concat(rows, ignore_index=True).sort_values(["date", "sector"])
    dataset = add_forward_return_targets(dataset, horizon_days=horizon_days)
    dataset = dataset.drop(columns=["sector_forward_base_close", "spy_forward_base_close"])
    return dataset.reset_index(drop=True)


def export_ml_dataset(df: pd.DataFrame, path=ML_TRAINING_DATASET_PATH):
    ensure_directories()
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build ML training dataset.")
    parser.add_argument("--feature-set", choices=["market_fundamental", "full"], default="market_fundamental")
    parser.add_argument("--start", default="2018-01-01")
    parser.add_argument("--end", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_directories()
    dataset = build_historical_feature_dataset(start=args.start, end=args.end, feature_set=args.feature_set)
    path = export_ml_dataset(dataset)
    print(f"[OK] ML training dataset exported: {path.relative_to(PROJECT_ROOT)} ({len(dataset)} rows)")
    print(f"[OK] Feature set: {args.feature_set}")
    if not dataset.empty and "trend_data_status" in dataset and dataset["trend_data_status"].eq("demo").any():
        print("[WARN] ML dataset includes demo trend data. ML outputs are prototype-only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
