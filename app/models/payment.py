"""Payment models for Toss Payments integration."""

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class OrderStatus(str, Enum):
    """Order status enum."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    """Payment status enum (Toss Payments)."""

    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_FOR_DEPOSIT = "WAITING_FOR_DEPOSIT"
    DONE = "DONE"
    CANCELED = "CANCELED"
    PARTIAL_CANCELED = "PARTIAL_CANCELED"


class PaymentMethod(str, Enum):
    """Payment method enum."""

    CARD = "CARD"
    VIRTUAL_ACCOUNT = "VIRTUAL_ACCOUNT"
    EASY_PAY = "EASY_PAY"
    TRANSFER = "TRANSFER"
    GIFT_CERTIFICATE = "GIFT_CERTIFICATE"


class BillingCycle(str, Enum):
    """Subscription billing cycle."""

    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"


class SubscriptionStatus(str, Enum):
    """Subscription status."""

    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ENDED = "ENDED"


class Product(Base, TimestampMixin):
    """Product for sale."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[int] = mapped_column(Integer, nullable=False)  # In KRW
    original_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    stock: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)


class Order(Base, TimestampMixin):
    """Order model."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=OrderStatus.PENDING.value, nullable=False)
    total_price: Mapped[int] = mapped_column(Integer, nullable=False)

    # Customer info
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer_mobile_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)


class OrderItem(Base, TimestampMixin):
    """Order item model."""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    report_id: Mapped[int | None] = mapped_column(
        ForeignKey("reports.id", ondelete="SET NULL"), nullable=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class Payment(Base, TimestampMixin):
    """Payment record (Toss Payments)."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default=PaymentStatus.READY.value, nullable=False)
    method: Mapped[str | None] = mapped_column(String(30), nullable=True)
    payment_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payment_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    receipt_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Card details
    card_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    card_owner_type: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Other payment methods
    easy_pay_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    virtual_account_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cash_receipt_type: Mapped[str | None] = mapped_column(String(30), nullable=True)

    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class BillingKey(Base, TimestampMixin):
    """Billing key for recurring payments."""

    __tablename__ = "billing_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    billing_key: Mapped[str] = mapped_column(String(255), nullable=False)
    card_company: Mapped[str | None] = mapped_column(String(50), nullable=True)
    card_number: Mapped[str | None] = mapped_column(String(20), nullable=True)  # Masked
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Subscription(Base, TimestampMixin):
    """Subscription for recurring payments."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    billing_key_id: Mapped[int] = mapped_column(
        ForeignKey("billing_keys.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(20), default=SubscriptionStatus.ACTIVE.value, nullable=False
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    billing_cycle: Mapped[str] = mapped_column(
        String(20), default=BillingCycle.MONTHLY.value, nullable=False
    )
    next_billing_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)


class Coupon(Base, TimestampMixin):
    """Discount coupon."""

    __tablename__ = "coupons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'percentage' or 'fixed'
    discount_value: Mapped[int] = mapped_column(Integer, nullable=False)
    min_order_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_discount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class UserCoupon(Base, TimestampMixin):
    """User's coupon assignment."""

    __tablename__ = "user_coupons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    coupon_id: Mapped[int] = mapped_column(ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
