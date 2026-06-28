import pandas as pd
import numpy as np

from src.ml_dataset import TREND_FEATURE_COLUMNS, add_forward_return_targets, build_historical_feature_dataset, calculate_historical_sector_features


def _prices(start="2024-01-01", periods=80, base=100, step=1.0):
    dates = pd.bdate_range(start=start, periods=periods)
    close = pd.Series(base + step * np.arange(periods), index=dates)
    return pd.DataFrame({"Open": close, "High": close * 1.01, "Low": close * .99, "Close": close, "Adj Close": close, "Volume": 1_000_000}, index=dates)


def test_forward_targets_use_future_returns_without_future_features():
    frame = pd.DataFrame({
        "date": pd.bdate_range("2024-01-01", periods=6),
        "sector": ["Technology"] * 6,
        "ticker": ["XLK"] * 6,
        "sector_forward_base_close": [100, 102, 104, 106, 108, 110],
        "spy_forward_base_close": [100, 101, 102, 103, 104, 105],
    })

    result = add_forward_return_targets(frame, horizon_days=2)

    first = result.iloc[0]
    assert first["date"] == pd.Timestamp("2024-01-01")
    assert round(first["sector_forward_return_4w"], 4) == .04
    assert round(first["spy_forward_return_4w"], 4) == .02
    assert round(first["target_excess_return_4w"], 4) == .02


def test_historical_sector_features_include_relative_strength():
    features = calculate_historical_sector_features("Technology", "XLK", _prices(step=1.5), _prices(step=1.0))

    assert {"relative_strength_vs_spy_63", "relative_strength_vs_spy_126", "momentum_21"}.issubset(features.columns)
    assert features["sector"].eq("Technology").all()


def test_market_fundamental_dataset_does_not_require_trend_features(monkeypatch):
    import src.ml_dataset as module

    monkeypatch.setattr(module, "_download_ohlcv", lambda ticker, start="2018-01-01", end=None: _prices(periods=260, step=1.2 if ticker != "SPY" else 1.0))
    dataset = build_historical_feature_dataset(feature_set="market_fundamental", use_demo_market_fallback=False)

    assert not dataset.empty
    assert dataset["feature_set"].eq("market_fundamental").all()
    assert dataset["trend_data_status"].eq("not_used").all()
    assert not set(TREND_FEATURE_COLUMNS).intersection(dataset.columns)
