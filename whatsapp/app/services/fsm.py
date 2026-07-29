"""Top-level FSM constants for the guided chatbot."""

from __future__ import annotations

from app.services.session_store import GuidedStep


FSM_TERMINAL_STATE = GuidedStep.DONE
FSM_INITIAL_STATE = GuidedStep.AWAIT_HI
