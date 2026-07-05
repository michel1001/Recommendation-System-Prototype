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
  text(slide, "Quellenangaben: Projektartefakte src/ml_model.py, src/pipeline.py, data/processed/ml_sector_ranking.csv", 18, 668, 820, 18, { size: 11, color: C.muted });
  text(slide, "KI Consulting Projekt", 12, 700, 180, 18, { size: 12, color: C.muted });
  text(slide, "Konzeption eines KI-gestützten Sector Monitorings am Kapitalmarkt", 280, 700, 650, 18, { size: 12, color: C.muted, align: "center" });
  text(slide, String(page), 1236, 700, 30, 18, { size: 12, color: C.muted, align: "right" });
}

function node(slide, label, note, x, y, w, h, idx) {
  const box = shape(slide, x, y, w, h, C.white, C.teal, `workflow-node-${idx}`);
  box.line = { fill: C.teal, width: 2.5 };
  shape(slide, x + 16, y + 16, 30, 30, C.teal, "none");
  text(slide, String(idx), x + 16, y + 17, 30, 28, { size: 15, color: C.white, bold: true, align: "center" });
  text(slide, label, x + 56, y + 17, w - 70, 46, { size: 21, color: C.ink, bold: true });
  text(slide, note, x + 28, y + 76, w - 56, h - 98, { size: 13, color: C.muted, align: "center" });
  return box;
}

function connect(slide, a, b) {
  const line = slide.shapes.connect(a, b, { kind: "straight", line: { fill: C.teal, width: 3 } });
  return line;
}

export async function slide01(presentation) {
  const slide = presentation.slides.add();
  shape(slide, 0, 0, W, H, C.bg, "none");
  header(slide, "Modelling");

  text(slide, "Supervised ML ersetzt die alte regelbasierte Logik vollständig", 46, 145, 720, 34, { size: 22, color: C.ink, bold: true });
  text(slide, "Zielvariable: Outperformance eines Sektor-ETFs gegenüber SPY über die nächsten 4 Wochen.", 46, 180, 730, 28, { size: 16, color: C.muted });

  const n1 = node(slide, "SQLite-Daten", "Historische ETF-Preise, SPY-Benchmark und verfügbare Fundamentaldaten", 54, 264, 210, 160, 1);
  const n2 = node(slide, "Data Cleaning", "Einheitliche Preisreihen nach Ticker, Sektor und Datum", 302, 264, 210, 160, 2);
  const n3 = node(slide, "Feature Engineering", "Momentum, Volatilität, Drawdown, relative Stärke vs. SPY", 550, 264, 230, 160, 3);
  const n4 = node(slide, "Train/Test Split", "Chronologische Trennung zur Reduktion von Look-Ahead-Bias", 820, 264, 210, 160, 4);
  const n5 = node(slide, "Random Forest", "Klassifikation: outperformt der Sektor SPY in 21 Handelstagen?", 1068, 264, 170, 160, 5);
  connect(slide, n1, n2);
  connect(slide, n2, n3);
  connect(slide, n3, n4);
  connect(slide, n4, n5);

  shape(slide, 82, 486, 332, 102, C.pale, "#BFE6E2");
  text(slide, "Feature Set", 108, 501, 130, 24, { size: 17, color: C.teal, bold: true });
  text(slide, "Momentum 21/63/126 · Volatilität · Downside Volatility · Drawdown · MA200-Abstand · Volume Momentum · Relative Stärke vs. SPY", 108, 531, 270, 44, { size: 13, color: C.ink });

  shape(slide, 474, 486, 332, 102, C.white, C.teal);
  text(slide, "Modell-Output", 500, 501, 150, 24, { size: 17, color: C.teal, bold: true });
  text(slide, "ml_predicted_outperform_probability\n+ Modell-Konfidenz\n+ Ranking nach Wahrscheinlichkeit", 500, 530, 270, 48, { size: 13, color: C.ink });

  shape(slide, 866, 486, 332, 102, C.white, C.teal);
  text(slide, "Aktueller Stand", 892, 501, 150, 24, { size: 17, color: C.teal, bold: true });
  text(slide, "RandomForestClassifier · 21.110 historische Beobachtungen · market_fundamental Feature Set", 892, 531, 260, 44, { size: 13, color: C.ink });

  text(slide, "Google Trends bleibt vorbereitet, ist aber im aktuellen stabilen Modell nicht aktiv.", 392, 610, 520, 34, { size: 16, color: C.teal, bold: true, align: "center" });
  footer(slide, 42);
  return slide;
}
