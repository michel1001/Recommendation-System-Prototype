"""SQLite helpers for the local sector-monitoring data layer."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import DATABASE_PATH


def get_database_path() -> Path:
    """Return the configured SQLite database path."""
    override = os.getenv("SECTOR_MONITORING_DB_PATH")
    return Path(override).expanduser().resolve() if override else DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    """Open a SQLite connection and ensure the parent directory exists."""
    path = get_database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def execute_query(query: str, params: tuple[Any, ...] | dict[str, Any] | None = None) -> list[sqlite3.Row]:
    """Execute a SQL statement and return fetched rows for SELECT queries."""
    with get_connection() as connection:
        cursor = connection.execute(query, params or ())
        rows = cursor.fetchall()
        connection.commit()
        return rows


def read_table(table_name: str, where: str | None = None, params: tuple[Any, ...] | None = None) -> pd.DataFrame:
    """Read a table into a DataFrame with an optional WHERE clause."""
    query = f"SELECT * FROM {table_name}"
    if where:
        query += f" WHERE {where}"
    with get_connection() as connection:
        return pd.read_sql_query(query, connection, params=params)


def table_exists(table_name: str) -> bool:
    """Return True when a table exists in the configured database."""
    rows = execute_query("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return bool(rows)
