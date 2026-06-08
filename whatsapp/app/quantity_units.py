"""Supported quantity units for order menu lines."""

ALLOWED_QUANTITY_UNITS: frozenset[str] = frozenset(
    {
        "pcs",
        "kg",
        "g",
        "L",
        "ml",
        "box",
        "tray",
        "dozen",
        "nos",
        "serving",
        "cup",
        "plate",
        "bowl",
        "packet",
        "bundle",
        "tin",
    }
)

QUANTITY_UNIT_CHOICES: list[tuple[str, str]] = [
    ("pcs", "Pieces"),
    ("kg", "Kilogram (kg)"),
    ("g", "Gram (g)"),
    ("L", "Liter (L)"),
    ("ml", "Milliliter (ml)"),
    ("box", "Box"),
    ("tray", "Tray"),
    ("dozen", "Dozen"),
    ("nos", "Nos."),
    ("serving", "Serving"),
    ("cup", "Cup"),
    ("plate", "Plate"),
    ("bowl", "Bowl"),
    ("packet", "Packet"),
    ("bundle", "Bundle"),
    ("tin", "Tin"),
]


def normalize_quantity(value: float | int | None) -> float:
    try:
        q = float(value if value is not None else 1)
    except (TypeError, ValueError):
        q = 1.0
    return max(0.01, round(q, 3))


def normalize_quantity_unit(value: str | None) -> str:
    u = (value or "pcs").strip()
    return u if u in ALLOWED_QUANTITY_UNITS else "pcs"
