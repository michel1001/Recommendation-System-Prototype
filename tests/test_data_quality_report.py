import sqlite3

import pandas as pd

from src.data_quality_report import (
    generate_data_quality_report,
    google_trends_quality,
    missing_values_summary,
    sector_coverage_summary,
    table_row_counts,
    fundamentals_quality,
)
from src.db_schema import SCHEMA_STATEMENTS


def _create_database(path):
    with sqlite3.connect(path) as connection:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
        connection.commit()


def test_table_row_count_summary_and_missing_detection(tmp_path):
    db_path = tmp_path / "quality.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE sectors (sector TEXT PRIMARY KEY, ticker TEXT)")
        connection.execute("INSERT INTO sectors VALUES ('Technology', 'XLK')")
        counts = table_row_counts(connection)

    sectors = counts.loc[counts["table_name"].eq("sectors")].iloc[0]
    prices = counts.loc[counts["table_name"].eq("market_prices")].iloc[0]
    assert sectors["row_count"] == 1
    assert sectors["status"] == "OK"
    assert prices["status"] == "MISSING"


def test_sector_coverage_detects_missing_communication_services(tmp_path):
    db_path = tmp_path / "quality.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE sectors (sector TEXT PRIMARY KEY, ticker TEXT)")
        connection.execute("INSERT INTO sectors VALUES ('Technology', 'XLK')")
        summary = sector_coverage_summary(connection)

    communication = summary.loc[summary["expected_sector"].eq("Communication Services")].iloc[0]
    assert communication["expected_ticker"] == "XLC"
    assert communication["status"] == "MISSING"


def test_missing_values_summary_counts_nulls(tmp_path):
    db_path = tmp_path / "quality.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE fundamentals (ticker TEXT, beta REAL)")
        connection.executemany("INSERT INTO fundamentals VALUES (?, ?)", [("XLK", 1.1), ("XLC", None)])
        missing = missing_values_summary(connection)

    beta = missing.loc[(missing["table_name"].eq("fundamentals")) & (missing["column_name"].eq("beta"))].iloc[0]
    assert beta["row_count"] == 2
    assert beta["missing_count"] == 1
    assert beta["missing_pct"] == 50.0


def test_fundamentals_quality_detects_partial_data(tmp_path):
    db_path = tmp_path / "quality.db"
    _create_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO fundamentals
            (as_of_date, sector, ticker, trailing_pe, forward_pe, price_to_book, dividend_yield, beta, market_cap, source, loaded_at)
            VALUES ('2026-01-01', 'Technology', 'XLK', 20, NULL, NULL, NULL, NULL, NULL, 'test', 'now')
            """
        )
        quality = fundamentals_quality(connection)

    row = quality.iloc[0]
    assert row["available_field_count"] == 1
    assert row["status"] == "PARTIAL"


def test_google_trends_quality_detects_empty_data(tmp_path):
    db_path = tmp_path / "quality.db"
    _create_database(db_path)
    with sqlite3.connect(db_path) as connection:
        quality = google_trends_quality(connection)

    assert set(quality["status"]) == {"NOT_USED"}
    assert quality.loc[quality["sector"].eq("Communication Services"), "raw_trend_rows"].iloc[0] == 0


def test_markdown_report_and_csv_outputs_are_created(tmp_path):
    db_path = tmp_path / "quality.db"
    output_dir = tmp_path / "reports"
    _create_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute("INSERT INTO sectors (sector, ticker, description, created_at) VALUES ('Technology', 'XLK', '', 'now')")
        connection.execute(
            """
            INSERT INTO fundamentals
            (as_of_date, sector, ticker, trailing_pe, forward_pe, price_to_book, dividend_yield, beta, market_cap, source, loaded_at)
            VALUES ('2026-01-01', 'Technology', 'XLK', 20, NULL, 2, NULL, NULL, NULL, 'test', 'now')
            """
        )
        connection.execute(
            """
            INSERT INTO market_prices
            (date, sector, ticker, open, high, low, close, adj_close, volume, source, loaded_at)
            VALUES ('2026-01-01', 'Technology', 'XLK', 1, 1, 1, 1, 1, 100, 'test', 'now')
            """
        )
        connection.commit()

    result = generate_data_quality_report(db_path, output_dir)
    assert result["markdown_path"].exists()
    assert (output_dir / "table_row_counts.csv").exists()
    assert (output_dir / "missing_values_summary.csv").exists()
    assert (output_dir / "sector_coverage_summary.csv").exists()
    assert "Communication Services" in result["markdown_path"].read_text(encoding="utf-8")
