import pandas as pd

from src.trend_providers import DemoTrendProvider, ManualCSVTrendProvider


def test_manual_csv_provider_loads_google_trends_export(tmp_path):
    manual_dir = tmp_path / "google_trends_manual"
    manual_dir.mkdir()
    csv_path = manual_dir / "google_trends_manual_Technology.csv"
    csv_path.write_text(
        "Category: All categories\n\nWeek,artificial intelligence,semiconductors,isPartial\n2024-01-01,10,20,false\n2024-01-08,<1,30,false\n",
        encoding="utf-8",
    )

    data, metadata = ManualCSVTrendProvider(directory=manual_dir).fetch_sector_trends("Technology", ["artificial intelligence", "semiconductors"], "today 5-y", "US")

    assert metadata["trend_data_status"] == "manual_csv"
    assert metadata["provider"] == "manual_csv"
    assert metadata["observations"] == 2
    assert metadata["last_date"] == "2024-01-08"
    assert list(data.columns) == ["date", "sector", "value"]
    assert data["sector"].eq("Technology").all()
    assert data["value"].iloc[0] == 15


def test_demo_provider_returns_valid_synthetic_data():
    data, metadata = DemoTrendProvider(periods=20).fetch_sector_trends("Energy", ["oil price"], "today 5-y", "US")

    assert metadata["trend_data_status"] == "demo"
    assert len(data) == 20
    assert data["value"].between(0, 100).all()
    assert pd.to_datetime(data["date"]).is_monotonic_increasing
