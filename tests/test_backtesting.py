import numpy as np
import pandas as pd

from src.backtesting import calculate_historical_features, calculate_performance_metrics, rank_sectors_historically, run_monthly_rotation_backtest


def synthetic_prices():
    index = pd.date_range("2020-01-01", periods=400, freq="B")
    return pd.DataFrame({"AAA": np.linspace(100, 160, len(index)), "BBB": np.linspace(100, 130, len(index)) + np.sin(np.arange(len(index))), "CCC": np.linspace(100, 90, len(index))}, index=index)


def test_performance_metrics_keys_and_drawdown():
    metrics = calculate_performance_metrics(pd.Series([.02, -.03, .01]))
    assert {"cumulative_return", "annualized_return", "max_drawdown", "win_rate"}.issubset(metrics)
    assert metrics["max_drawdown"] <= 0


def test_historical_features_do_not_use_future_data():
    prices = synthetic_prices()
    as_of = prices.index[250]
    baseline = calculate_historical_features(prices, as_of)
    altered = prices.copy(); altered.loc[as_of + pd.Timedelta(days=1):, "AAA"] *= 100
    pd.testing.assert_frame_equal(baseline, calculate_historical_features(altered, as_of))


def test_ranking_and_backtest_structure():
    prices = synthetic_prices()
    ranked = rank_sectors_historically(calculate_historical_features(prices, prices.index[300]))
    assert not ranked.empty and "market_score" in ranked
    results = run_monthly_rotation_backtest(top_n=2, start="2020-01-01", prices=prices, benchmark_prices=prices["AAA"])
    assert {"results", "metrics"}.issubset(results)
    assert {"portfolio_return", "spy_return"}.issubset(results["results"].columns)
