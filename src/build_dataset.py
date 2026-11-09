"""Build the master dataset: the target plus the 24 predictors, one row per month.

Each row is a forecast origin T: the day the BOJ publishes adjusted CPI for
month T (about the 22nd-28th of month T+1). Every predictor column holds the
latest value a forecaster could have known on that day:

    month T          USD/JPY, import prices, PPI, food prices, CPI diffusion
                     index, tourist arrivals, bank lending, share prices
    month T-1        services PPI, unemployment, Consumption Activity Index,
                     earnings, shadow rate (published after the forecast date)
    quarterly        household survey, Tankan: the survey quarter ending in T or earlier
                     GDP, government spending: the quarter ending in T-1 or earlier
                     output gap: the quarter ending in T-3 or earlier
    annual           Shunto: that year's rate from T = August

Quarterly and annual values are carried forward until the next release.
Levels become % changes on a year earlier; rates are used as they are.
Column names start with the channel (c1_ ... c8_), so a channel model can
pick its own columns.

Run from the project folder:
    python src/build_dataset.py
Output:
    data/processed/dataset.csv
"""

import csv
import io
import re
import warnings

import pandas as pd
from scipy.stats import norm

from build_target import RAW, ROOT, build_target

OUT = ROOT / "data" / "processed" / "dataset.csv"

# name: (origin, description). The channel is the first part of the name.
PREDICTORS = {
    "c1_hh_expect_mean": ("IMF", "Households' expected inflation 1 year ahead, survey mean (%)"),
    "c1_hh_expect_cp": ("IMF", "Same survey, Carlson-Parkin index built from the answer shares"),
    "c2_usdjpy": ("IMF", "USD/JPY, % YoY (positive = weaker yen)"),
    "c2_import_prices": ("IMF", "Import prices, yen basis, % YoY"),
    "c2_energy_import": ("IMF", "Import prices, petroleum, coal and natural gas, yen basis, % YoY"),
    "c2_ppi": ("IMF", "Producer prices excluding consumption tax, % YoY"),
    "c2_sppi": ("IMF", "Services producer prices excluding consumption tax, % YoY"),
    "c3_food_import": ("ours", "Import prices, foodstuffs and feedstuffs, yen basis, % YoY"),
    "c3_food_ppi": ("ours", "Producer prices, beverages and foods, excluding tax, % YoY"),
    "c4_output_gap": ("IMF", "Output gap (BOJ, %)"),
    "c4_unemployment": ("IMF", "Unemployment rate, seasonally adjusted (%)"),
    "c4_gdp": ("IMF", "Real GDP, % YoY (official)"),
    "c4_consumption": ("IMF", "Real Consumption Activity Index, travel-balance adjusted, % YoY"),
    "c4_gov_consumption": ("IMF", "Real government consumption, % YoY (official)"),
    "c4_gov_investment": ("IMF", "Real public investment, % YoY (official)"),
    "c5_earnings": ("IMF", "Total cash earnings, % YoY (published by MHLW)"),
    "c5_shunto": ("ours", "Shunto wage settlement rate, major firms (%)"),
    "c6_tankan_all": ("ours", "Tankan output prices DI, forecast, all firms (% points)"),
    "c6_tankan_small_services": ("ours", "Tankan output prices DI, forecast, small non-manufacturing (% points)"),
    "c6_diffusion": ("ours", "CPI diffusion index: % of items rising minus % falling"),
    "c7_tourists": ("IMF", "Visitor arrivals, % YoY"),
    "c8_shadow_rate": ("IMF", "Shadow short rate (Krippner, %)"),
    "c8_bank_lending": ("IMF", "Bank lending, % YoY (official)"),
    "c8_share_prices": ("IMF", "Share prices (OECD index, in place of TOPIX), % YoY"),
}
IMF_BASED = [k for k, (origin, _) in PREDICTORS.items() if origin == "IMF"]
OURS = [k for k, (origin, _) in PREDICTORS.items() if origin == "ours"]

# Files kept out of the public repository (licence not confirmed): where to get them
LOCAL_ONLY = {
    "jnto_visitor_arrivals_by_country_month.csv": "https://statistics.jnto.go.jp/en/graph/",
    "SSR_Estimates_20260929.xlsx": "https://www.ljkmfa.com/wp-content/uploads/2021/08/SSR_Estimates_20260929.xlsx",
    "SPASTT01JPM661N.xlsx": "https://fred.stlouisfed.org/series/SPASTT01JPM661N",
}


# ---------- helpers ----------

def _path(name):
    path = RAW / name
    if not path.exists() and name in LOCAL_ONLY:
        raise FileNotFoundError(f"data/raw/{name} is not in the public repository. "
                                f"Download it from {LOCAL_ONLY[name]} (see data/README.md).")
    return path


def _num(x):
    """Turn a cell into a number; blanks, '-' and '***' become missing."""
    return pd.to_numeric(str(x).replace(",", "").strip(), errors="coerce")


def yoy(s):
    """% change on a year earlier, for a monthly series."""
    s = s.reindex(pd.period_range(s.index.min(), s.index.max(), freq="M"))  # no missing months
    return (s / s.shift(12) - 1) * 100  # shift(12) = the same month one year earlier


def known_at(s, delay=0, every=1):
    """Move a series from the month it refers to, to the first forecast origin T
    at which it is known (delay in months). Values of quarterly (every=3) and
    annual (every=12) series are then carried forward until the next release.

    Examples:
      unemployment, delay=1: the July 2026 rate goes in the row T = August 2026.
      GDP, delay=1, every=3: Q2 2026 is dated June; it goes in the row T = July,
                             and is repeated in August and September (Q3 arrives in October).
    """
    s = s.dropna().copy()
    s.index = s.index + delay  # move each value forward by the publication delay
    months = pd.period_range(s.index.min(), s.index.max() + (every - 1), freq="M")
    s = s.reindex(months)  # one row per month; months between releases are empty for now
    return s.ffill(limit=every - 1) if every > 1 else s  # fill them with the latest release


# ---------- one reader per raw file ----------

def read_boj_csv(name):
    """BOJ Time-Series Data Search CSV: header lines, then 'YYYY/MM,value'.
    Quarterly series are dated by the last month of the quarter."""
    out = {}
    with open(_path(name), encoding="utf-8") as f:
        for row in csv.reader(f):
            # Data lines look like "2000/01,105.21"; the header lines above them don't
            if len(row) > 1 and re.fullmatch(r"\d{4}/\d{2}", row[0]) and row[1].strip():
                out[pd.Period(row[0].replace("/", "-"), freq="M")] = float(row[1])
    return pd.Series(out).sort_index()


def read_household_survey(path=RAW / "survey04.csv"):
    """BOJ Opinion Survey, prices 1 year ahead (quarterly, from June 2006).

    mean:     the BOJ's published average of the numbers people give
    cp_index: Carlson-Parkin index from the five answer shares ("go up a lot"
              ... "go down a lot"), with "don't know" left out. With z1, z2 the
              standard-normal quantiles of the shares "down" and "down or about
              the same", the index is -(z1 + z2) / (z2 - z1).
    """
    rows = list(csv.reader(io.StringIO(path.read_bytes().decode("cp932"))))  # Japanese Windows encoding
    # Stop if the BOJ ever moves the columns: answer shares in columns 21-25, the mean in 27
    assert rows[5][21:26] == ["Will go up significantly", "Will go up slightly", "Will be almost unchanged",
                              "Will go down slightly", "Will go down significantly"]
    assert rows[5][27].startswith("Average")
    rows = [r for r in rows if re.fullmatch(r"\d{4} (Mar\.|June|Sept\.|Dec\.)", r[1])]  # e.g. "2006 June"
    month = {"Mar.": 3, "June": 6, "Sept.": 9, "Dec.": 12}
    idx = pd.PeriodIndex([pd.Period(year=int(r[1][:4]), month=month[r[1][5:]], freq="M") for r in rows])
    col = lambda j: pd.Series([_num(r[j]) for r in rows], index=idx)
    up_lot, up_little, same, down_little, down_lot = (col(j) for j in range(21, 26))
    answered = up_lot + up_little + same + down_little + down_lot  # "don't know" left out
    # Carlson-Parkin: turn each cumulative share into a point on the standard normal curve
    z1 = norm.ppf((down_little + down_lot) / answered)
    z2 = norm.ppf((down_little + down_lot + same) / answered)
    return pd.DataFrame({"mean": col(27), "cp_index": -(z1 + z2) / (z2 - z1)}, index=idx)


def read_diffusion_index(path=RAW / "cpirev.xlsx"):
    """CPI diffusion index (BOJ): % of items rising minus % falling, monthly from 2001.
    One column per CPI base year; each month appears in exactly one of them."""
    t = pd.read_excel(path, sheet_name="chart", header=None)
    cols = [j for j in t.columns if t.iloc[3, j] == "Diffusion index(% points)" and str(t.iloc[4, j]).endswith("base")]
    data = t.iloc[5:].dropna(subset=[0])
    block = data[cols].apply(pd.to_numeric, errors="coerce")
    if (block.notna().sum(axis=1) > 1).any():
        raise ValueError("cpirev.xlsx: a month appears in two base-year columns")
    s = block.bfill(axis=1).iloc[:, 0]
    s.index = pd.PeriodIndex(pd.to_datetime(data[0]), freq="M")
    return s.dropna()


def read_unemployment(path=RAW / "lt01-a10.xlsx"):
    """Unemployment rate, both sexes, seasonally adjusted (Labour Force Survey), from Jan 1953."""
    with warnings.catch_warnings():  # the sheet's print footer is unreadable; harmless
        warnings.filterwarnings("ignore", message="Cannot parse header or footer")
        t = pd.read_excel(path, sheet_name="季節調整値", header=None)
    assert "Unemployment rate" in str(t.iloc[6, 19]) and t.iloc[8, 19] == "Both sexes"
    labels = ["Jan.", "Feb.", "Mar.", "Apr.", "May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."]
    rows = t[t[2].isin(labels)]  # keep the rows whose month label is Jan.-Dec.
    idx = pd.period_range("1953-01", periods=len(rows), freq="M")
    # The rows must run Jan, Feb, ... without a break, and each year printed in the file must match
    assert list(rows[2]) == [labels[p.month - 1] for p in idx]
    years = pd.to_numeric(rows[0], errors="coerce")
    assert (years.dropna().astype(int).values == idx.year[years.notna().values]).all()
    return pd.Series(pd.to_numeric(rows[19], errors="coerce").values, index=idx).dropna()  # column 19 = the rate


def read_output_gap(path=RAW / "gap.xlsx"):
    """BOJ output gap (%), quarterly, dated by the last month of the quarter."""
    t = pd.read_excel(path, sheet_name="data1", header=None)
    assert t.iloc[2, 1] == "Output gap"
    rows = t[t[0].astype(str).str.fullmatch(r"\d{4}\.[1-4]Q")]
    idx = pd.PeriodIndex([pd.Period(year=int(q[:4]), month=3 * int(q[5]), freq="M") for q in rows[0]])
    return pd.Series(pd.to_numeric(rows[1], errors="coerce").values, index=idx).dropna()


def read_gdp(path=RAW / "ritu-jg2622.csv"):
    """Real GDP, government consumption and public investment: official % change on
    a year earlier (ESRI, quarterly, not seasonally adjusted), dated by the quarter's last month."""
    rows = list(csv.reader(io.StringIO(path.read_bytes().decode("cp932"))))
    head = rows[5]
    assert head[1].startswith("GDP") and head[8].startswith("Government") and head[9].startswith("Public")
    # The first column reads "1994/ 1- 3." for the first quarter of a year, then "4- 6.",
    # "7- 9.", "10-12.". The regex picks out the year (when it is there) and the quarter's
    # last month; the year is remembered for the quarters that don't repeat it.
    out, year = {}, None
    for r in rows:
        m = re.fullmatch(r"\s*(?:(\d{4})/)?\s*(\d{1,2})-\s*(\d{1,2})\.\s*", r[0])
        if not m:
            continue
        year = int(m.group(1)) if m.group(1) else year
        month = pd.Period(year=year, month=int(m.group(3)), freq="M")
        if month in out:
            raise ValueError(f"ritu-jg2622.csv: quarter ending {month} appears twice")
        out[month] = [_num(r[j]) for j in (1, 8, 9)]
    return pd.DataFrame.from_dict(out, orient="index", columns=["gdp", "gov_consumption", "gov_investment"])


def read_consumption(path=RAW / "cai.xlsx"):
    """BOJ Consumption Activity Index, real, travel-balance adjusted (s.a., 2020 = 100), monthly."""
    t = pd.read_excel(path, sheet_name="Data1", header=None)
    assert t.iloc[3, 4] == "Real Consumption Activity Index (travel balance adjusted)"
    rows = t.iloc[5:].dropna(subset=[0])
    return pd.Series(pd.to_numeric(rows[4]).values, index=pd.PeriodIndex(pd.to_datetime(rows[0]), freq="M"))


def read_earnings(path=RAW / "hon-t07.xls"):
    """Total cash earnings, 5+ employees, all industries: % change on a year earlier as
    PUBLISHED by MHLW. Never computed from the index, whose level breaks in Jan 2024."""
    t = pd.read_excel(path, sheet_name="TL", header=None)
    assert "Year-on-year" in str(t.iloc[90, 0]) and t.iloc[93, 8] == "Jan."
    out = {}
    for _, r in t.iloc[94:].iterrows():  # from row 94: one row per year, the year in column 0
        if pd.isna(_num(r[0])):
            continue
        for m in range(1, 13):  # columns 8-19 hold Jan-Dec
            v = _num(r[7 + m])
            if pd.notna(v):
                out[pd.Period(year=int(r[0]), month=m, freq="M")] = float(v)
    return pd.Series(out).sort_index()


def read_shunto(path=RAW / "mhlw_shunto_table2_transcribed.csv"):
    """Shunto wage settlement rate (%), major firms, typed from the MHLW table.
    Dated August of each year: the first forecast origin at which it is safely published."""
    t = pd.read_csv(path, comment="#")
    return pd.Series(t["rate_pct"].values, index=pd.PeriodIndex([pd.Period(year=y, month=8, freq="M") for y in t["year"]]))


def read_tankan(name):
    """Tankan output prices DI, forecast. The BOJ files each forecast under the quarter it
    predicts, so it is moved back one quarter to the survey that produced it."""
    s = read_boj_csv(name)
    s.index = s.index - 3  # e.g. the forecast filed under Sept 2026 came from the June 2026 survey
    return s


def read_tourists(name="jnto_visitor_arrivals_by_country_month.csv"):
    """JNTO visitor arrivals: the sum over all countries, monthly."""
    t = pd.read_csv(_path(name), encoding="utf-8-sig")
    t.columns = ["month", "year", "country", "growth", "arrivals"]
    labels = ["Jan.", "Feb.", "Mar.", "Apr.", "May", "Jun.", "Jul.", "Aug.", "Sep.", "Oct.", "Nov.", "Dec."]
    t["m"] = t["month"].map({lab: i for i, lab in enumerate(labels, 1)})
    assert t["m"].notna().all()
    total = t.groupby(["year", "m"])["arrivals"].sum()
    total = total[total > 0]  # months not yet published are blank in the file
    return pd.Series(total.values, index=pd.PeriodIndex([pd.Period(year=y, month=m, freq="M") for y, m in total.index]))


def read_shadow_rate(name="SSR_Estimates_20260929.xlsx"):
    """Krippner shadow short rate for Japan (%), monthly average."""
    t = pd.read_excel(_path(name), sheet_name="D. Monthly average SSR series", header=None)
    assert t.iloc[19, 4] == "Japan SSR"
    rows = t.iloc[20:].dropna(subset=[1, 4])
    return pd.Series(rows[4].astype(float).values, index=pd.PeriodIndex(pd.to_datetime(rows[1]), freq="M"))


def read_share_prices(name="SPASTT01JPM661N.xlsx"):
    """OECD share price index for Japan (via FRED), monthly."""
    t = pd.read_excel(_path(name), sheet_name="Monthly")
    return pd.Series(t.iloc[:, 1].values, index=pd.PeriodIndex(pd.to_datetime(t.iloc[:, 0]), freq="M"))


# ---------- the dataset ----------

def build_predictors():
    """The 24 predictors, each lined up with the forecast origin T it is known at."""
    hh = read_household_survey()
    gdp = read_gdp()
    p = {
        # C1 Expectations: survey quarter ending in T or earlier
        "c1_hh_expect_mean": known_at(hh["mean"], delay=0, every=3),
        "c1_hh_expect_cp": known_at(hh["cp_index"], delay=0, every=3),
        # C2 Exchange rate and costs
        "c2_usdjpy": known_at(yoy(read_boj_csv("boj_FXERM07_usdjpy.csv"))),
        "c2_import_prices": known_at(yoy(read_boj_csv("boj_PRCG20_2600000000_import_prices.csv"))),
        "c2_energy_import": known_at(yoy(read_boj_csv("boj_PRCG20_2600520001_import_energy.csv"))),
        "c2_ppi": known_at(yoy(read_boj_csv("boj_PRCG20_1200000000_ppi_extax.csv"))),
        "c2_sppi": known_at(yoy(read_boj_csv("boj_PRCS20_4200000000_sppi_extax.csv")), delay=1),
        # C3 Food costs
        "c3_food_import": known_at(yoy(read_boj_csv("boj_PRCG20_2600120001_import_food.csv"))),
        "c3_food_ppi": known_at(yoy(read_boj_csv("boj_PRCG20_1200120001_ppi_extax_food.csv"))),
        # C4 Slack and demand
        "c4_output_gap": known_at(read_output_gap(), delay=3, every=3),
        "c4_unemployment": known_at(read_unemployment(), delay=1),
        "c4_gdp": known_at(gdp["gdp"], delay=1, every=3),
        "c4_consumption": known_at(yoy(read_consumption()), delay=1),
        "c4_gov_consumption": known_at(gdp["gov_consumption"], delay=1, every=3),
        "c4_gov_investment": known_at(gdp["gov_investment"], delay=1, every=3),
        # C5 Wages
        "c5_earnings": known_at(read_earnings(), delay=1),
        "c5_shunto": known_at(read_shunto(), delay=0, every=12),
        # C6 Firms' price-setting: Tankan survey quarter ending in T or earlier
        "c6_tankan_all": known_at(read_tankan("boj_TK99F0000614GCQ10000_tankan_outprice_fcst_all.csv"), every=3),
        "c6_tankan_small_services": known_at(
            read_tankan("boj_TK99F2000614GCQ13000_tankan_outprice_fcst_small_nonmfg.csv"), every=3),
        "c6_diffusion": known_at(read_diffusion_index()),
        # C7 Tourism
        "c7_tourists": known_at(yoy(read_tourists())),
        # C8 Financial conditions
        "c8_shadow_rate": known_at(read_shadow_rate(), delay=1),
        "c8_bank_lending": known_at(read_boj_csv("boj_FAAPOBAL1_bank_loans_yoy.csv")),
        "c8_share_prices": known_at(yoy(read_share_prices())),
    }
    assert list(p) == list(PREDICTORS)
    return pd.DataFrame(p)


def build_dataset():
    """Monthly table, Jan 2006 to the latest target month: the target, then the 24 predictors."""
    target = build_target()["target"]
    df = pd.concat([target, build_predictors().reindex(target.index)], axis=1)
    df.index.name = "month"
    return df


def main():
    df = build_dataset()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, float_format="%.4f")
    print(f"Saved {OUT.relative_to(ROOT)}: {len(df)} months, {df.index[0]} to {df.index[-1]}, "
          f"target + {df.shape[1] - 1} predictors ({len(IMF_BASED)} IMF-based, {len(OURS)} ours)")
    gaps = df.loc["2007-01":].isna().sum()
    for name, n in gaps[gaps > 0].items():
        missing = df.index[df[name].isna() & (df.index >= pd.Period("2007-01", freq="M"))]
        print(f"Missing from Jan 2007: {name}, {n} months ({missing[0]} to {missing[-1]})")


if __name__ == "__main__":
    main()
