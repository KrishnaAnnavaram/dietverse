"""Person-based diet guide. Every field of the profile has an effect on the plan or on its notes."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from . import DISCLAIMER
from .energy import ACTIVITY_FACTORS, GOAL_ADJUSTMENT, bmi, bmi_category, daily_energy
from .guidelines import ALLERGENS, DIETS, EXCLUDED_BY_DIET, FOODS, GROUPS, INTOLERANCES, LIMITS, PATTERN, UNITS, pattern_level

CONDITIONS = ("diabetes", "hypertension", "kidney_disease", "heart_disease", "covid_recovery")
CONDITION_NOTES = {
    "diabetes": "Diabetes: spread carbohydrate across the day and ask your care team for an individual carbohydrate plan.",
    "hypertension": "High blood pressure: a sodium limit of 1,500 mg a day is often advised. Ask your doctor.",
    "kidney_disease": "Kidney disease: protein, potassium and phosphorus targets must come from your kidney care team. "
                      "Do not use the protein target in this plan.",
    "heart_disease": "Heart disease: choose unsaturated fats and limit saturated fat. Follow your cardiology team.",
    "covid_recovery": "After COVID-19: eat enough energy and protein while you recover, and drink enough fluid. "
                      "If you lost weight or muscle, ask for a referral to a dietitian.",
}


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    age: int = Field(ge=18, le=100, description="adults only")
    sex: Literal["female", "male"]
    weight_kg: float = Field(gt=25, lt=350)
    height_cm: float = Field(gt=120, lt=230)
    activity: str = "sedentary"
    goal: str = "maintain"
    diet: str = "omnivore"
    allergies: list[str] = Field(default_factory=list)
    intolerances: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    pregnant_or_breastfeeding: bool = False
    country: str | None = None

    @field_validator("activity")
    @classmethod
    def _activity(cls, v):
        if v not in ACTIVITY_FACTORS:
            raise ValueError(f"activity must be one of {sorted(ACTIVITY_FACTORS)}")
        return v

    @field_validator("goal")
    @classmethod
    def _goal(cls, v):
        if v not in GOAL_ADJUSTMENT:
            raise ValueError(f"goal must be one of {sorted(GOAL_ADJUSTMENT)}")
        return v

    @field_validator("diet")
    @classmethod
    def _diet(cls, v):
        if v not in DIETS:
            raise ValueError(f"diet must be one of {list(DIETS)}")
        return v

    @field_validator("allergies", "intolerances", "conditions")
    @classmethod
    def _known(cls, v, info):
        allowed = {"allergies": ALLERGENS, "intolerances": tuple(INTOLERANCES), "conditions": CONDITIONS}[info.field_name]
        bad = [x for x in v if x not in allowed]
        if bad:
            raise ValueError(f"unknown {info.field_name}: {bad}. Use {list(allowed)}")
        return sorted(set(v))


class GroupTarget(BaseModel):
    group: str
    amount: float
    unit: str
    examples: list[str]


class DietPlan(BaseModel):
    status: Literal["plan", "referral"]
    bmi: float | None = None
    bmi_category: str | None = None
    energy: dict | None = None
    pattern_kcal: int | None = None
    targets: list[GroupTarget] = Field(default_factory=list)
    limits: dict[str, str] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    country_context: dict | None = None
    disclaimer: str = DISCLAIMER


def _excluded_tags(p: Profile) -> set[str]:
    tags = set(EXCLUDED_BY_DIET[p.diet]) | set(p.allergies)
    for name in p.intolerances:
        tags.add(INTOLERANCES[name])
    return tags


def examples_for(group: str, excluded: set[str]) -> list[str]:
    return [name for name, g, tags in FOODS if g == group and not (tags & excluded)]


def make_plan(p: Profile, country_context: dict | None = None) -> DietPlan:
    if p.pregnant_or_breastfeeding:
        return DietPlan(status="referral", notes=[
            "Energy and nutrient needs change during pregnancy and breastfeeding. This guide does not cover them. "
            "Ask your midwife, doctor or a registered dietitian."])
    value = bmi(p.weight_kg, p.height_cm)
    energy = daily_energy(p.sex, p.weight_kg, p.height_cm, p.age, p.activity, p.goal)
    level = pattern_level(energy["target_kcal"])
    excluded = _excluded_tags(p)
    targets = []
    notes: list[str] = []
    for group, amount in zip(GROUPS, PATTERN[level]):
        ex = examples_for(group, excluded)
        if not ex and group != "oils":
            notes.append(f"No example food for {group} is left after your diet, allergies and intolerances. "
                         "Ask a dietitian for alternatives.")
        targets.append(GroupTarget(group=group, amount=amount, unit=UNITS[group], examples=ex))
    if p.diet == "vegan":
        notes.append("Vegan diet: use fortified foods or a supplement for vitamin B12.")
    if "kidney_disease" in p.conditions:
        targets = [t if t.group != "protein_foods" else GroupTarget(group=t.group, amount=0, unit=t.unit,
                                                                     examples=t.examples) for t in targets]
    notes += [CONDITION_NOTES[c] for c in p.conditions]
    category = bmi_category(value)
    if p.goal == "lose" and category in {"underweight", "healthy weight"}:
        notes.append(f"Your BMI is in the {category} range. Talk to a doctor before you try to lose weight.")
    if energy["floor_applied"]:
        notes.append("The target is at the minimum energy level for this guide. Do not eat less without medical advice.")
    if energy["target_kcal"] < min(PATTERN) or energy["target_kcal"] > max(PATTERN):
        notes.append(f"Your energy target is outside the pattern range. The food groups use the {level} kcal level.")
    limits = dict(LIMITS)
    if "hypertension" in p.conditions:
        limits["sodium"] = "less than 1,500 mg a day (ask your doctor)"
    if country_context:
        notes.append("Country context shows the national food supply, not what a person eats. It is not a target.")
    return DietPlan(status="plan", bmi=round(value, 1), bmi_category=category, energy=energy, pattern_kcal=level,
                    targets=targets, limits=limits, notes=notes, country_context=country_context)
