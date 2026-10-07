import pytest
from pydantic import ValidationError

from dietverse.energy import bmi, bmi_category, daily_energy, mifflin_st_jeor
from dietverse.guidelines import PATTERN, pattern_level
from dietverse.plan import Profile, make_plan
from dietverse.screener import ScreenerAnswers, score

BASE = dict(age=40, sex="female", weight_kg=70, height_cm=165, activity="moderate", goal="maintain")


def _plan(**kw):
    return make_plan(Profile(**{**BASE, **kw}))


def test_mifflin_st_jeor_known_values():
    assert mifflin_st_jeor("male", 80, 180, 30) == pytest.approx(1780)
    assert mifflin_st_jeor("female", 60, 165, 30) == pytest.approx(1320.25)
    e = daily_energy("male", 80, 180, 30, "moderate", "maintain")
    assert e["maintenance_kcal"] == round(1780 * 1.55)
    assert daily_energy("female", 45, 150, 80, "sedentary", "lose")["target_kcal"] == 1200


def test_bmi():
    assert bmi(70, 175) == pytest.approx(22.86, abs=0.01)
    assert [bmi_category(v) for v in (17, 22, 27, 33)] == ["underweight", "healthy weight", "overweight", "obesity"]


def test_pattern_level_is_nearest_in_range():
    assert pattern_level(2050) == 2000 and pattern_level(900) == 1600 and pattern_level(5000) == 3200
    assert PATTERN[2000] == (2.5, 2.0, 6, 3, 5.5, 27)


@pytest.mark.parametrize("field, value", [
    ("age", 70), ("sex", "male"), ("weight_kg", 95), ("height_cm", 185), ("activity", "very_active"), ("goal", "lose"),
    ("diet", "vegan"), ("allergies", ["fish"]), ("intolerances", ["lactose"]), ("conditions", ["hypertension"]),
    ("pregnant_or_breastfeeding", True),
])
def test_every_personal_field_changes_the_plan(field, value):
    assert _plan(**{field: value}).model_dump() != _plan().model_dump()


def test_diet_and_allergy_filters():
    vegan = _plan(diet="vegan", allergies=["soy"])
    dairy = next(t for t in vegan.targets if t.group == "dairy")
    assert dairy.examples == [] and any("dairy" in n for n in vegan.notes)
    protein = next(t for t in vegan.targets if t.group == "protein_foods")
    assert "salmon" not in protein.examples and "tofu" not in protein.examples and "lentils" in protein.examples
    lactose = next(t for t in _plan(intolerances=["lactose"]).targets if t.group == "dairy")
    assert "lactose-free milk" in lactose.examples and "low-fat milk" not in lactose.examples


def test_referral_and_condition_notes():
    assert _plan(pregnant_or_breastfeeding=True).status == "referral"
    kidney = _plan(conditions=["kidney_disease"])
    assert next(t for t in kidney.targets if t.group == "protein_foods").amount == 0
    assert "1,500 mg" in _plan(conditions=["hypertension"]).limits["sodium"]
    thin = make_plan(Profile(**{**BASE, "weight_kg": 50, "goal": "lose"}))
    assert any("Talk to a doctor before you try to lose weight" in n for n in thin.notes)


def test_profile_validation():
    for bad in ({"age": 15}, {"sex": "x"}, {"activity": "couch"}, {"allergies": ["kiwi"]}, {"height_cm": 20}):
        with pytest.raises(ValidationError):
            Profile(**{**BASE, **bad})
    with pytest.raises(ValidationError):
        Profile(**BASE, budget=10)


def test_country_context_is_labelled_context(ds):
    plan = make_plan(Profile(**BASE, country=ds.countries()[0]), ds.country_profile(ds.countries()[0]))
    assert plan.country_context["unit"].startswith("% of dietary energy supply")
    assert any("not a target" in n for n in plan.notes)


def test_phq2_gad2_scoring():
    r = score(ScreenerAnswers(phq2=[1, 1], gad2=[2, 1]))
    assert r["phq2"] == {"total": 2, "positive": False} and r["gad2"] == {"total": 3, "positive": True}
    assert "not a diagnosis" in r["message"]
    assert not score(ScreenerAnswers(phq2=[0, 0], gad2=[0, 2]))["gad2"]["positive"]
    with pytest.raises(ValueError):
        score(ScreenerAnswers(phq2=[4, 0], gad2=[0, 0]))
    with pytest.raises(ValidationError):
        ScreenerAnswers(phq2=[1], gad2=[0, 0])
