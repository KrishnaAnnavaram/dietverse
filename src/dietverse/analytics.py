"""Country-level (ecological) analysis with controls and intervals.

Every result here is about countries, not about persons. A country-level association does not show
that a person with more of a food group or more body fat has a higher risk (the ecological fallacy).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .data import Dataset

ECOLOGICAL_CAVEAT = (
    "Country-level association only. It does not apply to persons. Testing, reporting, age structure and "
    "income differ between countries and can explain the association."
)
DEFAULT_CONTROLS = ["undernourished_pct"]


def _rank(x: np.ndarray) -> np.ndarray:
    return pd.Series(x).rank().to_numpy()


def spearman(x, y) -> float:
    rx, ry = _rank(np.asarray(x, float)), _rank(np.asarray(y, float))
    if rx.std() == 0 or ry.std() == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def partial_spearman(x, y, controls: np.ndarray | None) -> float:
    """Spearman correlation of x and y after a linear fit of their ranks on the ranks of the controls."""
    if controls is None or controls.size == 0:
        return spearman(x, y)
    rx, ry = _rank(np.asarray(x, float)), _rank(np.asarray(y, float))
    z = np.column_stack([np.ones(len(rx))] + [_rank(c) for c in np.asarray(controls, float).T])
    res_x = rx - z @ np.linalg.lstsq(z, rx, rcond=None)[0]
    res_y = ry - z @ np.linalg.lstsq(z, ry, rcond=None)[0]
    if res_x.std() == 0 or res_y.std() == 0:
        return float("nan")
    return float(np.corrcoef(res_x, res_y)[0, 1])


def bootstrap_ci(x, y, controls, *, n_boot: int, seed: int) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = len(x)
    vals = []
    for _ in range(n_boot):
        i = rng.integers(0, n, n)
        c = None if controls is None else controls[i]
        v = partial_spearman(np.asarray(x)[i], np.asarray(y)[i], c)
        if not np.isnan(v):
            vals.append(v)
    if not vals:
        return (float("nan"), float("nan"))
    return (round(float(np.quantile(vals, 0.025)), 3), round(float(np.quantile(vals, 0.975)), 3))


def load_covariates(path: Path) -> pd.DataFrame:
    """Optional CSV with a ``Country`` column and numeric control columns, for example median age."""
    cov = pd.read_csv(path)
    if "Country" not in cov.columns:
        raise ValueError(f"{path} needs a 'Country' column")
    num = cov.drop(columns="Country").apply(pd.to_numeric, errors="coerce")
    if num.shape[1] == 0:
        raise ValueError(f"{path} has no control columns")
    return num.assign(Country=cov["Country"]).set_index("Country")


def associations(ds: Dataset, exposures: list[str], outcome: str, *, measure: str = "energy",
                 covariates: pd.DataFrame | None = None, n_boot: int = 500, seed: int = 0) -> dict:
    """Raw and partial Spearman correlations of exposures with one outcome, over countries.

    Countries with a missing value in any used column are left out, and the report gives the count.
    """
    out = ds.outcomes()
    table = ds.shares(measure).join(out, how="inner")
    controls = list(DEFAULT_CONTROLS)
    if covariates is not None:
        table = table.join(covariates, how="left")
        controls += list(covariates.columns)
    rows = []
    for exp in exposures:
        if exp not in table.columns:
            raise KeyError(f"unknown exposure {exp!r}")
        cols = [exp, outcome] + [c for c in controls if c != exp]
        sub = table[cols].dropna()
        ctrl = sub[[c for c in controls if c != exp]].to_numpy() if controls else None
        x, y = sub[exp].to_numpy(), sub[outcome].to_numpy()
        rows.append({
            "exposure": exp, "outcome": outcome, "n_countries": int(len(sub)),
            "dropped_countries": int(len(table) - len(sub)),
            "spearman": round(spearman(x, y), 3),
            "partial_spearman": round(partial_spearman(x, y, ctrl), 3),
            "partial_ci95": bootstrap_ci(x, y, ctrl, n_boot=n_boot, seed=seed),
            "controls": [c for c in controls if c != exp],
        })
    return {"measure": measure, "outcome": outcome, "results": rows, "caveat": ECOLOGICAL_CAVEAT}


def cfr_vs_deaths(ds: Dataset) -> dict:
    """How far the case-fatality ratio and deaths per 100,000 disagree in country rank."""
    o = ds.outcomes()[["cfr_pct", "deaths_per_100k", "confirmed_pct"]].dropna()
    return {"n_countries": int(len(o)), "spearman_cfr_vs_deaths": round(spearman(o["cfr_pct"], o["deaths_per_100k"]), 3),
            "spearman_cfr_vs_confirmed": round(spearman(o["cfr_pct"], o["confirmed_pct"]), 3),
            "note": "CFR = deaths / confirmed cases. It depends on how many cases a country tests and reports."}
