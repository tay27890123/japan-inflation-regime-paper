# Data

Raw files in `raw/` are kept exactly as downloaded. Everything in `processed/` is built by code in `src/` and is never edited by hand.

## What the code does to the data

No published number is changed, and no adjustment of my own is added. The inflation series uses only the adjustments published by the Statistics Bureau and the Bank of Japan.

| The code does this | Example |
|---|---|
| Joins two official series | The inflation series: Statistics Bureau to Dec 2015, Bank of Japan from Jan 2016 |
| Turns a level into a % change on a year earlier | Import prices, producer prices, USD/JPY |
| Adds published parts into their total | Tourist arrivals by country |
| Uses each value only from the month it was published, and repeats a quarterly or yearly value until the next one | July's unemployment rate is used in August |

One predictor is calculated instead of read: `c1_hh_expect_cp`, a Carlson-Parkin (1975) index. The Bank of Japan's household survey publishes the shares of people who expect prices to go up, stay about the same or go down. The index turns those shares into one number. The formula is in `src/build_dataset.py`, in `read_household_survey`.

One known limit: free high-school tuition lowered inflation by about half a point from April 2010 to March 2011. No official series removes it, so it stays in the inflation series.

## Sources and licences

| File | Source | Licence | In this repository |
|---|---|---|---|
| `zmy2025a.csv` (CPI, official year-on-year rates) | Statistics Bureau of Japan, via e-Stat | Government of Japan Standard Terms of Use 2.0 (CC BY 4.0 compatible) | Yes |
| `2025taxadj.xlsx` (CPI adjusted for consumption tax) | Statistics Bureau of Japan | Same as above | Yes |
| `lt01-a10.xlsx` (Labour Force Survey) | Statistics Bureau of Japan | Same as above | Yes |
| `ritu-jg2622.csv`, `gaku-jg2622.csv` (real GDP and components) | Cabinet Office (ESRI) | Same as above | Yes |
| `hon-t07.xls` (Monthly Labour Survey, total cash earnings) | Ministry of Health, Labour and Welfare, via e-Stat | Same as above | Yes |
| `mhlw_shunto_table2_001727594.pdf` (spring wage settlements) | Ministry of Health, Labour and Welfare | Same as above | Yes |
| `mhlw_shunto_table2_transcribed.csv` | Typed from the PDF above by the author (the PDF is a scanned image) | Same as above | Yes |
| `cpirev.xlsx` (CPI excluding special factors, underlying inflation measures) | Bank of Japan | Reproduction allowed with credit; not altered | Yes |
| `survey04.csv` (Opinion Survey on the General Public's Views and Behavior) | Bank of Japan | Same as above | Yes |
| `gap.xlsx` (output gap) | Bank of Japan | Same as above | Yes |
| `cai.xlsx` (Consumption Activity Index) | Bank of Japan | Same as above | Yes |
| `boj_*.csv` (import prices, PPI, services PPI, USD/JPY, bank loans, Tankan output-price DI) | Bank of Japan, Time-Series Data Search | Same as above | Yes |
| `jnto_visitor_arrivals_by_country_month.csv` (tourist arrivals) | Japan National Tourism Organization (JNTO) | Not yet checked | No: download instructions below |
| `SSR_Estimates_20260929.xlsx` (shadow short rate) | Leo Krippner | No licence stated | No: download instructions below |
| `SPASTT01JPM661N.xlsx` (share prices) | OECD, via FRED | Not yet checked | No: download instructions below |

Source credits: "Source: Statistics Bureau of Japan", "Source: Cabinet Office", "Source: Ministry of Health, Labour and Welfare" and "Source: Bank of Japan" apply to the files marked accordingly. The files in `processed/` are made from these sources by the code in `src/`. They are my own processing, not official statistics.

## Files to download yourself

Three files are used by the code but not stored here, because their licences are not confirmed. Save each one in `raw/` under the name shown. If one is missing, `src/build_dataset.py` stops and prints its link.

| Save as | Where to get it | How |
|---|---|---|
| `jnto_visitor_arrivals_by_country_month.csv` | JNTO statistics dashboard: https://statistics.jnto.go.jp/en/graph/ | "Trends in the Visitor Arrivals to Japan by Month", all years and all countries, download as CSV, then rename |
| `SSR_Estimates_20260929.xlsx` | Leo Krippner: https://www.ljkmfa.com/wp-content/uploads/2021/08/SSR_Estimates_20260929.xlsx | Direct download |
| `SPASTT01JPM661N.xlsx` | FRED: https://fred.stlouisfed.org/series/SPASTT01JPM661N | Click "Download" and choose Excel |

The versions used here are listed in `raw/SHA256SUMS.txt`. A newer download will not match those checksums: the JNTO file adds months, and the shadow-rate file re-estimates its whole history at each update, so results can change slightly.

## Checksums

`raw/SHA256SUMS.txt` lists a SHA-256 checksum for every raw file, so anyone can check they have the same versions. `raw/DOWNLOAD_LOG.md` records where and when each file was downloaded.

