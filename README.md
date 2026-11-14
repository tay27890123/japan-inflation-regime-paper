# Has Japan Entered a New Inflation Regime?

**Applying econometric and machine-learning models to forecasting Japanese inflation, 2007–2026**

## Project Overview

For about 25 years, Japan's prices barely moved, and at times they fell. Since 2022, core inflation has mostly stayed at or above 2%. I wanted to know whether this is a temporary shock or a real change, and what it means for anyone who has to forecast inflation.

<img alt="Japan's core-core inflation, 1995 to 2026: near zero for 25 years, mostly at or above 2% since 2022" src="results/figures/core_core_inflation_light.png">

Before my exchange I worked as a data-analysis intern, where I learned the data-science side of the work. This project is where I combine it with what I study: econometrics and time series. Research Paper I at Otaru University of Commerce, with weekly supervision from Professor Shinsuke Ikeda, gave me the chance to do it properly.

## Research Questions

The IMF (Liu, Pan and Xu, 2024, WP/24/206) notes that Japanese inflation has become harder to forecast, but does not test whether a lasting change has taken place. This project starts from that paper and asks:

1. **Diagnosis:** did Japan's inflation enter a new regime, and which economic explanations fit the evidence?
2. **Forecasting:** has inflation become harder to forecast, and which models and economic information help?
3. **Historical window:** does using more recent data improve forecasts?

## Approach

- **Inflation measure:** core-core CPI (excluding fresh food and energy), adjusted for one-off government measures, such as consumption-tax increases, that distort the underlying trend. It joins the Statistics Bureau's tax-adjusted series (to 2015) with the Bank of Japan's adjusted series (from 2016).
- **RQ1:** Bai–Perron structural-break tests, then three economic explanations from previous research: imported costs, firms' price-setting and wage–price feedback.
- **RQ2:** out-of-sample forecasts from 2013 at 1, 3 and 6 months ahead. Models: random walk, autoregressive (AR), AR plus one group of economic indicators, and LASSO (following the IMF). Forecasts use only data published at the time. Comparisons use the Diebold–Mariano test.
- **RQ3:** expanding vs 10-year vs 5-year training windows.

## Repository structure

```
data/        raw and processed data (sources and licences in data/README.md)
src/         Python code that builds the data
tests/       automatic checks on the data
notebooks/   the analysis: one notebook per step, in the paper's order
results/     figures and tables
docs/        research notes
```

## Reproducing the results

Python 3.13. On Windows:

```
py -3.13 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Then, from the project folder:

```
python src/build_target.py    # builds the inflation series: data/processed/target.csv
python src/build_dataset.py   # adds the 24 predictors: data/processed/dataset.csv
python src/plot_target.py     # redraws the chart above
python -m pytest              # checks the data
```

Then open the notebooks in the `notebooks/` folder in order and run all cells.

## Data

Most data come from official sources: the Statistics Bureau of Japan, the Bank of Japan, the Cabinet Office and the Ministry of Health, Labour and Welfare. Three files come from other sources (tourist arrivals, the shadow interest rate and share prices) and are downloaded separately. Sources, licences and download steps are listed in [data/README.md](data/README.md). Raw files are kept unchanged.

## About Me

Undergraduate research paper by **Tay Tze Ping** for Research Paper I at Otaru University of Commerce, supervised by Professor Shinsuke Ikeda. I am on exchange from the University of Malaya (Economics, Applied Statistics), September 2026 to February 2027.

## Licence

Code: MIT (see `LICENSE`). Data remain under their original licences (see `data/README.md`).
