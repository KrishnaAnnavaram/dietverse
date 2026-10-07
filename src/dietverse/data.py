"""Loader for the COVID-19 Healthy Diet CSV files, with the unit rules.

Facts about the files (checked by ``validate_shares``):
- Each food-group value is a percentage. In every row the 21 detailed groups add up to 50 and the two
  aggregates ("Animal Products", "Vegetal Products") add up to the other 50. So the share of the
  national supply of one group is 2 x the value (the loader divides by the row sum and multiplies by 100).
- ``Obesity``, ``Undernourished``, ``Confirmed``, ``Deaths``, ``Recovered`` and ``Active`` are % of the population.
- ``Undernourished`` has the text "<2.5". The loader keeps 2.5 as an upper bound and sets a flag.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

MEASURES = {
    "energy": "Food_Supply_kcal_Data.csv",
    "quantity": "Food_Supply_Quantity_kg_Data.csv",
    "fat": "Fat_Supply_Quantity_Data.csv",
    "protein": "Protein_Supply_Quantity_Data.csv",
}
MEASURE_LABEL = {
    "energy": "% of dietary energy supply (kcal)",
    "quantity": "% of food supply by weight (kg)",
    "fat": "% of fat supply",
    "protein": "% of protein supply",
}
AGGREGATES = ["Animal Products", "Vegetal Products"]
GROUPS = [
    "Alcoholic Beverages", "Animal fats", "Aquatic Products, Other", "Cereals - Excluding Beer", "Eggs",
    "Fish, Seafood", "Fruits - Excluding Wine", "Meat", "Milk - Excluding Butter", "Miscellaneous", "Offals",
    "Oilcrops", "Pulses", "Spices", "Starchy Roots", "Stimulants", "Sugar & Sweeteners", "Sugar Crops", "Treenuts",
    "Vegetable Oils", "Vegetables",
]
POPULATION_PCT = ["Obesity", "Undernourished", "Confirmed", "Deaths", "Recovered", "Active"]
UNIT_COLUMN = "Unit (all except Population)"
REQUIRED = ["Country", *GROUPS, *AGGREGATES, *POPULATION_PCT, "Population", UNIT_COLUMN]
SUM_TOLERANCE = 0.5


class DataError(ValueError):
    pass


@dataclass
class LoadReport:
    measure: str
    countries: int
    censored_undernourished: int
    missing: dict[str, int] = field(default_factory=dict)
    share_sum_range: tuple[float, float] = (0.0, 0.0)


def read_measure(data_dir: Path, measure: str) -> tuple[pd.DataFrame, LoadReport]:
    path = Path(data_dir) / MEASURES[measure]
    if not path.exists():
        raise FileNotFoundError(f"{path} not found (see data/README.md or run 'dietverse synth')")
    df = pd.read_csv(path)
    missing_cols = sorted(set(REQUIRED) - set(df.columns))
    if missing_cols:
        raise DataError(f"{path.name} lacks columns {missing_cols}")
    units = set(df[UNIT_COLUMN].dropna().astype(str).str.strip())
    if units != {"%"}:
        raise DataError(f"{path.name}: expected the unit '%', found {sorted(units)}")
    if df["Country"].duplicated().any():
        raise DataError(f"{path.name}: duplicate countries")
    und = df["Undernourished"].astype("string").str.strip()
    censored = und.str.startswith("<").fillna(False)
    df["Undernourished"] = pd.to_numeric(und.str.lstrip("<"), errors="coerce")
    df["undernourished_censored"] = censored.astype(bool)
    for c in [*GROUPS, *AGGREGATES, *POPULATION_PCT, "Population"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    sums = validate_shares(df, path.name)
    rep = LoadReport(measure, len(df), int(censored.sum()),
                     {c: int(n) for c, n in df[POPULATION_PCT].isna().sum().items() if n},
                     (round(float(sums.min()), 3), round(float(sums.max()), 3)))
    return df.drop(columns=[UNIT_COLUMN]), rep


def validate_shares(df: pd.DataFrame, name: str) -> pd.Series:
    groups = df[GROUPS].sum(axis=1)
    aggs = df[AGGREGATES].sum(axis=1)
    if ((groups - 50).abs() > SUM_TOLERANCE).any() or ((aggs - 50).abs() > SUM_TOLERANCE).any():
        raise DataError(f"{name}: the food groups and the aggregates must each add up to 50 in every row")
    return groups


def shares(df: pd.DataFrame) -> pd.DataFrame:
    """Share of the national supply of each detailed food group, in %, so the groups add up to 100."""
    g = df[GROUPS]
    return g.div(g.sum(axis=1), axis=0).mul(100).assign(Country=df["Country"].values).set_index("Country")


def outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Country outcomes with explicit units. CFR is reported, but it depends on testing."""
    out = df[["Country", "Obesity", "Undernourished", "undernourished_censored", "Confirmed", "Deaths",
              "Population"]].copy()
    out = out.rename(columns={"Obesity": "obesity_pct", "Undernourished": "undernourished_pct",
                              "Confirmed": "confirmed_pct", "Deaths": "deaths_pct", "Population": "population"})
    out["deaths_per_100k"] = out["deaths_pct"] * 1000.0
    out["cfr_pct"] = np.where(out["confirmed_pct"] > 0, 100 * out["deaths_pct"] / out["confirmed_pct"], np.nan)
    return out.set_index("Country")


@dataclass
class Dataset:
    tables: dict[str, pd.DataFrame]
    reports: dict[str, LoadReport]

    def shares(self, measure: str) -> pd.DataFrame:
        return shares(self.tables[measure])

    def outcomes(self) -> pd.DataFrame:
        return outcomes(self.tables["energy"])

    def countries(self) -> list[str]:
        return sorted(self.tables["energy"]["Country"])

    def country_profile(self, country: str, measure: str = "energy", top: int = 6) -> dict:
        s = self.shares(measure)
        if country not in s.index:
            raise KeyError(f"unknown country {country!r}")
        row = s.loc[country].sort_values(ascending=False).head(top)
        return {"country": country, "unit": MEASURE_LABEL[measure],
                "top_groups": {k: round(float(v), 1) for k, v in row.items()}}


def load_dataset(data_dir: Path) -> Dataset:
    tables, reports = {}, {}
    for m in MEASURES:
        tables[m], reports[m] = read_measure(data_dir, m)
    return Dataset(tables, reports)
