"""Explainable sector-relative scoring for the monitoring pipeline."""

from typing import Any
import numpy as np
import pandas as pd

from src.config import DATA_FRESHNESS_DAYS, OPERATING_MODE, SCORING_MODE, SCORING_WEIGHTS, SCORING_WEIGHTS_BY_MODE
from src.preprocessing import safe_last_value
from src.trends_loader import calculate_trend_features


MARKET_FIELDS = ["momentum_21", "momentum_63", "momentum_126", "volatility_20", "downside_volatility_20", "drawdown_current", "distance_to_ma_200", "risk_adjusted_return_63", "volume_momentum_20"]
FUNDAMENTAL_FIELDS = ["trailingPE", "forwardPE", "priceToBook", "dividendYield", "beta", "marketCap"]
LIVE_TREND_STATUSES = {"live", "live_pytrends", "manual_csv", "external_api"}
CACHED_TREND_STATUSES = {"cache"}
MISSING_TREND_STATUSES = {"fallback", "missing_from_db"}
USABLE_SENTIMENT_STATUSES = {"live", "cache", "available", "demo"}


def minmax_score(series: pd.Series | list[float], higher_is_better: bool = True) -> pd.Series:
    values = pd.to_numeric(pd.Series(series), errors="coerce")
    valid = values.dropna()
    if valid.empty or valid.max() == valid.min():
        return pd.Series(50.0, index=values.index)
    score = (values - valid.min()) / (valid.max() - valid.min()) * 100
    return score if higher_is_better else 100 - score


def collect_latest_features(sector: str, ticker: str, market_df: pd.DataFrame | None, fundamentals: pd.Series | None, trend_features: dict[str, Any] | None = None, google_trends: pd.DataFrame | None = None) -> dict[str, Any]:
    """Create a single transparent latest-feature record for a sector."""
    row: dict[str, Any] = {"sector": sector, "ticker": ticker}
    for field in MARKET_FIELDS:
        row[field] = safe_last_value(market_df[field]) if market_df is not None and field in market_df else np.nan
    for field in FUNDAMENTAL_FIELDS:
        row[field] = pd.to_numeric(fundamentals.get(field), errors="coerce") if fundamentals is not None else np.nan
    row.update(trend_features if trend_features is not None else calculate_trend_features(google_trends if google_trends is not None else pd.DataFrame()))
    return row


def _average_components(df: pd.DataFrame, specifications: list[tuple[str, bool]]) -> pd.Series:
    components = [minmax_score(df[column], higher) for column, higher in specifications if column in df and pd.to_numeric(df[column], errors="coerce").notna().any()]
    return pd.concat(components, axis=1).mean(axis=1) if components else pd.Series(50.0, index=df.index)


def calculate_momentum_score(feature_df: pd.DataFrame) -> pd.Series:
    return _average_components(feature_df, [(field, True) for field in ["momentum_21", "momentum_63", "momentum_126", "distance_to_ma_200", "risk_adjusted_return_63"]])


def calculate_risk_score(feature_df: pd.DataFrame) -> pd.Series:
    result = feature_df.copy()
    if "drawdown_current" in result:
        result["drawdown_magnitude"] = pd.to_numeric(result["drawdown_current"], errors="coerce").abs()
    if "beta" in result:
        result["beta_distance"] = (pd.to_numeric(result["beta"], errors="coerce") - 1).abs()
    return _average_components(result, [("volatility_20", False), ("downside_volatility_20", False), ("drawdown_magnitude", False), ("beta_distance", False)])


def calculate_fundamental_score(feature_df: pd.DataFrame) -> pd.Series:
    valid_fields = [("trailingPE", False), ("forwardPE", False), ("priceToBook", False), ("dividendYield", True), ("marketCap", True)]
    available = [field for field, _ in valid_fields if field in feature_df and pd.to_numeric(feature_df[field], errors="coerce").notna().any()]
    return _average_components(feature_df, valid_fields) if len(available) >= 2 else pd.Series(50.0, index=feature_df.index)


def calculate_trend_score(feature_df: pd.DataFrame) -> pd.Series:
    statuses = feature_df.get("trend_data_status", pd.Series("fallback", index=feature_df.index)).fillna("fallback").astype(str).str.lower()
    if statuses.eq("not_used").all():
        return pd.Series(0.0, index=feature_df.index)
    scores = pd.DataFrame(index=feature_df.index)
    for field in ["trend_z_score_12w", "trend_z_score_52w", "trend_momentum_4w", "trend_momentum_12w", "trend_acceleration", "trend_percentile_52w"]:
        if field in feature_df:
            scores[field] = minmax_score(feature_df[field], True)
    if "trend_spike" in feature_df:
        scores["spike"] = np.where(feature_df["trend_spike"].fillna(False), 80.0, 50.0)
    if "trend_volatility" in feature_df:
        scores["stability"] = minmax_score(feature_df["trend_volatility"], False)
    result = scores.mean(axis=1).fillna(50.0)
    result.loc[statuses.isin(MISSING_TREND_STATUSES)] = 50.0
    result.loc[statuses == "demo"] *= .95
    return result.clip(0, 100)


def calculate_sentiment_score(feature_df: pd.DataFrame) -> pd.Series:
    statuses = feature_df.get("sentiment_data_status", pd.Series("not_used", index=feature_df.index)).fillna("not_used").astype(str).str.lower()
    raw_score = pd.to_numeric(feature_df.get("sentiment_score_component", pd.Series(np.nan, index=feature_df.index)), errors="coerce")
    fallback_score = pd.to_numeric(feature_df.get("sentiment_score", pd.Series(np.nan, index=feature_df.index)), errors="coerce") * 100
    result = raw_score.fillna(fallback_score)
    result.loc[~statuses.isin(USABLE_SENTIMENT_STATUSES)] = np.nan
    return result.clip(0, 100)


def calculate_synergy_score(row: pd.Series | dict[str, Any]) -> float:
    label = assign_synergy_label(row)
    return {"Trend-confirmed opportunity": 85.0, "Early attention signal": 70.0, "Hype risk": 45.0, "Fundamental sleeper": 70.0, "Weak setup": 35.0, "Balanced setup": 60.0}[label]


def assign_synergy_label(row: pd.Series | dict[str, Any]) -> str:
    data = dict(row)
    trend, momentum, fundamentals = (float(data.get(key, 50)) for key in ("trend_score", "momentum_score", "fundamental_score"))
    if trend >= 70 and momentum >= 60 and fundamentals >= 55: return "Trend-confirmed opportunity"
    if trend >= 70 and momentum < 55: return "Early attention signal"
    if trend >= 70 and fundamentals < 45: return "Hype risk"
    if trend < 50 and fundamentals >= 65: return "Fundamental sleeper"
    if trend < 45 and momentum < 45: return "Weak setup"
    return "Balanced setup"


def _is_stale(value: Any, threshold_days: int = DATA_FRESHNESS_DAYS) -> bool:
    date = pd.to_datetime(value, errors="coerce")
    if pd.isna(date):
        return False
    return (pd.Timestamp.now().normalize() - date.normalize()).days > threshold_days


def assess_data_quality(row: pd.Series | dict[str, Any]) -> str:
    """Classify source completeness and freshness before interpreting a score."""
    data = dict(row)
    trend_status = str(data.get("trend_data_status", "fallback")).lower()
    operating_mode = str(data.get("operating_mode", "full")).lower()
    key_market_fields = ("momentum_21", "momentum_63", "volatility_20", "drawdown_current")
    if operating_mode == "market_fundamental":
        if str(data.get("price_data_status", "missing")).lower() == "missing" or any(pd.isna(data.get(field)) for field in key_market_fields):
            return "Insufficient data"
        if _is_stale(data.get("market_last_date")):
            return "Stale data"
        return "Market/fundamental research signal"
    if trend_status == "demo":
        return "Prototype only"
    if trend_status in MISSING_TREND_STATUSES or str(data.get("price_data_status", "missing")).lower() == "missing":
        return "Insufficient data"
    if any(pd.isna(data.get(field)) for field in key_market_fields):
        return "Insufficient data"
    if _is_stale(data.get("trend_last_date")) or _is_stale(data.get("market_last_date")):
        return "Stale data"
    if trend_status in LIVE_TREND_STATUSES:
        return "Live research signal"
    if trend_status in CACHED_TREND_STATUSES:
        return "Cached research signal"
    return "Insufficient data"


def assess_actionability(row: pd.Series | dict[str, Any], backtest_validated: bool = False) -> str:
    """Limit outputs to research use unless data and validation are adequate."""
    data = dict(row)
    quality = data.get("data_quality_status")
    if quality in {"Prototype only", "Insufficient data", "Stale data"}:
        return "Not actionable"
    if quality == "Market/fundamental research signal":
        return "Suitable for analyst review" if backtest_validated else "Research only"
    if not backtest_validated:
        return "Research only"
    if float(data.get("total_score", 0)) >= 70 and float(data.get("confidence_score", 0)) >= 70:
        return "Validated research candidate"
    return "Suitable for analyst review"


def assign_recommendation(total_score: float, confidence_score: float = 0, synergy_label: str | None = None, actionability_status: str | None = None, trend_data_status: str | None = None, operating_mode: str | None = None) -> str:
    """Return research labels only; never an instruction to trade."""
    if str(operating_mode).lower() == "demo":
        return "Research Prototype"
    if str(trend_data_status).lower() in MISSING_TREND_STATUSES:
        return "Insufficient Data"
    if str(trend_data_status).lower() == "demo" or actionability_status == "Not actionable":
        return "Research Prototype"
    if synergy_label == "Hype risk":
        return "Watch"
    if total_score >= 70 and confidence_score >= 65:
        return "Research Candidate"
    if total_score >= 60:
        return "Watch"
    return "Neutral" if total_score >= 45 else "Avoid"


def calculate_confidence_score(row: pd.Series | dict[str, Any]) -> float:
    data = dict(row)
    filled = sum(pd.notna(data.get(field)) for field in MARKET_FIELDS) * 4 + sum(pd.notna(data.get(field)) for field in FUNDAMENTAL_FIELDS) * 2
    confidence = 40 + min(filled, 45) + (8 if pd.notna(data.get("trend_latest")) else 0)
    status = str(data.get("trend_data_status", "fallback")).lower()
    if str(data.get("operating_mode", "full")).lower() == "market_fundamental":
        return float(np.clip(45 + min(filled, 50), 0, 100))
    confidence += {"live": 6, "live_pytrends": 6, "manual_csv": 6, "external_api": 6, "cache": 4, "demo": -8, "fallback": -22, "missing_from_db": -22}.get(status, -22)
    return float(np.clip(confidence, 0, 100))


def classify_trend_signal(row: pd.Series | dict[str, Any]) -> str:
    data = dict(row)
    if str(data.get("trend_data_status", "")).lower() == "not_used":
        return "Trend data not used in market/fundamental mode"
    if pd.isna(data.get("trend_latest")): return "No Trend Data"
    if data.get("trend_spike"): return "Strong Attention Spike"
    if data.get("trend_momentum_4w", 0) > 0 or data.get("trend_z_score_12w", 0) >= .5: return "Rising Attention"
    if data.get("trend_momentum_4w", 0) < 0 or data.get("trend_z_score_12w", 0) <= -.5: return "Falling Attention"
    return "Stable Attention"


def generate_explanation(row: pd.Series | dict[str, Any]) -> str:
    data = dict(row); status = str(data.get("trend_data_status", "fallback")).lower(); label = data.get("synergy_label")
    if str(data.get("operating_mode", "full")).lower() == "market_fundamental":
        return "Market/fundamental-only mode: Google Trends not used."
    if status == "demo": return "Demo trend data used for prototype validation; do not interpret as real search interest."
    if status == "manual_csv": return "Manual Google Trends CSV data used; analyst should confirm keyword/timeframe consistency."
    if status == "live_pytrends": return "Live pytrends data used; analyst should review Google Trends rate-limit and coverage context."
    if label == "Trend-confirmed opportunity": return "Strong Google Trends attention and positive market momentum support this sector."
    if label == "Early attention signal": return "Rising attention but weak price momentum suggests an early watch signal."
    if label == "Hype risk": return "High attention combined with weak fundamentals indicates hype risk."
    if label == "Fundamental sleeper": return "Stable fundamentals but low attention suggest a fundamental sleeper."
    return "Mixed relative signals warrant continued analyst monitoring."


def calculate_relative_scores(feature_df: pd.DataFrame, operating_mode: str | None = None) -> pd.DataFrame:
    scored = feature_df.copy()
    operating_mode = (operating_mode or (scored["operating_mode"].iloc[0] if "operating_mode" in scored and not scored.empty else OPERATING_MODE))
    weights = SCORING_WEIGHTS_BY_MODE.get(str(operating_mode), SCORING_WEIGHTS)
    scored["momentum_score"] = calculate_momentum_score(scored)
    scored["risk_score"] = calculate_risk_score(scored)
    scored["fundamental_score"] = calculate_fundamental_score(scored)
    scored["trend_score"] = calculate_trend_score(scored)
    scored["sentiment_score_component"] = calculate_sentiment_score(scored)
    if str(operating_mode) == "full" and "sentiment_score" in scored:
        available_sentiment = scored["sentiment_score_component"].notna()
        no_sentiment_weights = {"trend_score": 0.30, "momentum_score": 0.3181818182, "fundamental_score": 0.2545454545, "risk_score": 0.1272727273}
        full_sentiment_weights = {"trend_score": 0.30, "sentiment_score_component": 0.15, "momentum_score": 0.25, "fundamental_score": 0.20, "risk_score": 0.10}
        with_sentiment = sum(full_sentiment_weights[key] * scored[key].fillna(0) for key in full_sentiment_weights)
        without_sentiment = sum(no_sentiment_weights[key] * scored[key].fillna(0) for key in no_sentiment_weights)
        scored["total_score"] = without_sentiment.where(~available_sentiment, with_sentiment).clip(0, 100)
        scored["sentiment_score_component"] = scored["sentiment_score_component"].fillna(0.0)
    else:
        scored["sentiment_score_component"] = scored["sentiment_score_component"].fillna(0.0)
        scored["total_score"] = sum(weights[key] * scored[key].fillna(0) for key in weights).clip(0, 100)
    scored["trend_signal"] = scored.apply(classify_trend_signal, axis=1)
    scored["synergy_label"] = scored.apply(assign_synergy_label, axis=1)
    scored["synergy_score"] = scored.apply(calculate_synergy_score, axis=1)
    scored["confidence_score"] = scored.apply(calculate_confidence_score, axis=1)
    scored["data_quality_status"] = scored.apply(assess_data_quality, axis=1)
    scored["actionability_status"] = scored.apply(assess_actionability, axis=1)
    scored["recommendation"] = scored.apply(lambda row: assign_recommendation(row.total_score, row.confidence_score, row.synergy_label, row.actionability_status, row.trend_data_status, row.get("operating_mode")), axis=1)
    scored["short_explanation"] = scored.apply(generate_explanation, axis=1)
    return scored


# Backwards-compatible name used by an earlier report implementation.
classify_synergy_label = assign_synergy_label
