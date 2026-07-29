"""Session memory helpers for deterministic flow."""

from __future__ import annotations

from app.services.session_store import ConversationSession
from app.services.slot_manager import sync_slots_from_fields


def hydrate_memory(session: ConversationSession) -> None:
    """Keep slot metadata aligned with persisted fields and history."""
    sync_slots_from_fields(session)
    if session.history:
        for msg in reversed(session.history):
            if msg.get("role") == "assistant":
                session.last_assistant_question = msg.get("content") or session.last_assistant_question
                break
