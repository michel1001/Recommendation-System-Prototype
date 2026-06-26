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
- A ten-sector ETF universe.
- Google Trends loading with a live/cache/demo/fallback strategy.
- Explicit Google Trends refresh modes: `auto`, `cache_only`, `force_live`, and `demo_only`.
- Reproducible demo Google Trends data when live access is unavailable.
- Market and fundamental data loading through `yfinance`.
- Technical indicators: momentum, volatility, downside volatility, drawdown, moving averages, distance to the 200-day moving average, and volume momentum.
- Google Trends indicators: latest value, 4-week and 12-week momentum, 12-week and 52-week z-scores, spike detection, acceleration, volatility, and percentile.
- Explainable trend, momentum, risk, fundamental, synergy, and confidence scores.
- Recommendation labels: `Overweight Candidate`, `Watch`, `Neutral`, and `Avoid`.
- HTML management report generation and a Streamlit dashboard.
- Output verification and a pytest test suite.
- Data-quality and actionability gates that prevent demo or missing data from producing investment-like recommendations.
- A market-only monthly sector-rotation backtesting framework; Google Trends history is not yet part of the backtest.

Current local validation status: `18 passed` with `python -m pytest`.

Dashboard command:

```bash
python -m streamlit run app/app.py
```

## Repository Structure

```text
Recommendation-System-Prototype/
|-- app/
|   `-- app.py
|-- data/
|   |-- raw/
|   |-- processed/
|   |-- demo/
|   `-- reports/
|-- reports/
|   |-- html/
|   `-- figures/
|-- src/
|   |-- config.py
|   |-- data_loader.py
|   |-- trends_loader.py
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

## Google Trends Rate Limits and Refresh Modes

Google Trends may return HTTP 429 because `pytrends` uses unofficial web requests. To avoid unnecessary live calls, the prototype supports explicit refresh modes:

- `auto`: use fresh cache first; if cache is stale or missing, try live Google Trends; if live fails, use demo data.
- `cache_only`: never call Google live; use local cache if available, otherwise demo data.
- `force_live`: try live Google Trends first; if live fails, use cache if available, otherwise demo data.
- `demo_only`: never call Google live or cache; always use synthetic demo data.

Normal pipeline:

```bash
python src/pipeline.py --trend-mode auto
```

Demo-safe pipeline:

```bash
python src/pipeline.py --trend-mode demo_only
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
python src/pipeline.py --trend-mode auto
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
