"""Optional external news/social sentiment providers for sector research."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import numpy as np
import pandas as pd

from src.config import FINNHUB_API_KEY_ENV, RAW_SENTIMENT_DIR, SENTIMENT_CACHE_MAX_AGE_HOURS


SENTIMENT_FIELDS = [
    "sentiment_score",
    "sentiment_bullish_percent",
    "sentiment_bearish_percent",
    "sentiment_buzz",
    "sentiment_article_count",
    "sentiment_coverage_count",
    "sentiment_data_status",
    "sentiment_provider",
    "sentiment_last_updated",
]


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _empty_company(ticker: str, status: str, provider: str, error: str = "") -> dict:
    return {
        "ticker": ticker,
        "bullishPercent": np.nan,
        "bearishPercent": np.nan,
        "companyNewsScore": np.nan,
        "sectorAverageBullishPercent": np.nan,
        "sectorAverageNewsScore": np.nan,
        "articlesInLastWeek": 0,
        "buzz": np.nan,
        "sentiment_data_status": status,
        "sentiment_provider": provider,
        "sentiment_last_updated": _now_utc().isoformat(timespec="seconds"),
        "error": error,
    }


def _as_float(value, default=np.nan) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _parse_finnhub_response(ticker: str, payload: dict, provider: str, status: str = "live") -> dict:
    buzz = payload.get("buzz") or {}
    company_news_score = _as_float(payload.get("companyNewsScore"))
    if pd.isna(company_news_score) and not buzz and not any(key in payload for key in ("bullishPercent", "bearishPercent", "sectorAverageNewsScore")):
        status = "no_data" if status in {"live", "cache"} else status
    return {
        "ticker": ticker,
        "bullishPercent": _as_float(payload.get("bullishPercent")),
        "bearishPercent": _as_float(payload.get("bearishPercent")),
        "companyNewsScore": company_news_score,
        "sectorAverageBullishPercent": _as_float(payload.get("sectorAverageBullishPercent")),
        "sectorAverageNewsScore": _as_float(payload.get("sectorAverageNewsScore")),
        "articlesInLastWeek": _as_int(buzz.get("articlesInLastWeek")),
        "buzz": _as_float(buzz.get("buzz")),
        "sentiment_data_status": status,
        "sentiment_provider": provider,
        "sentiment_last_updated": _now_utc().isoformat(timespec="seconds"),
        "error": "",
    }


def _finnhub_error_status(payload: dict) -> tuple[str, str] | None:
    message = str(payload.get("error") or payload.get("detail") or payload.get("message") or "").strip()
    if not message:
        return None
    lowered = message.lower()
    if "api key" in lowered or "token" in lowered or "unauthorized" in lowered:
        return "invalid_api_key", message
    if "limit" in lowered:
        return "rate_limited", message
    return "error", message


class SentimentProvider(ABC):
    """Base interface for company-level sentiment providers."""

    name: str

    @abstractmethod
    def fetch_company_sentiment(self, ticker: str) -> dict:
        """Return robustly parsed company sentiment metadata."""


class FinnhubSentimentProvider(SentimentProvider):
    """Fetch Finnhub news sentiment as a black-box external supporting signal."""

    name = "finnhub"

    def __init__(self, api_key: str | None = None, cache_dir: Path = RAW_SENTIMENT_DIR, cache_max_age_hours: int = SENTIMENT_CACHE_MAX_AGE_HOURS):
        self.api_key = api_key if api_key is not None else os.getenv(FINNHUB_API_KEY_ENV)
        self.cache_dir = Path(cache_dir)
        self.cache_max_age_hours = cache_max_age_hours

    def _cache_path(self, ticker: str) -> Path:
        return self.cache_dir / f"finnhub_news_sentiment_{ticker.upper()}.json"

    def _read_fresh_cache(self, ticker: str) -> dict | None:
        path = self._cache_path(ticker)
        if not path.exists():
            return None
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        age_hours = (_now_utc() - modified).total_seconds() / 3600
        if age_hours > self.cache_max_age_hours:
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            raw = payload.get("raw", payload)
            error_status = _finnhub_error_status(raw)
            if error_status is not None:
                status, message = error_status
                return _empty_company(ticker, status, self.name, message)
            parsed = _parse_finnhub_response(ticker, raw, self.name, status="cache")
            parsed["sentiment_last_updated"] = payload.get("cached_at", parsed["sentiment_last_updated"])
            return parsed
        except Exception:
            return None

    def _write_cache(self, ticker: str, payload: dict) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        wrapped = {"ticker": ticker.upper(), "cached_at": _now_utc().isoformat(timespec="seconds"), "raw": payload}
        self._cache_path(ticker).write_text(json.dumps(wrapped, indent=2), encoding="utf-8")

    def fetch_company_sentiment(self, ticker: str) -> dict:
        ticker = ticker.upper()
        cached = self._read_fresh_cache(ticker)
        if cached is not None:
            return cached
        if not self.api_key:
            return _empty_company(ticker, "disabled_no_api_key", self.name, f"Set {FINNHUB_API_KEY_ENV} to enable Finnhub sentiment.")

        query = urlencode({"symbol": ticker, "token": self.api_key})
        url = f"https://finnhub.io/api/v1/news-sentiment?{query}"
        try:
            with urlopen(url, timeout=12) as response:
                payload = json.loads(response.read().decode("utf-8"))
            error_status = _finnhub_error_status(payload)
            if error_status is not None:
                status, message = error_status
                return _empty_company(ticker, status, self.name, message)
            self._write_cache(ticker, payload)
            return _parse_finnhub_response(ticker, payload, self.name, status="live")
        except HTTPError as exc:
            status = "rate_limited" if exc.code == 429 else "invalid_api_key" if exc.code in {401, 403} else "error"
            return _empty_company(ticker, status, self.name, f"Finnhub HTTP {exc.code}")
        except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            return _empty_company(ticker, "error", self.name, str(exc))


class DemoSentimentProvider(SentimentProvider):
    """Deterministic synthetic sentiment for tests and demonstrations only."""

    name = "demo"

    def fetch_company_sentiment(self, ticker: str) -> dict:
        ticker = ticker.upper()
        seed = sum((idx + 1) * ord(char) for idx, char in enumerate(ticker))
        rng = np.random.default_rng(seed)
        bullish = float(np.clip(rng.normal(0.52, 0.12), 0.05, 0.95))
        bearish = float(np.clip(rng.normal(0.28, 0.10), 0.01, 0.90))
        article_count = int(rng.integers(3, 80))
        score = float(np.clip((bullish - bearish + 1) / 2, 0, 1))
        buzz = float(np.clip(rng.normal(0.8, 0.25), 0, 2))
        return {
            "ticker": ticker,
            "bullishPercent": bullish,
            "bearishPercent": bearish,
            "companyNewsScore": score,
            "sectorAverageBullishPercent": bullish,
            "sectorAverageNewsScore": score,
            "articlesInLastWeek": article_count,
            "buzz": buzz,
            "sentiment_data_status": "demo",
            "sentiment_provider": self.name,
            "sentiment_last_updated": _now_utc().isoformat(timespec="seconds"),
            "error": "",
        }


def _weighted_average(values: list[float], weights: list[int]) -> float:
    numeric = pd.to_numeric(pd.Series(values), errors="coerce")
    valid = numeric.notna()
    if not valid.any():
        return np.nan
    usable_weights = pd.to_numeric(pd.Series(weights), errors="coerce").fillna(0).clip(lower=0)
    if usable_weights[valid].sum() <= 0:
        return float(numeric[valid].mean())
    return float(np.average(numeric[valid], weights=usable_weights[valid]))


def aggregate_sector_sentiment(sector: str, tickers: list[str], provider: SentimentProvider | None = None) -> dict:
    """Aggregate representative company sentiment into sector-level features."""
    provider = provider or FinnhubSentimentProvider()
    company_rows = [provider.fetch_company_sentiment(ticker) for ticker in tickers]
    valid_rows = [row for row in company_rows if pd.notna(row.get("companyNewsScore"))]

    statuses = [str(row.get("sentiment_data_status", "missing")) for row in company_rows]
    if not valid_rows:
        if statuses and all(status == "disabled_no_api_key" for status in statuses):
            status = "disabled_no_api_key"
        elif statuses and any(status == "invalid_api_key" for status in statuses):
            status = "invalid_api_key"
        elif statuses and all(status == "demo" for status in statuses):
            status = "demo"
        elif statuses and any(status == "rate_limited" for status in statuses):
            status = "rate_limited"
        elif statuses and all(status == "no_data" for status in statuses):
            status = "no_data"
        else:
            status = "missing"
        return {
            "sentiment_score": np.nan,
            "sentiment_score_component": 0.0,
            "sentiment_bullish_percent": np.nan,
            "sentiment_bearish_percent": np.nan,
            "sentiment_buzz": np.nan,
            "sentiment_article_count": 0,
            "sentiment_coverage_count": 0,
            "sentiment_data_status": status,
            "sentiment_provider": provider.name,
            "sentiment_last_updated": _now_utc().isoformat(timespec="seconds"),
        }

    weights = [_as_int(row.get("articlesInLastWeek")) for row in valid_rows]
    score = _weighted_average([row.get("companyNewsScore") for row in valid_rows], weights)
    status = "demo" if all(str(row.get("sentiment_data_status")) == "demo" for row in valid_rows) else "available"
    if any(str(row.get("sentiment_data_status")) == "cache" for row in valid_rows):
        status = "cache" if status != "demo" else status
    if any(str(row.get("sentiment_data_status")) == "live" for row in valid_rows):
        status = "live"
    return {
        "sentiment_score": score,
        "sentiment_score_component": float(np.clip(score * 100, 0, 100)) if pd.notna(score) else 0.0,
        "sentiment_bullish_percent": _weighted_average([row.get("bullishPercent") for row in valid_rows], weights),
        "sentiment_bearish_percent": _weighted_average([row.get("bearishPercent") for row in valid_rows], weights),
        "sentiment_buzz": _weighted_average([row.get("buzz") for row in valid_rows], weights),
        "sentiment_article_count": int(sum(weights)),
        "sentiment_coverage_count": len(valid_rows),
        "sentiment_data_status": status,
        "sentiment_provider": provider.name,
        "sentiment_last_updated": max(str(row.get("sentiment_last_updated", "")) for row in valid_rows),
    }


def sentiment_not_used_features(status: str = "not_used", provider: str = "disabled_by_mode") -> dict:
    """Return explicit empty sentiment fields for disabled modes."""
    return {
        "sentiment_score": np.nan,
        "sentiment_score_component": 0.0,
        "sentiment_bullish_percent": np.nan,
        "sentiment_bearish_percent": np.nan,
        "sentiment_buzz": np.nan,
        "sentiment_article_count": 0,
        "sentiment_coverage_count": 0,
        "sentiment_data_status": status,
        "sentiment_provider": provider,
        "sentiment_last_updated": "",
    }
