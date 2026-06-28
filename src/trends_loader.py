"""Resilient trend loading with providers, cache, demo, and fallback stages."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import warnings

import numpy as np
import pandas as pd

from src.config import (
    DEFAULT_TREND_GEO,
    DEFAULT_TREND_TIMEFRAME,
    DEMO_DATA_DIR,
    RAW_DATA_DIR,
    TREND_CACHE_MAX_AGE_HOURS,
    TREND_KEYWORDS,
    TREND_PROVIDER_ORDER,
    TREND_REFRESH_MODE,
)
from src.trend_providers import DemoTrendProvider, PytrendsTrendProvider, build_provider


ALLOWED_TREND_REFRESH_MODES = {"auto", "cache_only", "force_live", "demo_only"}
REAL_TREND_STATUSES = {"manual_csv", "external_api", "live_pytrends", "cache"}


def _slug(sector: str) -> str:
    return sector.lower().replace(" ", "_")


def _path(sector: str, demo: bool = False):
    directory = DEMO_DATA_DIR if demo else RAW_DATA_DIR
    prefix = "google_trends_demo" if demo else "google_trends"
    return directory / f"{prefix}_{_slug(sector)}.csv"


def _metadata_path(sector: str):
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


def _last_date(df: pd.DataFrame) -> str:
    return pd.to_datetime(df["date"]).max().strftime("%Y-%m-%d") if df is not None and not df.empty and "date" in df else ""


def load_trends_metadata(sector: str) -> dict:
    try:
        return json.loads(_metadata_path(sector).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def trend_cache_age_hours(sector: str) -> float:
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
    provider: str | None = None,
    source_detail: str = "",
) -> None:
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    metadata = {
        "sector": sector,
        "keywords": keywords or TREND_KEYWORDS.get(sector, []),
        "source": source,
        "provider": provider or source,
        "trend_source_detail": source_detail,
        "created_at": _utc_now().isoformat(),
        "timeframe": timeframe,
        "geo": geo,
        "observations": int(observations),
        "last_date": last_date,
    }
    _metadata_path(sector).write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def load_cached_trends(sector: str, require_fresh: bool = False, max_age_hours: float = TREND_CACHE_MAX_AGE_HOURS) -> pd.DataFrame:
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
    source: str = "live_pytrends",
    provider: str | None = None,
    source_detail: str = "",
) -> object:
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = _path(sector)
    clean = df[["date", "sector", "value"]].copy()
    clean.to_csv(path, index=False)
    save_trends_metadata(sector, keywords, source, timeframe, geo, len(clean), _last_date(clean), provider=provider or source, source_detail=source_detail)
    return path


def _cache_metadata(sector: str, refresh_mode: str) -> dict:
    metadata = load_trends_metadata(sector)
    age = trend_cache_age_hours(sector)
    return {
        "trend_refresh_mode": refresh_mode,
        "trend_cache_age_hours": age,
        "trend_provider": "cache",
        "trend_source_detail": metadata.get("trend_source_detail") or metadata.get("source") or "local cache",
    }


def _provider_metadata(provider_metadata: dict, refresh_mode: str, cache_age: float = np.nan) -> dict:
    status = provider_metadata.get("trend_data_status", provider_metadata.get("status", "fallback"))
    return {
        "trend_refresh_mode": refresh_mode,
        "trend_cache_age_hours": cache_age,
        "trend_provider": provider_metadata.get("trend_provider", provider_metadata.get("provider", status)),
        "trend_source_detail": provider_metadata.get("trend_source_detail", provider_metadata.get("source_detail", "")),
    }


def generate_demo_trends(sector: str, keywords: list[str] | None = None, periods: int = 260) -> pd.DataFrame:
    return DemoTrendProvider(periods=periods).generate(sector, keywords, periods=periods)


def _load_demo(sector: str) -> pd.DataFrame:
    data, _ = DemoTrendProvider().fetch_sector_trends(sector, TREND_KEYWORDS.get(sector, []))
    return data


def _demo_result(sector: str, keywords: list[str], refresh_mode: str) -> tuple[pd.DataFrame, str, dict]:
    data, metadata = DemoTrendProvider().fetch_sector_trends(sector, keywords)
    status = metadata.get("trend_data_status", "demo") if not data.empty else "fallback"
    if status == "demo" and refresh_mode != "demo_only":
        warnings.warn(
            f"Using reproducible demo Google Trends data for {sector} because real/cache data is unavailable. "
            "Demo values are synthetic and not real search interest.",
            stacklevel=3,
        )
    return data, status, _provider_metadata(metadata, refresh_mode)


def _provider_order_for_mode(refresh_mode: str) -> list[str]:
    if refresh_mode == "demo_only":
        return ["demo"]
    if refresh_mode == "cache_only":
        return ["cache", "demo"]
    if refresh_mode == "force_live":
        return [provider for provider in TREND_PROVIDER_ORDER if provider != "cache"] + ["cache", "demo"]
    return list(TREND_PROVIDER_ORDER)


def _fetch_cache_provider(sector: str, refresh_mode: str, require_fresh: bool) -> tuple[pd.DataFrame, str, dict]:
    cached = load_cached_trends(sector, require_fresh=require_fresh)
    if cached.empty:
        return _empty(), "unavailable", {}
    return cached, "cache", _cache_metadata(sector, refresh_mode)


def load_sector_trends_live(
    sector: str,
    keywords: list[str],
    timeframe: str = DEFAULT_TREND_TIMEFRAME,
    geo: str = DEFAULT_TREND_GEO,
    sleep_min_seconds: float | None = None,
    sleep_max_seconds: float | None = None,
) -> pd.DataFrame:
    """Compatibility wrapper for live pytrends loading."""
    data, _ = PytrendsTrendProvider(sleep_min_seconds=sleep_min_seconds, sleep_max_seconds=sleep_max_seconds).fetch_sector_trends(sector, keywords, timeframe, geo)
    return data


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
    """Load trends according to refresh mode and configured provider order."""
    keywords = keywords or TREND_KEYWORDS.get(sector, [])
    mode = _normalise_mode(refresh_mode)

    for provider_name in _provider_order_for_mode(mode):
        if provider_name == "cache":
            data, status, metadata = _fetch_cache_provider(sector, mode, require_fresh=(mode == "auto"))
        elif provider_name == "demo":
            data, status, metadata = _demo_result(sector, keywords, mode)
        else:
            provider = build_provider(provider_name, sleep_min_seconds=sleep_min_seconds, sleep_max_seconds=sleep_max_seconds)
            data, raw_metadata = provider.fetch_sector_trends(sector, keywords, timeframe, geo)
            status = raw_metadata.get("trend_data_status", "unavailable")
            metadata = _provider_metadata(raw_metadata, mode, cache_age=0.0 if status in {"manual_csv", "external_api", "live_pytrends"} else np.nan)
            if not data.empty and status in {"manual_csv", "external_api", "live_pytrends"}:
                save_trends_cache(data, sector, keywords, timeframe, geo, source=status, provider=provider_name, source_detail=metadata.get("trend_source_detail", ""))

        if not data.empty and status != "unavailable":
            if return_metadata:
                return data, status, metadata
            if return_status:
                return data, status
            return data

    result, status, metadata = _empty(), "fallback", _provider_metadata({"provider": "fallback", "trend_source_detail": "no trend provider available"}, mode)
    if return_metadata:
        return result, status, metadata
    if return_status:
        return result, status
    return result


def calculate_trend_features(df: pd.DataFrame) -> dict[str, float | bool | int | str]:
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


load_sector_trends = load_sector_trends_live
save_trends_data = save_trends_cache
compute_trend_features = lambda df, sector=None: calculate_trend_features(df)
