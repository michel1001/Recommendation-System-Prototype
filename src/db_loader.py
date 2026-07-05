"""Read/write helpers for the SQLite sector-monitoring database."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.database import get_connection, read_table, table_exists
from src.trends_loader import calculate_trend_features


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _date(value: Any | None = None) -> str:
    parsed = pd.Timestamp.now().normalize() if value is None else pd.to_datetime(value)
    return parsed.strftime("%Y-%m-%d")


def _float(value: Any) -> float | None:
    parsed = pd.to_numeric(value, errors="coerce")
    return None if pd.isna(parsed) else float(parsed)


def _prepare_dated_frame(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    if "date" not in data.columns:
        data = data.reset_index().rename(columns={"index": "date", "Date": "date"})
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    return data.dropna(subset=["date"]).sort_values("date")


def _query_date_clause(ticker_or_sector_column: str, start_date: str | None, end_date: str | None) -> str:
    clause = f"{ticker_or_sector_column} = ?"
    if start_date:
        clause += " AND date >= ?"
    if end_date:
        clause += " AND date <= ?"
    return clause


def _query_params(value: str, start_date: str | None, end_date: str | None) -> list[str]:
    params = [value]
    if start_date:
        params.append(start_date)
    if end_date:
        params.append(end_date)
    return params


def upsert_sectors(sector_etfs: dict[str, str]) -> None:
    rows = [(sector, ticker, f"Sector ETF proxy for {sector}", _now()) for sector, ticker in sector_etfs.items()]
    with get_connection() as connection:
        connection.executemany(
            "INSERT OR REPLACE INTO sectors (sector, ticker, description, created_at) VALUES (?, ?, ?, ?)",
            rows,
        )
        connection.commit()


def save_market_prices(df: pd.DataFrame, sector: str, ticker: str) -> None:
    data = _prepare_dated_frame(df)
    rows = [
        (
            row.date.strftime("%Y-%m-%d"), sector, ticker,
            _float(getattr(row, "open", np.nan)), _float(getattr(row, "high", np.nan)),
            _float(getattr(row, "low", np.nan)), _float(getattr(row, "close", np.nan)),
            _float(getattr(row, "adj_close", np.nan)), _float(getattr(row, "volume", np.nan)),
            "yfinance", _now(),
        )
        for row in data.itertuples(index=False)
    ]
    with get_connection() as connection:
        connection.executemany(
            """
            INSERT OR REPLACE INTO market_prices
            (date, sector, ticker, open, high, low, close, adj_close, volume, source, loaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        connection.commit()


def load_market_prices(ticker: str, start_date: str | None = None, end_date: str | None = None) -> pd.DataFrame:
    if not table_exists("market_prices"):
        return pd.DataFrame()
    df = read_table("market_prices", _query_date_clause("ticker", start_date, end_date), tuple(_query_params(ticker, start_date, end_date)))
    if df.empty:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date").sort_index()[["open", "high", "low", "close", "adj_close", "volume"]]


def save_market_indicators(df: pd.DataFrame, sector: str, ticker: str) -> None:
    data = _prepare_dated_frame(df)
    columns = [
        "daily_return", "cumulative_return", "ma_20", "ma_50", "ma_200", "momentum_21", "momentum_63",
        "momentum_126", "volatility_20", "downside_volatility_20", "drawdown_current", "max_drawdown",
        "distance_to_ma_200", "volume_momentum_20", "risk_adjusted_return_63",
        "relative_strength_vs_spy_63", "relative_strength_vs_spy_126",
    ]
    rows = []
    for row in data.itertuples(index=False):
        row_dict = row._asdict()
        rows.append((row_dict["date"].strftime("%Y-%m-%d"), sector, ticker, *[_float(row_dict.get(column)) for column in columns], "calculated", _now()))
    placeholders = ", ".join("?" for _ in range(22))
    with get_connection() as connection:
        connection.executemany(
            f"""
            INSERT OR REPLACE INTO market_indicators
            (date, sector, ticker, {', '.join(columns)}, source, loaded_at)
            VALUES ({placeholders})
            """,
            rows,
        )
        connection.commit()


def load_market_indicators(ticker: str, start_date: str | None = None, end_date: str | None = None) -> pd.DataFrame:
    if not table_exists("market_indicators"):
        return pd.DataFrame()
    df = read_table("market_indicators", _query_date_clause("ticker", start_date, end_date), tuple(_query_params(ticker, start_date, end_date)))
    if df.empty:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"])
    drop_columns = [column for column in ["sector", "ticker", "source", "loaded_at"] if column in df.columns]
    return df.drop(columns=drop_columns).set_index("date").sort_index()


def save_fundamentals(fundamentals_dict: dict[str, Any] | pd.Series, sector: str, ticker: str, as_of_date: str | None = None) -> None:
    values = dict(fundamentals_dict)
    mapping = {
        "trailing_pe": values.get("trailing_pe", values.get("trailingPE")),
        "forward_pe": values.get("forward_pe", values.get("forwardPE")),
        "price_to_book": values.get("price_to_book", values.get("priceToBook")),
        "dividend_yield": values.get("dividend_yield", values.get("dividendYield")),
        "beta": values.get("beta"),
        "market_cap": values.get("market_cap", values.get("marketCap")),
    }
    row = (_date(as_of_date), sector, ticker, *[_float(mapping[key]) for key in mapping], "yfinance", _now())
    with get_connection() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO fundamentals
            (as_of_date, sector, ticker, trailing_pe, forward_pe, price_to_book, dividend_yield, beta, market_cap, source, loaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            row,
        )
        connection.commit()


def load_latest_fundamentals(ticker: str) -> pd.Series:
    if not table_exists("fundamentals"):
        return pd.Series(dtype="float64")
    with get_connection() as connection:
        df = pd.read_sql_query("SELECT * FROM fundamentals WHERE ticker = ? ORDER BY as_of_date DESC LIMIT 1", connection, params=(ticker,))
    if df.empty:
        return pd.Series(dtype="float64")
    row = df.iloc[0]
    return pd.Series(
        {
            "trailingPE": _float(row.get("trailing_pe")),
            "forwardPE": _float(row.get("forward_pe")),
            "priceToBook": _float(row.get("price_to_book")),
            "dividendYield": _float(row.get("dividend_yield")),
            "beta": _float(row.get("beta")),
            "marketCap": _float(row.get("market_cap")),
        },
        dtype="float64",
    )


def save_google_trends(df: pd.DataFrame, sector: str, source_file: str | Path | None = None, geo: str = "US", timeframe: str = "today 5-y") -> None:
    data = df.copy()
    if "date" not in data.columns:
        data = data.reset_index().rename(columns={"index": "date"})
    if "keyword" not in data.columns and "value" in data.columns:
        data["keyword"] = sector
        data["trend_value"] = data["value"]
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data = data.dropna(subset=["date"])
    rows = [
        (
            row.date.strftime("%Y-%m-%d"), sector, str(row.keyword), _float(row.trend_value),
            geo, timeframe, str(source_file or ""), "manual_csv", _now(),
        )
        for row in data.itertuples(index=False)
    ]
    with get_connection() as connection:
        connection.executemany(
            """
            INSERT OR REPLACE INTO google_trends
            (date, sector, keyword, trend_value, geo, timeframe, source_file, source, loaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        connection.commit()


def load_google_trends(sector: str, start_date: str | None = None, end_date: str | None = None) -> pd.DataFrame:
    if not table_exists("google_trends"):
        return pd.DataFrame(columns=["date", "sector", "value"])
    df = read_table("google_trends", _query_date_clause("sector", start_date, end_date), tuple(_query_params(sector, start_date, end_date)))
    if df.empty:
        return pd.DataFrame(columns=["date", "sector", "value"])
    df["date"] = pd.to_datetime(df["date"])
    grouped = df.groupby(["date", "sector"], as_index=False)["trend_value"].mean()
    return grouped.rename(columns={"trend_value": "value"}).sort_values("date")


def save_trend_features(df: pd.DataFrame | dict[str, Any], sector: str) -> None:
    if isinstance(df, dict):
        features = dict(df)
        feature_date = features.get("trend_last_date") or _date()
    else:
        data = df.copy()
        features = calculate_trend_features(data if "value" in data.columns else load_google_trends(sector))
        feature_date = features.get("trend_last_date") or (pd.to_datetime(data["date"]).max().strftime("%Y-%m-%d") if "date" in data and not data.empty else _date())
    row = (
        feature_date, sector, _float(features.get("trend_mean")), _float(features.get("trend_latest")),
        _float(features.get("trend_momentum_4w")), _float(features.get("trend_momentum_12w")),
        _float(features.get("trend_z_score_12w")), _float(features.get("trend_z_score_52w")),
        int(bool(features.get("trend_spike", False))), _float(features.get("trend_acceleration")),
        _float(features.get("trend_percentile_52w")), str(features.get("trend_data_status", "manual_csv")),
        "calculated", _now(),
    )
    with get_connection() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO trend_features
            (date, sector, trend_mean, trend_latest, trend_momentum_4w, trend_momentum_12w, trend_z_score_12w,
             trend_z_score_52w, trend_spike, trend_acceleration, trend_percentile_52w, trend_data_status, source, loaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            row,
        )
        connection.commit()


def load_latest_trend_features(sector: str) -> dict[str, Any]:
    if not table_exists("trend_features"):
        return {}
    with get_connection() as connection:
        df = pd.read_sql_query("SELECT * FROM trend_features WHERE sector = ? ORDER BY date DESC LIMIT 1", connection, params=(sector,))
    if df.empty:
        return {}
    row = df.iloc[0].to_dict()
    row["trend_spike"] = bool(row.get("trend_spike"))
    row["trend_last_date"] = row.get("date", "")
    row["trend_observations"] = np.nan
    row["trend_volatility"] = np.nan
    return row


def save_ml_sector_rankings(df: pd.DataFrame, run_id: str, run_timestamp: str) -> None:
    columns = [
        "operating_mode", "rank", "date", "sector", "ticker", "ml_model_status",
        "ml_predicted_outperform_probability", "ml_model_confidence", "ml_signal_label", "data_readiness_status",
    ]
    rows = []
    for _, item in df.iterrows():
        rows.append((run_id, run_timestamp, *[item.get(column) for column in columns]))
    with get_connection() as connection:
        connection.executemany(
            """
            INSERT OR REPLACE INTO ml_sector_rankings
            (run_id, run_timestamp, operating_mode, rank, date, sector, ticker, ml_model_status,
             ml_predicted_outperform_probability, ml_model_confidence, ml_signal_label, data_readiness_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        connection.commit()


def save_pipeline_run(run_id: str, metadata: dict[str, Any]) -> None:
    row = (
        run_id,
        metadata.get("run_timestamp", _now()),
        metadata.get("operating_mode", ""),
        metadata.get("trend_mode", ""),
        int(bool(metadata.get("use_ml", False))),
        int(bool(metadata.get("use_sentiment", False))),
        metadata.get("status", "completed"),
        metadata.get("notes", ""),
    )
    with get_connection() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO pipeline_runs
            (run_id, run_timestamp, operating_mode, trend_mode, use_ml, use_sentiment, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            row,
        )
        connection.commit()
