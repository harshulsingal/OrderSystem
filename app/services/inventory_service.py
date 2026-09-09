from collections import defaultdict
import logging
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.inventory import Inventory
from app.models.order_item import OrderItem
from app.models.product import Product
from app.schemas.inventory import InventoryCreate

logger = logging.getLogger(__name__)


def create_inventory(db: Session, inventory_in: InventoryCreate) -> Inventory:
    product = (
        db.query(Product).filter(Product.id == inventory_in.product_id).first()
    )
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {inventory_in.product_id} not found",
        )

    existing = (
        db.query(Inventory)
        .filter(Inventory.product_id == inventory_in.product_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Inventory for product {inventory_in.product_id} already exists",
        )

    inventory = Inventory(
        product_id=inventory_in.product_id,
        available_quantity=inventory_in.available_quantity,
        reserved_quantity=0,
    )
    db.add(inventory)
    db.commit()
    db.refresh(inventory)
    return inventory


def get_inventory_by_product_id(db: Session, product_id: int) -> Inventory:
    inventory = (
        db.query(Inventory).filter(Inventory.product_id == product_id).first()
    )
    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory for product {product_id} not found",
        )
    return inventory


def get_all_inventories(
    db: Session, skip: int = 0, limit: int = 100
) -> list[Inventory]:
    return db.query(Inventory).offset(skip).limit(limit).all()


def reserve_inventory(
    db: Session, product_id: int, quantity: int
) -> Inventory:
    logger.info(
        "Reservation requested for product_id=%d, quantity=%d",
        product_id,
        quantity,
    )

    try:
        # Acquire row-level lock on inventory record
        inventory = (
            db.query(Inventory)
            .filter(Inventory.product_id == product_id)
            .with_for_update()
            .first()
        )
        logger.info("Inventory row locked for product_id=%d", product_id)

        if not inventory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventory for product {product_id} not found",
            )

        logger.info(
            "Stock check for product_id=%d: available=%d, requested=%d",
            product_id,
            inventory.available_quantity,
            quantity,
        )

        if inventory.available_quantity < quantity:
            logger.warning(
                "Insufficient inventory for product_id=%d: available=%d, requested=%d. Transaction rollback.",
                product_id,
                inventory.available_quantity,
                quantity,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Insufficient inventory for product {product_id}. Available: {inventory.available_quantity}, Requested: {quantity}",
            )

        inventory.available_quantity -= quantity
        inventory.reserved_quantity += quantity
        db.commit()
        db.refresh(inventory)
        logger.info(
            "Reservation successful for product_id=%d: new available=%d, new reserved=%d",
            product_id,
            inventory.available_quantity,
            inventory.reserved_quantity,
        )
        return inventory
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(
            "Unexpected error during inventory reservation for product_id=%d: %s",
            product_id,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reserve inventory",
        ) from e


def release_reservation_for_order_items(
    db: Session, order_items: list[OrderItem]
) -> None:
    """Compensating transaction: returns reserved stock to available quantity.

    Used when a downstream step (e.g. payment) fails after inventory was
    already reserved for an order. Must run inside the caller's existing
    transaction - it does not commit.
    """
    quantities: dict[int, int] = defaultdict(int)
    for item in order_items:
        quantities[item.product_id] += item.quantity

    # Deterministic sorted order to match the locking order used at reservation time
    for product_id in sorted(quantities):
        inventory = (
            db.query(Inventory)
            .filter(Inventory.product_id == product_id)
            .with_for_update()
            .first()
        )
        if inventory is None:
            logger.warning(
                "Inventory for product_id=%d not found during release", product_id
            )
            continue
        inventory.available_quantity += quantities[product_id]
        inventory.reserved_quantity -= quantities[product_id]
        logger.info(
            "Released %d units for product_id=%d: new available=%d, new reserved=%d",
            quantities[product_id],
            product_id,
            inventory.available_quantity,
            inventory.reserved_quantity,
        )


def release_inventory(
    db: Session, product_id: int, quantity: int
) -> Inventory:
    logger.info(
        "Release requested for product_id=%d, quantity=%d",
        product_id,
        quantity,
    )

    try:
        # Acquire row-level lock on inventory record
        inventory = (
            db.query(Inventory)
            .filter(Inventory.product_id == product_id)
            .with_for_update()
            .first()
        )
        logger.info("Inventory row locked for release for product_id=%d", product_id)

        if not inventory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventory for product {product_id} not found",
            )

        if inventory.reserved_quantity < quantity:
            logger.warning(
                "Cannot release %d units for product_id=%d. Currently reserved: %d",
                quantity,
                product_id,
                inventory.reserved_quantity,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot release {quantity} units for product {product_id}. Only {inventory.reserved_quantity} units are reserved.",
            )

        inventory.available_quantity += quantity
        inventory.reserved_quantity -= quantity
        db.commit()
        db.refresh(inventory)
        logger.info(
            "Release successful for product_id=%d: new available=%d, new reserved=%d",
            product_id,
            inventory.available_quantity,
            inventory.reserved_quantity,
        )
        return inventory
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(
            "Unexpected error during inventory release for product_id=%d: %s",
            product_id,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to release inventory",
        ) from e
