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
        "Which meal services do you need? Pick numbers or names (e.g. *1,3* or *breakfast, dinner*):",
        "",
    ]
    for key, label in MEAL_SESSION_OPTIONS:
        lines.append(f"{key}. {label}")
    lines.append("\nReply *skip* to discuss on the call.")
    return "\n".join(lines)


def _format_confirmation(session: ConversationSession) -> str:
    f = session.fields
    meals = ", ".join(d.dish_name for d in session.selected_dishes) if session.selected_dishes else "Team will suggest on call"
    return (
        f"Thank you, {f.customer_name}! ✅ We'll call you at {f.preferred_callback}.\n"
        f"Meals: {meals}. Send *new* for another enquiry."
    )


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
