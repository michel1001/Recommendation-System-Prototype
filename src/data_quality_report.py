"""Generate a SQLite data quality report for CRISP-DM documentation."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import SECTOR_ETFS
from src.database import get_database_path

EXPECTED_TABLES = [
    "sectors",
    "market_prices",
    "market_indicators",
    "fundamentals",
    "google_trends",
    "trend_features",
    "ml_sector_rankings",
    "pipeline_runs",
]
IMPORTANT_TABLES = ["sectors", "market_prices", "market_indicators", "fundamentals"]
FUNDAMENTAL_FIELDS = ["trailing_pe", "forward_pe", "price_to_book", "dividend_yield", "beta", "market_cap"]
INDICATOR_FIELDS = [
    "momentum_21",
    "momentum_63",
    "momentum_126",
    "volatility_20",
    "drawdown_current",
    "relative_strength_vs_spy_63",
    "relative_strength_vs_spy_126",
]


def _connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)).fetchone()
    return row is not None


def _row_count(connection: sqlite3.Connection, table_name: str) -> int:
    if not _table_exists(connection, table_name):
        return 0
    return int(connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def _read_table(connection: sqlite3.Connection, table_name: str) -> pd.DataFrame:
    if not _table_exists(connection, table_name):
        return pd.DataFrame()
    return pd.read_sql_query(f"SELECT * FROM {table_name}", connection)


def table_row_counts(connection: sqlite3.Connection) -> pd.DataFrame:
    rows = []
    for table_name in EXPECTED_TABLES:
        if not _table_exists(connection, table_name):
            rows.append({"table_name": table_name, "row_count": 0, "status": "MISSING"})
            continue
        count = _row_count(connection, table_name)
        rows.append({"table_name": table_name, "row_count": count, "status": "OK" if count > 0 else "EMPTY"})
    return pd.DataFrame(rows)


def sector_coverage_summary(connection: sqlite3.Connection) -> pd.DataFrame:
    sectors = _read_table(connection, "sectors")
    ticker_by_sector = {}
    if not sectors.empty and {"sector", "ticker"}.issubset(sectors.columns):
        ticker_by_sector = dict(zip(sectors["sector"].astype(str), sectors["ticker"].astype(str)))

    rows = []
    for expected_sector, expected_ticker in SECTOR_ETFS.items():
        ticker_in_db = ticker_by_sector.get(expected_sector, "")
        present = expected_sector in ticker_by_sector
        status = "OK" if present and ticker_in_db == expected_ticker else "TICKER_MISMATCH" if present else "MISSING"
        rows.append(
            {
                "expected_sector": expected_sector,
                "expected_ticker": expected_ticker,
                "present_in_db": present,
                "ticker_in_db": ticker_in_db,
                "status": status,
            }
        )

    expected = set(SECTOR_ETFS)
    for sector, ticker in sorted(ticker_by_sector.items()):
        if sector not in expected:
            rows.append(
                {
                    "expected_sector": sector,
                    "expected_ticker": "",
                    "present_in_db": True,
                    "ticker_in_db": ticker,
                    "status": "UNEXPECTED",
                }
            )
    return pd.DataFrame(rows)


def market_price_coverage(connection: sqlite3.Connection) -> pd.DataFrame:
    prices = _read_table(connection, "market_prices")
    columns = [
        "sector",
        "ticker",
        "row_count",
        "min_date",
        "max_date",
        "number_of_missing_close",
        "number_of_missing_adj_close",
        "number_of_missing_volume",
        "duplicate_date_rows",
        "status",
    ]
    if prices.empty:
        return pd.DataFrame(columns=columns)

    rows = []
    for (sector, ticker), group in prices.groupby(["sector", "ticker"], dropna=False):
        row_count = len(group)
        missing_close = int(group["close"].isna().sum()) if "close" in group else row_count
        missing_adj_close = int(group["adj_close"].isna().sum()) if "adj_close" in group else row_count
        missing_volume = int(group["volume"].isna().sum()) if "volume" in group else row_count
        duplicates = int(group.duplicated(subset=["date", "ticker"]).sum()) if {"date", "ticker"}.issubset(group.columns) else 0
        mostly_missing_prices = missing_close / max(row_count, 1) > 0.8 and missing_adj_close / max(row_count, 1) > 0.8
        if duplicates:
            status = "DUPLICATES"
        elif mostly_missing_prices:
            status = "MISSING_PRICE_DATA"
        elif row_count < 1000:
            status = "LOW_HISTORY"
        else:
            status = "OK"
        rows.append(
            {
                "sector": sector,
                "ticker": ticker,
                "row_count": row_count,
                "min_date": pd.to_datetime(group["date"], errors="coerce").min().strftime("%Y-%m-%d") if "date" in group else "",
                "max_date": pd.to_datetime(group["date"], errors="coerce").max().strftime("%Y-%m-%d") if "date" in group else "",
                "number_of_missing_close": missing_close,
                "number_of_missing_adj_close": missing_adj_close,
                "number_of_missing_volume": missing_volume,
                "duplicate_date_rows": duplicates,
                "status": status,
            }
        )
    return pd.DataFrame(rows).sort_values(["sector", "ticker"]).reset_index(drop=True)


def market_indicator_quality(connection: sqlite3.Connection) -> pd.DataFrame:
    indicators = _read_table(connection, "market_indicators")
    base_columns = ["sector", "ticker", "row_count", "min_date", "max_date", *[f"missing_{field}_pct" for field in INDICATOR_FIELDS], "status"]
    if indicators.empty:
        return pd.DataFrame(columns=base_columns)

    rows = []
    for (sector, ticker), group in indicators.groupby(["sector", "ticker"], dropna=False):
        group = group.sort_values("date")
        row: dict[str, Any] = {
            "sector": sector,
            "ticker": ticker,
            "row_count": len(group),
            "min_date": pd.to_datetime(group["date"], errors="coerce").min().strftime("%Y-%m-%d"),
            "max_date": pd.to_datetime(group["date"], errors="coerce").max().strftime("%Y-%m-%d"),
        }
        recent = group.tail(30)
        recent_missing = False
        for field in INDICATOR_FIELDS:
            missing_pct = float(group[field].isna().mean() * 100) if field in group and len(group) else 100.0
            row[f"missing_{field}_pct"] = round(missing_pct, 2)
            is_benchmark_relative_strength = str(ticker) == "SPY" and field.startswith("relative_strength_vs_spy")
            if field in recent and recent[field].isna().any() and not is_benchmark_relative_strength:
                recent_missing = True
        row["status"] = "CHECK_RECENT_INDICATORS" if recent_missing else "OK"
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["sector", "ticker"]).reset_index(drop=True)


def fundamentals_quality(connection: sqlite3.Connection) -> pd.DataFrame:
    fundamentals = _read_table(connection, "fundamentals")
    columns = [
        "sector",
        "ticker",
        "trailing_pe_available",
        "forward_pe_available",
        "price_to_book_available",
        "dividend_yield_available",
        "beta_available",
        "market_cap_available",
        "missing_field_count",
        "available_field_count",
        "status",
    ]
    if fundamentals.empty:
        return pd.DataFrame(columns=columns)

    fundamentals = fundamentals.sort_values("as_of_date") if "as_of_date" in fundamentals else fundamentals
    rows = []
    for (sector, ticker), group in fundamentals.groupby(["sector", "ticker"], dropna=False):
        latest = group.iloc[-1]
        availability = {field: pd.notna(latest.get(field)) for field in FUNDAMENTAL_FIELDS}
        available_count = sum(availability.values())
        status = "OK" if available_count >= 3 else "PARTIAL" if available_count >= 1 else "MISSING"
        rows.append(
            {
                "sector": sector,
                "ticker": ticker,
                **{f"{field}_available": availability[field] for field in FUNDAMENTAL_FIELDS},
                "missing_field_count": len(FUNDAMENTAL_FIELDS) - available_count,
                "available_field_count": available_count,
                "status": status,
            }
        )
    return pd.DataFrame(rows).sort_values(["sector", "ticker"]).reset_index(drop=True)


def google_trends_quality(connection: sqlite3.Connection) -> pd.DataFrame:
    raw = _read_table(connection, "google_trends")
    features = _read_table(connection, "trend_features")
    no_raw_rows = raw.empty
    sectors = list(SECTOR_ETFS)
    if not raw.empty and "sector" in raw:
        sectors = sorted(set(sectors) | set(raw["sector"].dropna().astype(str)))
    if not features.empty and "sector" in features:
        sectors = sorted(set(sectors) | set(features["sector"].dropna().astype(str)))

    rows = []
    for sector in sectors:
        raw_group = raw.loc[raw["sector"].astype(str).eq(sector)] if not raw.empty and "sector" in raw else pd.DataFrame()
        feature_group = features.loc[features["sector"].astype(str).eq(sector)] if not features.empty and "sector" in features else pd.DataFrame()
        has_raw = not raw_group.empty
        has_features = not feature_group.empty
        if no_raw_rows:
            status = "NOT_USED"
        elif has_raw and has_features:
            status = "OK"
        elif has_raw:
            status = "RAW_ONLY"
        else:
            status = "MISSING"
        rows.append(
            {
                "sector": sector,
                "has_raw_trends": has_raw,
                "raw_trend_rows": len(raw_group),
                "number_of_keywords": int(raw_group["keyword"].nunique()) if has_raw and "keyword" in raw_group else 0,
                "min_trend_date": pd.to_datetime(raw_group["date"], errors="coerce").min().strftime("%Y-%m-%d") if has_raw and "date" in raw_group else "",
                "max_trend_date": pd.to_datetime(raw_group["date"], errors="coerce").max().strftime("%Y-%m-%d") if has_raw and "date" in raw_group else "",
                "has_trend_features": has_features,
                "trend_feature_rows": len(feature_group),
                "latest_trend_feature_date": pd.to_datetime(feature_group["date"], errors="coerce").max().strftime("%Y-%m-%d") if has_features and "date" in feature_group else "",
                "status": status,
            }
        )
    return pd.DataFrame(rows)


def missing_values_summary(connection: sqlite3.Connection) -> pd.DataFrame:
    rows = []
    for table_name in EXPECTED_TABLES:
        if not _table_exists(connection, table_name):
            continue
        table = _read_table(connection, table_name)
        row_count = len(table)
        for column in table.columns:
            missing_count = int(table[column].isna().sum())
            rows.append(
                {
                    "table_name": table_name,
                    "column_name": column,
                    "row_count": row_count,
                    "missing_count": missing_count,
                    "missing_pct": round(missing_count / row_count * 100, 2) if row_count else 0.0,
                    "non_missing_count": row_count - missing_count,
                }
            )
    return pd.DataFrame(rows)


def ml_ranking_quality(connection: sqlite3.Connection) -> dict[str, Any]:
    rankings = _read_table(connection, "ml_sector_rankings")
    if rankings.empty:
        return {"status": "EMPTY", "latest_run_id": "", "latest_run_timestamp": "", "number_of_sectors": 0}
    latest_timestamp = rankings["run_timestamp"].max()
    latest = rankings.loc[rankings["run_timestamp"].eq(latest_timestamp)].copy()
    latest_run_id = str(latest["run_id"].iloc[0]) if "run_id" in latest and not latest.empty else ""
    return {
        "status": "OK",
        "latest_run_id": latest_run_id,
        "latest_run_timestamp": latest_timestamp,
        "number_of_sectors": int(latest["sector"].nunique()) if "sector" in latest else len(latest),
        "operating_mode": ", ".join(sorted(latest["operating_mode"].dropna().astype(str).unique())) if "operating_mode" in latest else "",
        "missing_ml_probability": int(latest["ml_predicted_outperform_probability"].isna().sum()) if "ml_predicted_outperform_probability" in latest else len(latest),
        "missing_model_confidence": int(latest["ml_model_confidence"].isna().sum()) if "ml_model_confidence" in latest else len(latest),
        "missing_data_readiness_status": int(latest["data_readiness_status"].isna().sum()) if "data_readiness_status" in latest else len(latest),
    }


def pipeline_run_summary(connection: sqlite3.Connection) -> dict[str, Any]:
    runs = _read_table(connection, "pipeline_runs")
    if runs.empty:
        return {"status": "EMPTY", "number_of_runs": 0}
    latest = runs.sort_values("run_timestamp").iloc[-1]
    return {
        "status": str(latest.get("status", "")),
        "number_of_runs": len(runs),
        "latest_run_timestamp": latest.get("run_timestamp", ""),
        "latest_operating_mode": latest.get("operating_mode", ""),
        "latest_trend_mode": latest.get("trend_mode", ""),
        "latest_use_ml": latest.get("use_ml", ""),
        "latest_use_sentiment": latest.get("use_sentiment", ""),
    }


def _fundamental_column_missing(missing_summary: pd.DataFrame, column_name: str, threshold: float = 50.0) -> bool:
    row = missing_summary.loc[(missing_summary["table_name"].eq("fundamentals")) & (missing_summary["column_name"].eq(column_name))]
    return bool(not row.empty and float(row["missing_pct"].iloc[0]) >= threshold)


def key_issues(
    row_counts: pd.DataFrame,
    sectors: pd.DataFrame,
    prices: pd.DataFrame,
    indicators: pd.DataFrame,
    fundamentals: pd.DataFrame,
    trends: pd.DataFrame,
    missing: pd.DataFrame,
) -> list[str]:
    issues: list[str] = []
    comm = sectors.loc[sectors["expected_sector"].eq("Communication Services")]
    if not comm.empty and comm["status"].iloc[0] != "OK":
        issues.append("Communication Services / XLC missing or mismatched in sectors table.")
    for table_name in IMPORTANT_TABLES:
        row = row_counts.loc[row_counts["table_name"].eq(table_name)]
        if not row.empty and row["status"].iloc[0] != "OK":
            issues.append(f"Important table {table_name} is {row['status'].iloc[0].lower()}.")
    if "google_trends" in set(row_counts["table_name"]):
        trends_row = row_counts.loc[row_counts["table_name"].eq("google_trends")]
        if not trends_row.empty and int(trends_row["row_count"].iloc[0]) == 0:
            issues.append("google_trends table is empty; import manual Google Trends CSVs for full mode.")
    trend_features_row = row_counts.loc[row_counts["table_name"].eq("trend_features")]
    if not trend_features_row.empty and int(trend_features_row["row_count"].iloc[0]) == 0:
        issues.append("trend_features table is empty; optional trend features are not available for ML experiments yet.")
    if _fundamental_column_missing(missing, "beta"):
        issues.append("fundamentals beta is missing for most ETFs.")
    if _fundamental_column_missing(missing, "market_cap"):
        issues.append("fundamentals market_cap is missing for most ETFs.")
    for _, row in prices.loc[prices["status"].ne("OK")].iterrows():
        issues.append(f"{row['ticker']} market price coverage status is {row['status']}.")
    for _, row in indicators.loc[indicators["status"].ne("OK")].iterrows():
        issues.append(f"{row['ticker']} latest market indicators need review.")
    if fundamentals["status"].isin(["PARTIAL", "MISSING"]).any():
        issues.append("ETF fundamentals are partially incomplete; this is common for yfinance ETF fields.")
    return issues or ["No major data quality issues detected."]


def recommended_next_steps(issues: list[str]) -> list[str]:
    steps = []
    if any("Communication Services" in issue for issue in issues):
        steps.append("Add Communication Services / XLC to config and refresh the database.")
    if any("google_trends" in issue or "trend_features" in issue for issue in issues):
        steps.append("Import manual Google Trends CSVs with src/import_trends_csv.py.")
    if any("fundamentals" in issue for issue in issues):
        steps.append("Review missing ETF fundamental fields and document yfinance limitations.")
    if any("market price" in issue or "indicators" in issue for issue in issues):
        steps.append("Refresh market data and inspect tickers with low history or missing recent indicators.")
    steps.extend(["Re-run python src/verify_database.py.", "Re-run python src/pipeline.py --mode market_fundamental --data-source db."])
    return list(dict.fromkeys(steps))


def _markdown_table(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df.empty:
        return "_No rows available._"
    sample = df.head(max_rows).fillna("").astype(str)
    headers = list(sample.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for _, row in sample.iterrows():
        lines.append("| " + " | ".join(str(row[column]).replace("|", "\\|") for column in headers) + " |")
    if len(df) > max_rows:
        lines.append(f"\n_Showing {max_rows} of {len(df)} rows._")
    return "\n".join(lines)


def write_markdown_report(
    output_path: Path,
    db_path: Path,
    row_counts: pd.DataFrame,
    sectors: pd.DataFrame,
    prices: pd.DataFrame,
    indicators: pd.DataFrame,
    fundamentals: pd.DataFrame,
    trends: pd.DataFrame,
    ml_ranking: dict[str, Any],
    pipeline: dict[str, Any],
    issues: list[str],
    steps: list[str],
) -> None:
    missing_sectors = sectors.loc[sectors["status"].eq("MISSING"), "expected_sector"].tolist()
    actual_sector_count = int(sectors["present_in_db"].sum()) if "present_in_db" in sectors else 0
    spy_status = prices.loc[prices["ticker"].eq("SPY"), "status"].iloc[0] if not prices.loc[prices["ticker"].eq("SPY")].empty else "MISSING"
    content = f"""# Data Quality Summary Report

## 1. Database Overview
- Database path: `{db_path}`
- Generated timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

{_markdown_table(row_counts)}

## 2. Sector Coverage
- Expected sector count: {len(SECTOR_ETFS)}
- Actual sector count: {actual_sector_count}
- Missing sectors: {", ".join(missing_sectors) if missing_sectors else "none"}
- Communication Services / XLC status: {sectors.loc[sectors["expected_sector"].eq("Communication Services"), "status"].iloc[0] if not sectors.loc[sectors["expected_sector"].eq("Communication Services")].empty else "MISSING"}

{_markdown_table(sectors)}

## 3. Market Data Coverage
- SPY benchmark status: {spy_status}
- Market price rows: {int(row_counts.loc[row_counts["table_name"].eq("market_prices"), "row_count"].iloc[0]) if not row_counts.loc[row_counts["table_name"].eq("market_prices")].empty else 0}

{_markdown_table(prices, max_rows=30)}

## 4. Market Indicator Quality
Rolling indicators naturally contain NULL values in early rows because they require historical windows. The status below focuses on recent rows, defined as the latest 30 available dates per ticker.

{_markdown_table(indicators, max_rows=30)}

## 5. Fundamental Data Quality
ETF fundamentals from yfinance may be incomplete, especially forward valuation and market-cap fields. OK means at least 3 of 6 tracked fields are available.

{_markdown_table(fundamentals, max_rows=30)}

## 6. Google Trends Data Quality
Google Trends data is optional in market/fundamental mode. If raw trends are missing, import manual CSV exports with `src/import_trends_csv.py`.

{_markdown_table(trends, max_rows=30)}

## 7. ML Ranking Output Quality
- Latest run id: {ml_ranking.get("latest_run_id", "")}
- Latest run timestamp: {ml_ranking.get("latest_run_timestamp", "")}
- Number of sectors in latest run: {ml_ranking.get("number_of_sectors", 0)}
- Operating mode: {ml_ranking.get("operating_mode", "")}
- Missing ML probability: {ml_ranking.get("missing_ml_probability", 0)}
- Missing model confidence: {ml_ranking.get("missing_model_confidence", 0)}
- Missing data readiness status: {ml_ranking.get("missing_data_readiness_status", 0)}
- Status: {ml_ranking.get("status", "")}

## 8. Pipeline Run History
- Number of runs: {pipeline.get("number_of_runs", 0)}
- Latest run timestamp: {pipeline.get("latest_run_timestamp", "")}
- Latest operating mode: {pipeline.get("latest_operating_mode", "")}
- Latest trend mode: {pipeline.get("latest_trend_mode", "")}
- Latest use_ml: {pipeline.get("latest_use_ml", "")}
- Latest use_sentiment: {pipeline.get("latest_use_sentiment", "")}
- Latest status: {pipeline.get("status", "")}

## 9. Key Data Quality Issues
{chr(10).join(f"- {issue}" for issue in issues)}

## 10. Recommended Next Steps
{chr(10).join(f"- {step}" for step in steps)}
"""
    output_path.write_text(content, encoding="utf-8")


def generate_data_quality_report(db_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    with _connect(db_path) as connection:
        row_counts = table_row_counts(connection)
        sectors = sector_coverage_summary(connection)
        prices = market_price_coverage(connection)
        indicators = market_indicator_quality(connection)
        fundamentals = fundamentals_quality(connection)
        trends = google_trends_quality(connection)
        missing = missing_values_summary(connection)
        ml_ranking = ml_ranking_quality(connection)
        pipeline = pipeline_run_summary(connection)

    issues = key_issues(row_counts, sectors, prices, indicators, fundamentals, trends, missing)
    steps = recommended_next_steps(issues)
    outputs = {
        "table_row_counts": row_counts,
        "missing_values_summary": missing,
        "sector_coverage_summary": sectors,
        "date_coverage_summary": prices,
        "market_indicator_quality_summary": indicators,
        "fundamentals_quality_summary": fundamentals,
        "google_trends_quality_summary": trends,
    }
    for name, frame in outputs.items():
        frame.to_csv(output_dir / f"{name}.csv", index=False)

    markdown_path = output_dir / "data_quality_summary.md"
    write_markdown_report(markdown_path, db_path, row_counts, sectors, prices, indicators, fundamentals, trends, ml_ranking, pipeline, issues, steps)
    return {
        "markdown_path": markdown_path,
        "row_counts": row_counts,
        "sector_summary": sectors,
        "issues": issues,
        "ml_ranking": ml_ranking,
        "pipeline": pipeline,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate SQLite data quality summary reports.")
    parser.add_argument("--db-path", type=Path, default=get_database_path(), help="Path to SQLite database.")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "reports" / "data_quality", help="Directory for Markdown and CSV outputs.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db_path = args.db_path.resolve()
    output_dir = args.output_dir.resolve()
    if not db_path.exists():
        print(f"[ERROR] Database not found: {db_path}")
        return 1
    print(f"[OK] Database found: {db_path}")
    result = generate_data_quality_report(db_path, output_dir)
    row_counts = result["row_counts"]
    existing_tables = int(row_counts["status"].ne("MISSING").sum())
    print(f"[OK] Tables checked: {existing_tables}/{len(EXPECTED_TABLES)}")
    comm = result["sector_summary"].loc[result["sector_summary"]["expected_sector"].eq("Communication Services")]
    if not comm.empty and comm["status"].iloc[0] != "OK":
        print("[WARN] Missing sector: Communication Services / XLC")
    market_rows = int(row_counts.loc[row_counts["table_name"].eq("market_prices"), "row_count"].iloc[0])
    print(f"[OK] Market prices available: {market_rows:,} rows")
    trends_row = row_counts.loc[row_counts["table_name"].eq("google_trends")]
    if not trends_row.empty and int(trends_row["row_count"].iloc[0]) == 0:
        print("[WARN] Google Trends table empty")
    if any("fundamentals" in issue for issue in result["issues"]):
        print("[WARN] ETF fundamentals partially incomplete")
    print(f"[OK] Report written: {result['markdown_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
