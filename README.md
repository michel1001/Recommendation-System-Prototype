# Recommendation-System-Prototype

AI-powered stock and sector recommendation prototype using market data, fundamental indicators, and explainable scoring to support investment decision-making.

## Overview

This repository contains a university prototype for an AI-based recommendation system in the financial sector.
The system is designed to evaluate stocks and sectors based on different data sources, such as market data and company fundamentals, and generate transparent recommendation scores.

The goal is not to predict stock prices with certainty, but to provide a decision-support tool that helps analysts, advisors, or financial institutions structure investment-related information more efficiently.

## Project Context

This prototype was developed as part of a university project focusing on artificial intelligence applications in business and finance.

The use case assumes a consulting scenario for a bank that wants to explore how artificial intelligence could support investment analysis, customer advisory processes, and internal decision-making.

The project focuses on two main areas:

1. **Recommendation Engine**
   A decision-support system that scores and ranks stocks or sectors based on selected indicators.

2. **Trading Bot Outlook**
   A conceptual extension showing how an automated trading system would require stricter regulatory, technical, and risk-control mechanisms.

## Key Features

* Collection and preparation of financial market data
* Integration of company and fundamental indicators
* Scoring logic for stocks and sectors
* Explainable recommendation output
* Comparison of selected assets based on transparent criteria
* Prototype structure suitable for future dashboard or Streamlit implementation

## Data Sources

The prototype may include or conceptually refer to the following data categories:

### Market & Price Data

* Historical stock prices
* Open-High-Low-Close data
* Trading volume
* Volatility indicators
* Technical indicators

### Company & Fundamental Data

* Earnings per share
* Debt-to-equity ratio
* Price-to-earnings ratio
* Price-to-book ratio
* Revenue and profitability indicators
* Sector classification

### Alternative Data Sources

* News and text data
* Social media sentiment
* Google Trends
* Website traffic
* Job postings
* Sustainability indicators

## Methodology

The recommendation logic follows a transparent scoring approach.

A simplified workflow could look like this:

1. Load market and company data
2. Clean and preprocess the data
3. Calculate relevant financial and technical indicators
4. Normalize indicators to make them comparable
5. Apply weighted scoring logic
6. Rank stocks or sectors
7. Generate an explainable recommendation output

The system is intended as a decision-support tool and does not replace human judgment.

## Planned Repository Structure

```text
Recommendation-System-Prototype/
│
├── data/                  # Raw and processed datasets
├── notebooks/             # Exploratory analysis and prototyping
├── src/                   # Core Python logic
│   ├── data_loader.py
│   ├── preprocessing.py
│   ├── indicators.py
│   ├── scoring.py
│   └── recommender.py
│
├── app/                   # Optional dashboard or Streamlit app
├── reports/               # Visualizations and project documentation
├── requirements.txt       # Python dependencies
├── README.md
└── .gitignore
```

## Installation

Clone the repository:

```bash
git clone https://github.com/michel1001/Recommendation-System-Prototype.git
cd Recommendation-System-Prototype
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate the environment:

```bash
# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Possible Dependencies

The final prototype may use the following Python libraries:

```text
pandas
numpy
scikit-learn
yfinance
matplotlib
plotly
streamlit
```

## Usage

After the prototype has been implemented, the recommendation process may be started through a script such as:

```bash
python src/recommender.py
```

If a Streamlit dashboard is added, it may be launched with:

```bash
streamlit run app/app.py
```

## Example Output

The system could generate an output similar to:

```text
Stock: Apple Inc.
Sector: Technology
Recommendation Score: 82/100
Signal: Positive
Reasoning:
- Strong profitability indicators
- Positive recent momentum
- Stable market position
- Moderate valuation risk
```

## Regulatory Considerations

Since this prototype is designed for a banking-related use case, regulatory aspects are an important part of the project.

Relevant topics include:

* MiFID II and investment advisory requirements
* Documentation and transparency obligations
* Human-in-the-loop decision-making
* Avoidance of misleading performance promises
* Conflict-of-interest management
* Data protection and responsible AI use

The prototype should therefore be understood as a decision-support system, not as an autonomous investment advisor or trading system.

## Limitations

This project is a prototype and has several limitations:

* No guarantee of prediction accuracy
* No real-time trading functionality
* Limited data scope
* Simplified scoring logic
* No production-ready risk management
* No regulatory approval for financial advisory use

Financial markets are complex, volatile, and influenced by many unpredictable factors. The results of this system should therefore always be interpreted critically.

## Disclaimer

This project is for educational and research purposes only.
It does not constitute financial advice, investment advice, or a recommendation to buy or sell any financial instrument.

Any investment decision should be made independently and, if necessary, with the support of a qualified financial advisor.

## Roadmap

* [ ] Define relevant data sources
* [ ] Implement data collection
* [ ] Add preprocessing pipeline
* [ ] Calculate technical and fundamental indicators
* [ ] Develop scoring model
* [ ] Add explainability logic
* [ ] Build dashboard prototype
* [ ] Add documentation and presentation materials

## Author

Developed by **michel1001** as part of a university AI project.

## License

This repository is intended for academic and educational use.
A license can be added later depending on the intended usage and publication scope.
