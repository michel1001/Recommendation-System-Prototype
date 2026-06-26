"""Streamlit dashboard for the educational sector-monitoring prototype."""

from pathlib import Path

import pandas as pd
import streamlit as st

from src.config import TREND_CACHE_MAX_AGE_HOURS

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "recommendation_scores.csv"

st.set_page_config(page_title="AI Sector Monitoring Dashboard", layout="wide")
st.title("AI Sector Monitoring Dashboard")
st.caption("Decision support only. No autonomous trading. Not financial advice.")

if not DATA_PATH.exists():
    st.warning("No ranking data found. Run `python src/pipeline.py --trend-mode auto` first, or use `--trend-mode demo_only` for a presentation-safe run.")
    st.stop()

ranking = pd.read_csv(DATA_PATH).sort_values("total_score", ascending=False).reset_index(drop=True)
ranking["trend_data_status"] = ranking["trend_data_status"].fillna("fallback").str.lower()
if "trend_refresh_mode" not in ranking:
    ranking["trend_refresh_mode"] = "unknown"
if "trend_cache_age_hours" not in ranking:
    ranking["trend_cache_age_hours"] = pd.NA
ranking["trend_cache_age_hours"] = pd.to_numeric(ranking["trend_cache_age_hours"], errors="coerce")
ranking["synergy_label"] = ranking["synergy_label"].fillna("Balanced setup")
status_counts = ranking["trend_data_status"].value_counts()
demo_count, fallback_count = status_counts.get("demo", 0), status_counts.get("fallback", 0)
refresh_modes = ", ".join(sorted(ranking["trend_refresh_mode"].dropna().astype(str).unique()))
st.caption(f"Trend refresh mode: {refresh_modes or 'unknown'}")

if fallback_count or (ranking.get("price_data_status", pd.Series("live", index=ranking.index)).eq("missing").sum() > len(ranking) / 2):
    current_mode = "Insufficient Data Mode"
elif demo_count:
    current_mode = "Prototype Mode"
else:
    current_mode = "Research Mode"
st.warning(f"Current mode: **{current_mode}**. Current outputs are research signals, not purchasing recommendations.")

if ranking["trend_refresh_mode"].astype(str).str.lower().eq("demo_only").all() or demo_count == len(ranking):
    st.warning("Demo-only trend data is displayed. Google Trends values are synthetic prototype data and must not be interpreted as real search interest.")
if demo_count:
    st.info(f"Data quality notice: {demo_count} sector(s) use synthetic demo Google Trends data for prototype validation. It must not be interpreted as real search interest.")
if fallback_count:
    st.warning(f"Data quality warning: {fallback_count} sector(s) use neutral fallback trend data; their attention signals have limited evidential value.")
stale_cache = ranking["trend_data_status"].eq("cache") & ranking["trend_cache_age_hours"].gt(TREND_CACHE_MAX_AGE_HOURS)
if stale_cache.any():
    st.warning(f"Cache freshness warning: {int(stale_cache.sum())} cached sector(s) are older than {TREND_CACHE_MAX_AGE_HOURS} hours and should be refreshed.")

best_sector = ranking.iloc[0]
metrics = st.columns(4)
metrics[0].metric("Top Sector", f"{best_sector['sector']} ({best_sector['ticker']})")
metrics[1].metric("Average Trend Score", f"{ranking['trend_score'].mean():.1f}")
metrics[2].metric("Strong Attention Spikes", int((ranking["trend_signal"] == "Strong Attention Spike").sum()))
metrics[3].metric("Hype Risks", int((ranking["synergy_label"] == "Hype risk").sum()))

st.subheader("Top-sector interpretation")
component_scores = {"Google Trends": best_sector["trend_score"], "momentum": best_sector["momentum_score"], "fundamentals": best_sector["fundamental_score"], "risk": best_sector["risk_score"]}
strongest_component, strongest_score = max(component_scores.items(), key=lambda item: item[1])
if best_sector["trend_data_status"] == "demo":
    limitation = "Its Google Trends input is synthetic demo data, so the attention signal is illustrative rather than observed."
elif best_sector["trend_data_status"] == "fallback":
    limitation = "Its Google Trends input is a neutral fallback, which is the weakest available data-quality state."
else:
    limitation = f"Its Google Trends input is marked {best_sector['trend_data_status']}, so source recency and coverage should still be reviewed."
st.info(f"{best_sector['sector']} ranks first because its combined relative score is {best_sector['total_score']:.1f}; {strongest_component} is its strongest component ({strongest_score:.1f}). {best_sector['short_explanation']} {limitation} Human analyst review is required before any decision-support use.")

st.subheader("Google Trends data status")
status_metrics = st.columns(5)
for column, status in zip(status_metrics, ("live", "cache", "demo", "fallback")):
    column.metric(f"{status.title()} Trend Sectors", int(status_counts.get(status, 0)))
fresh_cache_count = int((ranking["trend_data_status"].eq("cache") & ranking["trend_cache_age_hours"].le(TREND_CACHE_MAX_AGE_HOURS)).sum())
status_metrics[4].metric("Fresh Cache Sectors", fresh_cache_count)

st.subheader("Ranking")
display_columns = ["sector", "ticker", "total_score", "trend_score", "momentum_score", "risk_score", "fundamental_score", "confidence_score", "recommendation", "data_quality_status", "actionability_status", "trend_data_status", "trend_refresh_mode", "trend_cache_age_hours"]
st.dataframe(ranking[display_columns], width="stretch", hide_index=True)

st.subheader("Score distribution")
charts = st.columns(3)
charts[0].bar_chart(ranking.set_index("sector")["total_score"])
charts[1].bar_chart(ranking.set_index("sector")["trend_score"])
charts[2].bar_chart(ranking.set_index("sector")["synergy_score"])

sector = st.selectbox("Select a sector", ranking["sector"].tolist())
selected = ranking.loc[ranking["sector"] == sector].iloc[0]
st.subheader(f"{sector} details")
detail_columns = st.columns(2)
detail_columns[0].write(f"Recommendation: **{selected['recommendation']}**")
detail_columns[0].write(f"Trend signal: **{selected['trend_signal']}**")
detail_columns[0].write(f"Synergy: **{selected['synergy_label']}**")
detail_columns[1].write(f"Confidence score: **{selected['confidence_score']:.1f}**")
detail_columns[1].write(f"Google Trends data status: **{selected['trend_data_status'].upper()}**")
detail_columns[1].write(f"Trend refresh mode: **{selected.get('trend_refresh_mode', 'unknown')}**")
cache_age = selected.get("trend_cache_age_hours")
detail_columns[1].write(f"Trend cache age: {cache_age:.1f} hours" if pd.notna(cache_age) else "Trend cache age: not applicable")
detail_columns[1].write(f"Trend keywords: {selected.get('trend_keywords', '')}")
detail_columns[0].write(f"Data quality: **{selected.get('data_quality_status', 'Unavailable')}**")
detail_columns[0].write(f"Actionability: **{selected.get('actionability_status', 'Unavailable')}**")
detail_columns[1].write(f"Price data status: **{selected.get('price_data_status', 'Unavailable')}**")
detail_columns[1].write(f"Market last date: {selected.get('market_last_date', 'Unavailable')}")
detail_columns[1].write(f"Trend last date: {selected.get('trend_last_date', 'Unavailable')}")
st.write(f"Explanation: {selected['short_explanation']}")

feature_columns = ["trend_latest", "trend_momentum_4w", "trend_momentum_12w", "trend_z_score_12w", "trend_z_score_52w", "trend_percentile_52w", "momentum_21", "momentum_63", "momentum_126", "volatility_20", "drawdown_current", "trailingPE", "forwardPE", "priceToBook", "dividendYield", "beta", "marketCap"]
st.json({column: selected.get(column) for column in feature_columns if column in selected.index})

st.markdown("### Methodology")
st.write("The ranking combines Google Trends attention with market momentum, risk, and basic fundamental validation. Scores are relative, explainable research signals; no trading or orders are executed.")

st.markdown("### How analysts should interpret the output")
st.markdown("- **Overweight Candidate:** candidate for deeper analyst review and possible sector overweight.\n- **Watch:** monitor closely, but no automatic action.\n- **Neutral:** keep under observation or benchmark-level exposure.\n- **Avoid:** deprioritize unless supported by external analyst conviction.")

st.markdown("### Data quality interpretation")
st.markdown("- **live:** real Google Trends data from the current API request.\n- **cache:** previously loaded Google Trends data.\n- **demo:** synthetic prototype data used when live Google Trends is unavailable.\n- **fallback:** neutral placeholder and weakest data quality.")
st.caption("Dashboard command: `python -m streamlit run app/app.py`")

st.markdown("---")
st.header("Backtest")
BACKTEST_RESULTS = DATA_PATH.parent / "backtest_results.csv"
BACKTEST_METRICS = DATA_PATH.parent / "backtest_metrics.csv"
if not BACKTEST_RESULTS.exists() or not BACKTEST_METRICS.exists():
    st.info("Backtest outputs are not available. Run `python src/backtesting.py`.")
else:
    backtest_results = pd.read_csv(BACKTEST_RESULTS)
    backtest_metrics = pd.read_csv(BACKTEST_METRICS)
    st.caption("This is a market-only historical backtest. Google Trends validation requires stable historical trend data and is not yet fully implemented.")
    if not backtest_results.empty:
        chart_data = backtest_results.set_index("holding_end_date")[["portfolio_return_cumulative", "equal_weight_return_cumulative", "spy_return_cumulative"]]
        st.line_chart(chart_data)
    st.dataframe(backtest_metrics, width="stretch", hide_index=True)
