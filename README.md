Next Steps:
-> aus dem Dashboard nur die Management Sachen anzeigen, nochmal Dashboarding Papers anschauen.
-> Daten in Datenbank überführen, Trends Daten auch in die Datenbank
-> 10 Jahre Daten
-> für jeden Sektor einen Wert bestimmen für die Trends
-> Im Dashboard für jeden Sektor noch 3 Aktien die in letzter Zeit gestiegen sind.


# Recommendation-System-Prototype

AI-powered sector monitoring prototype using Google Trends, market data, fundamentals, and explainable scoring.

## Disclaimer

This project is for educational and research purposes only. It does not constitute financial advice, investment advice, or a recommendation to buy or sell any financial instrument. The system is a decision-support prototype and does not execute trades.

## Project Context

This prototype was developed as part of a university AI consulting project: *Konzeption eines KI-gestuetzten Sektor-Monitorings am Kapitalmarkt: Synergieanalyse von Google Trends und Fundamentaldaten zur Renditeoptimierung*.

The use case assumes a fictional bank or asset manager that wants to support its research team with AI-based sector monitoring. The focus is sector-level monitoring, not direct automated trading. Google Trends is used as an investor-attention proxy and is combined with sector ETF market data and fundamental indicators to provide analysts with a structured, explainable sector ranking.

## Current Implementation Status

The current prototype includes:

- Automated end-to-end pipeline in `src/pipeline.py`.
- An eleven-sector ETF universe aligned with the standard GICS sectors.
- Google Trends loading with a live/cache/demo/fallback strategy.
- Explicit Google Trends refresh modes: `auto`, `cache_only`, `force_live`, and `demo_only`.
- Provider-based trend architecture with manual CSV, external API placeholder, pytrends, cache, and demo providers.
- A supervised ML research layer that trains sector outperformance models using historical engineered features.
- Reproducible demo Google Trends data when live access is unavailable.
- Market and fundamental data loading through `yfinance`.
- Technical indicators: momentum, volatility, downside volatility, drawdown, moving averages, distance to the 200-day moving average, and volume momentum.
- Google Trends indicators: latest value, 4-week and 12-week momentum, 12-week and 52-week z-scores, spike detection, acceleration, volatility, and percentile.
- Explainable trend, momentum, risk, fundamental, synergy, and confidence scores.
- Recommendation labels: `Research Candidate`, `Watch`, `Neutral`, `Avoid`, `Research Prototype`, and `Insufficient Data`.
- HTML management report generation and a Streamlit dashboard.
- Output verification and a pytest test suite.
- Data-quality and actionability gates that prevent demo or missing data from producing investment-like recommendations.
- A market-only monthly sector-rotation backtesting framework; Google Trends history is not yet part of the backtest.

Current validation command: run `python -m pytest` for the latest result.

Dashboard command:

```bash
python -m streamlit run app/app.py
```

The dashboard now opens in a management-oriented default view with overview, sector details, data quality, and validation tabs. Technical diagnostics such as database row counts, detailed ranking fields, ML metrics, and feature importance can be enabled with the sidebar toggle `Show technical diagnostics`.

## Repository Structure

```text
Recommendation-System-Prototype/
|-- app/
|   `-- app.py
|-- data/
|   |-- raw/
|   |-- processed/
|   |-- demo/
|   |-- external/
|   |   `-- google_trends_manual/
|   `-- reports/
|-- models/
|   |-- sector_model.pkl
|   `-- feature_columns.json
|-- reports/
|   |-- html/
|   `-- figures/
|-- src/
|   |-- config.py
|   |-- data_loader.py
|   |-- trends_loader.py
|   |-- trend_providers.py
|   |-- ml_dataset.py
|   |-- ml_model.py
|   |-- ml_evaluation.py
|   |-- preprocessing.py
|   |-- indicators.py
|   |-- scoring.py
|   |-- report_generator.py
|   |-- pipeline.py
|   |-- refresh_trends.py
|   |-- backtesting.py
|   `-- verify_outputs.py
|-- tests/
|   |-- test_indicators.py
|   |-- test_scoring.py
|   |-- test_trends_loader.py
|   |-- test_backtesting.py
|   `-- test_pipeline_outputs.py
|-- requirements.txt
|-- README.md
`-- .gitignore
```

## Data Sources

Current data sources are:

- `yfinance` for sector ETF market data.
- `yfinance` for simple fundamental fields where they are available for ETFs.
- `pytrends` for live Google Trends requests.
- Local cached data or synthetic demo trend data if live Google Trends requests fail.

Live Google Trends access can fail because of rate limits or API restrictions. In that case, the prototype uses clearly flagged synthetic demo data. Demo data is used only to validate and demonstrate the pipeline; it must not be interpreted as real investor attention.

Current external-data status:

- The stable default workflow is `market_fundamental`; it does not require Google Trends or Finnhub sentiment.
- Google Trends live access through `pytrends` is unreliable and may return rate limits or blocking responses.
- Finnhub news sentiment is optional. In current testing, the Finnhub key loaded correctly, but the news-sentiment endpoint returned HTTP 403 / `invalid_api_key`, which likely indicates an account, plan, endpoint, or key-permission issue.
- The project handles these failures without crashing and labels unusable source data explicitly.

## Google Trends Rate Limits and Refresh Modes

Google Trends may return HTTP 429 because `pytrends` uses unofficial web requests. To avoid unnecessary live calls, the prototype supports explicit refresh modes:

- `auto`: use fresh cache first; if cache is stale or missing, try live Google Trends; if live fails, use demo data.
- `cache_only`: never call Google live; use local cache if available, otherwise demo data.
- `force_live`: try live Google Trends first; if live fails, use cache if available, otherwise demo data.
- `demo_only`: never call Google live or cache; always use synthetic demo data.

Normal pipeline:

```bash
python src/pipeline.py --mode full --trend-mode auto
```

Demo-safe pipeline:

```bash
python src/pipeline.py --mode demo
```

Cache-only pipeline:

```bash
python src/pipeline.py --trend-mode cache_only
```

Force live refresh during a pipeline run:

```bash
python src/pipeline.py --trend-mode force_live
```

Refresh trend cache separately:

```bash
python src/refresh_trends.py --all
```

Run dashboard:

```bash
python -m streamlit run app/app.py
```

Each run writes `trend_data_status`, `trend_refresh_mode`, and `trend_cache_age_hours` to the output CSV so analysts can see whether a sector used live, cached, demo, or fallback trend input.

## Operating Modes

### Market/Fundamental Mode

Default mode. Uses ETF market data and available fundamental data only. Google Trends are not used in scoring. This is the most reliable mode when no real trend data is available.

```bash
python src/pipeline.py --mode market_fundamental
```

### Full Mode

Uses Google Trends if real manual/cache/live/API data is available, plus market and fundamental data.

```bash
python src/pipeline.py --mode full
```

### Demo Mode

Uses synthetic Google Trends data to demonstrate the full dashboard logic. Outputs are prototype-only and not actionable.

```bash
python src/pipeline.py --mode demo
```

## Real Google Trends Data Options

The prototype no longer depends on only `pytrends`. It uses a provider-based architecture:

- `manual_csv`: real Google Trends data exported manually from the Google Trends website.
- `external_api`: placeholder for future providers such as SerpApi, DataForSEO, or an official Google Trends API.
- `live_pytrends`: real Google Trends data requested through pytrends; this may fail with HTTP 429 rate limits.
- `cache`: previously loaded real trend data from `data/raw/`.
- `demo`: synthetic prototype data used only when real data is unavailable or intentionally selected.

Manual CSV is preferred because it avoids pytrends rate limiting while still allowing real Google Trends data in a university prototype.

## Local SQLite Database

The prototype can store historical market data, fundamentals, imported Google Trends data, indicators, and scoring outputs in a local SQLite database.

Database path:

```text
data/database/sector_monitoring.db
```

Create or refresh the market database:

```bash
python src/refresh_market_data.py --period 5y
```

Import manual Google Trends CSV data:

```bash
python src/import_trends_csv.py --file data/external/google_trends_manual/google_trends_manual_Technology.csv --sector Technology --geo US --timeframe "today 5-y"
```

Run the pipeline from SQLite:

```bash
python src/pipeline.py --mode market_fundamental --data-source db
```

Run the pipeline live and save inputs/results to SQLite:

```bash
python src/pipeline.py --mode market_fundamental --data-source live --save-to-db
```

Verify the database:

```bash
python src/verify_database.py
```

## Data Quality Report

The project includes a database-level data quality report for CRISP-DM Data Understanding and Data Preparation. It reads only from the local SQLite database and creates Markdown plus CSV summaries.

```bash
python src/data_quality_report.py
```

Outputs:

- `reports/data_quality/data_quality_summary.md`
- `reports/data_quality/table_row_counts.csv`
- `reports/data_quality/missing_values_summary.csv`
- `reports/data_quality/sector_coverage_summary.csv`
- `reports/data_quality/date_coverage_summary.csv`
- `reports/data_quality/fundamentals_quality_summary.csv`
- `reports/data_quality/google_trends_quality_summary.csv`

## How to add real Google Trends data manually

1. Go to Google Trends in the browser.
2. Search the sector keywords, for example `artificial intelligence`, `semiconductors`, and `cloud computing` for Technology.
3. Set the same region and timeframe used by the project, for example United States and `today 5-y`.
4. Download the CSV from Google Trends.
5. Save it with this pattern:

```text
data/external/google_trends_manual/google_trends_manual_Technology.csv
```

6. Run the pipeline:

```bash
python src/pipeline.py --mode full --trend-mode auto
```

Manual CSV data is real Google Trends data, unlike demo data. However, keyword choices, timeframe, geography, and export date must be documented consistently.

## Optional News/Social Sentiment Module

The prototype includes an optional news/social sentiment module for future sector-enrichment work. It can use Finnhub company-level news sentiment and aggregate representative company tickers into sector-level features.

Important caveats:

- Finnhub sentiment is an external vendor signal.
- The exact Finnhub scoring methodology is not fully transparent.
- Sentiment is treated as supporting alternative data, not as a standalone investment signal.
- The module is optional and disabled by default.
- It requires a `FINNHUB_API_KEY`.

Representative company sentiment is aggregated into fields such as `sentiment_score_component`, `sentiment_bullish_percent`, `sentiment_bearish_percent`, `sentiment_buzz`, and `sentiment_article_count`.

The project automatically loads environment variables from `config/.env` and `.env` if those files exist. A variable already set in PowerShell takes priority.

`config/.env` example:

```text
FINNHUB_API_KEY=your_key_here
```

PowerShell setup alternative:

```powershell
$env:FINNHUB_API_KEY="your_key_here"
python src/pipeline.py --mode full --use-sentiment
```

Without sentiment, use the stable default workflow:

```bash
python src/pipeline.py --mode market_fundamental
```

If `--use-sentiment` is requested without an API key, the pipeline does not crash. It marks sentiment as `disabled_no_api_key` and explains the missing key in the console, dashboard, and report.

## External Source Debug Scripts

The repository includes small standalone scripts to debug external data access without running the full scoring pipeline. These scripts are useful for team members who want to check whether the source itself works before debugging scoring, dashboard, or ML logic.

Debug Google Trends / pytrends:

```bash
python scripts/debug_google_trends.py --sector Technology
```

Optional explicit keywords:

```bash
python scripts/debug_google_trends.py --sector Technology --keywords "artificial intelligence" semiconductors "cloud computing"
```

If this returns no rows or an error, the likely cause is Google/pytrends rate limiting or blocking. This is expected behavior for unofficial Google Trends access.

Debug Finnhub news sentiment:

```bash
python scripts/debug_finnhub_sentiment.py --ticker AAPL
```

Debug one sector aggregation:

```bash
python scripts/debug_finnhub_sentiment.py --sector Technology
```

Clear cached Finnhub responses before testing:

```bash
python scripts/debug_finnhub_sentiment.py --ticker AAPL --clear-cache
```

The Finnhub debug script does not print the API key. It only prints whether a key is loaded, the key length, and a short hash fingerprint for comparing local setups safely.

Typical Finnhub statuses:

- `live`: Finnhub returned usable sentiment data.
- `cache`: cached usable sentiment data was loaded.
- `disabled_no_api_key`: no `FINNHUB_API_KEY` was loaded.
- `invalid_api_key`: Finnhub returned HTTP 401/403 or an invalid-key style response.
- `rate_limited`: Finnhub rate limit was reached.
- `no_data`: Finnhub responded, but no usable sentiment fields were present.
- `missing`: no valid company sentiment could be aggregated.

## AI / ML Component

The rule-based score remains the transparent baseline. It is not a trained AI prediction; it is a weighted, explainable scoring framework.

The ML layer is the actual supervised AI research component. It trains models on historical sector-date features and predicts:

- `ml_predicted_outperform_probability`: probability that a sector outperforms SPY over the next 4 weeks.
- `ml_predicted_excess_return_4w`: expected 4-week sector return minus SPY return.

Implemented model families:

- Classification: Logistic Regression and Random Forest Classifier.
- Regression: Ridge and Random Forest Regressor.

The ML workflow uses a time-based train/test split, not a random split, to reduce time-series leakage.

## ML Training Workflow

Recommended market/fundamental ML workflow:

```bash
python src/pipeline.py --mode market_fundamental
python src/ml_dataset.py --feature-set market_fundamental
python src/ml_model.py
python src/ml_evaluation.py
python src/pipeline.py --mode market_fundamental --use-ml
python src/verify_outputs.py
python -m pytest
python -m streamlit run app/app.py
```

Presentation-safe workflow:

```bash
python src/pipeline.py --mode demo
python src/ml_dataset.py --feature-set full
python src/ml_model.py
python src/ml_evaluation.py
python src/pipeline.py --mode demo --use-ml
python -m streamlit run app/app.py
```

Outputs:

- `data/processed/ml_training_dataset.csv`
- `data/processed/ml_predictions.csv`
- `data/processed/ml_evaluation_metrics.csv`
- `data/processed/ml_backtest_results.csv`
- `data/processed/ml_backtest_metrics.csv`
- `data/processed/ml_feature_importance.csv`
- `models/sector_model.pkl`
- `models/feature_columns.json`
- `models/model_metadata.json`

## Difference Between Rule-Based Score and ML Prediction

- Rule-based score: transparent weighted baseline combining trend, momentum, risk, and fundamental features.
- ML prediction: supervised model output trained on historical features and forward 4-week SPY-relative outcomes.

Both remain decision-support research signals. Neither is a buy/sell recommendation.

## Limitations and Data Leakage Warning

The ML model is only meaningful when trained on real historical data. If the dataset uses synthetic demo trend data, ML outputs are marked prototype-only and should not be interpreted as investment-grade evidence.

The dataset builder avoids direct look-ahead bias by using current/past features and future returns only as targets. Current ETF fundamentals from yfinance are not treated as point-in-time historical fundamentals by default, because that could introduce look-ahead bias.

## Google Trends Data Status

The `trend_data_status` field appears in the output CSV, dashboard, and report.

- `live`: real Google Trends data loaded from the current API request.
- `cache`: previously loaded Google Trends data from the local CSV cache.
- `demo`: synthetic prototype data used when live Google Trends is unavailable.
- `fallback`: neutral placeholder used only if no trend time series is available; this is the weakest data-quality state.

## Research Signal Status

`data_quality_status` describes whether the inputs are usable for research: `Live research signal`, `Cached research signal`, `Prototype only`, `Insufficient data`, or `Stale data`. `actionability_status` then limits interpretation to `Not actionable`, `Research only`, `Suitable for analyst review`, or `Validated research candidate`.

Demo trend inputs are always marked `Prototype only` and `Not actionable`; their recommendation label is capped at `Research Prototype`. A usable research signal requires live or cached data, freshness checks, historical validation, and human analyst review.

## Methodology

The total score combines four sector-relative components:

| Component | Weight | Purpose |
| --- | ---: | --- |
| Google Trends / attention score | 40% | Measures relative investor-attention signals. |
| Market momentum score | 25% | Summarises price momentum and risk-adjusted return. |
| Fundamental score | 20% | Adds available ETF valuation, income, size, and beta context. |
| Risk score | 15% | Considers volatility, downside volatility, drawdown, and beta. |

Google Trends receives the highest weight because investor attention and sector monitoring are the core research focus. Market and fundamental data act as validation and risk filters. The synergy score checks whether Google Trends, momentum, fundamentals, and risk tell a consistent story.

The output is intended to support human research workflows. Analysts should review source status, data limitations, and external evidence before drawing conclusions.

## Output Files

After running the pipeline, the prototype creates:

- `data/processed/recommendation_scores.csv` - complete explainable sector ranking.
- `reports/html/sector_monitoring_report.html` - HTML management report.

The Streamlit dashboard reads the processed CSV.

## Installation and Usage

Create and activate a virtual environment, then install the required packages:

```bash
python -m venv venv
```

Windows PowerShell:

```powershell
venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source venv/bin/activate
```

Install dependencies and run the prototype:

```bash
pip install -r requirements.txt
python src/pipeline.py --mode market_fundamental
python src/verify_outputs.py
python -m pytest
python -m streamlit run app/app.py
python src/backtesting.py
```

## Demo Mode

Due to Google Trends rate limits, the prototype may use synthetic demo data. This is clearly flagged through `trend_data_status` and is intended only to demonstrate the pipeline and scoring logic.

## Backtesting

`python src/backtesting.py` runs a market-only monthly sector-rotation backtest. It ranks sectors using historical momentum, volatility, drawdown, and risk-adjusted return, then compares the following month's selected-sector return against SPY and an equal-weight sector portfolio. It deliberately avoids look-ahead bias by ranking only from data available at each rebalance date.

The current backtest does not validate Google Trends because stable historical trend data is not yet available.

## Can this be used for stock purchasing?

No. The current prototype is not suitable for direct purchasing decisions. It becomes useful as a research-support tool only after live or cached data, backtesting, and analyst review are available. It does not execute trades.

## Suggested Next Improvements

- Improve the reliability and refresh strategy for live Google Trends collection while respecting provider limits.
- Add validated historical-data experiments and clearer data-version tracking.
- Extend the fundamental validation layer with ETF-appropriate sources and coverage checks.
- Add analyst feedback workflows, richer visualisations, and role-based review documentation.
- Review the scoring assumptions with domain experts before any broader use.

## Team Notes

The project is designed for collaborative university work. Before presenting results, run the pipeline, verification script, and tests so that the CSV, dashboard, and report are based on the same generated output.
