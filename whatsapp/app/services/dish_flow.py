import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import AgentTurnResult, SelectedDishItem
from app.services.session_store import ConversationPhase, ConversationSession

MEAL_SESSION_OPTIONS: list[tuple[str, str]] = [
    ("1", "Breakfast"),
    ("2", "Lunch"),
    ("3", "Dinner"),
    ("4", "Reception Dinner"),
    ("5", "Snacks"),
    ("6", "Coffee"),
    ("7", "Tea"),
    ("8", "Juice"),
    ("9", "Dessert"),
]

SESSION_BY_KEY = {k: label for k, label in MEAL_SESSION_OPTIONS}
SESSION_BY_LABEL = {label.lower(): label for _, label in MEAL_SESSION_OPTIONS}
PREFERENCE_CATEGORY = "Meal Preference"


def _parse_numbers(text: str) -> list[str]:
    return re.findall(r"\d+", text)


def _format_session_prompt() -> str:
    lines = [
        "Wonderful — your event details are with our team. 🌿\n",
        "Which *meal services* do you need? (e.g. breakfast, lunch, reception dinner, coffee)",
        "Pick any (e.g. *1,3,4* for Breakfast + Dinner + Reception Dinner):\n",
    ]
    for key, label in MEAL_SESSION_OPTIONS:
        lines.append(f"{key}. {label}")
    lines.extend([
        "",
        "You can also type names, e.g. *breakfast* or *reception dinner*.",
        "Reply *skip* if you want our team to suggest options on the callback.",
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
        f"• Callback: {f.preferred_callback}",
        "",
    ]
    if session.selected_dishes:
        lines.append("*Meal services requested*")
        for d in session.selected_dishes:
            extra = f" – {d.notes}" if d.notes else ""
            lines.append(f"• {d.dish_name}{extra}")
    else:
        lines.append("*Meals:* Team will discuss menu options on callback")
    lines.extend([
        "",
        "Our team will contact you at your preferred time with a tailored menu.",
        "Send *new* to start another enquiry.",
    ])
    return "\n".join(lines)


def _resolve_session_selections(text: str) -> list[str]:
    lower = text.strip().lower()
    if lower in {"skip", "0", "none", "no", "later"}:
        return []

    selected: list[str] = []
    keys = _parse_numbers(text)
    for k in keys:
        if k in SESSION_BY_KEY and SESSION_BY_KEY[k] not in selected:
            selected.append(SESSION_BY_KEY[k])

    for label_key, label in SESSION_BY_LABEL.items():
        if label_key in lower and label not in selected:
            selected.append(label)

    if not selected and len(text.strip()) > 2:
        return [text.strip()[:120]]

    return selected


def _preferences_to_items(labels: list[str]) -> list[SelectedDishItem]:
    return [
        SelectedDishItem(
            dish_id=None,
            dish_name=label,
            category=PREFERENCE_CATEGORY,
        )
        for label in labels
    ]


async def start_dish_flow(session: ConversationSession, _db: AsyncSession) -> AgentTurnResult:
    """Ask meal session types only — no per-dish selection."""
    session.phase = ConversationPhase.SELECT_CATEGORIES
    reply = _format_session_prompt()
    session.history.append({"role": "assistant", "content": reply})
    return AgentTurnResult(reply=reply, fields=session.fields, enquiry_fields_complete=True)


async def handle_dish_flow(
    session: ConversationSession, user_text: str, _db: AsyncSession
) -> AgentTurnResult:
    if session.phase != ConversationPhase.SELECT_CATEGORIES:
        return AgentTurnResult(
            reply="Something went wrong. Send *new* to start again.",
            fields=session.fields,
        )

    labels = _resolve_session_selections(user_text)
    session.selected_dishes = _preferences_to_items(labels)
    session.phase = ConversationPhase.DONE
    session.completed = True
    reply = _format_confirmation(session)
    session.history.append({"role": "assistant", "content": reply})
    return AgentTurnResult(
        reply=reply,
        fields=session.fields,
        is_complete=True,
        enquiry_fields_complete=True,
    )
