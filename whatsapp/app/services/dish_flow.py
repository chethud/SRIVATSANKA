import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.seed_dishes import CATEGORY_LABELS, CUSTOMIZATION_OPTIONS
from app.models import Dish, DishCategory
from app.schemas import AgentTurnResult, SelectedDishItem
from app.services.session_store import ConversationPhase, ConversationSession

CATEGORY_MENU: list[tuple[str, DishCategory]] = [
    ("1", DishCategory.SOUTH_INDIAN),
    ("2", DishCategory.NORTH_INDIAN),
    ("3", DishCategory.CHINESE),
    ("4", DishCategory.SNACKS),
    ("5", DishCategory.DESSERTS),
    ("6", DishCategory.BEVERAGES),
]

CATEGORY_BY_KEY = {k: cat for k, cat in CATEGORY_MENU}
CATEGORY_BY_LABEL = {label.lower(): cat for cat, label in CATEGORY_LABELS.items()}


def _parse_numbers(text: str) -> list[str]:
    return re.findall(r"\d+", text)


def _format_categories_prompt() -> str:
    lines = [
        "Great! Now let's plan your menu 🍽️\n",
        "Which *types of dishes* do you need? Reply with numbers (e.g. 1,3,5):\n",
    ]
    for key, cat in CATEGORY_MENU:
        lines.append(f"{key}. {CATEGORY_LABELS[cat]}")
    lines.append("\nReply *skip* if you want the owner to suggest the menu on callback.")
    return "\n".join(lines)


async def _get_dishes_for_category(db: AsyncSession, category: DishCategory) -> list[Dish]:
    result = await db.execute(
        select(Dish)
        .where(Dish.category == category, Dish.isActive.is_(True))
        .order_by(Dish.name)
    )
    return list(result.scalars().all())


def _format_dishes_prompt(category: DishCategory, dishes: list[Dish]) -> str:
    label = CATEGORY_LABELS[category]
    lines = [f"*{label}* – select dishes (reply with numbers, e.g. 1,2):\n"]
    for i, dish in enumerate(dishes, 1):
        lines.append(f"{i}. {dish.name} – ₹{dish.price:.0f}")
    lines.append("\nReply *0* or *skip* to skip this category.")
    return "\n".join(lines)


def _format_customizations_prompt(dishes: list[SelectedDishItem]) -> str:
    lines = [
        "Your selected dishes:\n",
    ]
    for i, d in enumerate(dishes, 1):
        lines.append(f"{i}. {d.dish_name} ({d.category})")
    lines.extend([
        "",
        "Any *customizations*? Reply with numbers for ALL dishes, or type per dish:",
        "",
    ])
    for key, label in CUSTOMIZATION_OPTIONS:
        lines.append(f"{key}. {label}")
    lines.extend([
        "",
        'Examples:\n• "1,4" → No Milk + Less Spice for all\n• "Sambar - less spice"\n• "none" → no customizations',
    ])
    return "\n".join(lines)


def _format_confirmation(session: ConversationSession) -> str:
    f = session.fields
    lines = [
        f"Thank you, {f.customer_name}! ✅\n",
        "*Event Details*",
        f"• Event: {f.event_type}",
        f"• Date: {f.event_date}",
        f"• Location: {f.event_location}",
        f"• Guests: {f.guest_count}",
        f"• Callback: {f.preferred_callback}",
        "",
    ]
    if session.selected_dishes:
        lines.append("*Selected Menu*")
        for d in session.selected_dishes:
            custom = ", ".join(d.customizations) if d.customizations else "None"
            extra = f" ({d.notes})" if d.notes else ""
            lines.append(f"• {d.dish_name} [{d.category}] – {custom}{extra}")
    else:
        lines.append("*Menu:* Owner will discuss menu on callback")
    lines.extend([
        "",
        "Our team will contact you at your preferred time.",
        "Send *new* to start another enquiry.",
    ])
    return "\n".join(lines)


def _apply_customizations_to_all(dishes: list[SelectedDishItem], keys: list[str]) -> None:
    labels = [label for key, label in CUSTOMIZATION_OPTIONS if key in keys]
    for dish in dishes:
        for label in labels:
            if label not in dish.customizations:
                dish.customizations.append(label)


def _parse_customization_text(text: str, dishes: list[SelectedDishItem]) -> None:
    lower = text.lower()
    if lower in {"none", "no", "nothing", "skip", "na", "n/a"}:
        return

    keys = _parse_numbers(text)
    if keys and all(k in {o[0] for o in CUSTOMIZATION_OPTIONS} for k in keys):
        _apply_customizations_to_all(dishes, keys)
        return

    # Per-dish notes: "sambar less spice, gulab less sweet"
    for dish in dishes:
        if dish.dish_name.lower() in lower:
            dish.notes = text.strip()


async def start_dish_flow(session: ConversationSession, db: AsyncSession) -> AgentTurnResult:
    session.phase = ConversationPhase.SELECT_CATEGORIES
    reply = _format_categories_prompt()
    session.history.append({"role": "assistant", "content": reply})
    return AgentTurnResult(reply=reply, fields=session.fields, enquiry_fields_complete=True)


async def handle_dish_flow(
    session: ConversationSession, user_text: str, db: AsyncSession
) -> AgentTurnResult:
    text = user_text.strip()
    lower = text.lower()

    if session.phase == ConversationPhase.SELECT_CATEGORIES:
        if lower in {"skip", "0", "none", "no"}:
            session.selected_dishes = []
            session.completed = True
            session.phase = ConversationPhase.DONE
            reply = _format_confirmation(session)
            return AgentTurnResult(reply=reply, fields=session.fields, is_complete=True)

        keys = _parse_numbers(text)
        session.selected_category_keys = [k for k in keys if k in CATEGORY_BY_KEY]
        if not session.selected_category_keys:
            # try matching names
            for label, cat in CATEGORY_BY_LABEL.items():
                if label in lower:
                    key = next(k for k, c in CATEGORY_MENU if c == cat)
                    session.selected_category_keys.append(key)
            if not session.selected_category_keys:
                return AgentTurnResult(
                    reply="Please reply with category numbers (e.g. 1,3,5) or type *skip*.",
                    fields=session.fields,
                )

        session.current_category_index = 0
        session.phase = ConversationPhase.SELECT_DISHES
        cat = CATEGORY_BY_KEY[session.selected_category_keys[0]]
        dishes = await _get_dishes_for_category(db, cat)
        reply = _format_dishes_prompt(cat, dishes)
        session.history.append({"role": "assistant", "content": reply})
        return AgentTurnResult(reply=reply, fields=session.fields)

    if session.phase == ConversationPhase.SELECT_DISHES:
        cat_key = session.selected_category_keys[session.current_category_index]
        cat = CATEGORY_BY_KEY[cat_key]
        dishes = await _get_dishes_for_category(db, cat)

        if lower not in {"0", "skip", "none"}:
            nums = [int(n) for n in _parse_numbers(text)]
            for n in nums:
                if 1 <= n <= len(dishes):
                    d = dishes[n - 1]
                    session.selected_dishes.append(
                        SelectedDishItem(
                            dish_id=d.id,
                            dish_name=d.name,
                            category=CATEGORY_LABELS[cat],
                        )
                    )

        session.current_category_index += 1
        if session.current_category_index < len(session.selected_category_keys):
            next_cat = CATEGORY_BY_KEY[session.selected_category_keys[session.current_category_index]]
            next_dishes = await _get_dishes_for_category(db, next_cat)
            reply = _format_dishes_prompt(next_cat, next_dishes)
            session.history.append({"role": "assistant", "content": reply})
            return AgentTurnResult(reply=reply, fields=session.fields)

        if not session.selected_dishes:
            session.completed = True
            session.phase = ConversationPhase.DONE
            reply = _format_confirmation(session)
            return AgentTurnResult(reply=reply, fields=session.fields, is_complete=True)

        session.phase = ConversationPhase.CUSTOMIZATIONS
        reply = _format_customizations_prompt(session.selected_dishes)
        session.history.append({"role": "assistant", "content": reply})
        return AgentTurnResult(reply=reply, fields=session.fields)

    if session.phase == ConversationPhase.CUSTOMIZATIONS:
        _parse_customization_text(text, session.selected_dishes)
        session.completed = True
        session.phase = ConversationPhase.DONE
        reply = _format_confirmation(session)
        return AgentTurnResult(reply=reply, fields=session.fields, is_complete=True)

    return AgentTurnResult(
        reply="Something went wrong. Send *new* to start again.",
        fields=session.fields,
    )
