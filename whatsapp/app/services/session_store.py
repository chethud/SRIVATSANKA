from dataclasses import dataclass, field
from enum import Enum

from app.schemas import EnquiryFields, SelectedDishItem


class ConversationPhase(str, Enum):
    ENQUIRY = "enquiry"
    SELECT_CATEGORIES = "select_categories"
    SELECT_DISHES = "select_dishes"
    CUSTOMIZATIONS = "customizations"
    DONE = "done"


class GuidedStep(str, Enum):
    AWAIT_HI = "await_hi"
    AWAIT_NAME = "await_name"
    AWAIT_EVENT_TYPE = "await_event_type"
    AWAIT_POST_SHOWCASE = "await_post_showcase"
    COLLECT_DETAILS = "collect_details"
    DONE = "done"


@dataclass
class ConversationSession:
    whatsapp_id: str
    phase: ConversationPhase = ConversationPhase.ENQUIRY
    history: list[dict[str, str]] = field(default_factory=list)
    fields: EnquiryFields = field(default_factory=EnquiryFields)
    completed: bool = False
    selected_category_keys: list[str] = field(default_factory=list)
    current_category_index: int = 0
    selected_dishes: list[SelectedDishItem] = field(default_factory=list)
    customization_dish_index: int = 0
    welcome_media_sent: bool = False
    guided_step: GuidedStep = GuidedStep.AWAIT_HI
    _saved: bool = False


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, ConversationSession] = {}

    def get(self, whatsapp_id: str) -> ConversationSession:
        if whatsapp_id not in self._sessions:
            self._sessions[whatsapp_id] = ConversationSession(whatsapp_id=whatsapp_id)
        return self._sessions[whatsapp_id]

    def reset(self, whatsapp_id: str) -> ConversationSession:
        self._sessions[whatsapp_id] = ConversationSession(whatsapp_id=whatsapp_id)
        return self._sessions[whatsapp_id]


session_store = SessionStore()
