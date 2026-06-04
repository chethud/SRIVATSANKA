import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import AgentTurnResult, SelectedDishItem
from app.services.session_store import ConversationPhase, ConversationSession

# Cuisine / menu style options (not individual dishes)
CUISINE_OPTIONS: list[tuple[str, str]] = [
    ("1", "Multi Cuisine"),
    ("2", "South Indian"),
    ("3", "North Indian"),
    ("4", "Chinese"),
    ("5", "Snacks & Starters"),
    ("6", "Desserts"),
    ("7", "Beverages"),
]

CUISINE_BY_KEY = {k: label for k, label in CUISINE_OPTIONS}
CUISINE_BY_LABEL = {label.lower(): label for _, label in CUISINE_OPTIONS}
PREFERENCE_CATEGORY = "Cuisine Preference"


def _parse_numbers(text: str) -> list[str]:
    return re.findall(r"\d+", text)


def _format_cuisine_prompt() -> str:
    lines = [
        "Wonderful — your event details are with our team. 🌿\n",
        "To help Mr. Kannan prepare ideas for your call, what *cuisine styles* do you have in mind?",
        "Pick any (e.g. *1,2,4* for Multi Cuisine + South Indian + Chinese):\n",
    ]
    for key, label in CUISINE_OPTIONS:
        lines.append(f"{key}. {label}")
    lines.extend([
        "",
        "You can also type names, e.g. *multi cuisine* or *south indian*.",
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
        f"• Guests: {f.guest_count}",
        f"• Callback: {f.preferred_callback}",
        "",
    ]
    if session.selected_dishes:
        lines.append("*Cuisine / menu style*")
        for d in session.selected_dishes:
            extra = f" – {d.notes}" if d.notes else ""
            lines.append(f"• {d.dish_name}{extra}")
    else:
        lines.append("*Cuisine:* Team will discuss menu options on callback")
    lines.extend([
        "",
        "Our team will contact you at your preferred time with a tailored menu.",
        "Send *new* to start another enquiry.",
    ])
    return "\n".join(lines)


def _resolve_cuisine_selections(text: str) -> list[str]:
    lower = text.strip().lower()
    if lower in {"skip", "0", "none", "no", "later"}:
        return []

    selected: list[str] = []
    keys = _parse_numbers(text)
    for k in keys:
        if k in CUISINE_BY_KEY and CUISINE_BY_KEY[k] not in selected:
            selected.append(CUISINE_BY_KEY[k])

    for label_key, label in CUISINE_BY_LABEL.items():
        if label_key in lower and label not in selected:
            selected.append(label)

    # Free text fallback (e.g. "multi cuisine and north indian")
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
    """Ask cuisine types only — no per-dish selection."""
    session.phase = ConversationPhase.SELECT_CATEGORIES
    reply = _format_cuisine_prompt()
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

    labels = _resolve_cuisine_selections(user_text)
    if not labels and user_text.strip().lower() not in {"skip", "0", "none", "no", "later"}:
        return AgentTurnResult(
            reply=(
                "Please pick cuisine types by number (e.g. *1,2*) or name (*multi cuisine*), "
                "or reply *skip*."
            ),
            fields=session.fields,
        )

    session.selected_dishes = _preferences_to_items(labels)
    session.completed = True
    session.phase = ConversationPhase.DONE
    reply = _format_confirmation(session)
    return AgentTurnResult(reply=reply, fields=session.fields, is_complete=True)
