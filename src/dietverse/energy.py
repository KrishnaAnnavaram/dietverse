"""Energy needs from the person: BMI, Mifflin-St Jeor resting energy and an activity factor."""

from __future__ import annotations

ACTIVITY_FACTORS = {
    "sedentary": 1.2,     # little or no exercise
    "light": 1.375,       # light exercise 1-3 days a week
    "moderate": 1.55,     # moderate exercise 3-5 days a week
    "active": 1.725,      # hard exercise 6-7 days a week
    "very_active": 1.9,   # physical job or training two times a day
}
GOAL_ADJUSTMENT = {"maintain": 0, "lose": -500, "gain": 300}
MIN_KCAL = {"female": 1200, "male": 1500}


def bmi(weight_kg: float, height_cm: float) -> float:
    return weight_kg / (height_cm / 100) ** 2


def bmi_category(value: float) -> str:
    if value < 18.5:
        return "underweight"
    if value < 25:
        return "healthy weight"
    if value < 30:
        return "overweight"
    return "obesity"


def mifflin_st_jeor(sex: str, weight_kg: float, height_cm: float, age: int) -> float:
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    if sex == "male":
        return base + 5
    if sex == "female":
        return base - 161
    raise ValueError("sex must be 'male' or 'female' for the Mifflin-St Jeor equation")


def daily_energy(sex: str, weight_kg: float, height_cm: float, age: int, activity: str, goal: str) -> dict:
    if activity not in ACTIVITY_FACTORS:
        raise ValueError(f"activity must be one of {sorted(ACTIVITY_FACTORS)}")
    if goal not in GOAL_ADJUSTMENT:
        raise ValueError(f"goal must be one of {sorted(GOAL_ADJUSTMENT)}")
    rest = mifflin_st_jeor(sex, weight_kg, height_cm, age)
    maintain = rest * ACTIVITY_FACTORS[activity]
    target = max(maintain + GOAL_ADJUSTMENT[goal], MIN_KCAL[sex])
    return {"resting_kcal": round(rest), "maintenance_kcal": round(maintain), "target_kcal": round(target),
            "floor_applied": target == MIN_KCAL[sex] and maintain + GOAL_ADJUSTMENT[goal] < MIN_KCAL[sex]}
