"""Resilient Google Trends loading with cache, demo, and fallback stages."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import random
import time
from pathlib import Path
import warnings

import numpy as np
import pandas as pd

from src.config import (
    DEFAULT_TREND_GEO,
    DEFAULT_TREND_TIMEFRAME,
    DEMO_DATA_DIR,
    GOOGLE_TRENDS_MAX_SLEEP_SECONDS,
    GOOGLE_TRENDS_MIN_SLEEP_SECONDS,
    RAW_DATA_DIR,
    TREND_CACHE_MAX_AGE_HOURS,
    TREND_KEYWORDS,
    TREND_REFRESH_MODE,
)

try:
    from pytrends.request import TrendReq
except ImportError:  # optional in constrained environments
    TrendReq = None


ALLOWED_TREND_REFRESH_MODES = {"auto", "cache_only", "force_live", "demo_only"}


def _slug(sector: str) -> str:
    return sector.lower().replace(" ", "_")


def _path(sector: str, demo: bool = False) -> Path:
    directory = DEMO_DATA_DIR if demo else RAW_DATA_DIR
    prefix = "google_trends_demo" if demo else "google_trends"
    return directory / f"{prefix}_{_slug(sector)}.csv"


def _metadata_path(sector: str) -> Path:
    return RAW_DATA_DIR / f"google_trends_{_slug(sector)}_metadata.json"


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "sector", "value"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalise_mode(refresh_mode: str | None) -> str:
    mode = (refresh_mode or TREND_REFRESH_MODE).strip().lower()
    if mode not in ALLOWED_TREND_REFRESH_MODES:
        raise ValueError(f"Invalid trend refresh mode '{refresh_mode}'. Allowed values: {sorted(ALLOWED_TREND_REFRESH_MODES)}")
    return mode


def _parse_created_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def load_trends_metadata(sector: str) -> dict:
    """Load cached Google Trends metadata, if present."""
    try:
        return json.loads(_metadata_path(sector).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def trend_cache_age_hours(sector: str) -> float:
    """Return cache age in hours using metadata first, then CSV mtime."""
    path = _path(sector)
    if not path.exists():
        return float("nan")

    metadata = load_trends_metadata(sector)
    created_at = _parse_created_at(metadata.get("created_at"))
    if created_at is not None:
        return max(0.0, (_utc_now() - created_at).total_seconds() / 3600)

    try:
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        return max(0.0, (_utc_now() - modified).total_seconds() / 3600)
    except OSError:
        return float("nan")


def is_cache_fresh(sector: str, max_age_hours: float = TREND_CACHE_MAX_AGE_HOURS) -> bool:
    age = trend_cache_age_hours(sector)
    return bool(pd.notna(age) and age <= max_age_hours)


def save_trends_metadata(
    sector: str,
    keywords: list[str] | None,
    source: str,
    timeframe: str,
    geo: str,
    observations: int,
    last_date: str,
) -> Path:
    """Persist operational metadata for a cached Google Trends file."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    metadata = {
        "sector": sector,
        "keywords": keywords or TREND_KEYWORDS.get(sector, []),
        "source": source,
        "created_at": _utc_now().isoformat(),
        "timeframe": timeframe,
        "geo": geo,
        "observations": int(observations),
        "last_date": last_date,
    }
    path = _metadata_path(sector)
    path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return path


def _sleep_before_live_request(
    sector: str,
    sleep_min_seconds: float | None = None,
    sleep_max_seconds: float | None = None,
) -> None:
    sleep_min = GOOGLE_TRENDS_MIN_SLEEP_SECONDS if sleep_min_seconds is None else sleep_min_seconds
    sleep_max = GOOGLE_TRENDS_MAX_SLEEP_SECONDS if sleep_max_seconds is None else sleep_max_seconds
    sleep_min, sleep_max = max(0.0, float(sleep_min)), max(0.0, float(sleep_max))
    if sleep_max < sleep_min:
        sleep_max = sleep_min
    seconds = random.uniform(sleep_min, sleep_max) if sleep_max else 0.0
    if seconds > 0:
        print(f"[INFO] Waiting {seconds:.1f} seconds before live Google Trends request for {sector}")
        time.sleep(seconds)


def load_sector_trends_live(
    sector: str,
    keywords: list[str],
    timeframe: str = DEFAULT_TREND_TIMEFRAME,
    geo: str = DEFAULT_TREND_GEO,
    sleep_min_seconds: float | None = None,
    sleep_max_seconds: float | None = None,
) -> pd.DataFrame:
    """Load and average up to five keyword series from Google Trends."""
    if TrendReq is None or not keywords:
        return _empty()
    _sleep_before_live_request(sector, sleep_min_seconds, sleep_max_seconds)
    try:
        # pytrends 4.x can conflict with urllib3's removed ``method_whitelist``
        # argument whenever retries are enabled. Keep retries disabled here;
        # cache/demo stages provide the resilient fallback strategy.
        client = TrendReq(hl="en-US", tz=360, retries=0)
        client.build_payload(keywords[:5], timeframe=timeframe, geo=geo)
        raw = client.interest_over_time()
        if raw is None or raw.empty:
            return _empty()
        available_keywords = [key for key in keywords[:5] if key in raw.columns]
        if not available_keywords:
            return _empty()
        values = raw[available_keywords].mean(axis=1)
        return pd.DataFrame({"date": pd.to_datetime(values.index), "sector": sector, "value": values.to_numpy()})
    except Exception as exc:  # live provider is intentionally non-fatal
        warnings.warn(f"Google Trends live request failed for {sector}: {exc}")
        return _empty()


def load_cached_trends(
    sector: str,
    require_fresh: bool = False,
    max_age_hours: float = TREND_CACHE_MAX_AGE_HOURS,
) -> pd.DataFrame:
    if require_fresh and not is_cache_fresh(sector, max_age_hours):
        return _empty()
    path = _path(sector)
    try:
        data = pd.read_csv(path)
        data["date"] = pd.to_datetime(data["date"])
        return data[["date", "sector", "value"]].dropna(subset=["value"])
    except (FileNotFoundError, KeyError, ValueError, pd.errors.EmptyDataError):
        return _empty()


def save_trends_cache(
    df: pd.DataFrame,
    sector: str,
    keywords: list[str] | None = None,
    timeframe: str = DEFAULT_TREND_TIMEFRAME,
    geo: str = DEFAULT_TREND_GEO,
    source: str = "live",
) -> Path:
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = _path(sector)
    clean = df[["date", "sector", "value"]].copy()
    clean.to_csv(path, index=False)
    last_date = pd.to_datetime(clean["date"]).max().strftime("%Y-%m-%d") if not clean.empty else ""
    save_trends_metadata(sector, keywords, source, timeframe, geo, len(clean), last_date)
    return path


def generate_demo_trends(sector: str, keywords: list[str] | None = None, periods: int = 260) -> pd.DataFrame:
    """Generate deterministic, clearly synthetic weekly attention data."""
    seed = sum((index + 1) * ord(char) for index, char in enumerate(sector))
    rng = np.random.default_rng(seed)
    t = np.arange(periods, dtype=float)
    if sector == "Technology":
        values = 42 + 9 * np.sin(t / 14) + 0.12 * t + rng.normal(0, 2.2, periods)
    elif sector == "Energy":
        values = 50 + 17 * np.sin(t / 4.8) + rng.normal(0, 5.0, periods)
    elif sector == "Utilities":
        values = 56 + 4 * np.sin(t / 18) + rng.normal(0, 1.8, periods)
    elif sector == "Real Estate":
        values = 54 - 0.055 * t + 10 * np.sin(t / 7) + rng.normal(0, 4.5, periods)
    elif sector == "Healthcare":
        values = 48 + 0.045 * t + 6 * np.sin(t / 13) + rng.normal(0, 2.8, periods)
    elif sector == "Financials":
        values = 51 + 11 * np.sin(t / 10) + 3 * np.sin(t / 3) + rng.normal(0, 3, periods)
    else:
        values = 52 + 8 * np.sin(t / 9 + seed % 7) + 0.015 * t + rng.normal(0, 3, periods)
    frame = pd.DataFrame({"date": pd.date_range(end=datetime.today(), periods=periods, freq="W-MON"), "sector": sector, "value": np.clip(values, 0, 100)})
    DEMO_DATA_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(_path(sector, demo=True), index=False)
    return frame


def _load_demo(sector: str) -> pd.DataFrame:
    path = _path(sector, demo=True)
    try:
        result = pd.read_csv(path)
        result["date"] = pd.to_datetime(result["date"])
        return result[["date", "sector", "value"]]
    except (FileNotFoundError, KeyError, ValueError, pd.errors.EmptyDataError):
        return _empty()


def _demo_result(sector: str, keywords: list[str], refresh_mode: str) -> tuple[pd.DataFrame, str, dict]:
    demo = _load_demo(sector)
    result, status = (demo if not demo.empty else generate_demo_trends(sector, keywords)), "demo"
    if result.empty:
        result, status = _empty(), "fallback"
    elif refresh_mode != "demo_only":
        warnings.warn(
            f"Using reproducible demo Google Trends data for {sector} because live/cache data is unavailable. "
            "Demo values are synthetic and not real search interest.",
            stacklevel=3,
        )
    metadata = {"trend_refresh_mode": refresh_mode, "trend_cache_age_hours": np.nan}
    return result, status, metadata


def _metadata_for_status(sector: str, status: str, refresh_mode: str) -> dict:
    age = 0.0 if status == "live" else trend_cache_age_hours(sector) if status == "cache" else np.nan
    return {"trend_refresh_mode": refresh_mode, "trend_cache_age_hours": age}


def get_trends_with_cache_or_demo(
    sector: str,
    keywords: list[str] | None = None,
    timeframe: str = DEFAULT_TREND_TIMEFRAME,
    geo: str = DEFAULT_TREND_GEO,
    return_status: bool = False,
    return_metadata: bool = False,
    refresh_mode: str | None = None,
    sleep_min_seconds: float | None = None,
    sleep_max_seconds: float | None = None,
) -> pd.DataFrame | tuple[pd.DataFrame, str] | tuple[pd.DataFrame, str, dict]:
    """Load trends according to the configured refresh strategy."""
    keywords = keywords or TREND_KEYWORDS.get(sector, [])
    mode = _normalise_mode(refresh_mode)

    result: pd.DataFrame
    status: str
    metadata: dict

    if mode == "demo_only":
        result, status, metadata = _demo_result(sector, keywords, mode)
    elif mode == "cache_only":
        cached = load_cached_trends(sector)
        if not cached.empty:
            result, status, metadata = cached, "cache", _metadata_for_status(sector, "cache", mode)
        else:
            result, status, metadata = _demo_result(sector, keywords, mode)
    elif mode == "auto":
        cached = load_cached_trends(sector, require_fresh=True)
        if not cached.empty:
            result, status, metadata = cached, "cache", _metadata_for_status(sector, "cache", mode)
        else:
            live = load_sector_trends_live(sector, keywords, timeframe, geo, sleep_min_seconds, sleep_max_seconds)
            if not live.empty:
                save_trends_cache(live, sector, keywords, timeframe, geo, source="live")
                result, status, metadata = live, "live", _metadata_for_status(sector, "live", mode)
            else:
                result, status, metadata = _demo_result(sector, keywords, mode)
    else:  # force_live
        live = load_sector_trends_live(sector, keywords, timeframe, geo, sleep_min_seconds, sleep_max_seconds)
        if not live.empty:
            save_trends_cache(live, sector, keywords, timeframe, geo, source="live")
            result, status, metadata = live, "live", _metadata_for_status(sector, "live", mode)
        else:
            cached = load_cached_trends(sector)
            if not cached.empty:
                result, status, metadata = cached, "cache", _metadata_for_status(sector, "cache", mode)
            else:
                result, status, metadata = _demo_result(sector, keywords, mode)

    if return_metadata:
        return result, status, metadata
    if return_status:
        return result, status
    return result


def calculate_trend_features(df: pd.DataFrame) -> dict[str, float | bool | int | str]:
    """Calculate interpretable weekly attention features."""
    data = df.copy() if df is not None else _empty()
    if data.empty or "value" not in data:
        return {"trend_mean": np.nan, "trend_latest": np.nan, "trend_momentum_4w": np.nan, "trend_momentum_12w": np.nan, "trend_z_score_12w": np.nan, "trend_z_score_52w": np.nan, "trend_spike": False, "trend_acceleration": np.nan, "trend_volatility": np.nan, "trend_percentile_52w": np.nan, "trend_observations": 0, "trend_last_date": ""}
    data["date"] = pd.to_datetime(data["date"])
    values = pd.to_numeric(data["value"], errors="coerce").dropna().reset_index(drop=True)
    dates = data.loc[pd.to_numeric(data["value"], errors="coerce").notna(), "date"]
    if values.empty:
        return calculate_trend_features(_empty())
    recent12, recent52 = values.tail(12), values.tail(52)

    def change(period: int) -> float:
        return float(values.iloc[-1] / values.iloc[-1 - period] - 1) if len(values) > period and values.iloc[-1 - period] else np.nan

    def zscore(sample: pd.Series) -> float:
        return float((values.iloc[-1] - sample.mean()) / sample.std()) if len(sample) > 1 and sample.std() else np.nan

    momentum4 = change(4)
    return {"trend_mean": float(values.mean()), "trend_latest": float(values.iloc[-1]), "trend_momentum_4w": momentum4, "trend_momentum_12w": change(12), "trend_z_score_12w": zscore(recent12), "trend_z_score_52w": zscore(recent52), "trend_spike": bool(pd.notna(zscore(recent12)) and zscore(recent12) > 1.5), "trend_acceleration": float(momentum4 - change(8)) if pd.notna(momentum4) and pd.notna(change(8)) else np.nan, "trend_volatility": float(recent12.std()) if len(recent12) > 1 else np.nan, "trend_percentile_52w": float(recent52.rank(pct=True).iloc[-1] * 100), "trend_observations": int(len(values)), "trend_last_date": dates.max().strftime("%Y-%m-%d")}


# Compatibility aliases retained for existing notebooks.
load_sector_trends = load_sector_trends_live
save_trends_data = save_trends_cache
compute_trend_features = lambda df, sector=None: calculate_trend_features(df)
