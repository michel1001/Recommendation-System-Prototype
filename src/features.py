"""Feature assembly and readiness labels for the ML sector model."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.config import DATA_FRESHNESS_DAYS
from src.preprocessing import safe_last_value
from src.trends_loader import calculate_trend_features


MARKET_FIELDS = [
    "momentum_21",
    "momentum_63",
    "momentum_126",
    "volatility_20",
    "downside_volatility_20",
    "drawdown_current",
    "distance_to_ma_200",
    "risk_adjusted_return_63",
    "volume_momentum_20",
]
FUNDAMENTAL_FIELDS = ["trailingPE", "forwardPE", "priceToBook", "dividendYield", "beta", "marketCap"]
MISSING_TREND_STATUSES = {"fallback", "missing_from_db"}


def collect_latest_features(
    sector: str,
    ticker: str,
    market_df: pd.DataFrame | None,
    fundamentals: pd.Series | None,
    trend_features: dict[str, Any] | None = None,
    google_trends: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Create one latest point-in-time feature record for a sector ETF."""
    row: dict[str, Any] = {"sector": sector, "ticker": ticker}
    for field in MARKET_FIELDS:
        row[field] = safe_last_value(market_df[field]) if market_df is not None and field in market_df else np.nan
    for field in FUNDAMENTAL_FIELDS:
        row[field] = pd.to_numeric(fundamentals.get(field), errors="coerce") if fundamentals is not None else np.nan
    row.update(trend_features if trend_features is not None else calculate_trend_features(google_trends if google_trends is not None else pd.DataFrame()))
    return row


def _is_stale(value: Any, threshold_days: int = DATA_FRESHNESS_DAYS) -> bool:
    date = pd.to_datetime(value, errors="coerce")
    if pd.isna(date):
        return False
    return (pd.Timestamp.now().normalize() - date.normalize()).days > threshold_days


def assess_data_readiness(row: pd.Series | dict[str, Any]) -> str:
    """Classify whether the latest feature row is usable for ML inference."""
    data = dict(row)
    key_market_fields = ("momentum_21", "momentum_63", "volatility_20", "drawdown_current")
    if str(data.get("price_data_status", "missing")).lower() == "missing":
        return "Insufficient market data"
    if any(pd.isna(data.get(field)) for field in key_market_fields):
        return "Insufficient market features"
    if _is_stale(data.get("market_last_date")):
        return "Stale market data"
    if str(data.get("trend_data_status", "")).lower() == "demo":
        return "Prototype trend data"
    return "Ready for ML inference"


def ml_signal_label(probability: Any) -> str:
    """Convert model probability into non-trading research language."""
    prob = pd.to_numeric(probability, errors="coerce")
    if pd.isna(prob):
        return "Model unavailable"
    if prob >= 0.58:
        return "High outperformance probability"
    if prob <= 0.42:
        return "Low outperformance probability"
    return "Unclear model signal"


def ml_explanation(row: pd.Series | dict[str, Any]) -> str:
    data = dict(row)
    label = ml_signal_label(data.get("ml_predicted_outperform_probability"))
    trend_status = str(data.get("trend_data_status", "")).lower()
    if trend_status == "demo":
        return f"{label}. Google Trends features are synthetic demo inputs in this run."
    if trend_status in {"not_used", *MISSING_TREND_STATUSES}:
        return f"{label}. Current model ranking is based on market/fundamental features; Google Trends are not active."
    return f"{label}. Google Trends features are available as optional supporting inputs."

