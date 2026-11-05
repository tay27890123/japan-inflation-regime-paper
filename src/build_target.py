"""Build the forecasting target: policy-adjusted core-core CPI inflation.

Core-core CPI = consumer prices excluding fresh food and energy
(Statistics Bureau item code 0178). Inflation = % change on a year earlier.
Policy-adjusted = without the effects of government measures: consumption-tax
rises, free education, travel subsidies and the 2021 mobile-phone fee cut.

The target joins two official series:

    Jan 2006 - Dec 2015   Statistics Bureau, adjusted for consumption tax
                          (2025taxadj.xlsx, sheet "zmy"), plus our only fix:
                          +0.6 pp in Apr 2010 - Mar 2011 (free high-school tuition)
    Jan 2016 onward       Bank of Japan, excluding special factors (cpirev.xlsx)

Where both series exist (Jan 2016 - Jul 2020) they are identical, so the join
is seamless. The official unadjusted series (zmy2025a.csv) is kept next to the
target for comparison.

Run from the project folder:
    python src/build_target.py
Output:
    data/processed/target.csv
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed" / "target.csv"

CORE_CORE = "0178"  # Statistics Bureau code: all items less fresh food and energy
START, JOIN = "2006-01", "2016-01"
TUITION_FIX = 0.6  # pp; Statistics Bureau estimate, scaled to core-core
TUITION_MONTHS = ("2010-04", "2011-03")


def _months(values):
    """Turn 6-digit dates like 201004 into monthly periods."""
    return pd.PeriodIndex(pd.to_datetime(pd.Series(values).astype(str), format="%Y%m"), freq="M")


def read_official(path=RAW / "zmy2025a.csv"):
    """Official core-core YoY %, as published (Statistics Bureau, e-Stat CSV)."""
    t = pd.read_csv(path, encoding="cp932", header=None, dtype=str)
    col = list(t.iloc[2]).index(CORE_CORE)  # row 3 holds the item codes
    rows = t[t[0].str.fullmatch(r"\d{6}", na=False)]
    s = pd.to_numeric(rows[col], errors="coerce")
    s.index = _months(rows[0])
    return s.dropna().rename("official")


def read_tax_adjusted(path=RAW / "2025taxadj.xlsx"):
    """Core-core YoY %, adjusted for consumption tax (Statistics Bureau), to Dec 2020."""
    t = pd.read_excel(path, sheet_name="zmy", header=None)
    col = list(t.iloc[2].astype(str)).index(CORE_CORE)
    rows = t[t[0].astype(str).str.fullmatch(r"\d{6}")]
    s = pd.to_numeric(rows[col], errors="coerce")
    s.index = _months(rows[0])
    return s.dropna().rename("sb_tax_adjusted")


def read_boj(path=RAW / "cpirev.xlsx"):
    """Core-core YoY % excluding special factors (Bank of Japan), from Jan 2016.

    The file has one column per CPI base year (2015, 2020, 2025). Each month
    appears in exactly one of them, so the three columns are combined into one.
    (The quarterly block further right has the same name, so we also check the base.)
    """
    t = pd.read_excel(path, sheet_name="chart", header=None)
    cols = [j for j in t.columns
            if str(t.iloc[3, j]).startswith("Excluding fresh food, energy, and institutional")
            and t.iloc[4, j] in ("2015base", "2020base", "2025base")]
    data = t.iloc[5:].dropna(subset=[0])
    block = data[cols].apply(pd.to_numeric, errors="coerce")
    if (block.notna().sum(axis=1) > 1).any():
        raise ValueError("cpirev.xlsx: a month appears in two base-year columns")
    s = block.bfill(axis=1).iloc[:, 0]
    s.index = pd.PeriodIndex(pd.to_datetime(data[0]), freq="M")
    return s.dropna().rename("boj_adjusted")


def build_target():
    """Return a monthly table: target, official series, and the source of each month."""
    sb = read_tax_adjusted()
    boj = read_boj()
    official = read_official()

    early = sb.loc[START:"2015-12"].copy()
    fix = pd.Series(0.0, index=early.index)
    fix.loc[TUITION_MONTHS[0]:TUITION_MONTHS[1]] = TUITION_FIX
    early = early + fix

    target = pd.concat([early, boj.loc[JOIN:]]).round(1)
    source = pd.Series("Bank of Japan, excluding special factors", index=target.index)
    source.loc[:"2015-12"] = "Statistics Bureau, tax-adjusted"
    source.loc[TUITION_MONTHS[0]:TUITION_MONTHS[1]] = "Statistics Bureau, tax-adjusted, +0.6 tuition fix"

    out = pd.DataFrame({"target": target, "official": official.reindex(target.index), "source": source})
    out.index.name = "month"
    return out


def main():
    df = build_target()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT)
    print(f"Saved {OUT.relative_to(ROOT)}: {len(df)} months, {df.index[0]} to {df.index[-1]}")
    print(f"Average target 2013-2021: {df.loc['2013-01':'2021-12', 'target'].mean():.2f}%, "
          f"2022 onward: {df.loc['2022-01':, 'target'].mean():.2f}%")
    print(f"Latest: {df.index[-1]} = {df['target'].iloc[-1]}%")


if __name__ == "__main__":
    main()
