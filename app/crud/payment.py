"""CRUD operations for payments."""

from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.payment import (
    Coupon,
    Order,
    OrderItem,
    OrderStatus,
    Payment,
    PaymentStatus,
    Product,
    Subscription,
    SubscriptionStatus,
    UserCoupon,
)
from app.schemas.payment import (
    CouponCreate,
    OrderCreate,
    OrderQuery,
    ProductCreate,
    ProductUpdate,
    SubscriptionCreate,
)


class CRUDProduct(CRUDBase[Product]):
    """CRUD operations for Product model."""

    async def get_active(
        self,
        db: AsyncSession,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Product]:
        """Get active products."""
        result = await db.execute(
            select(Product)
            .where(Product.is_active == True)
            .order_by(Product.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_product(
        self,
        db: AsyncSession,
        *,
        obj_in: ProductCreate,
    ) -> Product:
        """Create a new product."""
        db_obj = Product(
            name=obj_in.name,
            description=obj_in.description,
            price=obj_in.price,
            original_price=obj_in.original_price,
            image_url=obj_in.image_url,
            stock=obj_in.stock,
            metadata_=obj_in.metadata,
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update_product(
        self,
        db: AsyncSession,
        *,
        db_obj: Product,
        obj_in: ProductUpdate,
    ) -> Product:
        """Update a product."""
        update_data = obj_in.model_dump(exclude_unset=True)
        return await self.update(db, db_obj=db_obj, obj_in=update_data)


class CRUDOrder(CRUDBase[Order]):
    """CRUD operations for Order model."""

    async def get_multi_with_query(
        self,
        db: AsyncSession,
        *,
        query: OrderQuery,
        user_id: str | None = None,
    ) -> tuple[list[Order], int]:
        """Get orders with filtering."""
        conditions = []

        if user_id:
            conditions.append(Order.user_id == user_id)
        elif query.user_id:
            conditions.append(Order.user_id == query.user_id)

        if query.status:
            conditions.append(Order.status == query.status.value)

        where_clause = and_(*conditions) if conditions else True

        result = await db.execute(
            select(Order)
            .where(where_clause)
            .order_by(Order.created_at.desc())
            .offset(query.offset)
            .limit(query.limit)
        )
        orders = list(result.scalars().all())

        count_result = await db.execute(
            select(func.count()).select_from(Order).where(where_clause)
        )
        total = count_result.scalar() or 0

        return orders, total

    async def create_order(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        obj_in: OrderCreate,
    ) -> Order:
        """Create a new order with items."""
        total_price = sum(item.price * item.quantity for item in obj_in.items)

        db_obj = Order(
            user_id=user_id,
            status=OrderStatus.PENDING.value,
            total_price=total_price,
            customer_email=obj_in.customer_email,
            customer_name=obj_in.customer_name,
            customer_mobile_phone=obj_in.customer_mobile_phone,
        )
        db.add(db_obj)
        await db.flush()

        # Create order items
        for item in obj_in.items:
            db_item = OrderItem(
                order_id=db_obj.id,
                product_id=item.product_id,
                report_id=item.report_id,
                name=item.name,
                price=item.price,
                quantity=item.quantity,
            )
            db.add(db_item)

        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update_status(
        self,
        db: AsyncSession,
        *,
        db_obj: Order,
        status: OrderStatus,
    ) -> Order:
        """Update order status."""
        db_obj.status = status.value
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_items(
        self,
        db: AsyncSession,
        *,
        order_id: int,
    ) -> list[OrderItem]:
        """Get items for an order."""
        result = await db.execute(
            select(OrderItem).where(OrderItem.order_id == order_id)
        )
        return list(result.scalars().all())


class CRUDPayment(CRUDBase[Payment]):
    """CRUD operations for Payment model."""

    async def get_by_order(
        self,
        db: AsyncSession,
        *,
        order_id: int,
    ) -> Payment | None:
        """Get payment for an order."""
        result = await db.execute(
            select(Payment).where(Payment.order_id == order_id)
        )
        return result.scalar_one_or_none()

    async def get_by_payment_key(
        self,
        db: AsyncSession,
        *,
        payment_key: str,
    ) -> Payment | None:
        """Get payment by Toss payment key."""
        result = await db.execute(
            select(Payment).where(Payment.payment_key == payment_key)
        )
        return result.scalar_one_or_none()

    async def create_payment(
        self,
        db: AsyncSession,
        *,
        order_id: int,
        amount: int,
    ) -> Payment:
        """Create a new payment record."""
        db_obj = Payment(
            order_id=order_id,
            amount=amount,
            status=PaymentStatus.READY.value,
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def confirm_payment(
        self,
        db: AsyncSession,
        *,
        db_obj: Payment,
        payment_key: str,
        method: str,
    ) -> Payment:
        """Confirm a payment."""
        db_obj.status = PaymentStatus.DONE.value
        db_obj.payment_key = payment_key
        db_obj.method = method
        db_obj.approved_at = datetime.utcnow()
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def cancel_payment(
        self,
        db: AsyncSession,
        *,
        db_obj: Payment,
    ) -> Payment:
        """Cancel a payment."""
        db_obj.status = PaymentStatus.CANCELED.value
        db_obj.canceled_at = datetime.utcnow()
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj


class CRUDCoupon(CRUDBase[Coupon]):
    """CRUD operations for Coupon model."""

    async def get_by_code(
        self,
        db: AsyncSession,
        *,
        code: str,
    ) -> Coupon | None:
        """Get coupon by code."""
        result = await db.execute(
            select(Coupon).where(Coupon.code == code)
        )
        return result.scalar_one_or_none()

    async def create_coupon(
        self,
        db: AsyncSession,
        *,
        obj_in: CouponCreate,
    ) -> Coupon:
        """Create a new coupon."""
        db_obj = Coupon(
            code=obj_in.code,
            name=obj_in.name,
            description=obj_in.description,
            discount_type=obj_in.discount_type,
            discount_value=obj_in.discount_value,
            min_order_amount=obj_in.min_order_amount,
            max_discount=obj_in.max_discount,
            usage_limit=obj_in.usage_limit,
            valid_from=obj_in.valid_from,
            valid_until=obj_in.valid_until,
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def increment_usage(
        self,
        db: AsyncSession,
        *,
        db_obj: Coupon,
    ) -> Coupon:
        """Increment coupon usage count."""
        db_obj.used_count += 1
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj


class CRUDUserCoupon(CRUDBase[UserCoupon]):
    """CRUD operations for UserCoupon model."""

    async def get_user_coupons(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        is_used: bool | None = None,
    ) -> list[UserCoupon]:
        """Get coupons for a user."""
        conditions = [UserCoupon.user_id == user_id]
        if is_used is not None:
            conditions.append(UserCoupon.is_used == is_used)

        result = await db.execute(
            select(UserCoupon)
            .where(and_(*conditions))
            .order_by(UserCoupon.created_at.desc())
        )
        return list(result.scalars().all())

    async def assign_coupon(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        coupon_id: int,
    ) -> UserCoupon:
        """Assign a coupon to a user."""
        db_obj = UserCoupon(
            user_id=user_id,
            coupon_id=coupon_id,
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def use_coupon(
        self,
        db: AsyncSession,
        *,
        db_obj: UserCoupon,
    ) -> UserCoupon:
        """Mark a coupon as used."""
        db_obj.is_used = True
        db_obj.used_at = datetime.utcnow()
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj


class CRUDSubscription(CRUDBase[Subscription]):
    """CRUD operations for Subscription model."""

    async def get_user_subscriptions(
        self,
        db: AsyncSession,
        *,
        user_id: str,
    ) -> list[Subscription]:
        """Get subscriptions for a user."""
        result = await db.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_active_subscriptions(
        self,
        db: AsyncSession,
        *,
        user_id: str,
    ) -> list[Subscription]:
        """Get active subscriptions for a user."""
        result = await db.execute(
            select(Subscription)
            .where(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.status == SubscriptionStatus.ACTIVE.value,
                )
            )
        )
        return list(result.scalars().all())

    async def create_subscription(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        obj_in: SubscriptionCreate,
    ) -> Subscription:
        """Create a new subscription."""
        db_obj = Subscription(
            user_id=user_id,
            billing_key_id=obj_in.billing_key_id,
            product_id=obj_in.product_id,
            amount=obj_in.amount,
            billing_cycle=obj_in.billing_cycle.value,
            status=SubscriptionStatus.ACTIVE.value,
            start_date=datetime.utcnow(),
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update_status(
        self,
        db: AsyncSession,
        *,
        db_obj: Subscription,
        status: SubscriptionStatus,
    ) -> Subscription:
        """Update subscription status."""
        db_obj.status = status.value
        if status == SubscriptionStatus.ENDED:
            db_obj.end_date = datetime.utcnow()
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj


product = CRUDProduct(Product)
order = CRUDOrder(Order)
payment = CRUDPayment(Payment)
coupon = CRUDCoupon(Coupon)
user_coupon = CRUDUserCoupon(UserCoupon)
subscription = CRUDSubscription(Subscription)
