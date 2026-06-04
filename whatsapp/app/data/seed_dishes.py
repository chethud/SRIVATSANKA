"""Default menu items seeded on first run."""

from app.models import Dish, DishCategory

DEFAULT_DISHES: list[tuple[str, DishCategory, float]] = [
    # South Indian
    ("Sambar Rice", DishCategory.SOUTH_INDIAN, 80),
    ("Lemon Rice", DishCategory.SOUTH_INDIAN, 70),
    ("Coconut Rice", DishCategory.SOUTH_INDIAN, 75),
    ("Vegetable Biryani", DishCategory.SOUTH_INDIAN, 120),
    ("Masala Dosa", DishCategory.SOUTH_INDIAN, 60),
    ("Idli Sambar", DishCategory.SOUTH_INDIAN, 50),
    ("Pongal", DishCategory.SOUTH_INDIAN, 65),
    ("Curd Rice", DishCategory.SOUTH_INDIAN, 55),
    # North Indian
    ("Paneer Butter Masala", DishCategory.NORTH_INDIAN, 180),
    ("Dal Makhani", DishCategory.NORTH_INDIAN, 140),
    ("Veg Biryani", DishCategory.NORTH_INDIAN, 130),
    ("Naan", DishCategory.NORTH_INDIAN, 40),
    ("Roti", DishCategory.NORTH_INDIAN, 25),
    ("Palak Paneer", DishCategory.NORTH_INDIAN, 160),
    ("Chole Bhature", DishCategory.NORTH_INDIAN, 120),
    # Chinese
    ("Veg Fried Rice", DishCategory.CHINESE, 110),
    ("Noodles", DishCategory.CHINESE, 100),
    ("Manchurian", DishCategory.CHINESE, 130),
    ("Spring Rolls", DishCategory.CHINESE, 90),
    ("Gobi Manchurian", DishCategory.CHINESE, 120),
    # Snacks
    ("Samosa", DishCategory.SNACKS, 30),
    ("Veg Cutlet", DishCategory.SNACKS, 40),
    ("Pakora", DishCategory.SNACKS, 50),
    ("Sandwich", DishCategory.SNACKS, 60),
    ("Puffs", DishCategory.SNACKS, 35),
    # Desserts
    ("Gulab Jamun", DishCategory.DESSERTS, 50),
    ("Rasmalai", DishCategory.DESSERTS, 60),
    ("Ice Cream", DishCategory.DESSERTS, 45),
    ("Kheer", DishCategory.DESSERTS, 55),
    ("Jalebi", DishCategory.DESSERTS, 40),
    # Beverages
    ("Filter Coffee", DishCategory.BEVERAGES, 30),
    ("Tea", DishCategory.BEVERAGES, 20),
    ("Fresh Juice", DishCategory.BEVERAGES, 50),
    ("Buttermilk", DishCategory.BEVERAGES, 25),
    ("Soft Drink", DishCategory.BEVERAGES, 35),
]

CATEGORY_LABELS: dict[DishCategory, str] = {
    DishCategory.SOUTH_INDIAN: "South Indian",
    DishCategory.NORTH_INDIAN: "North Indian",
    DishCategory.CHINESE: "Chinese",
    DishCategory.SNACKS: "Snacks",
    DishCategory.DESSERTS: "Desserts",
    DishCategory.BEVERAGES: "Beverages",
}

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
        session.add(Dish(name=name, category=category, price=price, isActive=True))
    await session.commit()
