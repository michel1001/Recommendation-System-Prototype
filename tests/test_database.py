import os

import pandas as pd

from src.database import get_connection, table_exists
from src.db_loader import (
    load_google_trends,
    load_latest_fundamentals,
    load_market_prices,
    save_fundamentals,
    save_google_trends,
    save_market_prices,
    upsert_sectors,
)
from src.db_schema import create_database_schema
from src.verify_database import verify_database


def _use_temp_database(monkeypatch, tmp_path):
    db_path = tmp_path / "sector_monitoring.db"
    monkeypatch.setenv("SECTOR_MONITORING_DB_PATH", str(db_path))
    return db_path


def test_schema_creation_uses_temp_database(monkeypatch, tmp_path):
    db_path = _use_temp_database(monkeypatch, tmp_path)
    create_database_schema()
    assert db_path.exists()
    for table in ("sectors", "market_prices", "market_indicators", "fundamentals", "google_trends"):
        assert table_exists(table)


def test_upsert_sectors_does_not_duplicate(monkeypatch, tmp_path):
    _use_temp_database(monkeypatch, tmp_path)
    create_database_schema()
    upsert_sectors({"Technology": "XLK", "Healthcare": "XLV"})
    upsert_sectors({"Technology": "XLK", "Healthcare": "XLV"})
    with get_connection() as connection:
        count = connection.execute("SELECT COUNT(*) FROM sectors").fetchone()[0]
    assert count == 2


def test_save_and_load_market_prices_without_duplicates(monkeypatch, tmp_path):
    _use_temp_database(monkeypatch, tmp_path)
    create_database_schema()
    prices = pd.DataFrame(
        {"open": [1, 2], "high": [2, 3], "low": [0.5, 1.5], "close": [1.5, 2.5], "adj_close": [1.4, 2.4], "volume": [100, 200]},
        index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
    )
    save_market_prices(prices, "Technology", "XLK")
    save_market_prices(prices, "Technology", "XLK")
    loaded = load_market_prices("XLK")
    assert len(loaded) == 2
    assert list(loaded.columns) == ["open", "high", "low", "close", "adj_close", "volume"]
    assert loaded.loc[pd.Timestamp("2024-01-02"), "close"] == 2.5


def test_save_and_load_latest_fundamentals(monkeypatch, tmp_path):
    _use_temp_database(monkeypatch, tmp_path)
    create_database_schema()
    save_fundamentals({"trailingPE": 20, "forwardPE": 18, "priceToBook": 4, "dividendYield": 0.01, "beta": 1.1, "marketCap": 1000}, "Technology", "XLK", "2024-01-01")
    save_fundamentals({"trailingPE": 22, "forwardPE": 19, "priceToBook": 5, "dividendYield": 0.02, "beta": 1.2, "marketCap": 2000}, "Technology", "XLK", "2024-02-01")
    loaded = load_latest_fundamentals("XLK")
    assert loaded["trailingPE"] == 22
    assert loaded["priceToBook"] == 5


def test_save_and_load_google_trends_without_duplicates(monkeypatch, tmp_path):
    _use_temp_database(monkeypatch, tmp_path)
    create_database_schema()
    trends = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-08"]),
            "keyword": ["ai", "cloud", "ai"],
            "trend_value": [80, 60, 90],
        }
    )
    save_google_trends(trends, "Technology", source_file="manual.csv", geo="US", timeframe="today 5-y")
    save_google_trends(trends, "Technology", source_file="manual.csv", geo="US", timeframe="today 5-y")
    loaded = load_google_trends("Technology")
    assert len(loaded) == 2
    assert loaded.loc[loaded["date"].eq(pd.Timestamp("2024-01-01")), "value"].iloc[0] == 70
    with get_connection() as connection:
        count = connection.execute("SELECT COUNT(*) FROM google_trends").fetchone()[0]
    assert count == 3


def test_verify_database_reports_missing_required_data(monkeypatch, tmp_path):
    _use_temp_database(monkeypatch, tmp_path)
    create_database_schema()
    upsert_sectors({"Technology": "XLK"})
    assert verify_database() is False
