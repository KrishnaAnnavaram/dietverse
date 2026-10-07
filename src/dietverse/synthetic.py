"""Synthetic files in the layout of the COVID-19 Healthy Diet data set, with its quirks.

The countries are invented ("Country 001", ...). Food-group values add up to 50 and the two
aggregates add up to 50, as in the real files. ``Undernourished`` has some "<2.5" strings and
some outcome cells are empty. A covariates file with invented median ages is also written.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .data import AGGREGATES, GROUPS, MEASURES, UNIT_COLUMN

ANIMAL = {"Animal fats", "Aquatic Products, Other", "Eggs", "Fish, Seafood", "Meat", "Milk - Excluding Butter", "Offals"}


# Typical relative weights inside the animal part and the plant part of a national supply.
BASE = {"Animal fats": 0.10, "Aquatic Products, Other": 0.01, "Eggs": 0.07, "Fish, Seafood": 0.10, "Meat": 0.35,
        "Milk - Excluding Butter": 0.32, "Offals": 0.05, "Alcoholic Beverages": 0.04, "Cereals - Excluding Beer": 0.45,
        "Fruits - Excluding Wine": 0.04, "Miscellaneous": 0.01, "Oilcrops": 0.02, "Pulses": 0.04, "Spices": 0.005,
        "Starchy Roots": 0.08, "Stimulants": 0.01, "Sugar & Sweeteners": 0.10, "Sugar Crops": 0.005,
        "Treenuts": 0.01, "Vegetable Oils": 0.10, "Vegetables": 0.04}


def _measure_table(rng: np.random.Generator, n: int, animal_share: np.ndarray) -> pd.DataFrame:
    rows = []
    base = np.array([BASE[g] for g in GROUPS])
    for i in range(n):
        weights = base * rng.gamma(8.0, 1 / 8.0, len(GROUPS))
        animal_idx = [j for j, g in enumerate(GROUPS) if g in ANIMAL]
        plant_idx = [j for j, g in enumerate(GROUPS) if g not in ANIMAL]
        w = np.zeros(len(GROUPS))
        w[animal_idx] = weights[animal_idx] / weights[animal_idx].sum() * animal_share[i]
        w[plant_idx] = weights[plant_idx] / weights[plant_idx].sum() * (1 - animal_share[i])
        values = np.round(w * 50, 4)
        values[-1] += round(50 - values.sum(), 4)  # make the row add up to 50 after rounding
        row = dict(zip(GROUPS, values))
        row["Animal Products"] = round(50 * animal_share[i], 4)
        row["Vegetal Products"] = round(50 - row["Animal Products"], 4)
        rows.append(row)
    return pd.DataFrame(rows)


def write_synthetic(out: Path, n_countries: int = 60, seed: int = 11) -> Path:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    countries = [f"Country {i:03d}" for i in range(1, n_countries + 1)]
    development = rng.random(n_countries)                       # hidden driver of everything below
    animal_share = np.clip(0.1 + 0.4 * development + rng.normal(0, 0.05, n_countries), 0.05, 0.6)
    median_age = np.round(18 + 25 * development + rng.normal(0, 3, n_countries), 1)
    obesity = np.round(np.clip(3 + 25 * development + rng.normal(0, 4, n_countries), 1, 40), 1)
    under = np.round(np.clip(30 * (1 - development) + rng.normal(0, 3, n_countries), 0.5, 45), 1)
    confirmed = np.clip(0.05 + 4 * development ** 2 + rng.normal(0, 0.3, n_countries), 0.01, None)
    deaths = np.clip(confirmed * (0.01 + 0.02 * (median_age - 18) / 25) + rng.normal(0, 0.003, n_countries), 0.0001, None)
    population = rng.integers(100_000, 90_000_000, n_countries)
    base = pd.DataFrame({
        "Obesity": obesity,
        "Undernourished": [("<2.5" if u < 2.5 else f"{u:.1f}") for u in under],
        "Confirmed": confirmed, "Deaths": deaths, "Recovered": confirmed * 0.6, "Active": confirmed * 0.35,
        "Population": population,
    })
    base.loc[rng.choice(n_countries, 3, replace=False), ["Confirmed", "Deaths", "Recovered", "Active"]] = np.nan
    base.loc[rng.choice(n_countries, 2, replace=False), "Undernourished"] = np.nan
    for m, fname in MEASURES.items():
        shift = {"energy": 0.0, "quantity": 0.05, "fat": 0.15, "protein": 0.1}[m]
        t = _measure_table(rng, n_countries, np.clip(animal_share + shift, 0.05, 0.8))
        df = pd.concat([pd.DataFrame({"Country": countries}), t[GROUPS[:1] + AGGREGATES[:1] + GROUPS[1:] + AGGREGATES[1:]],
                        base], axis=1)
        df[UNIT_COLUMN] = "%"
        df.to_csv(out / fname, index=False)
    pd.DataFrame({"Country": countries, "median_age": median_age}).to_csv(out / "covariates.csv", index=False)
    (out / "SYNTHETIC").write_text("Synthetic files written by dietverse. Not real country data.\n", encoding="utf-8")
    return out
