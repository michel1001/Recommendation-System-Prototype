"""Schema management for the local SQLite persistence layer."""

from __future__ import annotations

from src.database import get_connection


SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS sectors (
        sector TEXT PRIMARY KEY,
        ticker TEXT,
        description TEXT,
        created_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS market_prices (
        date TEXT,
        sector TEXT,
        ticker TEXT,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        adj_close REAL,
        volume REAL,
        source TEXT,
        loaded_at TEXT,
        PRIMARY KEY (date, ticker)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS market_indicators (
        date TEXT,
        sector TEXT,
        ticker TEXT,
        daily_return REAL,
        cumulative_return REAL,
        ma_20 REAL,
        ma_50 REAL,
        ma_200 REAL,
        momentum_21 REAL,
        momentum_63 REAL,
        momentum_126 REAL,
        volatility_20 REAL,
        downside_volatility_20 REAL,
        drawdown_current REAL,
        max_drawdown REAL,
        distance_to_ma_200 REAL,
        volume_momentum_20 REAL,
        risk_adjusted_return_63 REAL,
        relative_strength_vs_spy_63 REAL,
        relative_strength_vs_spy_126 REAL,
        source TEXT,
        loaded_at TEXT,
        PRIMARY KEY (date, ticker)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS fundamentals (
        as_of_date TEXT,
        sector TEXT,
        ticker TEXT,
        trailing_pe REAL,
        forward_pe REAL,
        price_to_book REAL,
        dividend_yield REAL,
        beta REAL,
        market_cap REAL,
        source TEXT,
        loaded_at TEXT,
        PRIMARY KEY (as_of_date, ticker)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS google_trends (
        date TEXT,
        sector TEXT,
        keyword TEXT,
        trend_value REAL,
        geo TEXT,
        timeframe TEXT,
        source_file TEXT,
        source TEXT,
        loaded_at TEXT,
        PRIMARY KEY (date, sector, keyword, geo, timeframe)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS trend_features (
        date TEXT,
        sector TEXT,
        trend_mean REAL,
        trend_latest REAL,
        trend_momentum_4w REAL,
        trend_momentum_12w REAL,
        trend_z_score_12w REAL,
        trend_z_score_52w REAL,
        trend_spike INTEGER,
        trend_acceleration REAL,
        trend_percentile_52w REAL,
        trend_data_status TEXT,
        source TEXT,
        loaded_at TEXT,
        PRIMARY KEY (date, sector)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ml_sector_rankings (
        run_id TEXT,
        run_timestamp TEXT,
        operating_mode TEXT,
        rank INTEGER,
        date TEXT,
        sector TEXT,
        ticker TEXT,
        ml_model_status TEXT,
        ml_predicted_outperform_probability REAL,
        ml_model_confidence REAL,
        ml_signal_label TEXT,
        data_readiness_status TEXT,
        PRIMARY KEY (run_id, sector)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pipeline_runs (
        run_id TEXT PRIMARY KEY,
        run_timestamp TEXT,
        operating_mode TEXT,
        trend_mode TEXT,
        use_ml INTEGER,
        use_sentiment INTEGER,
        status TEXT,
        notes TEXT
    )
    """,
]


def create_database_schema() -> None:
    """Create all SQLite tables used by the prototype."""
    with get_connection() as connection:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
        connection.commit()
