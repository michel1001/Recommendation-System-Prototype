import pandas as pd

from src.scoring import calculate_relative_scores


def _base_rows():
    base = {
        "momentum_21": .1, "momentum_63": .2, "momentum_126": .3,
        "volatility_20": .2, "downside_volatility_20": .1, "drawdown_current": -.05,
        "distance_to_ma_200": .1, "risk_adjusted_return_63": 1, "volume_momentum_20": 1.1,
        "trailingPE": 20, "priceToBook": 2, "dividendYield": .02, "marketCap": 1e9,
        "trend_latest": pd.NA, "trend_data_status": "not_used", "price_data_status": "live",
        "market_last_date": pd.Timestamp.today().strftime("%Y-%m-%d"),
        "operating_mode": "market_fundamental", "scoring_profile": "market_fundamental_only",
    }
    return pd.DataFrame([{**base, "sector": "A", "ticker": "AAA"}, {**base, "sector": "B", "ticker": "BBB", "momentum_21": .2}])


def test_market_fundamental_mode_excludes_trend_score_from_total():
    scored = calculate_relative_scores(_base_rows(), operating_mode="market_fundamental")
    recomputed = scored["momentum_score"] * .40 + scored["fundamental_score"] * .30 + scored["risk_score"] * .30

    assert scored["trend_data_status"].eq("not_used").all()
    assert scored["trend_score"].eq(0).all()
    assert scored["total_score"].round(6).equals(recomputed.round(6))
    assert not scored["recommendation"].eq("Research Prototype").all()


def test_demo_mode_caps_recommendations_to_research_prototype():
    frame = _base_rows()
    frame["trend_data_status"] = "demo"
    frame["trend_latest"] = 50
    frame["operating_mode"] = "demo"
    frame["scoring_profile"] = "demo_trend_market_fundamental"

    scored = calculate_relative_scores(frame, operating_mode="demo")

    assert scored["recommendation"].eq("Research Prototype").all()
