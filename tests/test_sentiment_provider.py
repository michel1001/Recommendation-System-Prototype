import json

import pandas as pd

from src.features import assess_data_readiness
from src.sentiment_provider import DemoSentimentProvider, FinnhubSentimentProvider, SentimentProvider, aggregate_sector_sentiment, sentiment_not_used_features


class MissingSentimentProvider(SentimentProvider):
    name = "missing_test"

    def fetch_company_sentiment(self, ticker: str) -> dict:
        return {
            "ticker": ticker,
            "companyNewsScore": pd.NA,
            "bullishPercent": pd.NA,
            "bearishPercent": pd.NA,
            "articlesInLastWeek": 0,
            "buzz": pd.NA,
            "sentiment_data_status": "missing",
            "sentiment_provider": self.name,
        }


def test_finnhub_missing_api_key_returns_disabled(monkeypatch, tmp_path):
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)

    result = FinnhubSentimentProvider(api_key=None, cache_dir=tmp_path).fetch_company_sentiment("AAPL")

    assert result["sentiment_data_status"] == "disabled_no_api_key"
    assert result["sentiment_provider"] == "finnhub"


def test_finnhub_cached_error_payload_returns_invalid_api_key(tmp_path):
    cache_file = tmp_path / "finnhub_news_sentiment_AAPL.json"
    cache_file.write_text(json.dumps({"raw": {"error": "Invalid API key"}}), encoding="utf-8")

    result = FinnhubSentimentProvider(api_key="placeholder", cache_dir=tmp_path).fetch_company_sentiment("AAPL")

    assert result["sentiment_data_status"] == "invalid_api_key"


def test_demo_sentiment_returns_deterministic_values():
    provider = DemoSentimentProvider()

    first = provider.fetch_company_sentiment("MSFT")
    second = provider.fetch_company_sentiment("MSFT")

    assert first["sentiment_data_status"] == "demo"
    assert first["companyNewsScore"] == second["companyNewsScore"]
    assert first["articlesInLastWeek"] == second["articlesInLastWeek"]


def test_sector_aggregation_handles_missing_company_sentiment():
    result = aggregate_sector_sentiment("Technology", ["AAPL", "MSFT"], provider=MissingSentimentProvider())

    assert result["sentiment_data_status"] == "missing"
    assert result["sentiment_coverage_count"] == 0
    assert result["sentiment_article_count"] == 0


def test_sentiment_columns_can_be_merged_into_feature_frame():
    sentiment = aggregate_sector_sentiment("Technology", ["AAPL", "MSFT"], provider=DemoSentimentProvider())
    row = {
        "sector": "Technology",
        "ticker": "XLK",
        "momentum_21": .1,
        "momentum_63": .2,
        "momentum_126": .3,
        "volatility_20": .2,
        "downside_volatility_20": .1,
        "drawdown_current": -.05,
        "distance_to_ma_200": .1,
        "risk_adjusted_return_63": 1,
        "volume_momentum_20": 1.1,
        "trailingPE": 20,
        "priceToBook": 2,
        "dividendYield": .02,
        "marketCap": 1e9,
        "trend_latest": 50,
        "trend_data_status": "cache",
        "price_data_status": "live",
        "market_last_date": pd.Timestamp.today().strftime("%Y-%m-%d"),
        "operating_mode": "full",
        **sentiment,
    }

    frame = pd.DataFrame([row])

    assert "sentiment_score_component" in frame.columns
    assert frame["sentiment_data_status"].iloc[0] == "demo"
    assert assess_data_readiness(frame.iloc[0]) == "Ready for ML inference"


def test_market_fundamental_mode_works_without_sentiment():
    row = {
        "sector": "Utilities",
        "ticker": "XLU",
        "momentum_21": .1,
        "momentum_63": .2,
        "momentum_126": .3,
        "volatility_20": .2,
        "downside_volatility_20": .1,
        "drawdown_current": -.05,
        "distance_to_ma_200": .1,
        "risk_adjusted_return_63": 1,
        "volume_momentum_20": 1.1,
        "trailingPE": 20,
        "priceToBook": 2,
        "dividendYield": .02,
        "marketCap": 1e9,
        "trend_latest": pd.NA,
        "trend_data_status": "not_used",
        "price_data_status": "live",
        "market_last_date": pd.Timestamp.today().strftime("%Y-%m-%d"),
        "operating_mode": "market_fundamental",
        **sentiment_not_used_features(),
    }

    frame = pd.DataFrame([row])

    assert frame["sentiment_data_status"].iloc[0] == "not_used"
    assert assess_data_readiness(frame.iloc[0]) == "Ready for ML inference"
