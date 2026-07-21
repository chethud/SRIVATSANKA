"""Default menu items seeded on first run."""

from sqlalchemy import select

from app.data.meal_sessions import MEAL_SESSION_LABELS
from app.models import Dish, DishCategory

# Re-export for existing imports (enum → label)
CATEGORY_LABELS = MEAL_SESSION_LABELS

DEFAULT_DISHES: list[tuple[str, DishCategory, float]] = [
    # Breakfast
    ("Thari Idly", DishCategory.BREAKFAST, 0),
    ("Thatte Idly", DishCategory.BREAKFAST, 0),
    ("Rave Idly", DishCategory.BREAKFAST, 0),
    ("Rava Idli", DishCategory.BREAKFAST, 0),
    ("Masala Dosa", DishCategory.BREAKFAST, 0),
    ("Mulbhaglu Dose", DishCategory.BREAKFAST, 0),
    ("Idli Sambar", DishCategory.BREAKFAST, 0),
    ("Pongal", DishCategory.BREAKFAST, 0),
    ("Khara Pongal", DishCategory.BREAKFAST, 0),
    ("Vade", DishCategory.BREAKFAST, 0),
    ("Paddu", DishCategory.BREAKFAST, 0),
    ("Bonda", DishCategory.BREAKFAST, 0),
    ("Shavige Bath", DishCategory.BREAKFAST, 0),
    ("Akki Thari coconut Upma", DishCategory.BREAKFAST, 0),
    ("Gojju Avalakki", DishCategory.BREAKFAST, 0),
    # Lunch
    ("Sambar Rice", DishCategory.LUNCH, 0),
    ("Lemon Rice", DishCategory.LUNCH, 0),
    ("Coconut Rice", DishCategory.LUNCH, 0),
    ("Curd Rice", DishCategory.LUNCH, 0),
    ("Raw Mango Rice", DishCategory.LUNCH, 0),
    ("Tomato Peas Bath", DishCategory.LUNCH, 0),
    ("Vegetable Biryani", DishCategory.LUNCH, 0),
    ("Veg Biryani", DishCategory.LUNCH, 0),
    ("Dal Makhani", DishCategory.LUNCH, 0),
    ("Chole Bhature", DishCategory.LUNCH, 0),
    ("Kabul Usli", DishCategory.LUNCH, 0),
    # Dinner / reception
    ("Paneer Butter Masala", DishCategory.DINNER, 0),
    ("Palak Paneer", DishCategory.DINNER, 0),
    ("Naan", DishCategory.DINNER, 0),
    ("Roti", DishCategory.DINNER, 0),
    ("Veg Fried Rice", DishCategory.RECEPTION_DINNER, 0),
    ("Noodles", DishCategory.RECEPTION_DINNER, 0),
    ("Manchurian", DishCategory.RECEPTION_DINNER, 0),
    ("Gobi Manchurian", DishCategory.RECEPTION_DINNER, 0),
    # Snacks
    ("Samosa", DishCategory.SNACKS, 0),
    ("Pakora", DishCategory.SNACKS, 0),
    ("Mangalore Bajji", DishCategory.SNACKS, 0),
    ("Aloo Tikki", DishCategory.SNACKS, 0),
    ("Spring Rolls", DishCategory.SNACKS, 0),
    ("Veg Cutlet", DishCategory.SNACKS, 0),
    ("Sandwich", DishCategory.SNACKS, 0),
    ("Puffs", DishCategory.SNACKS, 0),
    ("Ambode", DishCategory.SNACKS, 0),
    # Dessert
    ("Gulab Jamun", DishCategory.DESSERT, 0),
    ("Angoor Jamun", DishCategory.DESSERT, 0),
    ("Ashoka Halwa", DishCategory.DESSERT, 0),
    ("Carrot Halwa", DishCategory.DESSERT, 0),
    ("Badam Halwa", DishCategory.DESSERT, 0),
    ("Jangiri", DishCategory.DESSERT, 0),
    ("Shavige payasa", DishCategory.DESSERT, 0),
    ("Kheer", DishCategory.DESSERT, 0),
    ("Rasmalai", DishCategory.DESSERT, 0),
    ("Jalebi", DishCategory.DESSERT, 0),
    # Coffee / tea / juice
    ("Filter Coffee", DishCategory.COFFEE, 0),
    ("Coffee Sugarless", DishCategory.COFFEE, 0),
    ("Tea Coffee", DishCategory.COFFEE, 0),
    ("Tea", DishCategory.TEA, 0),
    ("Fresh Juice", DishCategory.JUICE, 0),
    ("Buttermilk", DishCategory.JUICE, 0),
]

CUSTOMIZATION_OPTIONS: list[tuple[str, str]] = [
    ("1", "No Milk"),
    ("2", "No Onion"),
    ("3", "No Garlic"),
    ("4", "Less Spice"),
    ("5", "Less Sweet"),
    ("6", "Extra Vegetables"),
]


async def seed_dishes(session) -> None:
    from sqlalchemy import func, select

    count = await session.scalar(select(func.count()).select_from(Dish)) or 0
    if count > 0:
        return

    for name, category, price in DEFAULT_DISHES:
        session.add(
            Dish(
                name=name,
                category=MEAL_SESSION_LABELS[category],
                price=price,
                isActive=True,
            )
        )
    await session.commit()
