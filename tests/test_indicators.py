import numpy as np
import pandas as pd

from src.indicators import calculate_drawdowns, calculate_momentum, calculate_returns, calculate_volatility, enrich_market_indicators


def sample_data():
    index = pd.date_range("2023-01-01", periods=260, freq="B")
    return pd.DataFrame({"close": np.linspace(100, 150, 260), "volume": 1000}, index=index)


def test_returns_momentum_volatility_and_drawdown():
    data = sample_data()
    assert calculate_returns(data)["daily_return"].notna().any()
    assert calculate_momentum(data)["momentum_21"].notna().any()
    assert calculate_volatility(calculate_returns(data))["volatility_20"].notna().any()
    assert calculate_drawdowns(calculate_returns(data))["drawdown_current"].notna().any()


def test_enriched_indicators_are_not_all_empty():
    enriched = enrich_market_indicators(sample_data())
    assert not enriched[["momentum_21", "momentum_63", "momentum_126", "volatility_20", "drawdown_current"]].isna().all().any()
