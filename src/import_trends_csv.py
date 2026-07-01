"""Import manually downloaded Google Trends CSV files into SQLite."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEFAULT_TREND_GEO, DEFAULT_TREND_TIMEFRAME
from src.db_loader import save_google_trends, save_trend_features
from src.db_schema import create_database_schema


def _read_google_trends_csv(path: Path) -> pd.DataFrame:
    for skiprows in (0, 1, 2, 3):
        try:
            data = pd.read_csv(path, skiprows=skiprows)
        except pd.errors.EmptyDataError:
            continue
        date_columns = [column for column in data.columns if str(column).strip().lower() in {"date", "week", "month", "day"}]
        if date_columns:
            date_column = date_columns[0]
            break
    else:
        raise ValueError(f"Could not find a date/week column in {path}")

    data = data.rename(columns={date_column: "date"})
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data = data.dropna(subset=["date"])
    value_columns = [column for column in data.columns if column != "date"]
    long = data.melt(id_vars=["date"], value_vars=value_columns, var_name="keyword", value_name="trend_value")
    long["keyword"] = long["keyword"].astype(str).str.replace(r":\s*\([^)]*\)$", "", regex=True).str.strip()
    long["trend_value"] = pd.to_numeric(long["trend_value"].astype(str).str.replace("<1", "0.5", regex=False), errors="coerce")
    return long.dropna(subset=["trend_value"])


def import_file(path: Path, sector: str, geo: str, timeframe: str) -> int:
    create_database_schema()
    long = _read_google_trends_csv(path)
    save_google_trends(long, sector=sector, source_file=path, geo=geo, timeframe=timeframe)
    feature_input = long.groupby("date", as_index=False)["trend_value"].mean().rename(columns={"trend_value": "value"})
    feature_input["sector"] = sector
    save_trend_features(feature_input, sector)
    return len(long)


def _sector_from_filename(path: Path) -> str:
    name = path.stem
    for prefix in ("google_trends_manual_", "google_trends_"):
        if name.lower().startswith(prefix):
            name = name[len(prefix):]
            break
    return name.replace("_", " ").title()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import manual Google Trends CSV exports into SQLite.")
    parser.add_argument("--file", type=Path, help="Path to one Google Trends CSV export.")
    parser.add_argument("--folder", type=Path, help="Folder containing Google Trends CSV exports.")
    parser.add_argument("--sector", help="Sector name for --file imports.")
    parser.add_argument("--geo", default=DEFAULT_TREND_GEO)
    parser.add_argument("--timeframe", default=DEFAULT_TREND_TIMEFRAME)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.file:
        sector = args.sector
        if not sector:
            raise SystemExit("--sector is required when --file is used")
        rows = import_file(args.file, sector, args.geo, args.timeframe)
        print(f"[OK] Imported Google Trends rows: {sector} / {rows}")
    elif args.folder:
        total = 0
        for file_path in sorted(args.folder.glob("*.csv")):
            sector = args.sector or _sector_from_filename(file_path)
            rows = import_file(file_path, sector, args.geo, args.timeframe)
            total += rows
            print(f"[OK] Imported Google Trends rows: {sector} / {rows}")
        print(f"[OK] Imported Google Trends rows total: {total}")
    else:
        raise SystemExit("Use --file ... --sector ... or --folder ...")
