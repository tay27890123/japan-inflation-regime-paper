# Data

Raw files in `raw/` are kept exactly as downloaded. Everything in `processed/` is built by code in `src/` and is never edited by hand.

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

Source credits: "Source: Statistics Bureau of Japan", "Source: Cabinet Office", "Source: Ministry of Health, Labour and Welfare" and "Source: Bank of Japan" apply to the files marked accordingly. Files built from them in `processed/` are our own edits, not official statistics.

## Files to download yourself

The links and download steps for files not stored here will be added with the code that reads them.

## Checksums

`raw/SHA256SUMS.txt` lists a SHA-256 checksum for every raw file, so anyone can check they have the same versions. `raw/DOWNLOAD_LOG.md` records where and when each file was downloaded.
