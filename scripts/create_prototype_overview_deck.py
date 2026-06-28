"""Create a 5-slide PowerPoint overview deck for the current prototype."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import win32com.client


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports" / "AI_Sector_Monitoring_Prototype_Overview.pptx"
RANKING_PATH = ROOT / "data" / "processed" / "recommendation_scores.csv"
BACKTEST_METRICS_PATH = ROOT / "data" / "processed" / "backtest_metrics.csv"

WIDE = 13.333
HIGH = 7.5
PT = 72

NAVY = 0x2B1B0F
INK = 0x30251D
PAPER = 0xF7F2EA
MUTED = 0xB6A99C
TEAL = 0x9F7D18
GOLD = 0x4BB6E8
RUST = 0x3564C8
GREEN = 0x7AA85C
RED = 0x586BE0
WHITE = 0xFFFFFF


def inches(value: float) -> float:
    return value * PT


def add_text(slide, text: str, x: float, y: float, w: float, h: float, size: int = 18, color: int = INK, bold: bool = False, name: str | None = None):
    box = slide.Shapes.AddTextbox(1, inches(x), inches(y), inches(w), inches(h))
    if name:
        box.Name = name
    frame = box.TextFrame
    frame.MarginLeft = inches(0.04)
    frame.MarginRight = inches(0.04)
    frame.MarginTop = inches(0.02)
    frame.MarginBottom = inches(0.02)
    frame.TextRange.Text = text
    frame.TextRange.Font.Name = "Aptos"
    frame.TextRange.Font.Size = size
    frame.TextRange.Font.Color.RGB = color
    frame.TextRange.Font.Bold = -1 if bold else 0
    return box


def add_rect(slide, x: float, y: float, w: float, h: float, fill: int, line: int | None = None, radius: bool = False):
    shape_type = 5 if radius else 1
    shp = slide.Shapes.AddShape(shape_type, inches(x), inches(y), inches(w), inches(h))
    shp.Fill.ForeColor.RGB = fill
    shp.Line.ForeColor.RGB = line if line is not None else fill
    return shp


def add_line(slide, x1: float, y1: float, x2: float, y2: float, color: int = MUTED, weight: float = 1.2):
    line = slide.Shapes.AddLine(inches(x1), inches(y1), inches(x2), inches(y2))
    line.Line.ForeColor.RGB = color
    line.Line.Weight = weight
    return line


def add_kicker(slide, label: str, color: int = TEAL):
    add_rect(slide, 0.58, 0.45, 0.13, 0.13, color)
    add_text(slide, label.upper(), 0.78, 0.37, 3.2, 0.25, 10, color, True)


def add_title(slide, title: str, subtitle: str | None = None):
    add_text(slide, title, 0.58, 0.72, 9.25, 1.05, 28, INK, True)
    if subtitle:
        add_text(slide, subtitle, 0.62, 1.78, 9.25, 0.38, 12, MUTED, False)


def add_footer(slide, page: int):
    add_line(slide, 0.58, 7.05, 12.75, 7.05, 0xD7CEC4, 0.8)
    add_text(slide, "Decision support only · No autonomous trading · Not financial advice", 0.58, 7.1, 7.4, 0.22, 8, MUTED)
    add_text(slide, f"{page}/5", 12.25, 7.1, 0.5, 0.22, 8, MUTED)


def add_bullet(slide, text: str, x: float, y: float, w: float, color: int = INK):
    add_rect(slide, x, y + 0.08, 0.07, 0.07, TEAL)
    add_text(slide, text, x + 0.18, y, w - 0.18, 0.62, 13, color)


def add_metric_card(slide, label: str, value: str, note: str, x: float, y: float, w: float, h: float, accent: int = TEAL):
    add_rect(slide, x, y, w, h, WHITE, 0xE4DAD0, True)
    add_rect(slide, x, y, 0.08, h, accent)
    add_text(slide, value, x + 0.22, y + 0.18, w - 0.35, 0.36, 23, INK, True)
    add_text(slide, label.upper(), x + 0.24, y + 0.61, w - 0.35, 0.20, 8, accent, True)
    add_text(slide, note, x + 0.24, y + 0.9, w - 0.38, h - 0.95, 10, MUTED)


def add_process_node(slide, label: str, note: str, x: float, y: float, w: float, accent: int):
    add_rect(slide, x, y, w, 1.12, WHITE, 0xE4DAD0, True)
    add_rect(slide, x + 0.16, y + 0.18, 0.16, 0.16, accent)
    add_text(slide, label, x + 0.42, y + 0.12, w - 0.55, 0.38, 13, INK, True)
    add_text(slide, note, x + 0.42, y + 0.55, w - 0.55, 0.45, 9, MUTED)


def add_table(slide, rows: list[list[str]], x: float, y: float, w: float, row_h: float, col_widths: list[float]):
    header_fill = NAVY
    for r, row in enumerate(rows):
        current_x = x
        for c, value in enumerate(row):
            fill = header_fill if r == 0 else (WHITE if r % 2 else 0xFBF8F3)
            color = WHITE if r == 0 else INK
            add_rect(slide, current_x, y + r * row_h, col_widths[c], row_h, fill, 0xE4DAD0)
            add_text(slide, value, current_x + 0.06, y + r * row_h + 0.08, col_widths[c] - 0.12, row_h - 0.12, 9 if r else 8, color, r == 0)
            current_x += col_widths[c]


def create_deck() -> Path:
    ranking = pd.read_csv(RANKING_PATH)
    top = ranking.sort_values("total_score", ascending=False).head(5)
    statuses = ranking["trend_data_status"].fillna("fallback").str.lower().value_counts()
    refresh_modes = ", ".join(sorted(ranking["trend_refresh_mode"].dropna().astype(str).unique())) if "trend_refresh_mode" in ranking else "unknown"
    backtest = pd.read_csv(BACKTEST_METRICS_PATH) if BACKTEST_METRICS_PATH.exists() else pd.DataFrame()

    app = win32com.client.Dispatch("PowerPoint.Application")
    deck = app.Presentations.Add()
    deck.PageSetup.SlideWidth = inches(WIDE)
    deck.PageSetup.SlideHeight = inches(HIGH)

    # Slide 1
    slide = deck.Slides.Add(1, 12)
    add_rect(slide, 0, 0, WIDE, HIGH, PAPER)
    add_rect(slide, 8.9, 0, 4.43, HIGH, NAVY)
    add_kicker(slide, "Prototype overview")
    add_text(slide, "AI Sector Monitoring Prototype", 0.58, 1.04, 7.75, 1.25, 38, INK, True)
    add_text(slide, "Explainable sector ranking that combines live market/fundamental data with Google Trends-style attention signals for analyst review.", 0.62, 2.38, 7.0, 0.8, 17, MUTED)
    add_bullet(slide, "Ten sector ETF universe with yfinance market and available ETF fundamental data.", 0.72, 3.55, 7.25)
    add_bullet(slide, "Google Trends integration is implemented, but current presentation mode uses clearly flagged demo trend data due to HTTP 429 rate limiting.", 0.72, 4.05, 7.25)
    add_bullet(slide, "Outputs include CSV ranking, Streamlit dashboard, HTML report, verification checks, and tests.", 0.72, 4.72, 7.25)
    add_metric_card(slide, "Automated validation", "18 tests", "pytest suite currently passes", 9.35, 0.9, 3.05, 1.35, GOLD)
    add_metric_card(slide, "Trend mode", refresh_modes, "data status is visible in every output", 9.35, 2.55, 3.05, 1.35, TEAL)
    add_metric_card(slide, "Trading scope", "0 orders", "decision support only", 9.35, 4.2, 3.05, 1.35, GREEN)
    add_footer(slide, 1)

    # Slide 2
    slide = deck.Slides.Add(2, 12)
    add_rect(slide, 0, 0, WIDE, HIGH, PAPER)
    add_kicker(slide, "System flow")
    add_title(slide, "The prototype turns raw data into an explainable sector ranking.", "Pipeline command: python src/pipeline.py --trend-mode demo_only or --trend-mode auto")
    nodes = [
        ("Live market data", "OHLCV prices and available ETF fundamentals loaded from yfinance.", 0.75, 2.35, 2.35, GOLD),
        ("Trend acquisition", "Google Trends live/cache/demo/fallback strategy with visible source status.", 3.35, 2.35, 2.35, TEAL),
        ("Feature engineering", "Momentum, volatility, drawdown, volume, valuation, yield, and trend features.", 5.95, 2.35, 2.35, RUST),
        ("Scoring layer", "Relative trend, momentum, risk, fundamental, synergy, and confidence scores.", 8.55, 2.35, 2.35, GREEN),
        ("Analyst outputs", "CSV, Streamlit dashboard, HTML report, verification, and backtest artifacts.", 5.2, 4.65, 3.3, NAVY),
    ]
    for label, note, x, y, w, accent in nodes:
        add_process_node(slide, label, note, x, y, w, accent)
    for x in [3.12, 5.72, 8.32]:
        add_line(slide, x, 2.91, x + 0.22, 2.91, TEAL, 2)
    add_line(slide, 9.75, 3.5, 7.05, 4.65, TEAL, 2)
    add_line(slide, 1.9, 3.5, 6.75, 4.65, TEAL, 2)
    add_text(slide, "Key design choice: failures are made visible instead of hidden. If Google Trends is unavailable, the system marks demo/fallback status and caps actionability.", 0.92, 6.15, 11.2, 0.42, 13, INK, True)
    add_footer(slide, 2)

    # Slide 3
    slide = deck.Slides.Add(3, 12)
    add_rect(slide, 0, 0, WIDE, HIGH, PAPER)
    add_kicker(slide, "Scoring")
    add_title(slide, "Scores are explainable and deliberately constrained by data quality.", "Current top sectors are research-prototype signals, not investment instructions.")
    weights = [("Trend / attention", 40, TEAL), ("Momentum", 25, GOLD), ("Fundamentals", 20, GREEN), ("Risk", 15, RUST)]
    y = 2.2
    for label, value, color in weights:
        add_text(slide, label, 0.82, y + 0.02, 2.2, 0.22, 11, INK, True)
        bar_width = value / 16
        add_rect(slide, 3.0, y, bar_width, 0.25, color)
        add_text(slide, f"{value}%", 3.0 + bar_width + 0.18, y - 0.01, 0.6, 0.22, 10, color, True)
        y += 0.55
    rows = [["Sector", "Ticker", "Score", "Label", "Trend status"]]
    for _, row in top.iterrows():
        rows.append([
            str(row["sector"]),
            str(row["ticker"]),
            f"{float(row['total_score']):.1f}",
            str(row["recommendation"]),
            str(row["trend_data_status"]),
        ])
    add_table(slide, rows, 6.15, 2.0, 5.95, 0.46, [1.55, 0.65, 0.65, 1.65, 1.1])
    add_text(slide, "Interpretation guardrails", 0.82, 4.85, 2.8, 0.25, 14, INK, True)
    add_bullet(slide, "Demo trend data forces Prototype only / Not actionable status.", 0.92, 5.25, 5.1)
    add_bullet(slide, "Recommendation labels are research labels; no buy/sell/order execution logic exists.", 0.92, 5.72, 5.1)
    add_bullet(slide, "Human analyst review is required before any decision-support use.", 0.92, 6.19, 5.1)
    add_footer(slide, 3)

    # Slide 4
    slide = deck.Slides.Add(4, 12)
    add_rect(slide, 0, 0, WIDE, HIGH, PAPER)
    add_kicker(slide, "Data quality")
    add_title(slide, "Google Trends is operationally fragile, so the prototype is transparent by design.", "Live Trends requests currently reach Google but fail with HTTP 429 rate limiting.")
    add_metric_card(slide, "Live sectors", str(int(statuses.get("live", 0))), "current API request", 0.75, 2.2, 2.65, 1.25, GREEN)
    add_metric_card(slide, "Cached sectors", str(int(statuses.get("cache", 0))), "previously loaded Trends data", 3.65, 2.2, 2.65, 1.25, TEAL)
    add_metric_card(slide, "Demo sectors", str(int(statuses.get("demo", 0))), "synthetic prototype trend data", 6.55, 2.2, 2.65, 1.25, GOLD)
    add_metric_card(slide, "Fallback sectors", str(int(statuses.get("fallback", 0))), "neutral placeholder", 9.45, 2.2, 2.65, 1.25, RED)
    add_rect(slide, 0.85, 4.25, 11.25, 1.45, WHITE, 0xE4DAD0, True)
    add_text(slide, "What this means for the presentation", 1.12, 4.47, 3.6, 0.25, 14, INK, True)
    add_text(slide, "Market data and available ETF fundamentals are loaded live through yfinance. Google Trends live loading is implemented, but Google currently rate-limits pytrends requests. For a stable demo, the dashboard/report clearly flag synthetic trend data with trend_data_status=demo and trend_refresh_mode=demo_only.", 1.12, 4.88, 10.35, 0.55, 12, MUTED)
    add_text(slide, "Fields added for transparency: trend_data_status · trend_refresh_mode · trend_cache_age_hours", 1.12, 5.78, 10.3, 0.28, 12, TEAL, True)
    add_footer(slide, 4)

    # Slide 5
    slide = deck.Slides.Add(5, 12)
    add_rect(slide, 0, 0, WIDE, HIGH, PAPER)
    add_kicker(slide, "Readiness")
    add_title(slide, "The prototype is presentation-ready as a research tool, with clear next steps.", "Final validation confirms the pipeline, report, dashboard, and tests are aligned.")
    add_metric_card(slide, "Pipeline", "Pass", "python src/pipeline.py --trend-mode demo_only", 0.75, 2.05, 3.0, 1.35, GREEN)
    add_metric_card(slide, "Verification", "Pass", "python src/verify_outputs.py", 4.05, 2.05, 3.0, 1.35, TEAL)
    add_metric_card(slide, "Tests", "18 passed", "python -m pytest", 7.35, 2.05, 3.0, 1.35, GOLD)
    if not backtest.empty:
        top_bt = backtest.iloc[0]
        bt_text = f"Market-only backtest: {top_bt['number_of_rebalances']} rebalances, Sharpe {float(top_bt['sharpe_ratio']):.2f}, max drawdown {float(top_bt['max_drawdown']):.1%}."
    else:
        bt_text = "Market-only backtest is included; Google Trends history is not yet part of backtest validation."
    add_rect(slide, 0.78, 4.05, 5.55, 1.55, WHITE, 0xE4DAD0, True)
    add_text(slide, "Current proof points", 1.05, 4.28, 2.2, 0.26, 14, INK, True)
    add_text(slide, bt_text, 1.05, 4.7, 4.85, 0.46, 12, MUTED)
    add_text(slide, "Dashboard: python -m streamlit run app/app.py", 1.05, 5.24, 4.8, 0.25, 11, TEAL, True)
    add_rect(slide, 6.65, 4.05, 5.55, 2.15, WHITE, 0xE4DAD0, True)
    add_text(slide, "Recommended next steps", 6.92, 4.28, 2.8, 0.26, 14, INK, True)
    add_bullet(slide, "Run demo mode for presentation stability.", 6.95, 4.67, 4.7)
    add_bullet(slide, "Use cache refresh script for later live Trends attempts.", 6.95, 5.08, 4.7)
    add_bullet(slide, "Expand ETF fundamentals and historical Trends validation after presentation.", 6.95, 5.49, 4.7)
    add_footer(slide, 5)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    deck.SaveAs(str(OUTPUT))
    deck.Close()
    app.Quit()
    return OUTPUT


if __name__ == "__main__":
    print(create_deck())
