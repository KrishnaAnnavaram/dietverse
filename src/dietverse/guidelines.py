"""Food-group targets for each energy level, and example foods with diet and allergen tags.

The targets follow the Healthy U.S.-Style Dietary Pattern for ages 2 and older (Dietary Guidelines for
Americans 2020-2025, Appendix 3). Check them against the source before you use them for other purposes.
"""

from __future__ import annotations

# kcal level -> (vegetables cup-eq, fruits cup-eq, grains oz-eq, dairy cup-eq, protein foods oz-eq, oils g)
PATTERN: dict[int, tuple[float, float, float, float, float, float]] = {
    1600: (2.0, 1.5, 5, 3, 5.0, 22),
    1800: (2.5, 1.5, 6, 3, 5.0, 24),
    2000: (2.5, 2.0, 6, 3, 5.5, 27),
    2200: (3.0, 2.0, 7, 3, 6.0, 29),
    2400: (3.0, 2.0, 8, 3, 6.5, 31),
    2600: (3.5, 2.0, 9, 3, 6.5, 34),
    2800: (3.5, 2.5, 10, 3, 7.0, 36),
    3000: (4.0, 2.5, 10, 3, 7.0, 44),
    3200: (4.0, 2.5, 10, 3, 7.0, 51),
}
GROUPS = ("vegetables", "fruits", "grains", "dairy", "protein_foods", "oils")
UNITS = {"vegetables": "cup-eq", "fruits": "cup-eq", "grains": "oz-eq", "dairy": "cup-eq",
         "protein_foods": "oz-eq", "oils": "g"}
LIMITS = {
    "added_sugars": "less than 10% of energy",
    "saturated_fat": "less than 10% of energy",
    "sodium": "less than 2,300 mg a day",
}

DIETS = ("omnivore", "vegetarian", "vegan", "pescatarian")
ALLERGENS = ("dairy", "egg", "fish", "shellfish", "peanut", "tree_nut", "soy", "wheat", "sesame")
INTOLERANCES = {"lactose": "dairy_lactose", "gluten": "gluten"}

# name, group, tags. Tags: animal kinds ("meat", "poultry", "fish", "shellfish", "egg", "dairy"),
# allergens and "gluten" / "dairy_lactose".
FOODS: list[tuple[str, str, set[str]]] = [
    ("leafy greens", "vegetables", set()), ("carrots", "vegetables", set()), ("broccoli", "vegetables", set()),
    ("tomatoes", "vegetables", set()), ("beans and lentils (as a vegetable)", "vegetables", set()),
    ("apples", "fruits", set()), ("bananas", "fruits", set()), ("berries", "fruits", set()), ("oranges", "fruits", set()),
    ("oats", "grains", {"gluten"}), ("brown rice", "grains", set()), ("whole-wheat bread", "grains", {"wheat", "gluten"}),
    ("quinoa", "grains", set()), ("corn tortillas", "grains", set()),
    ("low-fat milk", "dairy", {"dairy", "dairy_lactose"}), ("plain yogurt", "dairy", {"dairy", "dairy_lactose"}),
    ("lactose-free milk", "dairy", {"dairy"}), ("fortified soy beverage", "dairy", {"soy"}),
    ("fortified soy yogurt", "dairy", {"soy"}),
    ("chicken", "protein_foods", {"poultry"}), ("lean beef", "protein_foods", {"meat"}),
    ("salmon", "protein_foods", {"fish"}), ("shrimp", "protein_foods", {"shellfish"}),
    ("eggs", "protein_foods", {"egg"}), ("lentils", "protein_foods", set()), ("chickpeas", "protein_foods", set()),
    ("tofu", "protein_foods", {"soy"}), ("peanut butter", "protein_foods", {"peanut"}),
    ("almonds", "protein_foods", {"tree_nut"}), ("sunflower seeds", "protein_foods", set()),
    ("tahini", "protein_foods", {"sesame"}),
    ("olive oil", "oils", set()), ("canola oil", "oils", set()), ("sunflower oil", "oils", set()),
]
EXCLUDED_BY_DIET = {
    "omnivore": set(),
    "pescatarian": {"meat", "poultry"},
    "vegetarian": {"meat", "poultry", "fish", "shellfish"},
    "vegan": {"meat", "poultry", "fish", "shellfish", "egg", "dairy"},
}


def pattern_level(target_kcal: float) -> int:
    """The pattern level nearest to the target, limited to the adult range 1,600 to 3,200 kcal."""
    levels = sorted(PATTERN)
    return min(levels, key=lambda lv: (abs(lv - target_kcal), lv))
