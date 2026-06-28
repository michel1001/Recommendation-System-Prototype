"""Provider abstraction for Google Trends-like sector attention data."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
import csv
import random
import time
import warnings

import numpy as np
import pandas as pd

from src.config import (
    DEFAULT_TREND_GEO,
    DEFAULT_TREND_TIMEFRAME,
    DEMO_DATA_DIR,
    GOOGLE_TRENDS_MAX_SLEEP_SECONDS,
    GOOGLE_TRENDS_MIN_SLEEP_SECONDS,
    MANUAL_TRENDS_DIR,
    TREND_KEYWORDS,
)

try:
    from pytrends.request import TrendReq
except ImportError:  # optional in constrained environments
    TrendReq = None


def _slug(sector: str) -> str:
    return sector.lower().replace(" ", "_")


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "sector", "value"])


def _metadata(provider: str, status: str, source_detail: str = "", error: str = "", observations: int = 0, last_date: str = "") -> dict:
    return {
        "provider": provider,
        "trend_provider": provider,
        "trend_data_status": status,
        "trend_source_detail": source_detail,
        "error": error,
        "observations": int(observations),
        "trend_observations": int(observations),
        "last_date": last_date,
        "trend_last_date": last_date,
    }


def _clean_values(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace("<1", "0.5", regex=False).str.replace("%", "", regex=False), errors="coerce")


class TrendProvider(ABC):
    """Base interface for sector attention providers."""

    name: str

    @abstractmethod
    def fetch_sector_trends(self, sector: str, keywords: list[str], timeframe: str, geo: str) -> tuple[pd.DataFrame, dict]:
        """Return a cleaned weekly dataframe plus provider metadata."""


class ManualCSVTrendProvider(TrendProvider):
    """Load manually exported Google Trends CSV files from data/external."""

    name = "manual_csv"

    def __init__(self, directory=MANUAL_TRENDS_DIR):
        self.directory = directory

    def _path(self, sector: str):
        return self.directory / f"google_trends_manual_{sector}.csv"

    def _read_google_csv(self, path) -> pd.DataFrame:
        rows: list[list[str]] = []
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.reader(handle):
                if any(str(cell).strip() for cell in row):
                    rows.append(row)

        header_index = None
        for index, row in enumerate(rows):
            first = str(row[0]).strip().lower() if row else ""
            if first in {"week", "day", "month", "date"}:
                header_index = index
                break
        if header_index is None:
            raise ValueError("No Google Trends date header found.")

        header = [str(cell).strip() or f"col_{idx}" for idx, cell in enumerate(rows[header_index])]
        data_rows = [row + [""] * (len(header) - len(row)) for row in rows[header_index + 1 :] if len(row) >= 2]
        raw = pd.DataFrame(data_rows, columns=header[: len(data_rows[0])] if data_rows else header)
        if raw.empty:
            return _empty()

        date_col = raw.columns[0]
        raw["date"] = pd.to_datetime(raw[date_col], errors="coerce")
        value_columns = [column for column in raw.columns if column != date_col and column != "date" and str(column).lower() != "ispartial"]
        if not value_columns:
            raise ValueError("No trend value columns found.")
        values = pd.concat([_clean_values(raw[column]) for column in value_columns], axis=1).mean(axis=1)
        return pd.DataFrame({"date": raw["date"], "value": values}).dropna(subset=["date", "value"])

    def fetch_sector_trends(self, sector: str, keywords: list[str], timeframe: str = DEFAULT_TREND_TIMEFRAME, geo: str = DEFAULT_TREND_GEO) -> tuple[pd.DataFrame, dict]:
        path = self._path(sector)
        if not path.exists():
            slug_path = self.directory / f"google_trends_manual_{_slug(sector)}.csv"
            path = slug_path if slug_path.exists() else path
        if not path.exists():
            return _empty(), _metadata(self.name, "unavailable", "manual CSV not found")
        try:
            data = self._read_google_csv(path)
            if data.empty:
                return _empty(), _metadata(self.name, "unavailable", str(path), "manual CSV contained no usable rows")
            data["sector"] = sector
            data = data[["date", "sector", "value"]].sort_values("date").reset_index(drop=True)
            last_date = data["date"].max().strftime("%Y-%m-%d")
            return data, _metadata(self.name, "manual_csv", str(path), observations=len(data), last_date=last_date)
        except Exception as exc:
            return _empty(), _metadata(self.name, "unavailable", str(path), str(exc))


class PytrendsTrendProvider(TrendProvider):
    """Fetch live Google Trends data through pytrends with conservative retries."""

    name = "pytrends"

    def __init__(self, sleep_min_seconds: float | None = None, sleep_max_seconds: float | None = None):
        self.sleep_min_seconds = sleep_min_seconds
        self.sleep_max_seconds = sleep_max_seconds

    def _sleep_before_request(self, sector: str) -> None:
        sleep_min = GOOGLE_TRENDS_MIN_SLEEP_SECONDS if self.sleep_min_seconds is None else self.sleep_min_seconds
        sleep_max = GOOGLE_TRENDS_MAX_SLEEP_SECONDS if self.sleep_max_seconds is None else self.sleep_max_seconds
        sleep_min, sleep_max = max(0.0, float(sleep_min)), max(0.0, float(sleep_max))
        if sleep_max < sleep_min:
            sleep_max = sleep_min
        seconds = random.uniform(sleep_min, sleep_max) if sleep_max else 0.0
        if seconds > 0:
            print(f"[INFO] Waiting {seconds:.1f} seconds before live Google Trends request for {sector}")
            time.sleep(seconds)

    def fetch_sector_trends(self, sector: str, keywords: list[str], timeframe: str = DEFAULT_TREND_TIMEFRAME, geo: str = DEFAULT_TREND_GEO) -> tuple[pd.DataFrame, dict]:
        if TrendReq is None or not keywords:
            return _empty(), _metadata(self.name, "unavailable", "pytrends not installed or no keywords")
        self._sleep_before_request(sector)
        try:
            client = TrendReq(hl="en-US", tz=360, retries=0)
            client.build_payload(keywords[:5], timeframe=timeframe, geo=geo)
            raw = client.interest_over_time()
            if raw is None or raw.empty:
                return _empty(), _metadata(self.name, "unavailable", "empty pytrends response")
            available_keywords = [key for key in keywords[:5] if key in raw.columns]
            if not available_keywords:
                return _empty(), _metadata(self.name, "unavailable", "no requested keyword columns")
            values = raw[available_keywords].mean(axis=1)
            data = pd.DataFrame({"date": pd.to_datetime(values.index), "sector": sector, "value": values.to_numpy()})
            return data, _metadata(self.name, "live_pytrends", "current pytrends request", observations=len(data), last_date=data["date"].max().strftime("%Y-%m-%d"))
        except Exception as exc:
            warnings.warn(f"Google Trends live request failed for {sector}: {exc}")
            return _empty(), _metadata(self.name, "unavailable", "pytrends request failed", str(exc))


class ExternalAPITrendProvider(TrendProvider):
    """Placeholder for future paid/official Google Trends API integrations."""

    name = "external_api"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    def fetch_sector_trends(self, sector: str, keywords: list[str], timeframe: str = DEFAULT_TREND_TIMEFRAME, geo: str = DEFAULT_TREND_GEO) -> tuple[pd.DataFrame, dict]:
        if not self.api_key:
            return _empty(), _metadata(
                self.name,
                "unavailable",
                "No API key configured. Future integration point for SerpApi, DataForSEO, or official Google Trends API Alpha.",
            )
        return _empty(), _metadata(self.name, "unavailable", "external API provider placeholder not implemented")


class DemoTrendProvider(TrendProvider):
    """Generate deterministic synthetic trend data for tests and demonstrations."""

    name = "demo"

    def __init__(self, periods: int = 260):
        self.periods = periods

    def _path(self, sector: str):
        return DEMO_DATA_DIR / f"google_trends_demo_{_slug(sector)}.csv"

    def generate(self, sector: str, keywords: list[str] | None = None, periods: int | None = None) -> pd.DataFrame:
        periods = periods or self.periods
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
        if periods == 260:
            DEMO_DATA_DIR.mkdir(parents=True, exist_ok=True)
            frame.to_csv(self._path(sector), index=False)
        return frame

    def fetch_sector_trends(self, sector: str, keywords: list[str] | None = None, timeframe: str = DEFAULT_TREND_TIMEFRAME, geo: str = DEFAULT_TREND_GEO) -> tuple[pd.DataFrame, dict]:
        path = self._path(sector)
        try:
            if path.exists():
                data = pd.read_csv(path)
                data["date"] = pd.to_datetime(data["date"])
                data = data[["date", "sector", "value"]].dropna(subset=["value"])
                if len(data) != self.periods:
                    data = self.generate(sector, keywords, periods=self.periods)
            else:
                data = self.generate(sector, keywords, periods=self.periods)
            last_date = data["date"].max().strftime("%Y-%m-%d") if not data.empty else ""
            return data, _metadata(self.name, "demo", "synthetic reproducible demo data", observations=len(data), last_date=last_date)
        except Exception as exc:
            return _empty(), _metadata(self.name, "fallback", "demo provider failed", str(exc))


def build_provider(name: str, sleep_min_seconds: float | None = None, sleep_max_seconds: float | None = None) -> TrendProvider:
    if name == "manual_csv":
        return ManualCSVTrendProvider()
    if name == "external_api":
        return ExternalAPITrendProvider()
    if name == "pytrends":
        return PytrendsTrendProvider(sleep_min_seconds=sleep_min_seconds, sleep_max_seconds=sleep_max_seconds)
    if name == "demo":
        return DemoTrendProvider()
    raise ValueError(f"Unknown trend provider: {name}")
