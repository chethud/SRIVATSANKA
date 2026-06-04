from datetime import datetime

from pydantic import BaseModel, Field, field_validator


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


class AgentTurnResult(BaseModel):
    reply: str
    fields: EnquiryFields = Field(default_factory=EnquiryFields)
    is_complete: bool = False
    enquiry_fields_complete: bool = False


class EnquiryDishOut(BaseModel):
    id: str
    dishId: str | None = None
    dishName: str
    category: str
    customizations: str | None = None
    notes: str | None = None
    quantity: int = 1
    unitPrice: float | None = None
    served: bool = False

    model_config = {"from_attributes": True}


class OrderDishIn(BaseModel):
    dishId: str
    quantity: int = 1
    customizations: str | None = None
    notes: str | None = None
    unitPrice: float | None = None


class OrderDishUpdate(BaseModel):
    customizations: str | None = None
    notes: str | None = None
    quantity: int | None = None
    unitPrice: float | None = None
    served: bool | None = None


class DishIn(BaseModel):
    name: str
    category: str
    price: float = 0
    description: str | None = None


class InvoiceUploadOut(BaseModel):
    id: str
    enquiryId: str | None = None
    docType: str
    fileName: str
    amount: float | None
    notes: str | None
    createdAt: datetime
    recognized: bool = False


class InvoiceUploadWithOrder(InvoiceUploadOut):
    customerName: str | None = None
    eventType: str | None = None


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


class WorkerOut(WorkerIn):
    id: str
    createdAt: datetime


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


class AIAssistantRequest(BaseModel):
    query: str


class AIAssistantResponse(BaseModel):
    reply: str
