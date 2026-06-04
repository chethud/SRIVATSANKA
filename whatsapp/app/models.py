import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def cuid() -> str:
    return uuid4().hex[:25]


class EnquiryStatus(str, enum.Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    CONVERTED = "CONVERTED"
    CLOSED = "CLOSED"


class NotificationType(str, enum.Enum):
    NEW_ENQUIRY = "NEW_ENQUIRY"
    CALLBACK_REMINDER = "CALLBACK_REMINDER"


class DishCategory(str, enum.Enum):
    SOUTH_INDIAN = "SOUTH_INDIAN"
    NORTH_INDIAN = "NORTH_INDIAN"
    CHINESE = "CHINESE"
    SNACKS = "SNACKS"
    DESSERTS = "DESSERTS"
    BEVERAGES = "BEVERAGES"


class Enquiry(Base):
    __tablename__ = "Enquiry"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=cuid)
    customerName: Mapped[str] = mapped_column(String)
    phoneNumber: Mapped[str] = mapped_column(String)
    eventType: Mapped[str] = mapped_column(String)
    eventDate: Mapped[datetime] = mapped_column(DateTime)
    eventLocation: Mapped[str] = mapped_column(String)
    guestCount: Mapped[int] = mapped_column(Integer)
    preferredCallbackAt: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[EnquiryStatus] = mapped_column(Enum(EnquiryStatus), default=EnquiryStatus.NEW)
    reminderSent: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    dish_items: Mapped[list["EnquiryDish"]] = relationship(back_populates="enquiry", cascade="all, delete-orphan")
    uploads: Mapped[list["InvoiceUpload"]] = relationship(back_populates="enquiry", cascade="all, delete-orphan")


class Dish(Base):
    __tablename__ = "Dish"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=cuid)
    name: Mapped[str] = mapped_column(String)
    category: Mapped[DishCategory] = mapped_column(Enum(DishCategory))
    price: Mapped[float] = mapped_column(Float, default=0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    isActive: Mapped[bool] = mapped_column(Boolean, default=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EnquiryDish(Base):
    __tablename__ = "EnquiryDish"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=cuid)
    enquiryId: Mapped[str] = mapped_column(String, ForeignKey("Enquiry.id", ondelete="CASCADE"))
    dishId: Mapped[str | None] = mapped_column(String, ForeignKey("Dish.id"), nullable=True)
    dishName: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)
    customizations: Mapped[str | None] = mapped_column(Text, nullable=True)  # comma-separated
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unitPrice: Mapped[float | None] = mapped_column(Float, nullable=True)
    served: Mapped[bool] = mapped_column(Boolean, default=False)

    enquiry: Mapped["Enquiry"] = relationship(back_populates="dish_items")


class InvoiceUpload(Base):
    __tablename__ = "InvoiceUpload"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=cuid)
    enquiryId: Mapped[str | None] = mapped_column(
        String, ForeignKey("Enquiry.id", ondelete="SET NULL"), nullable=True
    )
    docType: Mapped[str] = mapped_column(String)  # expense, profit, invoice, other
    fileName: Mapped[str] = mapped_column(String)
    filePath: Mapped[str] = mapped_column(String)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    purpose: Mapped[str | None] = mapped_column(String, nullable=True)
    expenseDate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    enquiry: Mapped["Enquiry | None"] = relationship(back_populates="uploads")


class Notification(Base):
    __tablename__ = "Notification"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=cuid)
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType))
    title: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(String)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    createdAt: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Vendor(Base):
    __tablename__ = "Vendor"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=cuid)
    name: Mapped[str] = mapped_column(String)
    businessName: Mapped[str | None] = mapped_column(String, nullable=True)
    phoneNumber: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Worker(Base):
    __tablename__ = "Worker"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=cuid)
    name: Mapped[str] = mapped_column(String)
    phoneNumber: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
    dailyWage: Mapped[float] = mapped_column(Float, default=0)
    isLead: Mapped[bool] = mapped_column(Boolean, default=False)
    createdAt: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    assignments: Mapped[list["WorkerAssignment"]] = relationship(
        back_populates="worker", cascade="all, delete-orphan"
    )


class WorkerAssignment(Base):
    __tablename__ = "WorkerAssignment"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=cuid)
    workerId: Mapped[str] = mapped_column(String, ForeignKey("Worker.id", ondelete="CASCADE"))
    enquiryId: Mapped[str | None] = mapped_column(
        String, ForeignKey("Enquiry.id", ondelete="SET NULL"), nullable=True
    )
    dutyDate: Mapped[datetime] = mapped_column(DateTime)
    dutyType: Mapped[str] = mapped_column(String)
    wage: Mapped[float] = mapped_column(Float, default=0)
    paymentCompleted: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    worker: Mapped["Worker"] = relationship(back_populates="assignments")
    enquiry: Mapped["Enquiry | None"] = relationship()


class Expense(Base):
    __tablename__ = "Expense"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=cuid)
    category: Mapped[str] = mapped_column(String)
    amount: Mapped[float] = mapped_column(Float)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    expenseDate: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    createdAt: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
