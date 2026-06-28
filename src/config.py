"""Central configuration for the educational sector-monitoring prototype."""

from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # keep imports robust if optional dev dependencies are missing
    load_dotenv = None

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_ENV_PATH = PROJECT_ROOT / "config" / ".env"
ROOT_ENV_PATH = PROJECT_ROOT / ".env"

if load_dotenv is not None:
    load_dotenv(ROOT_ENV_PATH, override=False)
    load_dotenv(CONFIG_ENV_PATH, override=False)

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
RAW_SENTIMENT_DIR = RAW_DATA_DIR / "sentiment"
DEMO_DATA_DIR = DATA_DIR / "demo"
EXTERNAL_DATA_DIR = DATA_DIR / "external"
MANUAL_TRENDS_DIR = EXTERNAL_DATA_DIR / "google_trends_manual"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"
MODELS_DIR = PROJECT_ROOT / "models"
HTML_REPORT_PATH = REPORTS_DIR / "html" / "sector_monitoring_report.html"
RANKING_PATH = PROCESSED_DATA_DIR / "recommendation_scores.csv"
BACKTEST_RESULTS_PATH = PROCESSED_DATA_DIR / "backtest_results.csv"
BACKTEST_METRICS_PATH = PROCESSED_DATA_DIR / "backtest_metrics.csv"
ML_TRAINING_DATASET_PATH = PROCESSED_DATA_DIR / "ml_training_dataset.csv"
ML_PREDICTIONS_PATH = PROCESSED_DATA_DIR / "ml_predictions.csv"
ML_EVALUATION_METRICS_PATH = PROCESSED_DATA_DIR / "ml_evaluation_metrics.csv"
ML_BACKTEST_RESULTS_PATH = PROCESSED_DATA_DIR / "ml_backtest_results.csv"
ML_BACKTEST_METRICS_PATH = PROCESSED_DATA_DIR / "ml_backtest_metrics.csv"
ML_FEATURE_IMPORTANCE_PATH = PROCESSED_DATA_DIR / "ml_feature_importance.csv"
MODEL_PATH = MODELS_DIR / "sector_model.pkl"
FEATURE_COLUMNS_PATH = MODELS_DIR / "feature_columns.json"
MODEL_METADATA_PATH = MODELS_DIR / "model_metadata.json"

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

SENTIMENT_ENABLED = False
SENTIMENT_PROVIDER = "finnhub"
FINNHUB_API_KEY_ENV = "FINNHUB_API_KEY"
SENTIMENT_CACHE_MAX_AGE_HOURS = 24
SECTOR_REPRESENTATIVE_TICKERS = {
    "Technology": ["AAPL", "MSFT", "NVDA", "AMD", "AVGO"],
    "Healthcare": ["UNH", "JNJ", "LLY", "PFE", "MRK"],
    "Financials": ["JPM", "BAC", "WFC", "GS", "MS"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "EOG"],
    "Consumer Discretionary": ["AMZN", "TSLA", "HD", "MCD", "NKE"],
    "Industrials": ["CAT", "BA", "GE", "HON", "UPS"],
    "Utilities": ["NEE", "DUK", "SO", "AEP", "EXC"],
    "Materials": ["LIN", "SHW", "FCX", "NEM", "APD"],
    "Real Estate": ["PLD", "AMT", "EQIX", "SPG", "O"],
    "Consumer Staples": ["PG", "KO", "PEP", "WMT", "COST"],
}

SCORING_WEIGHTS = {"trend_score": 0.40, "momentum_score": 0.25, "fundamental_score": 0.20, "risk_score": 0.15}
SCORING_WEIGHTS_BY_MODE = {
    "full": {"trend_score": 0.40, "momentum_score": 0.25, "fundamental_score": 0.20, "risk_score": 0.15},
    "market_fundamental": {"trend_score": 0.0, "momentum_score": 0.40, "fundamental_score": 0.30, "risk_score": 0.30},
    "demo": {"trend_score": 0.40, "momentum_score": 0.25, "fundamental_score": 0.20, "risk_score": 0.15},
}
SCORING_PROFILE_BY_MODE = {
    "full": "full_trend_market_fundamental",
    "market_fundamental": "market_fundamental_only",
    "demo": "demo_trend_market_fundamental",
}
OPERATING_MODE = "market_fundamental"
ALLOWED_OPERATING_MODES = {"full", "market_fundamental", "demo"}
DEFAULT_MARKET_PERIOD = "5y"
DEFAULT_TREND_TIMEFRAME = "today 5-y"
DEFAULT_TREND_GEO = "US"
TREND_REFRESH_MODE = "auto"  # Allowed: auto, cache_only, force_live, demo_only.
TREND_CACHE_MAX_AGE_HOURS = 168
GOOGLE_TRENDS_MIN_SLEEP_SECONDS = 30
GOOGLE_TRENDS_MAX_SLEEP_SECONDS = 90
TREND_PROVIDER_ORDER = ["manual_csv", "external_api", "pytrends", "cache", "demo"]
SCORING_MODE = "research"  # Allowed values: "demo" and "research".
DATA_FRESHNESS_DAYS = 14
DISCLAIMER = "Decision support only. No autonomous trading. Not financial advice."


def ensure_directories() -> None:
    """Create output folders used by the pipeline."""
    for directory in (RAW_DATA_DIR, RAW_SENTIMENT_DIR, DEMO_DATA_DIR, MANUAL_TRENDS_DIR, PROCESSED_DATA_DIR, MODELS_DIR, HTML_REPORT_PATH.parent):
        directory.mkdir(parents=True, exist_ok=True)
