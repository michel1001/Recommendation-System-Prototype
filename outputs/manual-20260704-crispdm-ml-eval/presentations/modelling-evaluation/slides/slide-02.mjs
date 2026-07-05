const W = 1280;
const H = 720;
const C = {
  bg: "#F6F7F8",
  teal: "#008C85",
  cyan: "#087EA4",
  ink: "#182426",
  muted: "#667677",
  pale: "#E8F6F4",
  line: "#D6DEDE",
  white: "#FFFFFF",
  warn: "#DCA62A",
  red: "#B85A5A",
};

function shape(slide, x, y, w, h, fill = C.white, line = C.line, name = "") {
  const transparent = "#00000000";
  const shapeFill = fill === "none" ? transparent : fill;
  const shapeLine = line === "none" ? { style: "solid", fill: transparent, width: 0 } : { style: "solid", fill: line, width: 1.5 };
  const s = slide.shapes.add({ geometry: "rect", position: { x, y, w, h }, fill: shapeFill, line: shapeLine });
  s.frame = { left: x, top: y, width: w, height: h };
  if (name) s.name = name;
  return s;
}

function text(slide, value, x, y, w, h, opts = {}) {
  const s = shape(slide, x, y, w, h, "none", "none", opts.name || "");
  s.text = value;
  s.text.typeface = opts.face || "Aptos";
  s.text.fontSize = opts.size || 20;
  s.text.color = opts.color || C.ink;
  s.text.bold = Boolean(opts.bold);
  s.text.alignment = opts.align || "left";
  s.text.verticalAlignment = opts.valign || "middle";
  s.text.insets = opts.insets || { top: 4, right: 6, bottom: 4, left: 6 };
  return s;
}

function header(slide, title) {
  shape(slide, 0, 0, W, 112, "linear(0deg, #00A08E, #087EA4)", "none");
  text(slide, "Technische Umsetzung (Prototyp)", 22, 14, 520, 28, { size: 24, color: "#BDEFEA" });
  text(slide, title, 22, 54, 760, 52, { size: 39, color: C.white, bold: true });
  text(slide, "Digitales\nLive-Studium", 1068, 34, 130, 48, { size: 18, color: C.white, bold: true, align: "right" });
  shape(slide, 1204, 16, 70, 84, C.white, "none");
  text(slide, "FOM", 1206, 25, 66, 38, { size: 25, color: "#00BFA5", bold: true, align: "center", insets: { top: 0, right: 0, bottom: 0, left: 0 } });
  text(slide, "Hochschule", 1207, 65, 64, 20, { size: 8, color: "#00BFA5", bold: true, align: "center", insets: { top: 0, right: 0, bottom: 0, left: 0 } });
}

function footer(slide, page) {
  shape(slide, 14, 655, 1252, 34, "none", "#A7B0B0");
  text(slide, "Quellenangaben: data/processed/ml_evaluation_metrics.csv, ml_backtest_metrics.csv, ml_feature_importance.csv", 18, 668, 820, 18, { size: 11, color: C.muted });
  text(slide, "KI Consulting Projekt", 12, 700, 180, 18, { size: 12, color: C.muted });
  text(slide, "Konzeption eines KI-gestützten Sector Monitorings am Kapitalmarkt", 280, 700, 650, 18, { size: 12, color: C.muted, align: "center" });
  text(slide, String(page), 1236, 700, 30, 18, { size: 12, color: C.muted, align: "right" });
}

function metric(slide, label, value, note, x, y, color = C.teal) {
  shape(slide, x, y, 164, 104, C.white, color);
  shape(slide, x, y, 8, 104, color, "none");
  text(slide, value, x + 20, y + 16, 130, 34, { size: 28, color: C.ink, bold: true });
  text(slide, label, x + 20, y + 50, 130, 18, { size: 12, color, bold: true });
  text(slide, note, x + 20, y + 72, 130, 16, { size: 10, color: C.muted });
}

function bar(slide, label, value, max, x, y, w, color) {
  text(slide, label, x, y - 2, 185, 20, { size: 12, color: C.ink, bold: true });
  shape(slide, x + 205, y + 5, w, 12, "#EEF2F2", "none");
  shape(slide, x + 205, y + 5, Math.max(1, (value / max) * w), 12, color, "none");
  text(slide, value.toFixed(3), x + 205 + w + 10, y - 2, 60, 20, { size: 11, color: C.muted });
}

export async function slide02(presentation) {
  const slide = presentation.slides.add();
  shape(slide, 0, 0, W, H, C.bg, "none");
  header(slide, "Evaluation");

  text(slide, "Evaluation misst die Qualität der ML-basierten Ranking-Logik", 46, 145, 760, 34, { size: 22, color: C.ink, bold: true });
  text(slide, "Die technische Pipeline ist validiert; die aktuelle Modellgüte bleibt aber klar als Research-Prototyp einzuordnen.", 46, 180, 850, 28, { size: 16, color: C.muted });

  text(slide, "Klassifikationsmetriken", 56, 226, 250, 28, { size: 19, color: C.teal, bold: true });
  metric(slide, "Accuracy", "0,523", "Test Set", 58, 268, C.teal);
  metric(slide, "F1", "0,398", "Ranking-Signal schwach", 238, 268, C.warn);
  metric(slide, "ROC AUC", "0,516", "knapp über Zufall", 418, 268, C.warn);
  metric(slide, "Recall", "0,366", "Outperformer-Erkennung", 598, 268, C.teal);

  shape(slide, 812, 218, 386, 210, C.white, C.teal);
  text(slide, "Backtest-Diagnose", 838, 238, 190, 26, { size: 20, color: C.teal, bold: true });
  text(slide, "Monatlich Top-Sektoren nach ML-Wahrscheinlichkeit auswählen und gegen Equal-Weight-Sektorbaseline vergleichen.", 838, 270, 310, 44, { size: 13, color: C.muted });
  text(slide, "ML Top Sectors", 846, 330, 130, 22, { size: 13, color: C.ink, bold: true });
  shape(slide, 990, 335, 132, 14, "#F4E5E5", "none");
  shape(slide, 990, 335, 86, 14, C.red, "none");
  text(slide, "-18,7%", 1130, 326, 58, 25, { size: 16, color: C.red, bold: true, align: "right" });
  text(slide, "Equal-weight", 846, 368, 130, 22, { size: 13, color: C.ink, bold: true });
  shape(slide, 990, 373, 132, 14, "#F4E5E5", "none");
  shape(slide, 990, 373, 67, 14, "#9C7777", "none");
  text(slide, "-14,5%", 1130, 364, 58, 25, { size: 16, color: "#9C7777", bold: true, align: "right" });
  text(slide, "Hit Rate ML: 45,2% · Equal-weight: 48,4%", 846, 392, 300, 20, { size: 12, color: C.muted });

  shape(slide, 58, 455, 520, 150, C.pale, "#BFE6E2");
  text(slide, "Feature Importance", 84, 474, 190, 24, { size: 19, color: C.teal, bold: true });
  bar(slide, "volatility_20", 0.123, 0.13, 84, 512, 180, C.teal);
  bar(slide, "drawdown_current", 0.117, 0.13, 84, 542, 180, C.teal);
  bar(slide, "rel_strength_vs_spy_126", 0.115, 0.13, 84, 572, 180, C.teal);

  shape(slide, 628, 455, 570, 150, C.white, C.warn);
  text(slide, "Interpretation", 654, 474, 160, 24, { size: 19, color: C.warn, bold: true });
  text(slide, "Das Modell ist end-to-end evaluierbar und die Ranking-Logik ist transparent messbar. Die aktuelle Güte liegt jedoch nur knapp über Zufallsniveau. Für CRISP-DM heißt das: technisch validierter Prototyp, fachlich nächster Zyklus mit Feature- und Datenverbesserung.", 654, 508, 500, 58, { size: 15, color: C.ink });
  text(slide, "Status: Research Prototype · keine produktive Investment-Entscheidung", 654, 569, 455, 22, { size: 14, color: C.red, bold: true });

  footer(slide, 43);
  return slide;
}
