"""Load sector ETF prices and a deliberately small fundamental data set."""

import numpy as np
import pandas as pd
import yfinance as yf

from src.config import SECTOR_ETFS


def get_sector_etfs() -> dict[str, str]:
    return dict(SECTOR_ETFS)


def load_market_data(ticker: str, period: str = "5y") -> pd.DataFrame:
    """Return clean OHLCV download data, or an empty frame with a warning."""
    try:
        data = yf.download(ticker, period=period, progress=False, auto_adjust=False)
    except Exception as exc:  # network dependent
        print(f"[WARN] Market data unavailable for {ticker}: {exc}")
        return pd.DataFrame()
    if data is None or data.empty:
        print(f"[WARN] No market data returned for {ticker}.")
        return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [str(column[0]) for column in data.columns]
    data.index = pd.to_datetime(data.index)
    preferred = [column for column in ["Open", "High", "Low", "Close", "Adj Close", "Volume"] if column in data.columns]
    return data.loc[:, preferred].copy()


def load_fundamentals(ticker: str) -> pd.Series:
    """Return ETF-compatible fundamentals; unavailable values remain NaN."""
    fields = ["trailingPE", "forwardPE", "priceToBook", "dividendYield", "beta", "marketCap"]
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception as exc:  # network dependent
        print(f"[WARN] Fundamentals unavailable for {ticker}: {exc}")
        info = {}
    return pd.Series({field: pd.to_numeric(info.get(field), errors="coerce") for field in fields}, dtype="float64")
