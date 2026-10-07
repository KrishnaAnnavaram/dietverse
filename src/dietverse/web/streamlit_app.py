"""Streamlit dashboard (extra: web). Run with: dietverse web  (or streamlit run this file)."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from dietverse import DISCLAIMER
from dietverse.analytics import ECOLOGICAL_CAVEAT, associations, cfr_vs_deaths, load_covariates
from dietverse.data import GROUPS, MEASURE_LABEL, MEASURES, load_dataset
from dietverse.energy import ACTIVITY_FACTORS
from dietverse.guidelines import ALLERGENS, DIETS, INTOLERANCES
from dietverse.plan import CONDITIONS, Profile, make_plan
from dietverse.screener import OPTIONS, QUESTIONS, ScreenerAnswers, score

DATA_DIR = Path(os.environ.get("DIETVERSE_DATA_DIR", "data/covid-healthy-diet"))


@st.cache_data
def _load(path: str):
    return load_dataset(Path(path))


st.set_page_config(page_title="dietverse", layout="wide")
st.title("dietverse")
st.caption(DISCLAIMER)
try:
    ds = _load(str(DATA_DIR))
except FileNotFoundError as exc:
    st.error(f"{exc}. Run 'dietverse synth --out {DATA_DIR}' for synthetic data.")
    st.stop()

explore, analysis, plan_tab, screen_tab = st.tabs(["Explorer", "Country analysis", "Diet guide", "Wellbeing check"])

with explore:
    measure = st.selectbox("Measure", list(MEASURES), format_func=lambda m: MEASURE_LABEL[m])
    shares = ds.shares(measure)
    group = st.selectbox("Food group", GROUPS, index=GROUPS.index("Cereals - Excluding Beer"))
    st.caption(f"Unit: {MEASURE_LABEL[measure]}. The food groups of each country add up to 100%.")
    st.bar_chart(shares[group].sort_values(ascending=False).head(30))
    out = ds.outcomes()
    st.caption("Outcomes: deaths per 100,000 people. CFR depends on testing, so it is not shown here.")
    st.bar_chart(out["deaths_per_100k"].dropna().sort_values(ascending=False).head(30))

with analysis:
    st.warning(ECOLOGICAL_CAVEAT)
    outcome = st.selectbox("Outcome", ["deaths_per_100k", "obesity_pct", "cfr_pct"])
    exposures = st.multiselect("Exposures", GROUPS + ["obesity_pct"], default=["Animal fats", "obesity_pct"])
    cov_path = DATA_DIR / "covariates.csv"
    cov = load_covariates(cov_path) if cov_path.exists() else None
    exposures = [e for e in exposures if e != outcome]
    if exposures:
        res = associations(ds, exposures, outcome, covariates=cov, n_boot=300)
        st.dataframe(pd.DataFrame(res["results"]))
    st.json(cfr_vs_deaths(ds))

with plan_tab:
    with st.form("profile"):
        c1, c2, c3 = st.columns(3)
        age = c1.number_input("Age", 18, 100, 40)
        sex = c1.selectbox("Sex (for the energy equation)", ["female", "male"])
        weight = c2.number_input("Weight (kg)", 30.0, 300.0, 70.0)
        height = c2.number_input("Height (cm)", 125.0, 225.0, 170.0)
        activity = c3.selectbox("Activity", list(ACTIVITY_FACTORS))
        goal = c3.selectbox("Goal", ["maintain", "lose", "gain"])
        diet = st.selectbox("Diet", DIETS)
        allergies = st.multiselect("Allergies", ALLERGENS)
        intolerances = st.multiselect("Intolerances", list(INTOLERANCES))
        conditions = st.multiselect("Conditions", CONDITIONS)
        pregnant = st.checkbox("Pregnant or breastfeeding")
        country = st.selectbox("Country (context only)", [""] + ds.countries())
        submitted = st.form_submit_button("Make my guide")
    if submitted:
        p = Profile(age=age, sex=sex, weight_kg=weight, height_cm=height, activity=activity, goal=goal, diet=diet,
                    allergies=allergies, intolerances=intolerances, conditions=conditions,
                    pregnant_or_breastfeeding=pregnant, country=country or None)
        result = make_plan(p, ds.country_profile(country) if country else None)
        st.json(result.model_dump())

with screen_tab:
    st.caption("PHQ-2 and GAD-2. Over the last 2 weeks, how often were you bothered by these problems?")
    answers = {}
    for name, qs in QUESTIONS.items():
        answers[name] = [st.radio(q, list(OPTIONS), format_func=OPTIONS.get, key=f"{name}{i}", horizontal=True)
                         for i, q in enumerate(qs)]
    if st.button("Show my result"):
        st.json(score(ScreenerAnswers(**answers)))
