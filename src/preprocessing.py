"""Robust cleaning helpers for downloaded OHLCV data."""

import numpy as np
import pandas as pd


def clean_market_data(df: pd.DataFrame | None) -> pd.DataFrame:
    """Standardise OHLCV column names while preserving available price fields."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "adj_close", "volume"])
    data = df.copy()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [str(column[0]) for column in data.columns]
    data.columns = [str(column).strip().lower().replace(" ", "_") for column in data.columns]
    data.index = pd.to_datetime(data.index, errors="coerce")
    data = data.loc[~data.index.isna()].sort_index()
    aliases = {"open": "open", "high": "high", "low": "low", "close": "close", "adj_close": "adj_close", "volume": "volume"}
    cleaned = pd.DataFrame(index=data.index)
    for target, source in aliases.items():
        cleaned[target] = pd.to_numeric(data[source], errors="coerce") if source in data else np.nan
    if cleaned["close"].isna().all() and not cleaned["adj_close"].isna().all():
        cleaned["close"] = cleaned["adj_close"]
    cleaned[["open", "high", "low", "close", "adj_close"]] = cleaned[["open", "high", "low", "close", "adj_close"]].ffill().bfill()
    cleaned["volume"] = cleaned["volume"].fillna(0.0)
    return cleaned


def normalize_series(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    if values.dropna().empty or values.max() == values.min():
        return pd.Series(50.0, index=values.index)
    return (values - values.min()) / (values.max() - values.min()) * 100.0


def safe_last_value(series: pd.Series | None, default: float = np.nan) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna() if series is not None else pd.Series(dtype=float)
    return float(values.iloc[-1]) if not values.empty else default
