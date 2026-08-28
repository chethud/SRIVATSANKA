from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from app.schemas import EnquiryFields, SelectedDishItem


class ConversationPhase(str, Enum):
    ENQUIRY = "enquiry"
    SELECT_CATEGORIES = "select_categories"
    SELECT_DISHES = "select_dishes"
    CUSTOMIZATIONS = "customizations"
    DONE = "done"


class ConversationState(str, Enum):
    START = "START"
    INITIAL_GREETING = "INITIAL_GREETING"
    WAITING_FOR_NAME = "WAITING_FOR_NAME"
    MAIN_MENU = "MAIN_MENU"
    NEW_BOOKING = "NEW_BOOKING"
    PAST_SETUPS = "PAST_SETUPS"
    SHOWING_EVENT_INFORMATION = "SHOWING_EVENT_INFORMATION"
    EVENT_DETAILS = "EVENT_DETAILS"
    BOOKING_CONFIRMATION = "BOOKING_CONFIRMATION"
    COMPLETED = "COMPLETED"


class GuidedStep(str, Enum):
    AWAIT_HI = "await_hi"
    AWAIT_NAME = "await_name"
    AWAIT_NAME_CONFIRM = "await_name_confirm"
    AWAIT_EVENT_TYPE = "await_event_type"
    AWAIT_OTHER_EVENT = "await_other_event"
    AWAIT_POST_SHOWCASE = "await_post_showcase"
    PAST_SETUPS = "past_setups"
    SHOWING_EVENT_INFORMATION = "showing_event_information"
    COLLECT_DETAILS = "collect_details"
    AWAIT_BOOKING_CONFIRM = "await_booking_confirm"
    AWAIT_EDIT_FIELD = "await_edit_field"
    AWAIT_CANCEL_CONFIRM = "await_cancel_confirm"
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
    pending_date_confirm: str | None = None
    pending_event_month: str | None = None  # YYYY-MM while choosing a day
    pending_event_type_switch: str | None = None
    conversation_state: ConversationState = ConversationState.START
    last_user_message: str | None = None
    last_processed_message_id: str | None = None
    pending_ampm_hour: int | None = None
    pending_callback_phone_confirm: bool = False
    pending_alt_callback_phone: bool = False
    special_req_done: bool = False
    awaiting_special_req_text: bool = False
    callback_period: str | None = None
    conversation_version: int = 0
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
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
        self._seen_message_ids: set[str] = set()

    def is_duplicate_message(self, message_id: str) -> bool:
        if not message_id:
            return False
        if message_id in self._seen_message_ids:
            return True
        self._seen_message_ids.add(message_id)
        if len(self._seen_message_ids) > 5000:
            self._seen_message_ids = set(list(self._seen_message_ids)[-2500:])
        return False

    def get(self, whatsapp_id: str) -> ConversationSession:
        if whatsapp_id not in self._sessions:
            self._sessions[whatsapp_id] = ConversationSession(whatsapp_id=whatsapp_id)
        return self._sessions[whatsapp_id]

    def reset(self, whatsapp_id: str) -> ConversationSession:
        self._sessions[whatsapp_id] = ConversationSession(whatsapp_id=whatsapp_id)
        return self._sessions[whatsapp_id]


session_store = SessionStore()
