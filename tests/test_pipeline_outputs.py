import pandas as pd

from src.scoring import calculate_relative_scores
from src import verify_outputs as verifier


def test_scoring_produces_required_output_columns(tmp_path):
    base = {"momentum_21": .1, "momentum_63": .2, "momentum_126": .3, "volatility_20": .2, "downside_volatility_20": .1, "drawdown_current": -.05, "distance_to_ma_200": .1, "risk_adjusted_return_63": 1, "trailingPE": 20, "priceToBook": 2, "dividendYield": .02, "marketCap": 1e9, "trend_z_score_12w": 1, "trend_z_score_52w": 1, "trend_momentum_4w": .1, "trend_momentum_12w": .2, "trend_acceleration": .01, "trend_percentile_52w": 70, "trend_spike": False, "trend_volatility": 3, "trend_latest": 70, "trend_data_status": "demo", "trend_refresh_mode": "demo_only", "trend_cache_age_hours": pd.NA}
    ranking = calculate_relative_scores(pd.DataFrame([{**base, "sector": "A", "ticker": "AAA"}, {**base, "sector": "B", "ticker": "BBB", "momentum_21": .2}]))
    assert {"trend_score", "synergy_score", "total_score", "recommendation", "short_explanation"}.issubset(ranking.columns)
    dashboard_input = tmp_path / "recommendation_scores.csv"
    ranking.to_csv(dashboard_input, index=False)
    reloaded = pd.read_csv(dashboard_input)
    assert {"trend_data_status", "trend_refresh_mode", "trend_cache_age_hours", "confidence_score"}.issubset(reloaded.columns)


def test_verify_outputs_fails_when_every_sector_is_fallback(tmp_path, monkeypatch):
    row = {column: 1 for column in verifier.REQUIRED_COLUMNS}
    row.update({"sector": "Example", "ticker": "EX", "trend_data_status": "fallback", "recommendation": "Neutral", "short_explanation": "test"})
    for field in verifier.REQUIRED_MARKET_FEATURES:
        row[field] = .1
    csv_path = tmp_path / "ranking.csv"
    pd.DataFrame([row]).to_csv(csv_path, index=False)
    html_path = tmp_path / "report.html"; html_path.write_text("report")
    dashboard_path = tmp_path / "app.py"; dashboard_path.write_text("app")
    monkeypatch.setattr(verifier, "CSV_PATH", csv_path)
    monkeypatch.setattr(verifier, "HTML_REPORT_PATH", html_path)
    monkeypatch.setattr(verifier, "DASHBOARD_PATH", dashboard_path)
    assert verifier.verify_outputs() is False
