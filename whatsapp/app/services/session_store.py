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
    AWAIT_NAME_CONFIRM = "await_name_confirm"
    AWAIT_EVENT_TYPE = "await_event_type"
    AWAIT_POST_SHOWCASE = "await_post_showcase"
    COLLECT_DETAILS = "collect_details"
    DONE = "done"


@dataclass
class SlotValue:
    value: str | int | None = None
    confidence: float = 0.0
    collected: bool = False


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
    sent_gallery_urls: list[str] = field(default_factory=list)
    guided_step: GuidedStep = GuidedStep.AWAIT_HI
    previous_guided_step: GuidedStep | None = None
    _saved: bool = False
    consecutive_loop_count: int = 0
    last_assistant_question: str | None = None
    last_asked_slot: str | None = None
    failed_turns_in_state: int = 0
    slot_fail_counts: dict[str, int] = field(default_factory=dict)
    showcase_prompted: bool = False
    pending_name: str | None = None
    name_confirmed: bool = False
    slots: dict[str, SlotValue] = field(
        default_factory=lambda: {
            "customer_name": SlotValue(),
            "event_type": SlotValue(),
            "event_date": SlotValue(),
            "guest_count": SlotValue(),
            "event_location": SlotValue(),
            "meal_preference": SlotValue(),
            "preferred_callback": SlotValue(),
            "special_requests": SlotValue(),
        }
    )


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
