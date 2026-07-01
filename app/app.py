"""Management-oriented Streamlit dashboard for sector monitoring."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.config import ML_EVALUATION_METRICS_PATH, ML_FEATURE_IMPORTANCE_PATH
from src.dashboard_helpers import (
    SECTOR_REPRESENTATIVE_STOCKS,
    component_rows,
    data_quality_label,
    ensure_dashboard_columns,
    management_ranking_table,
    ml_summary_table,
    representative_stock_fallback,
    risk_level,
    sector_caveats,
    signal_label,
)
from src.database import get_connection, table_exists


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "recommendation_scores.csv"
BACKTEST_RESULTS_PATH = DATA_PATH.parent / "backtest_results.csv"
BACKTEST_METRICS_PATH = DATA_PATH.parent / "backtest_metrics.csv"


@st.cache_data(ttl=86400, show_spinner=False)
def load_representative_stock_performance(sector: str, period: str = "6mo") -> pd.DataFrame:
    """Return top recent representative stock performers for analyst review."""
    tickers = SECTOR_REPRESENTATIVE_STOCKS.get(sector, [])
    if not tickers:
        return representative_stock_fallback(sector)
    try:
        import yfinance as yf

        rows = []
        for ticker in tickers:
            data = yf.download(ticker, period=period, progress=False, auto_adjust=False)
            if data is not None and isinstance(data.columns, pd.MultiIndex):
                data.columns = [str(column[0]) for column in data.columns]
            if data is None or data.empty or "Close" not in data:
                continue
            close = pd.to_numeric(data["Close"], errors="coerce").dropna()
            if close.empty:
                continue
            recent_return = close.iloc[-1] / close.iloc[0] - 1 if len(close) > 1 and close.iloc[0] else pd.NA
            rows.append(
                {
                    "Stock": ticker,
                    "6M Return": recent_return,
                    "Last Price": close.iloc[-1],
                    "Analyst Review Note": "Positive momentum, review valuation" if pd.notna(recent_return) and recent_return > 0 else "Review sector context",
                }
            )
        if not rows:
            return representative_stock_fallback(sector)
        result = pd.DataFrame(rows).sort_values("6M Return", ascending=False).head(3)
        result["6M Return"] = result["6M Return"].map(lambda value: f"{value:.1%}" if pd.notna(value) else "n/a")
        result["Last Price"] = result["Last Price"].map(lambda value: f"{value:.2f}" if pd.notna(value) else "n/a")
        return result.reset_index(drop=True)
    except Exception:
        return representative_stock_fallback(sector)


def database_management_status() -> dict:
    """Load minimal non-technical database status for management display."""
    status = {
        "sector_count": None,
        "has_spy": False,
        "latest_market_date": "",
        "market_rows": 0,
        "indicator_rows": 0,
        "fundamentals_rows": 0,
        "google_trends_rows": 0,
    }
    try:
        with get_connection() as connection:
            if table_exists("sectors"):
                status["sector_count"] = int(connection.execute("SELECT COUNT(*) FROM sectors").fetchone()[0])
            if table_exists("market_prices"):
                status["market_rows"] = int(connection.execute("SELECT COUNT(*) FROM market_prices").fetchone()[0])
                status["latest_market_date"] = connection.execute("SELECT MAX(date) FROM market_prices").fetchone()[0] or ""
                status["has_spy"] = bool(connection.execute("SELECT 1 FROM market_prices WHERE ticker = 'SPY' LIMIT 1").fetchone())
            if table_exists("market_indicators"):
                status["indicator_rows"] = int(connection.execute("SELECT COUNT(*) FROM market_indicators").fetchone()[0])
            if table_exists("fundamentals"):
                status["fundamentals_rows"] = int(connection.execute("SELECT COUNT(*) FROM fundamentals").fetchone()[0])
            if table_exists("google_trends"):
                status["google_trends_rows"] = int(connection.execute("SELECT COUNT(*) FROM google_trends").fetchone()[0])
    except Exception:
        pass
    return status


def score_bar_data(ranking: pd.DataFrame) -> pd.DataFrame:
    return (
        ranking[["sector", "total_score"]]
        .sort_values("total_score", ascending=False)
        .rename(columns={"sector": "Sector", "total_score": "Total Score"})
        .set_index("Sector")
    )


def technical_diagnostics(ranking: pd.DataFrame, db_status: dict) -> None:
    """Optional diagnostics for development use."""
    st.subheader("Technical diagnostics")
    st.caption("Hidden by default for management users.")
    st.write("Database row counts")
    st.dataframe(
        pd.DataFrame(
            [
                {"Table": "market_prices", "Rows": db_status["market_rows"]},
                {"Table": "market_indicators", "Rows": db_status["indicator_rows"]},
                {"Table": "fundamentals", "Rows": db_status["fundamentals_rows"]},
                {"Table": "google_trends", "Rows": db_status["google_trends_rows"]},
            ]
        ),
        width="stretch",
        hide_index=True,
    )
    st.write("Detailed ranking fields")
    st.dataframe(ranking, width="stretch", hide_index=True)
    if ML_EVALUATION_METRICS_PATH.exists():
        st.write("ML evaluation metrics")
        st.dataframe(pd.read_csv(ML_EVALUATION_METRICS_PATH), width="stretch", hide_index=True)
    if ML_FEATURE_IMPORTANCE_PATH.exists():
        importance = pd.read_csv(ML_FEATURE_IMPORTANCE_PATH)
        if not importance.empty:
            st.write("Feature importance")
            st.bar_chart(importance.head(12).set_index("feature")["importance"])


st.set_page_config(page_title="Sector Monitoring Management Dashboard", layout="wide")

st.title("Sector Monitoring Management Dashboard")
st.caption("Research-oriented overview of sector attractiveness, risk and data quality")

show_technical = st.sidebar.toggle("Show technical diagnostics", value=False)

if not DATA_PATH.exists():
    st.warning("No ranking data found. Run `python src/pipeline.py --mode market_fundamental --data-source db` first.")
    st.stop()

ranking = ensure_dashboard_columns(pd.read_csv(DATA_PATH)).sort_values("total_score", ascending=False).reset_index(drop=True)
db_status = database_management_status()

overview_tab, detail_tab, quality_tab, validation_tab = st.tabs(["Overview", "Sector Details", "Data Quality", "Validation"])

with overview_tab:
    best_sector = ranking.iloc[0]
    st.subheader("Executive Summary")
    kpis = st.columns(3)
    kpis[0].metric("Top ranked sector", f"{best_sector['sector']} ({best_sector['ticker']})")
    kpis[1].metric("Sectors under review", len(ranking))
    kpis[2].metric("Average sector score", f"{ranking['total_score'].mean():.1f}")

    st.subheader("Sector Ranking Overview")
    management_table = management_ranking_table(ranking)
    st.dataframe(management_table, width="stretch", hide_index=True)

    st.subheader("Sector score overview")
    st.bar_chart(score_bar_data(ranking))

with detail_tab:
    st.subheader("Sector Details")
    selected_sector = st.selectbox("Select sector", ranking["sector"].tolist())
    selected = ranking.loc[ranking["sector"].eq(selected_sector)].iloc[0]

    conclusion_cols = st.columns(3)
    conclusion_cols[0].metric("Research signal", signal_label(selected["recommendation"]))
    conclusion_cols[1].metric("Total score", f"{selected['total_score']:.1f}")
    conclusion_cols[2].metric("Risk level", risk_level(selected["risk_score"]))
    st.info(selected.get("short_explanation") or "Current sector signal should be reviewed by analysts in context.")

    st.subheader("What drives the signal?")
    components = component_rows(selected)
    st.bar_chart(components.set_index("Component")["Score"])

    st.subheader("Key risks / caveats")
    for caveat in sector_caveats(selected):
        st.write(f"- {caveat}")

    st.subheader("Representative stocks to review")
    st.caption("For analyst review only. These are not recommendations or buy/sell signals.")
    st.dataframe(load_representative_stock_performance(selected_sector), width="stretch", hide_index=True)

    st.subheader("Analyst note")
    st.write("Analysts should review whether the sector signal is supported by recent macro, earnings and valuation context.")

with quality_tab:
    st.subheader("Data quality and limitations")
    st.write(f"- Market data: {'complete' if db_status['market_rows'] > 0 else 'not available'}")
    st.write(f"- Sector coverage: {db_status['sector_count'] or len(ranking)}/{len(ranking)}")
    trend_rows = int(db_status.get("google_trends_rows") or 0)
    trend_status_text = "pending" if trend_rows == 0 else "available"
    if ranking["trend_data_status"].eq("demo").any():
        trend_status_text = "demo"
    st.write(f"- Google Trends: {trend_status_text}")
    fundamentals_partial = ranking.apply(data_quality_label, axis=1).eq("Partial fundamentals").any()
    st.write(f"- ETF fundamentals: {'partially available' if fundamentals_partial else 'available'}")
    sentiment_status = "available" if ~ranking["sentiment_data_status"].isin(["not_used", "disabled_by_mode", "disabled_no_api_key", "missing"]).all() else "not used"
    st.write(f"- Sentiment: {sentiment_status}")
    st.caption("Google Trends is prepared in the pipeline but not imported in the current market/fundamental baseline.")

    with st.expander("Technical diagnostics", expanded=False):
        technical_diagnostics(ranking, db_status)

with validation_tab:
    st.subheader("Validation and Backtest Summary")
    if BACKTEST_RESULTS_PATH.exists() and BACKTEST_METRICS_PATH.exists():
        backtest_results = pd.read_csv(BACKTEST_RESULTS_PATH)
        backtest_metrics = pd.read_csv(BACKTEST_METRICS_PATH)
        st.caption("Market-only validation. Google Trends validation requires imported historical trend data.")
        if not backtest_results.empty and {"holding_end_date", "portfolio_return_cumulative", "equal_weight_return_cumulative", "spy_return_cumulative"}.issubset(backtest_results.columns):
            chart_data = backtest_results.set_index("holding_end_date")[["portfolio_return_cumulative", "equal_weight_return_cumulative", "spy_return_cumulative"]]
            chart_data = chart_data.rename(columns={
                "portfolio_return_cumulative": "Strategy cumulative return",
                "equal_weight_return_cumulative": "Equal weight return",
                "spy_return_cumulative": "SPY return",
            })
            st.line_chart(chart_data)
        with st.expander("Backtest metrics", expanded=False):
            st.dataframe(backtest_metrics, width="stretch", hide_index=True)
    else:
        st.info("Backtest outputs are not available yet.")

    st.subheader("AI Research Signal")
    ml_statuses = ", ".join(sorted(ranking["ml_model_status"].fillna("not_trained").astype(str).unique()))
    st.write(f"ML status: **{ml_statuses}**")
    st.write("The ML layer estimates the probability that a sector outperforms SPY over a 4-week horizon. It is used as a supporting research signal.")
    st.dataframe(ml_summary_table(ranking), width="stretch", hide_index=True)

    with st.expander("Technical ML diagnostics", expanded=False):
        if ML_EVALUATION_METRICS_PATH.exists():
            st.dataframe(pd.read_csv(ML_EVALUATION_METRICS_PATH), width="stretch", hide_index=True)
        else:
            st.info("ML evaluation metrics are not available.")
        if ML_FEATURE_IMPORTANCE_PATH.exists():
            importance = pd.read_csv(ML_FEATURE_IMPORTANCE_PATH)
            if not importance.empty:
                st.bar_chart(importance.head(12).set_index("feature")["importance"])

if show_technical:
    st.markdown("---")
    technical_diagnostics(ranking, db_status)
