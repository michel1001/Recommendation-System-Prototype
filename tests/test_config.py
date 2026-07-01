from src.config import SECTOR_ETFS, SECTOR_REPRESENTATIVE_TICKERS, TREND_KEYWORDS


def test_sector_universe_includes_all_standard_gics_sectors():
    assert len(SECTOR_ETFS) == 11
    assert SECTOR_ETFS["Communication Services"] == "XLC"
    assert set(SECTOR_ETFS) == set(TREND_KEYWORDS) == set(SECTOR_REPRESENTATIVE_TICKERS)
