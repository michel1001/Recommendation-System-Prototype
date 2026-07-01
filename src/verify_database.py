"""Verify the local SQLite database used by the prototype."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import SECTOR_ETFS
from src.database import get_connection, get_database_path, table_exists
from src.db_schema import create_database_schema

KEY_TABLES = ["sectors", "market_prices", "market_indicators", "fundamentals"]
ALL_TABLES = KEY_TABLES + ["google_trends", "trend_features", "recommendation_scores", "pipeline_runs"]


def table_row_count(table_name: str) -> int:
    if not table_exists(table_name):
        return 0
    with get_connection() as connection:
        return int(connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def verify_database() -> bool:
    path = get_database_path()
    if not path.exists():
        print(f"[ERROR] Database not found: {path}")
        return False
    create_database_schema()
    ok = True
    for table in KEY_TABLES:
        if not table_exists(table):
            print(f"[ERROR] Missing table: {table}")
            ok = False
    counts = {table: table_row_count(table) for table in ALL_TABLES}
    for table, count in counts.items():
        print(f"{table}: {count}")
    for table in ("market_prices", "market_indicators", "fundamentals"):
        if counts.get(table, 0) == 0:
            print(f"[ERROR] Table is empty: {table}")
            ok = False
    if counts.get("sectors", 0) < len(SECTOR_ETFS):
        print(f"[ERROR] sectors has fewer than expected rows: {counts.get('sectors', 0)} < {len(SECTOR_ETFS)}")
        ok = False
    if counts.get("google_trends", 0) == 0:
        print("[WARN] google_trends is empty. Market/fundamental mode can still run.")
    print("[OK] Database verified successfully." if ok else "[FAIL] Database verification failed.")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if verify_database() else 1)
