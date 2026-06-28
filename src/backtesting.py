"""Market-only monthly sector-rotation backtest with no look-ahead bias."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import BACKTEST_METRICS_PATH, BACKTEST_RESULTS_PATH, SECTOR_ETFS, ensure_directories
from src.scoring import minmax_score


def load_backtest_prices(tickers: list[str], start: str = "2018-01-01") -> pd.DataFrame:
    """Load adjusted closes; callers can supply synthetic prices in tests."""
    raw = yf.download(tickers, start=start, progress=False, auto_adjust=True)["Close"]
    if isinstance(raw, pd.Series):
        raw = raw.to_frame(name=tickers[0])
    return raw.sort_index().dropna(how="all")


def calculate_historical_features(prices: pd.DataFrame, as_of_date: pd.Timestamp) -> pd.DataFrame:
    """Calculate features using prices at or before ``as_of_date`` only."""
    history = prices.loc[:pd.Timestamp(as_of_date)].dropna(how="all")
    rows = []
    for ticker in history.columns:
        series = history[ticker].dropna()
        if len(series) < 127:
            continue
        returns = series.pct_change().dropna()
        wealth = (1 + returns).cumprod()
        drawdown = wealth.iloc[-1] / wealth.cummax().iloc[-1] - 1
        volatility = returns.tail(21).std() * np.sqrt(252)
        momentum_21 = series.iloc[-1] / series.iloc[-22] - 1
        momentum_63 = series.iloc[-1] / series.iloc[-64] - 1
        momentum_126 = series.iloc[-1] / series.iloc[-127] - 1
        risk_adjusted = momentum_63 / volatility if volatility and pd.notna(volatility) else np.nan
        rows.append({"ticker": ticker, "momentum_21": momentum_21, "momentum_63": momentum_63, "momentum_126": momentum_126, "volatility": volatility, "drawdown": drawdown, "risk_adjusted_return": risk_adjusted})
    return pd.DataFrame(rows)


def rank_sectors_historically(features: pd.DataFrame) -> pd.DataFrame:
    """Rank market-only features relative to the available sector universe."""
    ranked = features.copy()
    if ranked.empty:
        return ranked
    components = [minmax_score(ranked[column], higher) for column, higher in [("momentum_21", True), ("momentum_63", True), ("momentum_126", True), ("volatility", False), ("drawdown", True), ("risk_adjusted_return", True)]]
    ranked["market_score"] = pd.concat(components, axis=1).mean(axis=1)
    return ranked.sort_values("market_score", ascending=False).reset_index(drop=True)


def calculate_performance_metrics(returns: pd.Series) -> dict[str, float]:
    """Return transparent portfolio metrics for a periodic return series."""
    values = pd.to_numeric(returns, errors="coerce").dropna()
    if values.empty:
        return {key: np.nan for key in ("cumulative_return", "annualized_return", "annualized_volatility", "sharpe_ratio", "max_drawdown", "win_rate", "number_of_rebalances", "turnover")}
    periods_per_year = 12
    cumulative = float((1 + values).prod() - 1)
    annual_return = float((1 + cumulative) ** (periods_per_year / len(values)) - 1)
    annual_volatility = float(values.std(ddof=0) * np.sqrt(periods_per_year))
    wealth = (1 + values).cumprod()
    max_drawdown = float((wealth / wealth.cummax() - 1).min())
    return {"cumulative_return": cumulative, "annualized_return": annual_return, "annualized_volatility": annual_volatility, "sharpe_ratio": float(annual_return / annual_volatility) if annual_volatility else np.nan, "max_drawdown": max_drawdown, "win_rate": float((values > 0).mean()), "number_of_rebalances": int(len(values)), "turnover": np.nan}


def run_monthly_rotation_backtest(top_n: int = 3, start: str = "2018-01-01", end: str | None = None, prices: pd.DataFrame | None = None, benchmark_prices: pd.Series | None = None) -> dict[str, pd.DataFrame]:
    """Select top sectors monthly, then measure only the following month's return.

    Features are calculated at each rebalance from data ending on that date; the
    subsequent return is never visible to the ranker, preventing look-ahead bias.
    """
    tickers = list(SECTOR_ETFS.values())
    if prices is None:
        prices = load_backtest_prices(tickers, start)
    prices = prices.loc[start:end].sort_index() if end else prices.loc[start:].sort_index()
    if benchmark_prices is None:
        benchmark_prices = load_backtest_prices(["SPY"], start).iloc[:, 0]
    benchmark_prices = benchmark_prices.loc[prices.index.min():prices.index.max()].sort_index()
    monthly_dates = prices.resample("ME").last().index
    records, previous_selection = [], set()
    for current, following in zip(monthly_dates[:-1], monthly_dates[1:]):
        features = calculate_historical_features(prices, current)
        ranked = rank_sectors_historically(features)
        if ranked.empty or "ticker" not in ranked.columns:
            continue  # Insufficient trailing history during the warm-up period.
        selected = ranked.head(top_n)["ticker"].tolist()
        if not selected:
            continue
        start_prices = prices.loc[:current, selected].ffill().iloc[-1]
        end_prices = prices.loc[:following, selected].ffill().iloc[-1]
        portfolio_return = float((end_prices / start_prices - 1).mean())
        equal_start = prices.loc[:current].ffill().iloc[-1]
        equal_end = prices.loc[:following].ffill().iloc[-1]
        equal_return = float((equal_end / equal_start - 1).mean())
        spy_start, spy_end = benchmark_prices.loc[:current].iloc[-1], benchmark_prices.loc[:following].iloc[-1]
        turnover = 1 - len(previous_selection.intersection(selected)) / top_n if previous_selection else np.nan
        records.append({"rebalance_date": current, "holding_end_date": following, "selected_tickers": ", ".join(selected), "portfolio_return": portfolio_return, "equal_weight_return": equal_return, "spy_return": float(spy_end / spy_start - 1), "turnover": turnover, "backtest_feature_set": "market_fundamental"})
        previous_selection = set(selected)
    result = pd.DataFrame(records)
    if not result.empty:
        for column in ("portfolio_return", "equal_weight_return", "spy_return"):
            result[f"{column}_cumulative"] = (1 + result[column]).cumprod() - 1
    metrics = pd.DataFrame([{"strategy": "Monthly top sectors", "backtest_feature_set": "market_fundamental", **calculate_performance_metrics(result.get("portfolio_return", pd.Series(dtype=float)))}, {"strategy": "Equal-weight sectors", "backtest_feature_set": "market_fundamental", **calculate_performance_metrics(result.get("equal_weight_return", pd.Series(dtype=float)))}, {"strategy": "SPY benchmark", "backtest_feature_set": "market_fundamental", **calculate_performance_metrics(result.get("spy_return", pd.Series(dtype=float)))}])
    if not result.empty:
        metrics.loc[0, "turnover"] = result["turnover"].mean()
    return {"results": result, "metrics": metrics}


def export_backtest_results(results: dict[str, pd.DataFrame]) -> tuple[Path, Path]:
    ensure_directories()
    results["results"].to_csv(BACKTEST_RESULTS_PATH, index=False)
    results["metrics"].to_csv(BACKTEST_METRICS_PATH, index=False)
    return BACKTEST_RESULTS_PATH, BACKTEST_METRICS_PATH


if __name__ == "__main__":
    paths = export_backtest_results(run_monthly_rotation_backtest())
    print(f"[OK] Backtest results exported: {paths[0].relative_to(PROJECT_ROOT)}")
    print(f"[OK] Backtest metrics exported: {paths[1].relative_to(PROJECT_ROOT)}")
