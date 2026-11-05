"""Checks that the target is built correctly from the raw files.

Run from the project folder:
    pytest
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import build_target as bt  # noqa: E402


@pytest.fixture(scope="module")
def df():
    return bt.build_target()


@pytest.fixture(scope="module")
def sb():
    return bt.read_tax_adjusted()


@pytest.fixture(scope="module")
def boj():
    return bt.read_boj()


def test_sources_identical_where_they_overlap(sb, boj):
    """Statistics Bureau and BOJ series are equal every month, Jan 2016 - Jul 2020."""
    diff = sb.loc["2016-01":"2020-07"] - boj.loc["2016-01":"2020-07"]
    assert len(diff) == 55
    assert diff.abs().max() < 1e-9


def test_join_step_matches_statistics_bureau(df, sb):
    """The move from Dec 2015 to Jan 2016 is the same as in the Statistics Bureau's own series (-0.3)."""
    step_target = df.loc["2016-01", "target"] - df.loc["2015-12", "target"]
    step_sb = sb.loc["2016-01"] - sb.loc["2015-12"]
    assert round(step_target, 1) == round(step_sb, 1) == -0.3


def test_tuition_fix_only_in_apr2010_to_mar2011(df, sb):
    """Our only adjustment: +0.6 pp in Apr 2010 - Mar 2011, nothing elsewhere before 2016."""
    added = (df.loc[:"2015-12", "target"] - sb.loc["2006-01":"2015-12"]).round(1)
    fix_months = added.loc["2010-04":"2011-03"]
    assert len(fix_months) == 12 and (fix_months == 0.6).all()
    assert (added.drop(fix_months.index) == 0).all()


def test_2014_tax_rise_removed(df):
    """The official series jumps in Apr 2014 because of the tax rise; the target does not."""
    jump_official = df.loc["2014-04", "official"] - df.loc["2014-03", "official"]
    jump_target = df.loc["2014-04", "target"] - df.loc["2014-03", "target"]
    assert jump_official >= 1.5
    assert abs(jump_target) <= 0.3


def test_boj_series_is_monthly_from_jan_2016(boj):
    """The BOJ file's monthly core-core columns start in Jan 2016 and have no gaps."""
    assert boj.index[0] == pd.Period("2016-01", "M")
    assert boj.index.equals(pd.period_range("2016-01", boj.index[-1], freq="M"))


def test_target_equals_boj_from_2016(df, boj):
    assert (df.loc["2016-01":, "target"] - boj.loc["2016-01":]).abs().max() < 1e-9


def test_no_gaps(df):
    """Every month from Jan 2006 to the latest month has a value."""
    expected = pd.period_range("2006-01", df.index[-1], freq="M")
    assert df.index.equals(expected)
    assert df["target"].notna().all()
    assert df.index[-1] >= pd.Period("2026-08", "M")


def test_differences_from_official_only_at_listed_events(df):
    """Before Oct 2019, the target differs from the official series only in the 2010
    tuition months and the 2014 tax months, apart from rounding (at most 0.1 pp).
    From Oct 2019 the differences are the BOJ's own adjustments (tax, free education,
    travel subsidies, mobile fees), taken as published."""
    diff = (df.loc[:"2019-09", "target"] - df.loc[:"2019-09", "official"]).round(1)
    tuition = diff.loc["2010-04":"2011-03"]
    tax = diff.loc["2014-04":"2015-03"]
    assert (tuition == 0.6).all()
    assert tax.between(-2.0, -1.8).all()
    other = diff.drop(tuition.index).drop(tax.index).drop(pd.Period("2015-04", "M"))
    assert other.abs().max() <= 0.1
