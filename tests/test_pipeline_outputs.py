import pandas as pd

from src import verify_outputs as verifier


def test_verify_outputs_rejects_removed_rule_based_columns(tmp_path, monkeypatch):
    row = {column: 1 for column in verifier.REQUIRED_COLUMNS}
    row.update({
        "sector": "Example",
        "ticker": "EX",
        "trend_data_status": "not_used",
        "price_data_status": "live",
        "ml_predicted_outperform_probability": 0.7,
        "total_score": 60,
    })
    for field in verifier.REQUIRED_MARKET_FEATURES:
        row[field] = .1
    csv_path = tmp_path / "ml_sector_ranking.csv"
    pd.DataFrame([row]).to_csv(csv_path, index=False)
    html_path = tmp_path / "report.html"
    html_path.write_text("report")
    dashboard_path = tmp_path / "app.py"
    dashboard_path.write_text("app")
    monkeypatch.setattr(verifier, "CSV_PATH", csv_path)
    monkeypatch.setattr(verifier, "HTML_REPORT_PATH", html_path)
    monkeypatch.setattr(verifier, "DASHBOARD_PATH", dashboard_path)

    assert verifier.verify_outputs() is False


def test_verify_outputs_accepts_ml_probability_ranking(tmp_path, monkeypatch):
    rows = []
    for idx, probability in enumerate([0.7, 0.55]):
        row = {column: 1 for column in verifier.REQUIRED_COLUMNS}
        row.update({
            "rank": idx + 1,
            "sector": f"Sector {idx}",
            "ticker": f"XL{idx}",
            "trend_data_status": "not_used",
            "price_data_status": "live",
            "ml_predicted_outperform_probability": probability,
            "ml_model_status": "trained",
        })
        for field in verifier.REQUIRED_MARKET_FEATURES:
            row[field] = .1
        rows.append(row)
    csv_path = tmp_path / "ml_sector_ranking.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    html_path = tmp_path / "report.html"
    html_path.write_text("report")
    dashboard_path = tmp_path / "app.py"
    dashboard_path.write_text("app")
    monkeypatch.setattr(verifier, "CSV_PATH", csv_path)
    monkeypatch.setattr(verifier, "HTML_REPORT_PATH", html_path)
    monkeypatch.setattr(verifier, "DASHBOARD_PATH", dashboard_path)
    monkeypatch.setattr(verifier, "MODEL_PATH", tmp_path / "sector_model.pkl")

    assert verifier.verify_outputs() is True
