"""Presentation helpers for the management-oriented Streamlit dashboard."""

from __future__ import annotations

from typing import Any

import pandas as pd


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
    """Ensure dashboard helper columns exist even for older CSV outputs."""
    result = ranking.copy()
    defaults: dict[str, Any] = {
        "trend_data_status": "fallback",
        "trend_score": 0.0,
        "sentiment_score_component": 0.0,
        "sentiment_data_status": "not_used",
        "momentum_score": 0.0,
        "risk_score": 0.0,
        "fundamental_score": 0.0,
        "total_score": 0.0,
        "recommendation": "Insufficient Data",
        "data_quality_status": "Unavailable",
        "actionability_status": "Analyst Review",
        "operating_mode": "market_fundamental",
        "ticker": "",
        "market_last_date": "",
        "price_data_status": "missing",
        "short_explanation": "",
        "ml_model_status": "not_trained",
        "ml_predicted_outperform_probability": pd.NA,
        "ml_predicted_excess_return_4w": pd.NA,
        "trailingPE": pd.NA,
        "forwardPE": pd.NA,
        "priceToBook": pd.NA,
        "dividendYield": pd.NA,
        "beta": pd.NA,
        "marketCap": pd.NA,
    }
    for column, default in defaults.items():
        if column not in result:
            result[column] = default
    result["trend_data_status"] = result["trend_data_status"].fillna("fallback").astype(str).str.lower()
    result["sentiment_data_status"] = result["sentiment_data_status"].fillna("not_used").astype(str).str.lower()
    for column in ["trend_score", "sentiment_score_component", "momentum_score", "risk_score", "fundamental_score", "total_score"]:
        result[column] = pd.to_numeric(result[column], errors="coerce").fillna(0.0)
    return result


def operating_mode_label(mode: str | None) -> str:
    mapping = {
        "market_fundamental": "Market/Fundamental Research",
        "full": "Full Research Mode",
        "demo": "Demo Mode",
    }
    return mapping.get(str(mode or "").lower(), "Research Mode")


def signal_label(recommendation: str | None) -> str:
    value = str(recommendation or "Insufficient Data")
    if value == "Avoid":
        return "Avoid / Weak Setup"
    if value in {"Research Candidate", "Watch", "Neutral", "Insufficient Data", "Research Prototype"}:
        return value
    return value


def main_driver(row: pd.Series | dict[str, Any]) -> str:
    data = dict(row)
    components = {
        "Momentum": pd.to_numeric(data.get("momentum_score"), errors="coerce"),
        "Risk": pd.to_numeric(data.get("risk_score"), errors="coerce"),
        "Fundamentals": pd.to_numeric(data.get("fundamental_score"), errors="coerce"),
    }
    trend_status = str(data.get("trend_data_status", "")).lower()
    if trend_status not in {"not_used", "fallback", "missing_from_db"}:
        components["Trend Attention"] = pd.to_numeric(data.get("trend_score"), errors="coerce")
    sentiment_status = str(data.get("sentiment_data_status", "not_used")).lower()
    if sentiment_status not in {"not_used", "disabled_by_mode", "disabled_no_api_key", "missing"}:
        components["Sentiment"] = pd.to_numeric(data.get("sentiment_score_component"), errors="coerce")
    ml_probability = pd.to_numeric(data.get("ml_predicted_outperform_probability"), errors="coerce")
    if pd.notna(ml_probability):
        components["ML Support"] = float(ml_probability) * 100
    clean = {key: float(value) for key, value in components.items() if pd.notna(value)}
    return max(clean, key=clean.get) if clean else "Market data"


def risk_level(risk_score: Any) -> str:
    score = pd.to_numeric(risk_score, errors="coerce")
    if pd.isna(score):
        return "Limited data"
    if score >= 70:
        return "Low risk"
    if score >= 45:
        return "Medium risk"
    return "Elevated risk"


def _available_fundamental_count(row: pd.Series | dict[str, Any]) -> int:
    data = dict(row)
    fields = ["trailingPE", "forwardPE", "priceToBook", "dividendYield", "beta", "marketCap"]
    return sum(pd.notna(pd.to_numeric(data.get(field), errors="coerce")) for field in fields)


def data_quality_label(row: pd.Series | dict[str, Any]) -> str:
    data = dict(row)
    quality = str(data.get("data_quality_status", "")).lower()
    trend_status = str(data.get("trend_data_status", "")).lower()
    price_status = str(data.get("price_data_status", "")).lower()
    if "insufficient" in quality or price_status == "missing":
        return "Limited data"
    if trend_status == "demo":
        return "Demo data"
    if _available_fundamental_count(data) < 3:
        return "Partial fundamentals"
    if trend_status in {"not_used", "missing_from_db", "fallback"}:
        return "Trends pending"
    return "Complete market data"


def analyst_action(row: pd.Series | dict[str, Any]) -> str:
    signal = signal_label(dict(row).get("recommendation"))
    quality = data_quality_label(row)
    if quality == "Limited data" or signal == "Insufficient Data":
        return "Check data first"
    if signal in {"Research Candidate", "Watch"}:
        return "Review sector thesis"
    if signal == "Neutral":
        return "Monitor further"
    return "No priority"


def management_ranking_table(ranking: pd.DataFrame) -> pd.DataFrame:
    data = ensure_dashboard_columns(ranking).sort_values("total_score", ascending=False).reset_index(drop=True)
    return pd.DataFrame(
        {
            "Rank": range(1, len(data) + 1),
            "Sector": data["sector"],
            "ETF": data["ticker"],
            "Total Score": data["total_score"].round(1),
            "Signal": data["recommendation"].map(signal_label),
            "Main Driver": data.apply(main_driver, axis=1),
            "Risk Level": data["risk_score"].map(risk_level),
            "Data Quality": data.apply(data_quality_label, axis=1),
            "Analyst Action": data.apply(analyst_action, axis=1),
        }
    )


def data_readiness_summary(ranking: pd.DataFrame) -> str:
    data = ensure_dashboard_columns(ranking)
    parts = ["Market data complete"]
    if data["trend_data_status"].isin(["not_used", "missing_from_db", "fallback"]).all():
        parts.append("Google Trends pending")
    elif data["trend_data_status"].eq("demo").any():
        parts.append("Demo Trends")
    else:
        parts.append("Google Trends available")
    if data.apply(_available_fundamental_count, axis=1).lt(3).any():
        parts.append("Fundamentals partially available")
    else:
        parts.append("Fundamentals available")
    return " | ".join(parts)


def management_summary(ranking: pd.DataFrame) -> str:
    data = ensure_dashboard_columns(ranking).sort_values("total_score", ascending=False)
    top_sectors = data["sector"].head(2).astype(str).tolist()
    top_text = " and ".join(top_sectors) if len(top_sectors) <= 2 else ", ".join(top_sectors)
    modes = set(data["operating_mode"].dropna().astype(str).str.lower())
    if modes == {"market_fundamental"}:
        return (
            f"The current research baseline identifies {top_text} as the strongest sectors based on market, risk and "
            "fundamental indicators. Google Trends data has not yet been imported, therefore the current view should "
            "be interpreted as a market/fundamental baseline."
        )
    if modes == {"demo"}:
        return (
            f"The demo view highlights {top_text}, but trend inputs are synthetic and should be used only for "
            "presentation and workflow validation."
        )
    return (
        f"The current full research view identifies {top_text} as the strongest sectors using market, fundamental and "
        "available alternative-data signals. Analysts should still validate each sector thesis before any decision use."
    )


def component_rows(row: pd.Series | dict[str, Any]) -> pd.DataFrame:
    data = dict(row)
    rows = [
        {"Component": "Market momentum", "Score": float(pd.to_numeric(data.get("momentum_score"), errors="coerce") or 0)},
        {"Component": "Risk profile", "Score": float(pd.to_numeric(data.get("risk_score"), errors="coerce") or 0)},
        {"Component": "Fundamentals", "Score": float(pd.to_numeric(data.get("fundamental_score"), errors="coerce") or 0)},
    ]
    if str(data.get("trend_data_status", "")).lower() not in {"not_used", "fallback", "missing_from_db"}:
        rows.append({"Component": "Google Trends attention", "Score": float(pd.to_numeric(data.get("trend_score"), errors="coerce") or 0)})
    if str(data.get("sentiment_data_status", "not_used")).lower() not in {"not_used", "disabled_by_mode", "disabled_no_api_key", "missing"}:
        rows.append({"Component": "News/Social sentiment", "Score": float(pd.to_numeric(data.get("sentiment_score_component"), errors="coerce") or 0)})
    return pd.DataFrame(rows)


def sector_caveats(row: pd.Series | dict[str, Any]) -> list[str]:
    data = dict(row)
    caveats: list[str] = []
    trend_status = str(data.get("trend_data_status", "")).lower()
    if trend_status in {"not_used", "missing_from_db", "fallback"}:
        caveats.append("Google Trends data has not been imported for this view.")
    if _available_fundamental_count(data) < 3:
        caveats.append("ETF fundamental fields are partially available.")
    if risk_level(data.get("risk_score")) == "Elevated risk":
        caveats.append("Risk profile is elevated relative to other sectors.")
    ml_probability = pd.to_numeric(data.get("ml_predicted_outperform_probability"), errors="coerce")
    if pd.isna(ml_probability):
        caveats.append("ML support signal is unavailable.")
    elif ml_probability < 0.45:
        caveats.append("ML support is weak or contradictory.")
    return caveats or ["No major caveat flagged in the current research baseline."]


def ml_support_label(probability: Any) -> str:
    prob = pd.to_numeric(probability, errors="coerce")
    if pd.isna(prob):
        return "Unavailable"
    if prob >= 0.58:
        return "Supportive"
    if prob <= 0.42:
        return "Contradictory"
    return "Neutral"


def ml_summary_table(ranking: pd.DataFrame) -> pd.DataFrame:
    data = ensure_dashboard_columns(ranking)
    probability = pd.to_numeric(data["ml_predicted_outperform_probability"], errors="coerce")
    excess = pd.to_numeric(data["ml_predicted_excess_return_4w"], errors="coerce")
    return pd.DataFrame(
        {
            "Sector": data["sector"],
            "ML support": probability.map(ml_support_label),
            "Probability": probability.map(lambda value: "" if pd.isna(value) else f"{value:.1%}"),
            "Expected excess return": excess.map(lambda value: "" if pd.isna(value) else f"{value:.2%}"),
            "Interpretation": probability.map(lambda value: "Supporting research signal" if ml_support_label(value) == "Supportive" else "Review with analyst context" if ml_support_label(value) == "Neutral" else "Model signal disagrees" if ml_support_label(value) == "Contradictory" else "Not available"),
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
