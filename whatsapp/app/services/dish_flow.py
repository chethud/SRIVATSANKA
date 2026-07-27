import random
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
    lead = random.choice(
        (
            "Almost there — which meals do you need?",
            "Which meal services should we plan for?",
            "Quick one — which meals?",
        )
    )
    lines = [lead, ""]
    for key, label in MEAL_SESSION_OPTIONS:
        lines.append(f"{key}. {label}")
    lines.append("\nReply with numbers/names, or say *skip*.")
    return "\n".join(lines)


def _format_confirmation(session: ConversationSession) -> str:
    f = session.fields
    name = f.customer_name or "there"
    event_name = (f.event_type or "celebration").lower()
    if event_name == "general":
        event_name = "celebration"

    variant_a = (
        f"Thank you so much, {name}! It was a absolute pleasure chatting with you. "
        f"We’re thrilled at the opportunity to make your {event_name} truly unforgettable. ✨\n\n"
        f"Have a wonderful rest of your day, and talk to you soon!"
    )
    variant_b = (
        f"Thank you, {name}! We’re honored to be considered for your big day. "
        f"Our team will connect with you at the scheduled time. 🙏\n\n"
        f"Wishing you a lovely day ahead!"
    )
    return random.choice((variant_a, variant_b))


def _resolve_session_selections(text: str) -> list[str] | None:
    """Return selected meal labels, [] for skip, or None if the reply was unclear."""
    lower = text.strip().lower()
    if lower in {"skip", "0", "none", "no", "later"}:
        return []

    selected: list[str] = []
    keys = _parse_numbers(text)
    for k in keys:
        if k in SESSION_BY_KEY and SESSION_BY_KEY[k] not in selected:
            selected.append(SESSION_BY_KEY[k])

    for label_key, label in SESSION_BY_LABEL.items():
        if re.search(rf"\b{re.escape(label_key)}\b", lower) and label not in selected:
            selected.append(label)

    return selected or None


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
    if labels is None:
        reply = (
            "Hmm, didn’t quite get that — try *1,3* or *breakfast, dinner*, or say *skip*."
        )
        session.history.append({"role": "assistant", "content": reply})
        return AgentTurnResult(
            reply=reply,
            fields=session.fields,
            enquiry_fields_complete=True,
        )

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
