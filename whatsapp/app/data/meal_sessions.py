"""Meal / service session labels — matches wedding menu Excel layout."""

from app.models import DishCategory

MEAL_SESSION_LABELS: dict[DishCategory, str] = {
    DishCategory.BREAKFAST: "Breakfast",
    DishCategory.LUNCH: "Lunch",
    DishCategory.DINNER: "Dinner",
    DishCategory.RECEPTION_DINNER: "Reception Dinner",
    DishCategory.COFFEE: "Coffee",
    DishCategory.TEA: "Tea",
    DishCategory.JUICE: "Juice",
    DishCategory.DESSERT: "Dessert",
    DishCategory.SNACKS: "Snacks",
}

MEAL_SESSION_ORDER: list[str] = [
    "Breakfast",
    "Lunch",
    "Dinner",
    "Reception Dinner",
    "Snacks",
    "Coffee",
    "Tea",
    "Juice",
    "Dessert",
    "Meal Preference",
    "Cuisine Preference",
]

PREFERENCE_SESSION_LABELS = frozenset({"Meal Preference", "Cuisine Preference"})

LABEL_TO_DISH_CATEGORY: dict[str, DishCategory] = {v: k for k, v in MEAL_SESSION_LABELS.items()}
LABEL_TO_DISH_CATEGORY.update(
    {
        "reception dinner": DishCategory.RECEPTION_DINNER,
        "Reception dinner": DishCategory.RECEPTION_DINNER,
    }
)

OLD_DISH_ENUM_MAP: dict[str, str] = {
    "SOUTH_INDIAN": "BREAKFAST",
    "NORTH_INDIAN": "LUNCH",
    "CHINESE": "DINNER",
    "SNACKS": "SNACKS",
    "DESSERTS": "DESSERT",
    "BEVERAGES": "COFFEE",
}

OLD_ENQUIRY_CATEGORY_MAP: dict[str, str] = {
    "South Indian": "Breakfast",
    "North Indian": "Lunch",
    "Chinese": "Dinner",
    "Snacks": "Snacks",
    "Snacks & Starters": "Snacks",
    "Desserts": "Dessert",
    "Beverages": "Coffee",
    "Multi Cuisine": "Lunch",
}

# Enum DB values → display labels (after Dish.category became free-text)
ENUM_VALUE_TO_LABEL: dict[str, str] = {
    **{c.value: label for c, label in MEAL_SESSION_LABELS.items()},
    **{c.name: label for c, label in MEAL_SESSION_LABELS.items()},
}


def custom_session_label(label: str) -> str | None:
    """Allow a free-form session name (High Tea, Midnight Snacks, …)."""
    trimmed = " ".join(label.split())
    if not trimmed or len(trimmed) > 40:
        return None
    if trimmed.lower() in {p.lower() for p in PREFERENCE_SESSION_LABELS}:
        return None
    return trimmed


def normalize_meal_session_label(label: str) -> str | None:
    trimmed = label.strip()
    if not trimmed:
        return None
    if trimmed in MEAL_SESSION_LABELS.values():
        return trimmed
    key = trimmed.lower()
    for _cat, lbl in MEAL_SESSION_LABELS.items():
        if lbl.lower() == key:
            return lbl
    if key in LABEL_TO_DISH_CATEGORY:
        return MEAL_SESSION_LABELS[LABEL_TO_DISH_CATEGORY[key]]
    enum_hit = ENUM_VALUE_TO_LABEL.get(trimmed) or ENUM_VALUE_TO_LABEL.get(trimmed.upper())
    if enum_hit:
        return enum_hit
    return custom_session_label(trimmed)


def dish_category_label(category: DishCategory | str) -> str:
    if isinstance(category, DishCategory):
        return MEAL_SESSION_LABELS[category]
    mapped = ENUM_VALUE_TO_LABEL.get(str(category)) or ENUM_VALUE_TO_LABEL.get(str(category).upper())
    if mapped:
        return mapped
    if str(category) in MEAL_SESSION_LABELS.values():
        return str(category)
    return str(category)
