import pandas as pd

from src.dashboard_helpers import (
    analyst_action,
    data_quality_label,
    main_driver,
    management_ranking_table,
    ml_support_label,
    representative_stock_fallback,
    risk_level,
)


def _row(**overrides):
    base = {
        "sector": "Technology",
        "ticker": "XLK",
        "total_score": 65,
        "momentum_score": 70,
        "risk_score": 80,
        "fundamental_score": 50,
        "trend_score": 0,
        "sentiment_score_component": 0,
        "recommendation": "Watch",
        "data_quality_status": "Market/fundamental research signal",
        "trend_data_status": "not_used",
        "sentiment_data_status": "not_used",
        "price_data_status": "db",
        "trailingPE": 20,
        "forwardPE": pd.NA,
        "priceToBook": 2,
        "dividendYield": 0.01,
        "beta": pd.NA,
        "marketCap": pd.NA,
        "ml_predicted_outperform_probability": 0.61,
    }
    base.update(overrides)
    return pd.Series(base)


def test_main_driver_uses_strongest_management_component():
    assert main_driver(_row(momentum_score=55, risk_score=76, fundamental_score=40, ml_predicted_outperform_probability=0.5)) == "Risk"
    assert main_driver(_row(momentum_score=55, risk_score=40, fundamental_score=40, ml_predicted_outperform_probability=0.7)) == "ML Support"


def test_risk_level_mapping():
    assert risk_level(75) == "Low risk"
    assert risk_level(55) == "Medium risk"
    assert risk_level(30) == "Elevated risk"


def test_data_quality_label_mapping():
    assert data_quality_label(_row()) == "Trends pending"
    assert data_quality_label(_row(trend_data_status="demo")) == "Demo data"
    assert data_quality_label(_row(trailingPE=pd.NA, priceToBook=pd.NA, dividendYield=pd.NA)) == "Partial fundamentals"
    assert data_quality_label(_row(data_quality_status="Insufficient data")) == "Limited data"


def test_analyst_action_mapping():
    assert analyst_action(_row(recommendation="Watch")) == "Review sector thesis"
    assert analyst_action(_row(recommendation="Neutral")) == "Monitor further"
    assert analyst_action(_row(recommendation="Avoid")) == "No priority"
    assert analyst_action(_row(data_quality_status="Insufficient data")) == "Check data first"


def test_management_ranking_table_hides_technical_columns():
    table = management_ranking_table(pd.DataFrame([_row(), _row(sector="Utilities", ticker="XLU", total_score=70)]))
    assert list(table.columns) == ["Rank", "Sector", "ETF", "Total Score", "Signal", "Main Driver", "Risk Level", "Data Quality", "Analyst Action"]
    assert table.iloc[0]["Sector"] == "Utilities"


def test_representative_stock_fallback_is_non_recommendation_copy():
    fallback = representative_stock_fallback("Technology")
    assert len(fallback) == 3
    assert "Analyst Review Note" in fallback.columns
    assert fallback["Analyst Review Note"].eq("Performance data unavailable").all()


def test_ml_support_label_mapping():
    assert ml_support_label(0.6) == "Supportive"
    assert ml_support_label(0.5) == "Neutral"
    assert ml_support_label(0.4) == "Contradictory"
    assert ml_support_label(pd.NA) == "Unavailable"
