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


def normalize_meal_session_label(label: str) -> str | None:
    trimmed = label.strip()
    if trimmed in MEAL_SESSION_LABELS.values():
        return trimmed
    key = trimmed.lower()
    for cat, lbl in MEAL_SESSION_LABELS.items():
        if lbl.lower() == key:
            return lbl
    if key in LABEL_TO_DISH_CATEGORY:
        return MEAL_SESSION_LABELS[LABEL_TO_DISH_CATEGORY[key]]
    return None
