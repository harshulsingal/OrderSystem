from collections import defaultdict
from decimal import Decimal
import logging
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.kafka.events import TOPIC_ORDER_EVENTS, OrderCreatedEvent
from app.kafka.producer import kafka_producer
from app.models.inventory import Inventory
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.schemas.order import OrderCreate

logger = logging.getLogger(__name__)


def create_order(db: Session, order_in: OrderCreate) -> Order:
    if not order_in.items:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Order must contain at least one item",
        )

    # 1. Validate that every product exists
    product_ids = [item.product_id for item in order_in.items]
    products = db.query(Product).filter(Product.id.in_(product_ids)).all()
    product_map = {p.id: p for p in products}

    for item in order_in.items:
        if item.product_id not in product_map:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {item.product_id} not found",
            )

    # 2. Aggregate required quantity per product
    product_quantities: dict[int, int] = defaultdict(int)
    for item in order_in.items:
        product_quantities[item.product_id] += item.quantity

    # 3. Deterministic order of product IDs to prevent deadlocks
    sorted_product_ids = sorted(product_quantities.keys())

    try:
        # 4. Lock and verify inventory in deterministic sorted order
        for p_id in sorted_product_ids:
            req_qty = product_quantities[p_id]
            product = product_map[p_id]

            inventory = (
                db.query(Inventory)
                .filter(Inventory.product_id == p_id)
                .with_for_update()
                .first()
            )
            logger.info("Acquired row lock on inventory for product_id=%d", p_id)

            if not inventory:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Inventory for product {product.name} (ID: {p_id}) not found",
                )

            logger.info(
                "Checking stock for product_id=%d: available=%d, required=%d",
                p_id,
                inventory.available_quantity,
                req_qty,
            )

            if inventory.available_quantity < req_qty:
                logger.warning(
                    "Insufficient inventory for product '%s' (ID: %d): Available=%d, Requested=%d. Rolling back order transaction.",
                    product.name,
                    p_id,
                    inventory.available_quantity,
                    req_qty,
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Insufficient inventory for product '{product.name}' (ID: {p_id}). Available: {inventory.available_quantity}, Requested: {req_qty}",
                )

            # Reserve inventory
            inventory.available_quantity -= req_qty
            inventory.reserved_quantity += req_qty

        # 5. Calculate total amount and prepare order items
        total_amount = Decimal("0.00")
        order_items_to_create: list[OrderItem] = []

        for item in order_in.items:
            product = product_map[item.product_id]
            item_price = Decimal(str(product.price))
            item_total = item_price * Decimal(item.quantity)
            total_amount += item_total

            order_item = OrderItem(
                product_id=product.id,
                quantity=item.quantity,
                price=item_price,
            )
            order_items_to_create.append(order_item)

        # 6. Create Order with status INVENTORY_RESERVED
        order = Order(
            user_id=order_in.user_id,
            status="INVENTORY_RESERVED",
            total_amount=total_amount,
            order_items=order_items_to_create,
        )

        db.add(order)
        db.commit()
        db.refresh(order)
        logger.info(
            "Order #%d created with status INVENTORY_RESERVED (Total: %s)",
            order.id,
            order.total_amount,
        )
        kafka_producer.publish(
            TOPIC_ORDER_EVENTS,
            OrderCreatedEvent(
                order_id=order.id,
                user_id=order.user_id,
                total_amount=str(order.total_amount),
            ).model_dump(),
        )
        return order
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error("Failed to create order: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create order and reserve inventory",
        ) from e


def get_order_by_id(db: Session, order_id: int) -> Order:
    order = (
        db.query(Order)
        .options(selectinload(Order.order_items))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id {order_id} not found",
        )
    return order


def get_orders(
    db: Session,
    user_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Order]:
    query = db.query(Order).options(selectinload(Order.order_items))
    if user_id is not None:
        query = query.filter(Order.user_id == user_id)
    return query.offset(skip).limit(limit).all()
