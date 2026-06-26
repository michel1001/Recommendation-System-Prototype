"""HTML report generation for the sector monitoring MVP."""

from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

import pandas as pd

from src.config import TREND_CACHE_MAX_AGE_HOURS

HTML_REPORT_PATH = Path(__file__).resolve().parents[1] / "reports" / "html" / "sector_monitoring_report.html"
CSV_REPORT_PATH = Path(__file__).resolve().parents[1] / "data" / "reports" / "recommendation_scores.csv"
BACKTEST_METRICS_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "backtest_metrics.csv"


def generate_html_report(ranking: pd.DataFrame, generated_at: datetime | None = None) -> Path:
    """Create an HTML report summarizing the ranking and methodology."""
    if generated_at is None:
        generated_at = datetime.now()

    report_dir = HTML_REPORT_PATH.parent
    report_dir.mkdir(parents=True, exist_ok=True)

    ranking = ranking.copy()
    ranking = ranking.sort_values(by="total_score", ascending=False).reset_index(drop=True)

    top_5 = ranking.head(5).copy()
    bottom_3 = ranking.tail(3).copy()
    trend_signal_overview = ranking[["sector", "trend_signal", "trend_data_status", "trend_refresh_mode", "trend_cache_age_hours", "trend_latest", "trend_momentum_4w", "synergy_label"]].copy()
    trend_signal_overview = trend_signal_overview.fillna({"trend_data_status": "fallback", "trend_signal": "No Trend Data"})

    summary_stats = []
    for _, row in top_5.iterrows():
        summary_stats.append(
            f"<li><strong>{escape(str(row['sector']))}</strong> — score {row['total_score']:.1f}, trend {row['trend_score']:.1f}, synergy {escape(str(row['synergy_label']))}</li>"
        )

    data_status_counts = ranking["trend_data_status"].fillna("fallback").value_counts().to_dict()
    live_sectors = ", ".join(sorted(ranking.loc[ranking["trend_data_status"] == "live", "sector"].astype(str).tolist())) or "none"
    cache_sectors = ", ".join(sorted(ranking.loc[ranking["trend_data_status"] == "cache", "sector"].astype(str).tolist())) or "none"
    demo_sectors = ", ".join(sorted(ranking.loc[ranking["trend_data_status"] == "demo", "sector"].astype(str).tolist())) or "none"
    fallback_sectors = ", ".join(sorted(ranking.loc[ranking["trend_data_status"] == "fallback", "sector"].astype(str).tolist())) or "none"
    quality_overview = ranking[["sector", "data_quality_status", "actionability_status", "price_data_status", "market_last_date", "trend_data_status", "trend_refresh_mode", "trend_cache_age_hours", "trend_last_date"]].copy()
    trend_operational_overview = ranking[["sector", "trend_data_status", "trend_refresh_mode", "trend_cache_age_hours", "trend_last_date", "trend_observations"]].copy()
    cache_ages = pd.to_numeric(ranking["trend_cache_age_hours"], errors="coerce") if "trend_cache_age_hours" in ranking else pd.Series(dtype=float)
    stale_cache_mask = ranking["trend_data_status"].eq("cache") & cache_ages.gt(TREND_CACHE_MAX_AGE_HOURS)
    stale_cache_count = int(stale_cache_mask.sum())
    refresh_modes = ", ".join(sorted(ranking["trend_refresh_mode"].dropna().astype(str).unique())) or "not available"
    if BACKTEST_METRICS_PATH.exists():
        backtest_section = pd.read_csv(BACKTEST_METRICS_PATH).to_html(index=False, escape=False)
    else:
        backtest_section = "<p>Backtest has not been executed yet. Run <code>python src/backtesting.py</code>.</p>"
    top_sector = ranking.iloc[0]
    component_scores = {
        "Google Trends": float(top_sector["trend_score"]),
        "momentum": float(top_sector["momentum_score"]),
        "fundamentals": float(top_sector["fundamental_score"]),
        "risk": float(top_sector["risk_score"]),
    }
    strongest_component, strongest_score = max(component_scores.items(), key=lambda item: item[1])
    top_status = str(top_sector["trend_data_status"]).lower()
    if top_status == "demo":
        top_limitation = "Its Google Trends input is synthetic demo data, so the attention signal is illustrative rather than observed."
    elif top_status == "fallback":
        top_limitation = "Its Google Trends input is neutral fallback data, the weakest data-quality state."
    else:
        top_limitation = f"Its Google Trends input is marked {top_status}; source recency and coverage should still be reviewed."
    quality_messages = []
    if data_status_counts.get("demo", 0):
        quality_messages.append(f"<li><strong>Demo data in use:</strong> {data_status_counts['demo']} sector(s) use synthetic Google Trends data for prototype validation. These values are not real search interest.</li>")
    if data_status_counts.get("live", 0) or data_status_counts.get("cache", 0):
        quality_messages.append(f"<li><strong>Observed data included:</strong> {data_status_counts.get('live', 0)} live and {data_status_counts.get('cache', 0)} cached sector trend series are included.</li>")
    if data_status_counts.get("fallback", 0):
        quality_messages.append(f"<li><strong>Fallback limitation:</strong> {data_status_counts['fallback']} sector(s) use neutral fallback attention data and should be interpreted cautiously.</li>")
    if not quality_messages:
        quality_messages.append("<li>Trend-data status was not available for this report.</li>")

    html = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>AI Sector Monitoring Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #1f2937; }}
    h1, h2 {{ color: #0f172a; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 12px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; }}
    th {{ background-color: #f3f4f6; }}
    .note {{ background-color: #fef3c7; padding: 12px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>AI Sector Monitoring Report</h1>
  <p><strong>Generated:</strong> {generated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
  <div class=\"note\">Educational prototype only. Not financial advice.</div>

  <h2>Executive Summary</h2>
  <p>This report summarizes the current Google Trends and market context for sector ETFs using an explainable, decision-support scoring pipeline.</p>
  <ul>
    {''.join(summary_stats)}
  </ul>

  <h2>Data Quality</h2>
  <p>Trend-source status is shown explicitly so analysts can distinguish observed attention signals from demonstration data.</p>
  <ul>
    {''.join(quality_messages)}
  </ul>

  <h2>Google Trends Operational Reliability</h2>
  <p>Google Trends live access may be rate-limited because pytrends uses unofficial web requests. This prototype uses refresh modes and cache-first behavior to avoid unnecessary live requests. Demo mode is used only when live/cache data is unavailable or intentionally selected. The <code>trend_data_status</code> and <code>trend_cache_age_hours</code> fields document the quality and recency of each sector's attention signal.</p>
  <ul>
    <li><strong>Refresh mode(s) in this run:</strong> {escape(refresh_modes)}</li>
    <li><strong>Freshness threshold:</strong> cached trends older than {TREND_CACHE_MAX_AGE_HOURS} hours should be refreshed.</li>
    <li><strong>Stale cache warnings:</strong> {stale_cache_count}</li>
  </ul>
  {trend_operational_overview.to_html(index=False, escape=False)}

  <h2>Actionability</h2>
  <p>Research Prototype means demo/synthetic data or an unvalidated signal. Research Candidate requires live or cached data and remains subject to analyst review. A validated research candidate requires historical validation and analyst review.</p>
  {quality_overview.to_html(index=False, escape=False)}

  <h2>Top-sector Interpretation</h2>
  <p><strong>{escape(str(top_sector['sector']))}</strong> ranks first because its combined relative score is {top_sector['total_score']:.1f}. Its strongest component is {escape(str(strongest_component))} ({strongest_score:.1f}). {escape(str(top_sector['short_explanation']))} {escape(top_limitation)} Human analyst review is required before any decision-support use.</p>

  <h2>Top 5 Sectors</h2>
  {top_5.to_html(index=False, escape=False)}

  <h2>Bottom 3 Sectors</h2>
  {bottom_3.to_html(index=False, escape=False)}

  <h2>Google Trends Signal Overview</h2>
  {trend_signal_overview.to_html(index=False, escape=False)}

  <h2>Synergy Analysis</h2>
  <p>Synergy labels describe whether attention, momentum, and fundamentals point in the same direction. This helps research teams separate strong setups from hype-driven moves.</p>
  <ul>
    <li>Trend-confirmed opportunity: attention, momentum, and fundamentals are aligned.</li>
    <li>Early attention signal: trend strength is high but momentum is still developing.</li>
    <li>Hype risk: attention is strong but fundamentals are not supportive.</li>
  </ul>

  <h2>Full Ranking Table</h2>
  {ranking.to_html(index=False, escape=False)}

  <h2>Methodology</h2>
  <p>The score blends Google Trends attention, relative momentum, fundamentals, and risk controls. Trend data is treated as the main signal, while market and fundamental signals act as validation and risk filters.</p>
  <p><em>Demo trend data is used only when Google Trends live access is unavailable, to keep the prototype demonstrable. It is clearly flagged and must not be interpreted as real market attention.</em></p>

  <h2>How Analysts Should Interpret the Output</h2>
  <ul>
    <li><strong>Overweight Candidate:</strong> candidate for deeper analyst review and possible sector overweight.</li>
    <li><strong>Watch:</strong> monitor closely, but no automatic action.</li>
    <li><strong>Neutral:</strong> keep under observation or benchmark-level exposure.</li>
    <li><strong>Avoid:</strong> deprioritize unless supported by external analyst conviction.</li>
  </ul>

  <h2>Data Quality Interpretation</h2>
  <ul>
    <li><strong>live:</strong> real Google Trends data from the current API request.</li>
    <li><strong>cache:</strong> previously loaded Google Trends data.</li>
    <li><strong>demo:</strong> synthetic prototype data used when live Google Trends is unavailable.</li>
    <li><strong>fallback:</strong> neutral placeholder and weakest data quality.</li>
  </ul>
  <p>Dashboard command: <code>python -m streamlit run app/app.py</code></p>

  <h2>Data Status</h2>
  <ul>
    <li>Live Google Trends data sectors: {data_status_counts.get('live', 0)}</li>
    <li>Cache-backed sectors: {data_status_counts.get('cache', 0)}</li>
    <li>Demo sectors: {data_status_counts.get('demo', 0)}</li>
    <li>Fallback sectors: {data_status_counts.get('fallback', 0)}</li>
    <li>Live sectors: {live_sectors}</li>
    <li>Cache sectors: {cache_sectors}</li>
    <li>Demo sectors: {demo_sectors}</li>
    <li>Fallback sectors: {fallback_sectors}</li>
  </ul>

  <h2>Backtest</h2>
  <p>This is a market-only historical backtest. Google Trends validation requires stable historical trend data and is not yet fully implemented.</p>
  {backtest_section}
  <p>Run: <code>python src/backtesting.py</code></p>

  <h2>Risks & Limitations</h2>
  <ul>
    <li>No real trading or order logic is implemented.</li>
    <li>Google Trends data can be delayed or incomplete.</li>
    <li>Fundamentals may be sparse for ETFs.</li>
    <li>Decision support only. Human review remains essential.</li>
  </ul>
</body>
</html>
"""

    HTML_REPORT_PATH.write_text(html, encoding="utf-8")
    return HTML_REPORT_PATH


def save_report_csv(ranking: pd.DataFrame) -> Path:
    """Persist the ranking to the data/reports folder for downstream consumers."""
    CSV_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ranking.to_csv(CSV_REPORT_PATH, index=False)
    return CSV_REPORT_PATH
