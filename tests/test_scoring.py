import pandas as pd

from src.scoring import assess_actionability, assess_data_quality, assign_recommendation, assign_synergy_label, minmax_score


def test_minmax_score_direction():
    assert minmax_score([1, 2, 3]).tolist() == [0.0, 50.0, 100.0]
    assert minmax_score([1, 2, 3], higher_is_better=False).tolist() == [100.0, 50.0, 0.0]


def test_recommendation_thresholds_and_hype_cap():
    assert assign_recommendation(76, 70, actionability_status="Suitable for analyst review", trend_data_status="live") == "Research Candidate"
    assert assign_recommendation(90, 90, "Hype risk", "Research only", "live") == "Watch"
    assert assign_recommendation(90, 90, trend_data_status="demo") == "Research Prototype"


def test_synergy_labels():
    assert assign_synergy_label(pd.Series({"trend_score": 75, "momentum_score": 65, "fundamental_score": 60})) == "Trend-confirmed opportunity"
    assert assign_synergy_label(pd.Series({"trend_score": 75, "momentum_score": 50, "fundamental_score": 60})) == "Early attention signal"
    assert assign_synergy_label(pd.Series({"trend_score": 40, "momentum_score": 55, "fundamental_score": 70})) == "Fundamental sleeper"


def test_demo_data_is_not_actionable():
    row = {"trend_data_status": "demo", "price_data_status": "live", "momentum_21": .1, "momentum_63": .1, "volatility_20": .2, "drawdown_current": -.1}
    assert assess_data_quality(row) == "Prototype only"
    assert assess_actionability({**row, "data_quality_status": "Prototype only"}) == "Not actionable"
