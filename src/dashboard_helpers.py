"""Presentation helpers for the ML-oriented Streamlit dashboard."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.features import FUNDAMENTAL_FIELDS, MARKET_FIELDS, ml_signal_label


SECTOR_REPRESENTATIVE_STOCKS = {
    "Technology": ["NVDA", "MSFT", "AAPL", "AVGO", "AMD"],
    "Healthcare": ["LLY", "UNH", "JNJ", "MRK", "ABBV"],
    "Financials": ["JPM", "BAC", "WFC", "GS", "MS"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "EOG"],
    "Consumer Discretionary": ["AMZN", "TSLA", "HD", "MCD", "NKE"],
    "Industrials": ["GE", "CAT", "HON", "BA", "UPS"],
    "Utilities": ["NEE", "DUK", "SO", "AEP", "EXC"],
    "Materials": ["LIN", "SHW", "FCX", "NEM", "APD"],
    "Real Estate": ["PLD", "AMT", "EQIX", "SPG", "O"],
    "Consumer Staples": ["WMT", "COST", "PG", "KO", "PEP"],
    "Communication Services": ["META", "GOOGL", "NFLX", "DIS", "CMCSA"],
}


def ensure_dashboard_columns(ranking: pd.DataFrame) -> pd.DataFrame:
    """Ensure dashboard columns exist for ML ranking outputs."""
    result = ranking.copy()
    defaults: dict[str, Any] = {
        "rank": pd.NA,
        "date": "",
        "sector": "",
        "ticker": "",
        "trend_data_status": "not_used",
        "sentiment_data_status": "not_used",
        "data_readiness_status": "Unavailable",
        "operating_mode": "market_fundamental",
        "market_last_date": "",
        "price_data_status": "missing",
        "short_explanation": "",
        "ml_model_status": "not_trained",
        "ml_classifier_model": "",
        "ml_feature_set": "",
        "ml_predicted_outperform_probability": pd.NA,
        "ml_model_confidence": 0.0,
    }
    for column in MARKET_FIELDS + FUNDAMENTAL_FIELDS:
        defaults.setdefault(column, pd.NA)
    for column, default in defaults.items():
        if column not in result:
            result[column] = default
    result["trend_data_status"] = result["trend_data_status"].fillna("not_used").astype(str).str.lower()
    result["sentiment_data_status"] = result["sentiment_data_status"].fillna("not_used").astype(str).str.lower()
    result["ml_predicted_outperform_probability"] = pd.to_numeric(result["ml_predicted_outperform_probability"], errors="coerce")
    result["ml_model_confidence"] = pd.to_numeric(result["ml_model_confidence"], errors="coerce").fillna(0.0)
    return result


def _available_fundamental_count(row: pd.Series | dict[str, Any]) -> int:
    data = dict(row)
    return sum(pd.notna(pd.to_numeric(data.get(field), errors="coerce")) for field in FUNDAMENTAL_FIELDS)


def data_quality_label(row: pd.Series | dict[str, Any]) -> str:
    data = dict(row)
    readiness = str(data.get("data_readiness_status", "")).lower()
    trend_status = str(data.get("trend_data_status", "")).lower()
    if "insufficient" in readiness or str(data.get("price_data_status", "")).lower() == "missing":
        return "Limited data"
    if trend_status == "demo":
        return "Demo trend inputs"
    if _available_fundamental_count(data) < 3:
        return "Partial fundamentals"
    if trend_status in {"not_used", "missing_from_db", "fallback"}:
        return "Trends optional/pending"
    return "Ready"


def analyst_action(row: pd.Series | dict[str, Any]) -> str:
    probability = pd.to_numeric(dict(row).get("ml_predicted_outperform_probability"), errors="coerce")
    if data_quality_label(row) == "Limited data" or pd.isna(probability):
        return "Check data/model"
    if probability >= 0.58:
        return "Review sector thesis"
    if probability <= 0.42:
        return "Deprioritize review"
    return "Monitor"


def management_ranking_table(ranking: pd.DataFrame) -> pd.DataFrame:
    data = ensure_dashboard_columns(ranking).sort_values("ml_predicted_outperform_probability", ascending=False, na_position="last").reset_index(drop=True)
    probability = data["ml_predicted_outperform_probability"]
    return pd.DataFrame(
        {
            "Rank": range(1, len(data) + 1),
            "Sector": data["sector"],
            "ETF": data["ticker"],
            "ML Outperformance Probability": probability.map(lambda value: "" if pd.isna(value) else f"{value:.1%}"),
            "Model Confidence": data["ml_model_confidence"].map(lambda value: f"{value:.1f}"),
            "Model Signal": probability.map(ml_signal_label),
            "Data Quality": data.apply(data_quality_label, axis=1),
            "Analyst Action": data.apply(analyst_action, axis=1),
        }
    )


def probability_bar_data(ranking: pd.DataFrame) -> pd.DataFrame:
    data = ensure_dashboard_columns(ranking)
    return (
        data[["sector", "ml_predicted_outperform_probability"]]
        .sort_values("ml_predicted_outperform_probability", ascending=False, na_position="last")
        .rename(columns={"sector": "Sector", "ml_predicted_outperform_probability": "ML Probability"})
        .set_index("Sector")
    )


def feature_snapshot_rows(row: pd.Series | dict[str, Any]) -> pd.DataFrame:
    data = dict(row)
    labels = {
        "momentum_21": "Momentum 21d",
        "momentum_63": "Momentum 63d",
        "momentum_126": "Momentum 126d",
        "volatility_20": "Volatility 20d",
        "downside_volatility_20": "Downside volatility",
        "drawdown_current": "Current drawdown",
        "distance_to_ma_200": "Distance to MA 200",
        "risk_adjusted_return_63": "Risk-adjusted return",
        "volume_momentum_20": "Volume momentum",
        "relative_strength_vs_spy_63": "Rel. strength vs SPY 63d",
        "relative_strength_vs_spy_126": "Rel. strength vs SPY 126d",
    }
    rows = []
    for field, label in labels.items():
        value = pd.to_numeric(data.get(field), errors="coerce")
        rows.append({"Feature": label, "Value": "" if pd.isna(value) else f"{value:.4f}"})
    return pd.DataFrame(rows)


def sector_caveats(row: pd.Series | dict[str, Any]) -> list[str]:
    data = dict(row)
    caveats: list[str] = []
    trend_status = str(data.get("trend_data_status", "")).lower()
    if trend_status in {"not_used", "missing_from_db", "fallback"}:
        caveats.append("Google Trends are optional and not active in the current model ranking.")
    if _available_fundamental_count(data) < 3:
        caveats.append("ETF fundamental fields are partially available.")
    probability = pd.to_numeric(data.get("ml_predicted_outperform_probability"), errors="coerce")
    if pd.isna(probability):
        caveats.append("ML probability is unavailable for this sector.")
    elif probability < 0.45:
        caveats.append("Model probability is below the neutral range.")
    return caveats or ["No major caveat flagged in the current ML ranking."]


def ml_summary_table(ranking: pd.DataFrame) -> pd.DataFrame:
    data = ensure_dashboard_columns(ranking)
    probability = data["ml_predicted_outperform_probability"]
    return pd.DataFrame(
        {
            "Sector": data["sector"],
            "ETF": data["ticker"],
            "Probability": probability.map(lambda value: "" if pd.isna(value) else f"{value:.1%}"),
            "Confidence": data["ml_model_confidence"].map(lambda value: f"{value:.1f}"),
            "Model": data["ml_classifier_model"],
            "Signal": probability.map(ml_signal_label),
        }
    )


def representative_stock_fallback(sector: str) -> pd.DataFrame:
    tickers = SECTOR_REPRESENTATIVE_STOCKS.get(sector, [])
    return pd.DataFrame(
        {
            "Stock": tickers[:3],
            "6M Return": ["n/a"] * min(3, len(tickers)),
            "Last Price": ["n/a"] * min(3, len(tickers)),
            "Analyst Review Note": ["Performance data unavailable"] * min(3, len(tickers)),
        }
    )
