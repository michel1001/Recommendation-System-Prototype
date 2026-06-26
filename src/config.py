"""Central configuration for the educational sector-monitoring prototype."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
DEMO_DATA_DIR = DATA_DIR / "demo"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"
HTML_REPORT_PATH = REPORTS_DIR / "html" / "sector_monitoring_report.html"
RANKING_PATH = PROCESSED_DATA_DIR / "recommendation_scores.csv"
BACKTEST_RESULTS_PATH = PROCESSED_DATA_DIR / "backtest_results.csv"
BACKTEST_METRICS_PATH = PROCESSED_DATA_DIR / "backtest_metrics.csv"

SECTOR_ETFS = {
    "Technology": "XLK", "Healthcare": "XLV", "Financials": "XLF",
    "Energy": "XLE", "Consumer Discretionary": "XLY", "Industrials": "XLI",
    "Utilities": "XLU", "Materials": "XLB", "Real Estate": "XLRE",
    "Consumer Staples": "XLP",
}

TREND_KEYWORDS = {
    "Technology": ["artificial intelligence", "semiconductors", "cloud computing"],
    "Healthcare": ["healthcare stocks", "biotech", "pharma"],
    "Financials": ["bank stocks", "interest rates", "financial sector"],
    "Energy": ["oil price", "energy stocks", "natural gas"],
    "Consumer Discretionary": ["retail sales", "consumer spending", "ecommerce"],
    "Industrials": ["manufacturing", "industrial stocks", "infrastructure"],
    "Utilities": ["electricity prices", "utility stocks", "renewable energy"],
    "Materials": ["commodity prices", "mining stocks", "raw materials"],
    "Real Estate": ["real estate market", "REIT", "mortgage rates"],
    "Consumer Staples": ["food prices", "consumer staples", "grocery prices"],
}

SCORING_WEIGHTS = {"trend_score": 0.40, "momentum_score": 0.25, "fundamental_score": 0.20, "risk_score": 0.15}
DEFAULT_MARKET_PERIOD = "5y"
DEFAULT_TREND_TIMEFRAME = "today 5-y"
DEFAULT_TREND_GEO = "US"
TREND_REFRESH_MODE = "auto"  # Allowed: auto, cache_only, force_live, demo_only.
TREND_CACHE_MAX_AGE_HOURS = 168
GOOGLE_TRENDS_MIN_SLEEP_SECONDS = 30
GOOGLE_TRENDS_MAX_SLEEP_SECONDS = 90
SCORING_MODE = "research"  # Allowed values: "demo" and "research".
DATA_FRESHNESS_DAYS = 14
DISCLAIMER = "Decision support only. No autonomous trading. Not financial advice."


def ensure_directories() -> None:
    """Create output folders used by the pipeline."""
    for directory in (RAW_DATA_DIR, DEMO_DATA_DIR, PROCESSED_DATA_DIR, HTML_REPORT_PATH.parent):
        directory.mkdir(parents=True, exist_ok=True)
