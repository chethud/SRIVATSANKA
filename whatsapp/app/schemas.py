from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class EnquiryFields(BaseModel):
    customer_name: str | None = None
    phone_number: str | None = None
    event_type: str | None = None
    event_date: str | None = None
    event_location: str | None = None
    guest_count: int | None = None
    preferred_callback: str | None = None


class SelectedDishItem(BaseModel):
    dish_id: str | None = None
    dish_name: str
    category: str
    customizations: list[str] = Field(default_factory=list)
    notes: str | None = None


class MediaAttachment(BaseModel):
    url: str
    caption: str | None = None


class AgentTurnResult(BaseModel):
    reply: str
    fields: EnquiryFields = Field(default_factory=EnquiryFields)
    is_complete: bool = False
    enquiry_fields_complete: bool = False
    media: list[MediaAttachment] = Field(default_factory=list)


class EnquiryDishOut(BaseModel):
    id: str
    dishId: str | None = None
    dishName: str
    category: str
    customizations: str | None = None
    notes: str | None = None
    quantity: float = 1
    quantityUnit: str = "pcs"
    unitPrice: float | None = None
    served: bool = False

    model_config = {"from_attributes": True}


class OrderDishIn(BaseModel):
    dishId: str | None = None
    dishName: str | None = None
    category: str | None = None
    quantity: float = 1
    quantityUnit: str = "pcs"
    customizations: str | None = None
    notes: str | None = None
    unitPrice: float | None = None
    # When False with dishName, add to this order only (do not create Dish catalog).
    saveToCatalog: bool = True
    # Optional menu session column id — assign dish in the same request (avoids 2nd PATCH).
    menuColumnId: str | None = None

    @model_validator(mode="after")
    def require_dish_reference(self) -> "OrderDishIn":
        has_id = bool(self.dishId and self.dishId.strip())
        has_name = bool(self.dishName and self.dishName.strip())
        if not has_id and not has_name:
            raise ValueError("Provide dishId or dishName")
        return self


class OrderDishUpdate(BaseModel):
    category: str | None = None
    customizations: str | None = None
    notes: str | None = None
    quantity: float | None = None
    quantityUnit: str | None = None
    unitPrice: float | None = None
    served: bool | None = None


class DishIn(BaseModel):
    name: str
    category: str
    price: float = 0
    description: str | None = None


class InvoiceRecognizeOut(BaseModel):
    pendingId: str
    fileName: str
    description: str | None = None
    expenseDate: str | None = None
    amount: float | None = None
    purpose: str | None = None
    recognized: bool = False
    message: str | None = None


class InvoiceConfirmIn(BaseModel):
    pendingId: str
    description: str | None = None
    expenseDate: str | None = None
    amount: float | None = None
    purpose: str | None = None


class InvoiceUploadOut(BaseModel):
    id: str
    enquiryId: str | None = None
    docType: str
    fileName: str
    amount: float | None
    notes: str | None = None
    purpose: str | None = None
    expenseDate: datetime | None = None
    createdAt: datetime
    recognized: bool = False


class InvoiceUploadWithOrder(InvoiceUploadOut):
    customerName: str | None = None
    eventType: str | None = None


class EnquiryCreateIn(BaseModel):
    customerName: str
    phoneNumber: str
    eventType: str
    eventDate: datetime
    eventLocation: str
    guestCount: int = 0
    preferredCallbackAt: datetime
    notes: str | None = None


class EnquiryUpdateIn(BaseModel):
    notes: str | None = None


class EnquiryOut(BaseModel):
    id: str
    customerName: str
    phoneNumber: str
    eventType: str
    eventDate: datetime
    eventLocation: str
    guestCount: int
    preferredCallbackAt: datetime
    status: str
    ownerViewedAt: datetime | None = None
    notes: str | None = None
    createdAt: datetime
    dishes: list[EnquiryDishOut] = Field(default_factory=list)

    @field_validator("status", mode="before")
    @classmethod
    def status_to_str(cls, v: object) -> str:
        return v.value if hasattr(v, "value") else str(v)


class NotificationOut(BaseModel):
    id: str
    type: str
    title: str
    message: str
    read: bool
    createdAt: datetime

    @field_validator("type", mode="before")
    @classmethod
    def type_to_str(cls, v: object) -> str:
        return v.value if hasattr(v, "value") else str(v)


class DashboardStats(BaseModel):
    new_enquiries: int
    new_orders: int
    total_enquiries: int
    unread_notifications: int
    total_dishes: int
    upcoming_events: int
    total_vendors: int = 0
    total_workers: int = 0
    total_expenses: float = 0


class DishOut(BaseModel):
    id: str
    name: str
    category: str
    price: float
    description: str | None = None


class VendorIn(BaseModel):
    name: str
    businessName: str | None = None
    phoneNumber: str
    category: str
    notes: str | None = None


class VendorOut(VendorIn):
    id: str
    createdAt: datetime


class WorkerIn(BaseModel):
    name: str
    phoneNumber: str
    role: str
    dailyWage: float = 0
    isLead: bool = False


class WorkerUpdateIn(BaseModel):
    isLead: bool | None = None


class WorkerOut(WorkerIn):
    id: str
    createdAt: datetime


class WorkerAssignmentIn(BaseModel):
    enquiryId: str | None = None
    dutyDate: datetime
    dutyType: str
    wage: float = 0
    notes: str | None = None


class WorkerAssignmentPatchIn(BaseModel):
    paymentCompleted: bool | None = None


class WorkerAssignmentOut(BaseModel):
    id: str
    workerId: str
    enquiryId: str | None = None
    dutyDate: datetime
    dutyType: str
    wage: float = 0
    paymentCompleted: bool = False
    notes: str | None = None
    createdAt: datetime
    customerName: str | None = None
    eventType: str | None = None
    eventLocation: str | None = None
    orderLabel: str | None = None

    model_config = {"from_attributes": True}


class WorkerProfileOut(BaseModel):
    worker: WorkerOut
    assignments: list[WorkerAssignmentOut]
    totalDuties: int
    upcomingDuties: int
    totalWagesEarned: float = 0


class ExpenseIn(BaseModel):
    category: str
    amount: float
    description: str | None = None
    expenseDate: datetime | None = None


class ExpenseOut(BaseModel):
    id: str
    category: str
    amount: float
    description: str | None
    expenseDate: datetime
    createdAt: datetime


class ChartMoneyItem(BaseModel):
    label: str
    amount: float
    date: str | None = None
    purpose: str | None = None


class MonthlyChartPoint(BaseModel):
    month: str
    revenue: float
    expenses: float
    profit: float


class AnalyticsOut(BaseModel):
    total_revenue: float
    order_revenue: float
    uploaded_revenue: float
    total_expenses: float
    global_expenses: float
    order_expenses: float
    net_profit: float
    converted_orders: int
    by_status: dict[str, int] = {}
    by_event_type: dict[str, int] = {}
    expense_items: list[ChartMoneyItem] = []
    profit_items: list[ChartMoneyItem] = []
    monthly: list[MonthlyChartPoint] = []


class UpdateEnquiryStatus(BaseModel):
    status: str


class DevMessageRequest(BaseModel):
    from_number: str = "919999999999"
    text: str


class DevMessageResponse(BaseModel):
    from_number: str
    sent: str
    reply: str
    is_complete: bool
    fields: EnquiryFields
    enquiry_saved: bool = False
    media: list[MediaAttachment] = Field(default_factory=list)


class ChatMessageOut(BaseModel):
    id: str
    phoneNumber: str
    role: str
    body: str
    media: list[MediaAttachment] = Field(default_factory=list)
    createdAt: datetime


class ChatConversationOut(BaseModel):
    phoneNumber: str
    customerName: str | None = None
    enquiryId: str | None = None
    lastMessage: str
    lastRole: str
    lastAt: datetime
    messageCount: int
    botPaused: bool = False


class OwnerChatMessageIn(BaseModel):
    text: str


class AIAssistantRequest(BaseModel):
    query: str
    ruleId: str | None = None


class AIAssistantResponse(BaseModel):
    reply: str
