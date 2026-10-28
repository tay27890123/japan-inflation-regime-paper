# Research log

One dated entry per week (or per milestone), newest at the top. Each entry covers what I did,wrong,insight,decision,what is next.
---

## 2026-10-20: Data collected and repository set up

**Did**
- Finished the research design: three research questions, the inflation measure, models and evaluation rules.
- Downloaded and checked all 25 data files (official sources); kept unchanged and with a download log and checksums.
- Set up this repository, its folder structure and the Python 3.13 environment.

**Found** (from preliminary checks, before any formal tests)
- The Bank of Japan's adjusted core-core series and the Statistics Bureau's tax-adjusted series are identical from Jan 2016 to Jul 2020, so the two join cleanly.
- A simple least-squares search puts the main shift in average inflation in mid-2022. Wage growth and firms' price plans (Tankan) shift at about the same time.

**Problems and decisions**
- Wages: the Monthly Labour Survey index jumps in Jan 2024, so year-on-year growth computed from it is about 2.3 points too high in 2024. I use the officially published year-on-year rates instead.
- The Shunto table is only available as a scanned PDF, so I typed it in and checked every year (settled amount ÷ wage base = published rate).
- Persistence is hard to measure on only about four years of post-2022 data, so it is described rather than tested.

**Next**
- Write `src/build_target.py` and the tests that check the joined series.

---

## 2026-10-13 to 2026-10-17: Research design (summary)

- Read the IMF paper (WP/24/206) as the starting point. Decided to extend it rather than replicate it.
- Audited the data: the target series, the predictors and their release dates.
- Chose six Japan-specific predictors on economic grounds, before running any model: firms' price plans (Tankan), food costs, wage settlements (Shunto) and the breadth of price rises.
