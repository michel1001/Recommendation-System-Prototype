"""HTML report generation for the ML sector monitoring prototype."""

from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

import pandas as pd

from src.config import ML_EVALUATION_METRICS_PATH, ML_FEATURE_IMPORTANCE_PATH

HTML_REPORT_PATH = Path(__file__).resolve().parents[1] / "reports" / "html" / "sector_monitoring_report.html"
CSV_REPORT_PATH = Path(__file__).resolve().parents[1] / "data" / "reports" / "ml_sector_ranking.csv"


def _format_probability(value) -> str:
    parsed = pd.to_numeric(value, errors="coerce")
    return "" if pd.isna(parsed) else f"{parsed:.1%}"


def generate_html_report(ranking: pd.DataFrame, generated_at: datetime | None = None) -> Path:
    """Create an HTML report summarizing the ML ranking and validation artifacts."""
    if generated_at is None:
        generated_at = datetime.now()

    report_dir = HTML_REPORT_PATH.parent
    report_dir.mkdir(parents=True, exist_ok=True)

    data = ranking.copy()
    for column, default in {
        "rank": pd.NA,
        "sector": "",
        "ticker": "",
        "ml_predicted_outperform_probability": pd.NA,
        "ml_model_confidence": 0.0,
        "ml_model_status": "not_trained",
        "ml_classifier_model": "",
        "ml_feature_set": "",
        "data_readiness_status": "",
        "trend_data_status": "not_used",
        "short_explanation": "",
    }.items():
        if column not in data:
            data[column] = default
    data = data.sort_values("ml_predicted_outperform_probability", ascending=False, na_position="last").reset_index(drop=True)

    top_sector = data.iloc[0] if not data.empty else pd.Series(dtype=object)
    trend_counts = data["trend_data_status"].fillna("not_used").astype(str).str.lower().value_counts().to_dict() if "trend_data_status" in data else {}
    model_statuses = ", ".join(sorted(data["ml_model_status"].fillna("not_trained").astype(str).unique())) if "ml_model_status" in data else "not_trained"

    summary_rows = []
    for _, row in data.head(5).iterrows():
        summary_rows.append(
            f"<li><strong>{escape(str(row['sector']))}</strong> ({escape(str(row['ticker']))}) - "
            f"{escape(_format_probability(row['ml_predicted_outperform_probability']))} ML probability</li>"
        )

    display_table = data.copy()
    display_table["ml_predicted_outperform_probability"] = display_table["ml_predicted_outperform_probability"].map(_format_probability)

    if ML_EVALUATION_METRICS_PATH.exists():
        ml_metrics_section = pd.read_csv(ML_EVALUATION_METRICS_PATH).to_html(index=False, escape=False)
    else:
        ml_metrics_section = "<p>ML metrics are not available yet. Run <code>python src/ml_dataset.py</code> and <code>python src/ml_model.py</code>.</p>"

    if ML_FEATURE_IMPORTANCE_PATH.exists():
        importance = pd.read_csv(ML_FEATURE_IMPORTANCE_PATH)
        ml_importance_section = importance.head(10).to_html(index=False, escape=False) if not importance.empty else "<p>Feature importance is unavailable for the selected model type.</p>"
    else:
        ml_importance_section = "<p>Feature importance has not been generated yet. Run <code>python src/ml_evaluation.py</code>.</p>"

    top_text = ""
    if not top_sector.empty:
        top_text = (
            f"<p><strong>{escape(str(top_sector.get('sector', '')))}</strong> ranks first because the supervised "
            f"ML model assigns the highest 4-week outperformance probability versus SPY "
            f"({_format_probability(top_sector.get('ml_predicted_outperform_probability'))}). "
            f"{escape(str(top_sector.get('short_explanation', '')))}</p>"
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>ML Sector Monitoring Report</title>
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
  <h1>ML Sector Monitoring Report</h1>
  <p><strong>Generated:</strong> {generated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
  <div class="note">Educational prototype only. Not financial advice.</div>

  <h2>Executive Summary</h2>
  <p>The final modelling approach is a supervised machine-learning classifier. It estimates whether each sector ETF will outperform SPY over the next 4 weeks. The displayed ranking is derived only from the model probability.</p>
  <ul>{''.join(summary_rows)}</ul>
  {top_text}

  <h2>Pipeline</h2>
  <p>SQLite data -> Data Cleaning -> Feature Engineering -> time-based Train/Test Split -> RandomForestClassifier -> Outperformance Probability -> Ranking/Dashboard.</p>

  <h2>Current ML Ranking</h2>
  {display_table.to_html(index=False, escape=False)}

  <h2>Data Readiness</h2>
  <ul>
    <li><strong>Model status:</strong> {escape(model_statuses)}</li>
    <li><strong>Google Trends not active:</strong> {trend_counts.get('not_used', 0)}</li>
    <li><strong>Google Trends demo inputs:</strong> {trend_counts.get('demo', 0)}</li>
    <li><strong>Google Trends observed/cache/manual inputs:</strong> {sum(trend_counts.get(status, 0) for status in ('live', 'live_pytrends', 'manual_csv', 'external_api', 'cache'))}</li>
  </ul>

  <h2>Model Evaluation</h2>
  <p>The ML model is evaluated with a time-based train/test split rather than a random split. This helps avoid look-ahead bias in the historical sector ETF setting.</p>
  {ml_metrics_section}

  <h2>Feature Importance</h2>
  {ml_importance_section}

  <h2>Interpretation</h2>
  <p>The model output is a research signal, not a buy/sell instruction. Google Trends may be used only as an optional feature source when reliable data is available; the current stable model can run on market/fundamental features alone.</p>

  <p>Dashboard command: <code>python -m streamlit run app/app.py</code></p>
</body>
</html>
"""

    HTML_REPORT_PATH.write_text(html, encoding="utf-8")
    return HTML_REPORT_PATH


def save_report_csv(ranking: pd.DataFrame) -> Path:
    """Persist the ML ranking to the data/reports folder for downstream consumers."""
    CSV_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ranking.to_csv(CSV_REPORT_PATH, index=False)
    return CSV_REPORT_PATH
