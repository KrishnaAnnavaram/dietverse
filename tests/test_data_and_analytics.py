import numpy as np
import pandas as pd
import pytest

from dietverse.analytics import ECOLOGICAL_CAVEAT, associations, cfr_vs_deaths, load_covariates, partial_spearman, spearman
from dietverse.data import GROUPS, MEASURE_LABEL, DataError, read_measure


def test_shares_add_up_to_100_with_the_correct_unit(ds):
    s = ds.shares("energy")
    assert np.allclose(s.sum(axis=1), 100)
    prof = ds.country_profile(ds.countries()[0])
    assert prof["unit"] == MEASURE_LABEL["energy"] and "kcal (Recommended)" not in str(prof)
    raw = ds.tables["energy"].set_index("Country")
    c = ds.countries()[0]
    assert s.loc[c, GROUPS[0]] == pytest.approx(2 * raw.loc[c, GROUPS[0]], rel=1e-3)


def test_censored_undernourishment_is_flagged(ds):
    t = ds.tables["energy"]
    assert t["undernourished_censored"].any()
    assert (t.loc[t["undernourished_censored"], "Undernourished"] == 2.5).all()
    assert ds.reports["energy"].censored_undernourished == int(t["undernourished_censored"].sum())


def test_wrong_unit_and_wrong_sums_are_errors(data_dir, tmp_path):
    df = pd.read_csv(data_dir / "Food_Supply_kcal_Data.csv")
    df["Unit (all except Population)"] = "kcal"
    df.to_csv(tmp_path / "Food_Supply_kcal_Data.csv", index=False)
    with pytest.raises(DataError, match="unit"):
        read_measure(tmp_path, "energy")
    df["Unit (all except Population)"] = "%"
    df.loc[0, "Meat"] += 10
    df.to_csv(tmp_path / "Food_Supply_kcal_Data.csv", index=False)
    with pytest.raises(DataError, match="add up to 50"):
        read_measure(tmp_path, "energy")
    df.drop(columns=["Meat"]).to_csv(tmp_path / "Food_Supply_kcal_Data.csv", index=False)
    with pytest.raises(DataError, match="lacks columns"):
        read_measure(tmp_path, "energy")


def test_outcomes_have_explicit_units(ds):
    o = ds.outcomes()
    row = o.dropna().iloc[0]
    assert row["deaths_per_100k"] == pytest.approx(row["deaths_pct"] * 1000)
    assert row["cfr_pct"] == pytest.approx(100 * row["deaths_pct"] / row["confirmed_pct"])
    assert o["deaths_pct"].isna().sum() == 3


def test_correlation_helpers():
    x = np.arange(20.0)
    assert spearman(x, x ** 2) == pytest.approx(1.0)
    rng = np.random.default_rng(0)
    z = rng.normal(0, 1, 300)  # a common driver
    y = z + rng.normal(0, 0.5, 300)
    xx = z + rng.normal(0, 0.5, 300)
    assert spearman(xx, y) > 0.7
    assert abs(partial_spearman(xx, y, z.reshape(-1, 1))) < 0.2
    assert partial_spearman(xx, y, None) == spearman(xx, y)


def test_associations_drop_missing_rows_and_use_controls(ds, data_dir):
    cov = load_covariates(data_dir / "covariates.csv")
    res = associations(ds, ["obesity_pct", "Meat"], "deaths_per_100k", covariates=cov, n_boot=50)
    r = res["results"][0]
    assert r["n_countries"] + r["dropped_countries"] == 50 and r["dropped_countries"] >= 3
    assert r["controls"] == ["undernourished_pct", "median_age"]
    assert abs(r["partial_spearman"]) < abs(r["spearman"])  # the hidden development driver is partly removed
    lo, hi = r["partial_ci95"]
    assert lo <= hi and res["caveat"] == ECOLOGICAL_CAVEAT
    with pytest.raises(KeyError):
        associations(ds, ["nothing"], "deaths_per_100k", n_boot=10)


def test_cfr_check(ds):
    res = cfr_vs_deaths(ds)
    assert res["n_countries"] == 47 and -1 <= res["spearman_cfr_vs_deaths"] <= 1


def test_covariates_need_a_country_column(tmp_path):
    (tmp_path / "c.csv").write_text("name,median_age\nA,30\n")
    with pytest.raises(ValueError):
        load_covariates(tmp_path / "c.csv")
