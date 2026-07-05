from datetime import datetime, timedelta, timezone
import json

import pandas as pd
from src import trends_loader
from src.trends_loader import calculate_trend_features, generate_demo_trends


def test_demo_trends_are_weekly_and_bounded():
    data = generate_demo_trends("Technology", periods=260)
    assert len(data) == 260
    assert data["value"].between(0, 100).all()
    assert data["date"].diff().dropna().dt.days.eq(7).all()


def test_demo_trend_features_have_observations():
    features = calculate_trend_features(generate_demo_trends("Energy"))
    assert features["trend_observations"] > 0
    assert features["trend_last_date"]


def test_demo_data_produces_ml_trend_feature_columns():
    features = calculate_trend_features(generate_demo_trends("Technology"))
    assert {"trend_z_score_12w", "trend_z_score_52w", "trend_momentum_4w", "trend_percentile_52w"}.issubset(features)


def test_cache_freshness_and_age_use_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(trends_loader, "RAW_DATA_DIR", tmp_path / "raw")
    frame = pd.DataFrame({"date": pd.date_range("2026-01-01", periods=4, freq="W-MON"), "sector": "Technology", "value": [10, 20, 30, 40]})
    trends_loader.save_trends_cache(frame, "Technology", keywords=["ai"], source="live")

    metadata_path = trends_loader._metadata_path("Technology")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["created_at"] = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    assert 1.5 <= trends_loader.trend_cache_age_hours("Technology") <= 2.5
    assert trends_loader.is_cache_fresh("Technology", max_age_hours=3)
    assert not trends_loader.is_cache_fresh("Technology", max_age_hours=1)


def test_demo_only_mode_never_calls_live(tmp_path, monkeypatch):
    monkeypatch.setattr(trends_loader, "RAW_DATA_DIR", tmp_path / "raw")
    monkeypatch.setattr(trends_loader, "DEMO_DATA_DIR", tmp_path / "demo")

    def fail_live(*args, **kwargs):
        raise AssertionError("live Google Trends should not be called in demo_only mode")

    monkeypatch.setattr(trends_loader, "load_sector_trends_live", fail_live)
    data, status, metadata = trends_loader.get_trends_with_cache_or_demo("Technology", ["ai"], refresh_mode="demo_only", return_status=True, return_metadata=True)

    assert status == "demo"
    assert not data.empty
    assert metadata["trend_refresh_mode"] == "demo_only"
    assert pd.isna(metadata["trend_cache_age_hours"])


def test_cache_only_uses_cache_or_demo_without_live(tmp_path, monkeypatch):
    monkeypatch.setattr(trends_loader, "RAW_DATA_DIR", tmp_path / "raw")
    monkeypatch.setattr(trends_loader, "DEMO_DATA_DIR", tmp_path / "demo")

    def fail_live(*args, **kwargs):
        raise AssertionError("live Google Trends should not be called in cache_only mode")

    monkeypatch.setattr(trends_loader, "load_sector_trends_live", fail_live)
    frame = pd.DataFrame({"date": pd.date_range("2026-01-01", periods=4, freq="W-MON"), "sector": "Technology", "value": [10, 20, 30, 40]})
    trends_loader.save_trends_cache(frame, "Technology", keywords=["ai"], source="live")

    cached, cached_status, cached_metadata = trends_loader.get_trends_with_cache_or_demo("Technology", ["ai"], refresh_mode="cache_only", return_status=True, return_metadata=True)
    demo, demo_status, _ = trends_loader.get_trends_with_cache_or_demo("Energy", ["oil"], refresh_mode="cache_only", return_status=True, return_metadata=True)

    assert cached_status == "cache"
    assert len(cached) == 4
    assert cached_metadata["trend_refresh_mode"] == "cache_only"
    assert pd.notna(cached_metadata["trend_cache_age_hours"])
    assert demo_status == "demo"
    assert not demo.empty


def test_metadata_json_creation(tmp_path, monkeypatch):
    monkeypatch.setattr(trends_loader, "RAW_DATA_DIR", tmp_path / "raw")
    frame = pd.DataFrame({"date": pd.date_range("2026-01-01", periods=2, freq="W-MON"), "sector": "Utilities", "value": [55, 60]})
    trends_loader.save_trends_cache(frame, "Utilities", keywords=["utility stocks"], timeframe="today 12-m", geo="US", source="live")

    metadata = trends_loader.load_trends_metadata("Utilities")
    assert metadata["sector"] == "Utilities"
    assert metadata["keywords"] == ["utility stocks"]
    assert metadata["source"] == "live"
    assert metadata["timeframe"] == "today 12-m"
    assert metadata["geo"] == "US"
    assert metadata["observations"] == 2
    assert metadata["last_date"] == "2026-01-12"
