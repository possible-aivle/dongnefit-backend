"""Payment endpoints for Toss Payments integration."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AdminUser, CurrentUser
from app.crud.payment import coupon as coupon_crud
from app.crud.payment import order as order_crud
from app.crud.payment import payment as payment_crud
from app.crud.payment import product as product_crud
from app.database import get_db
from app.schemas.base import PaginatedResponse, PaginationMeta
from app.schemas.payment import (
    CouponCreate,
    CouponResponse,
    OrderCreate,
    OrderQuery,
    OrderResponse,
    PaymentConfirm,
    PaymentRequest,
    PaymentResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)

router = APIRouter()


# === Products ===


@router.get(
    "/products",
    response_model=list[ProductResponse],
    summary="List products",
    description="List all active products",
    tags=["products"],
)
async def list_products(
    db: AsyncSession = Depends(get_db),
) -> list[ProductResponse]:
    """List active products."""
    products = await product_crud.get_active(db)
    return [ProductResponse.model_validate(p) for p in products]


@router.get(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Get product",
    description="Get a specific product by ID",
    tags=["products"],
)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Get a product by ID."""
    product = await product_crud.get(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="상품을 찾을 수 없습니다",
        )
    return ProductResponse.model_validate(product)


@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create product",
    description="Create a new product (Admin only)",
    tags=["products"],
)
async def create_product(
    product_in: ProductCreate,
    admin: AdminUser = None,
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Create a new product."""
    product = await product_crud.create_product(db, obj_in=product_in)
    return ProductResponse.model_validate(product)


@router.patch(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Update product",
    description="Update a product (Admin only)",
    tags=["products"],
)
async def update_product(
    product_id: int,
    product_in: ProductUpdate,
    admin: AdminUser = None,
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Update a product."""
    product = await product_crud.get(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="상품을 찾을 수 없습니다",
        )

    product = await product_crud.update_product(db, db_obj=product, obj_in=product_in)
    return ProductResponse.model_validate(product)


# === Orders ===


@router.get(
    "/orders",
    response_model=PaginatedResponse[OrderResponse],
    summary="List orders",
    description="List orders (Admin sees all, users see their own)",
    tags=["orders"],
)
async def list_orders(
    query: OrderQuery = Depends(),
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[OrderResponse]:
    """List orders."""
    user_id = None if current_user.role == "admin" else current_user.id
    orders, total = await order_crud.get_multi_with_query(
        db, query=query, user_id=user_id
    )

    # Get items for each order
    order_responses = []
    for order in orders:
        items = await order_crud.get_items(db, order_id=order.id)
        response = OrderResponse.model_validate(order)
        response.items = [
            {"id": i.id, "product_id": i.product_id, "report_id": i.report_id,
             "name": i.name, "price": i.price, "quantity": i.quantity}
            for i in items
        ]
        order_responses.append(response)

    return PaginatedResponse(
        data=order_responses,
        pagination=PaginationMeta(
            page=query.page,
            limit=query.limit,
            total=total,
            total_pages=(total + query.limit - 1) // query.limit,
        ),
    )


@router.get(
    "/orders/my",
    response_model=list[OrderResponse],
    summary="My orders",
    description="Get current user's orders",
    tags=["orders"],
)
async def my_orders(
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> list[OrderResponse]:
    """Get current user's orders."""
    query = OrderQuery(page=1, limit=100)
    orders, _ = await order_crud.get_multi_with_query(
        db, query=query, user_id=current_user.id
    )
    return [OrderResponse.model_validate(o) for o in orders]


@router.get(
    "/orders/{order_id}",
    response_model=OrderResponse,
    summary="Get order",
    description="Get a specific order",
    tags=["orders"],
)
async def get_order(
    order_id: int,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Get an order by ID."""
    order = await order_crud.get(db, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="주문을 찾을 수 없습니다",
        )

    if order.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 없습니다",
        )

    items = await order_crud.get_items(db, order_id=order.id)
    response = OrderResponse.model_validate(order)
    response.items = [
        {"id": i.id, "product_id": i.product_id, "report_id": i.report_id,
         "name": i.name, "price": i.price, "quantity": i.quantity}
        for i in items
    ]
    return response


@router.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create order",
    description="Create a new order",
    tags=["orders"],
)
async def create_order(
    order_in: OrderCreate,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Create a new order."""
    order = await order_crud.create_order(db, user_id=current_user.id, obj_in=order_in)
    items = await order_crud.get_items(db, order_id=order.id)
    response = OrderResponse.model_validate(order)
    response.items = [
        {"id": i.id, "product_id": i.product_id, "report_id": i.report_id,
         "name": i.name, "price": i.price, "quantity": i.quantity}
        for i in items
    ]
    return response


# === Payments ===


@router.post(
    "/request",
    response_model=dict,
    summary="Request payment",
    description="Initiate a payment request",
    tags=["payments"],
)
async def request_payment(
    payment_in: PaymentRequest,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Request a payment (returns Toss Payments form data)."""
    order = await order_crud.get(db, payment_in.order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="주문을 찾을 수 없습니다",
        )

    if order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 없습니다",
        )

    # Create payment record
    payment = await payment_crud.create_payment(
        db, order_id=order.id, amount=order.total_price
    )

    # Return Toss Payments form data
    return {
        "payment_id": payment.id,
        "order_id": order.id,
        "amount": order.total_price,
        "order_name": f"주문 #{order.id}",
        "customer_name": order.customer_name or current_user.name,
        "customer_email": order.customer_email or current_user.email,
    }


@router.post(
    "/confirm",
    response_model=PaymentResponse,
    summary="Confirm payment",
    description="Confirm a payment after Toss redirect",
    tags=["payments"],
)
async def confirm_payment(
    confirm_in: PaymentConfirm,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    """Confirm a payment."""
    payment = await payment_crud.get_by_order(db, order_id=confirm_in.order_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="결제 정보를 찾을 수 없습니다",
        )

    # TODO: Verify with Toss Payments API
    # For now, just confirm the payment
    payment = await payment_crud.confirm_payment(
        db, db_obj=payment, payment_key=confirm_in.payment_key, method="CARD"
    )

    # Update order status
    order = await order_crud.get(db, confirm_in.order_id)
    from app.models.payment import OrderStatus
    await order_crud.update_status(db, db_obj=order, status=OrderStatus.CONFIRMED)

    return PaymentResponse.model_validate(payment)


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    summary="Get payment",
    description="Get payment details",
    tags=["payments"],
)
async def get_payment(
    payment_id: int,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    """Get payment details."""
    payment = await payment_crud.get(db, payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="결제 정보를 찾을 수 없습니다",
        )

    # Verify ownership
    order = await order_crud.get(db, payment.order_id)
    if order.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 없습니다",
        )

    return PaymentResponse.model_validate(payment)


# === Coupons ===


@router.get(
    "/coupons",
    response_model=list[CouponResponse],
    summary="List coupons",
    description="List all coupons (Admin only)",
    tags=["coupons"],
)
async def list_coupons(
    admin: AdminUser = None,
    db: AsyncSession = Depends(get_db),
) -> list[CouponResponse]:
    """List all coupons."""
    coupons = await coupon_crud.get_multi(db, limit=100)
    return [CouponResponse.model_validate(c) for c in coupons]


@router.post(
    "/coupons",
    response_model=CouponResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create coupon",
    description="Create a new coupon (Admin only)",
    tags=["coupons"],
)
async def create_coupon(
    coupon_in: CouponCreate,
    admin: AdminUser = None,
    db: AsyncSession = Depends(get_db),
) -> CouponResponse:
    """Create a new coupon."""
    existing = await coupon_crud.get_by_code(db, code=coupon_in.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 쿠폰 코드입니다",
        )

    coupon = await coupon_crud.create_coupon(db, obj_in=coupon_in)
    return CouponResponse.model_validate(coupon)


@router.get(
    "/coupons/{code}",
    response_model=CouponResponse,
    summary="Get coupon",
    description="Get coupon by code",
    tags=["coupons"],
)
async def get_coupon(
    code: str,
    db: AsyncSession = Depends(get_db),
) -> CouponResponse:
    """Get a coupon by code."""
    coupon = await coupon_crud.get_by_code(db, code=code)
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="쿠폰을 찾을 수 없습니다",
        )
    return CouponResponse.model_validate(coupon)
