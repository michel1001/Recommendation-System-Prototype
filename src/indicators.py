"""Indicator calculations for the sector ETF ML prototype."""

from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate daily and cumulative returns from the close price."""
    data = df.copy()
    if "close" not in data.columns:
        data["daily_return"] = np.nan
        data["cumulative_return"] = np.nan
        return data

    close = pd.to_numeric(data["close"], errors="coerce")
    returns = close.pct_change()
    data["daily_return"] = returns
    data["cumulative_return"] = (1 + returns).cumprod() - 1
    return data


def calculate_moving_averages(df: pd.DataFrame, windows: list[int] | None = None) -> pd.DataFrame:
    """Add moving average columns for the requested windows."""
    if windows is None:
        windows = [20, 50, 200]

    data = df.copy()
    if "close" not in data.columns:
        for window in windows:
            data[f"ma_{window}"] = np.nan
        return data

    close = pd.to_numeric(data["close"], errors="coerce")
    for window in windows:
        data[f"ma_{window}"] = close.rolling(window).mean()
    return data


def calculate_volatility(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """Calculate rolling volatility based on daily returns."""
    data = df.copy()
    if "daily_return" in data.columns:
        returns = pd.to_numeric(data["daily_return"], errors="coerce")
    elif "close" in data.columns:
        returns = pd.to_numeric(data["close"], errors="coerce").pct_change()
    else:
        data["volatility_20"] = np.nan
        return data

    data["volatility_20"] = returns.rolling(window).std() * np.sqrt(252)
    return data


def calculate_downside_volatility(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """Calculate downside volatility from negative daily returns."""
    data = df.copy()
    if "daily_return" in data.columns:
        returns = pd.to_numeric(data["daily_return"], errors="coerce")
    else:
        data["downside_volatility_20"] = np.nan
        return data

    negative_returns = returns.where(returns < 0, np.nan)
    data["downside_volatility_20"] = negative_returns.rolling(window).std() * np.sqrt(252)
    data["downside_volatility_20"] = data["downside_volatility_20"].fillna(0.0)
    return data


def calculate_momentum(df: pd.DataFrame, windows: list[int] | None = None) -> pd.DataFrame:
    """Calculate momentum indicators relative to prior periods."""
    if windows is None:
        windows = [21, 63, 126]

    data = df.copy()
    if "close" not in data.columns:
        for window in windows:
            data[f"momentum_{window}"] = np.nan
        return data

    close = pd.to_numeric(data["close"], errors="coerce")
    for window in windows:
        data[f"momentum_{window}"] = close / close.shift(window) - 1
    return data


def calculate_max_drawdown(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate a rolling drawdown series based on cumulative returns."""
    data = df.copy()
    if "daily_return" in data.columns:
        returns = pd.to_numeric(data["daily_return"], errors="coerce")
    else:
        data["max_drawdown"] = np.nan
        return data

    wealth = (1 + returns).cumprod()
    running_max = wealth.cummax()
    drawdown = wealth / running_max - 1
    data["max_drawdown"] = drawdown
    return data


def calculate_drawdowns(df: pd.DataFrame) -> pd.DataFrame:
    """Add both historical drawdown and current drawdown columns."""
    return calculate_current_drawdown(calculate_max_drawdown(df))


def calculate_current_drawdown(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate the current drawdown versus the historical high."""
    data = df.copy()
    if "close" not in data.columns:
        data["drawdown_current"] = np.nan
        return data

    close = pd.to_numeric(data["close"], errors="coerce")
    data["drawdown_current"] = close / close.cummax() - 1
    return data


def calculate_distance_to_ma(df: pd.DataFrame, window: int = 200) -> pd.DataFrame:
    """Measure the current price distance to the moving average."""
    data = df.copy()
    if "close" not in data.columns:
        data["distance_to_ma_200"] = np.nan
        return data

    close = pd.to_numeric(data["close"], errors="coerce")
    ma = close.rolling(window).mean()
    data["distance_to_ma_200"] = close / ma - 1
    return data


def calculate_volume_momentum(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """Compare current volume to its rolling average."""
    data = df.copy()
    if "volume" not in data.columns:
        data["volume_momentum_20"] = np.nan
        return data

    volume = pd.to_numeric(data["volume"], errors="coerce")
    rolling_avg = volume.rolling(window).mean()
    data["volume_momentum_20"] = volume / rolling_avg
    return data


def calculate_risk_adjusted_return(df: pd.DataFrame) -> pd.DataFrame:
    """Compute momentum over volatility as a simple risk-adjusted signal."""
    data = df.copy()
    if "momentum_63" not in data.columns or "volatility_20" not in data.columns:
        data["risk_adjusted_return_63"] = np.nan
        return data

    momentum = pd.to_numeric(data["momentum_63"], errors="coerce")
    volatility = pd.to_numeric(data["volatility_20"], errors="coerce")
    data["risk_adjusted_return_63"] = momentum / volatility.replace(0, np.nan)
    return data


def enrich_market_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Create the full indicator feature set used by the ML model."""
    data = df.copy()
    data = calculate_returns(data)
    data = calculate_moving_averages(data, windows=[20, 50, 200])
    data = calculate_volatility(data, window=20)
    data = calculate_downside_volatility(data, window=20)
    data = calculate_momentum(data, windows=[21, 63, 126])
    data = calculate_drawdowns(data)
    data = calculate_distance_to_ma(data, window=200)
    data = calculate_volume_momentum(data, window=20)
    data = calculate_risk_adjusted_return(data)
    return data
