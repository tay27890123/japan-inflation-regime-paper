"""Checks that the master dataset is built correctly, above all that no value
is used before it was published.

Run from the project folder:
    pytest
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import build_dataset as bd  # noqa: E402

missing = [name for name in bd.LOCAL_ONLY if not (bd.RAW / name).exists()]
pytestmark = pytest.mark.skipif(bool(missing), reason=f"local-only raw files missing: {missing}")


def m(s):
    return pd.Period(s, freq="M")


@pytest.fixture(scope="module")
def df():
    return bd.build_dataset()


def test_columns_are_the_24_predictors(df):
    """Target first, then the 24 predictors: 18 IMF-based and our 6, in 8 channels."""
    assert list(df.columns) == ["target"] + list(bd.PREDICTORS)
    assert len(bd.IMF_BASED) == 18
    assert bd.OURS == ["c3_food_import", "c3_food_ppi", "c5_shunto",
                       "c6_tankan_all", "c6_tankan_small_services", "c6_diffusion"]
    assert sorted({name[:2] for name in bd.PREDICTORS}) == [f"c{i}" for i in range(1, 9)]


def test_same_months_as_the_target(df):
    """One row per month, Jan 2006 to the latest target month, no gaps."""
    target = bd.build_target()["target"]
    assert df.index.equals(target.index)
    assert (df["target"] == target).all()
    assert len(df) == len(pd.period_range(df.index[0], df.index[-1], freq="M"))


def test_no_missing_values_in_the_sample(df):
    """Complete from Oct 2006 (the first training month, Jan 2007, minus 3 lags).
    Only tourist arrivals stop early: the JNTO file ends in June 2026 (refresh it at the final run)."""
    assert df.loc["2006-10":"2026-06"].notna().all().all()
    assert df.loc["2026-07":].columns[df.loc["2026-07":].isna().any()].tolist() == ["c7_tourists"]


def test_monthly_series_known_in_month_t(df):
    """Released before the forecast date: the value for month T itself."""
    ppi = bd.yoy(bd.read_boj_csv("boj_PRCG20_1200000000_ppi_extax.csv"))
    assert df.loc["2026-08", "c2_ppi"] == pytest.approx(ppi[m("2026-08")])
    assert df.loc["2026-08", "c6_diffusion"] == pytest.approx(bd.read_diffusion_index()[m("2026-08")])


def test_monthly_series_known_one_month_late(df):
    """Released after the forecast date: the value for month T-1."""
    assert df.loc["2026-08", "c4_unemployment"] == bd.read_unemployment()[m("2026-07")]
    assert df.loc["2026-08", "c5_earnings"] == bd.read_earnings()[m("2026-07")]
    assert df.loc["2026-08", "c8_shadow_rate"] == pytest.approx(bd.read_shadow_rate()[m("2026-07")])
    sppi = bd.yoy(bd.read_boj_csv("boj_PRCS20_4200000000_sppi_extax.csv"))
    assert df.loc["2026-08", "c2_sppi"] == pytest.approx(sppi[m("2026-07")])


def test_gdp_known_one_month_after_the_quarter(df):
    """Q2 (Apr-Jun) is first used at T = July; at T = June the latest is still Q1."""
    gdp = bd.read_gdp()["gdp"]
    assert df.loc["2026-07", "c4_gdp"] == gdp[m("2026-06")]
    assert df.loc["2026-06", "c4_gdp"] == gdp[m("2026-03")]


def test_output_gap_known_three_months_after_the_quarter(df):
    """Q1 (Jan-Mar) is first used at T = June; at T = May the latest is still Q4."""
    gap = bd.read_output_gap()
    assert df.loc["2026-06", "c4_output_gap"] == pytest.approx(gap[m("2026-03")])
    assert df.loc["2026-05", "c4_output_gap"] == pytest.approx(gap[m("2025-12")])
    assert df.loc["2026-08", "c4_output_gap"] == pytest.approx(gap[m("2026-03")])  # Q2 only from September


def test_household_survey_known_in_its_quarter(df):
    """The June survey is used from T = June; before that, the March survey."""
    hh = bd.read_household_survey()
    assert df.loc["2026-06", "c1_hh_expect_mean"] == hh.loc[m("2026-06"), "mean"]
    assert df.loc["2026-05", "c1_hh_expect_mean"] == hh.loc[m("2026-03"), "mean"]


def test_tankan_moved_back_to_its_survey(df):
    """The BOJ files the June survey's forecast under September. It is used from T = June."""
    filed = bd.read_boj_csv("boj_TK99F0000614GCQ10000_tankan_outprice_fcst_all.csv")
    assert df.loc["2026-06", "c6_tankan_all"] == filed[m("2026-09")]
    assert df.loc["2026-05", "c6_tankan_all"] == filed[m("2026-06")]


def test_shunto_known_from_august(df):
    """Each year's settlement rate is used from T = August until July of the next year."""
    assert df.loc["2024-07", "c5_shunto"] == 3.60
    assert df.loc["2024-08", "c5_shunto"] == 5.33
    assert df.loc["2025-07", "c5_shunto"] == 5.33


def test_wages_use_the_published_rate(df):
    """In 2024 the index-based rate would be 3.3-8.0%; the published rate stays at or below 4.5%."""
    wages_2024 = df.loc["2024-02":"2025-01", "c5_earnings"]  # Jan-Dec 2024, known one month later
    assert wages_2024.max() <= 4.5


def test_carlson_parkin_index():
    """Related to the survey mean but not a copy (correlation about 0.86), and always within 0-5."""
    hh = bd.read_household_survey()
    assert 0.80 < hh["mean"].corr(hh["cp_index"]) < 0.92
    assert hh["cp_index"].between(0, 5).all()


def test_carlson_parkin_by_hand():
    """June 2006 survey, worked out by hand: shares 15.3, 63.2, 18.8, 1.5, 0.1 (up a lot ... down a lot)."""
    from statistics import NormalDist
    answered = 15.3 + 63.2 + 18.8 + 1.5 + 0.1
    z1 = NormalDist().inv_cdf((1.5 + 0.1) / answered)          # "down"
    z2 = NormalDist().inv_cdf((1.5 + 0.1 + 18.8) / answered)   # "down or about the same"
    assert bd.read_household_survey().loc[m("2006-06"), "cp_index"] == pytest.approx(-(z1 + z2) / (z2 - z1))


def test_no_value_before_its_reference_month(df):
    """General check on every monthly price series: the last value used at T = Aug 2026
    refers to Aug 2026 at the latest, never a later month."""
    for name, delay in [("boj_FXERM07_usdjpy.csv", 0), ("boj_PRCS20_4200000000_sppi_extax.csv", 1)]:
        raw = bd.yoy(bd.read_boj_csv(name))
        used = df.loc["2026-08", "c2_usdjpy" if delay == 0 else "c2_sppi"]
        assert used == pytest.approx(raw[m("2026-08") - delay])
        assert raw.index.max() > m("2026-08") - delay  # the file does hold later data, which is not used
