import pandas as pd

from src.dashboard_helpers import (
    analyst_action,
    data_quality_label,
    management_ranking_table,
    ml_summary_table,
    probability_bar_data,
    representative_stock_fallback,
)


def _row(**overrides):
    base = {
        "sector": "Technology",
        "ticker": "XLK",
        "rank": 1,
        "data_readiness_status": "Ready for ML inference",
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
        "ml_model_confidence": 22,
        "ml_classifier_model": "RandomForestClassifier",
    }
    base.update(overrides)
    return pd.Series(base)


def test_management_ranking_table_uses_ml_probability_only():
    table = management_ranking_table(pd.DataFrame([_row(), _row(sector="Utilities", ticker="XLU", ml_predicted_outperform_probability=0.72)]))
    assert list(table.columns) == ["Rank", "Sector", "ETF", "ML Outperformance Probability", "Model Confidence", "Model Signal", "Data Quality", "Analyst Action"]
    assert table.iloc[0]["Sector"] == "Utilities"


def test_probability_bar_data_uses_ml_probability():
    chart = probability_bar_data(pd.DataFrame([_row(sector="A", ml_predicted_outperform_probability=0.4), _row(sector="B", ml_predicted_outperform_probability=0.7)]))
    assert chart.index[0] == "B"
    assert "ML Probability" in chart.columns


def test_data_quality_and_analyst_action_mapping():
    assert data_quality_label(_row()) == "Trends optional/pending"
    assert data_quality_label(_row(trend_data_status="demo")) == "Demo trend inputs"
    assert data_quality_label(_row(data_readiness_status="Insufficient market data")) == "Limited data"
    assert analyst_action(_row(ml_predicted_outperform_probability=0.7)) == "Review sector thesis"
    assert analyst_action(_row(ml_predicted_outperform_probability=0.35)) == "Deprioritize review"


def test_ml_summary_table_and_stock_fallback():
    summary = ml_summary_table(pd.DataFrame([_row()]))
    assert list(summary.columns) == ["Sector", "ETF", "Probability", "Confidence", "Model", "Signal"]
    fallback = representative_stock_fallback("Technology")
    assert len(fallback) == 3
    assert "Analyst Review Note" in fallback.columns
