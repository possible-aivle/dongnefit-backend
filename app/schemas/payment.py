"""Payment schemas for Toss Payments integration."""

from datetime import datetime
from enum import Enum

from pydantic import Field

from app.schemas.base import BaseSchema, PaginationParams, TimestampSchema


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_FOR_DEPOSIT = "WAITING_FOR_DEPOSIT"
    DONE = "DONE"
    CANCELED = "CANCELED"
    PARTIAL_CANCELED = "PARTIAL_CANCELED"


class PaymentMethod(str, Enum):
    CARD = "CARD"
    VIRTUAL_ACCOUNT = "VIRTUAL_ACCOUNT"
    EASY_PAY = "EASY_PAY"
    TRANSFER = "TRANSFER"
    GIFT_CERTIFICATE = "GIFT_CERTIFICATE"


class BillingCycle(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"


class SubscriptionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ENDED = "ENDED"


# === Product Schemas ===


class ProductCreate(BaseSchema):
    """Schema for creating a product."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    price: int = Field(..., ge=0)
    original_price: int | None = None
    image_url: str | None = None
    stock: int | None = None
    metadata: dict | None = None


class ProductUpdate(BaseSchema):
    """Schema for updating a product."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    price: int | None = Field(None, ge=0)
    original_price: int | None = None
    image_url: str | None = None
    is_active: bool | None = None
    stock: int | None = None


class ProductResponse(TimestampSchema):
    """Product response."""

    id: int
    name: str
    description: str | None
    price: int
    original_price: int | None
    image_url: str | None
    is_active: bool
    stock: int | None


# === Order Schemas ===


class OrderItemCreate(BaseSchema):
    """Schema for order item."""

    product_id: int | None = None
    report_id: int | None = None
    name: str
    price: int
    quantity: int = 1


class OrderCreate(BaseSchema):
    """Schema for creating an order."""

    items: list[OrderItemCreate]
    customer_email: str | None = None
    customer_name: str | None = None
    customer_mobile_phone: str | None = None


class OrderQuery(PaginationParams):
    """Query parameters for listing orders."""

    status: OrderStatus | None = None
    user_id: str | None = None  # Admin only


class OrderItemResponse(BaseSchema):
    """Order item response."""

    id: int
    product_id: int | None
    report_id: int | None
    name: str
    price: int
    quantity: int


class OrderResponse(TimestampSchema):
    """Order response."""

    id: int
    user_id: str
    status: OrderStatus
    total_price: int
    customer_email: str | None
    customer_name: str | None
    customer_mobile_phone: str | None
    items: list[OrderItemResponse] = []


# === Payment Schemas ===


class PaymentRequest(BaseSchema):
    """Schema for requesting payment."""

    order_id: int
    method: PaymentMethod = PaymentMethod.CARD


class PaymentConfirm(BaseSchema):
    """Schema for confirming payment (after Toss redirect)."""

    payment_key: str
    order_id: int
    amount: int


class PaymentCancel(BaseSchema):
    """Schema for canceling payment."""

    cancel_reason: str


class PaymentResponse(TimestampSchema):
    """Payment response."""

    id: int
    order_id: int
    amount: int
    status: PaymentStatus
    method: PaymentMethod | None
    payment_key: str | None
    receipt_url: str | None
    approved_at: datetime | None
    canceled_at: datetime | None


# === Coupon Schemas ===


class CouponCreate(BaseSchema):
    """Schema for creating a coupon."""

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    discount_type: str  # 'percentage' or 'fixed'
    discount_value: int = Field(..., ge=0)
    min_order_amount: int | None = None
    max_discount: int | None = None
    usage_limit: int | None = None
    valid_from: datetime
    valid_until: datetime | None = None


class CouponUpdate(BaseSchema):
    """Schema for updating a coupon."""

    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    valid_until: datetime | None = None


class CouponApply(BaseSchema):
    """Schema for applying a coupon."""

    code: str


class CouponResponse(TimestampSchema):
    """Coupon response."""

    id: int
    code: str
    name: str
    description: str | None
    discount_type: str
    discount_value: int
    min_order_amount: int | None
    max_discount: int | None
    usage_limit: int | None
    used_count: int
    is_active: bool
    valid_from: datetime
    valid_until: datetime | None


# === Subscription Schemas ===


class SubscriptionCreate(BaseSchema):
    """Schema for creating a subscription."""

    billing_key_id: int
    product_id: int | None = None
    amount: int
    billing_cycle: BillingCycle = BillingCycle.MONTHLY


class SubscriptionResponse(TimestampSchema):
    """Subscription response."""

    id: int
    user_id: str
    billing_key_id: int
    product_id: int | None
    status: SubscriptionStatus
    amount: int
    billing_cycle: BillingCycle
    next_billing_date: datetime | None
    start_date: datetime
    end_date: datetime | None


class BillingKeyResponse(TimestampSchema):
    """Billing key response."""

    id: int
    user_id: str
    card_company: str | None
    card_number: str | None  # Masked
    is_active: bool


# === Stats Schemas ===


class PaymentStats(BaseSchema):
    """Payment statistics."""

    total_revenue: int
    total_orders: int
    average_order_value: float
    successful_payments: int
    canceled_payments: int
