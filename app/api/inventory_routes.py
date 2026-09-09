from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.inventory import (
    InventoryCreate,
    InventoryReservationRequest,
    InventoryReservationResponse,
    InventoryResponse,
)
from app.services import inventory_service

router = APIRouter()


@router.post(
    "",
    response_model=InventoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create inventory for a product",
)
def create_inventory(
    inventory_in: InventoryCreate, db: Session = Depends(get_db)
):
    return inventory_service.create_inventory(db, inventory_in)


@router.get(
    "",
    response_model=list[InventoryResponse],
    summary="Get all inventory records",
)
def get_all_inventories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return inventory_service.get_all_inventories(db, skip=skip, limit=limit)


@router.get(
    "/{product_id}",
    response_model=InventoryResponse,
    summary="Get inventory for a product",
)
def get_inventory_by_product(
    product_id: int, db: Session = Depends(get_db)
):
    return inventory_service.get_inventory_by_product_id(db, product_id)


@router.post(
    "/{product_id}/reserve",
    response_model=InventoryReservationResponse,
    status_code=status.HTTP_200_OK,
    summary="Reserve inventory for a product (SELECT FOR UPDATE)",
)
def reserve_inventory(
    product_id: int,
    request: InventoryReservationRequest,
    db: Session = Depends(get_db),
):
    inv = inventory_service.reserve_inventory(
        db, product_id=product_id, quantity=request.quantity
    )
    return InventoryReservationResponse(
        product_id=inv.product_id,
        available_quantity=inv.available_quantity,
        reserved_quantity=inv.reserved_quantity,
        message="Inventory reserved successfully",
    )


@router.post(
    "/{product_id}/release",
    response_model=InventoryReservationResponse,
    status_code=status.HTTP_200_OK,
    summary="Release reserved inventory for a product",
)
def release_inventory(
    product_id: int,
    request: InventoryReservationRequest,
    db: Session = Depends(get_db),
):
    inv = inventory_service.release_inventory(
        db, product_id=product_id, quantity=request.quantity
    )
    return InventoryReservationResponse(
        product_id=inv.product_id,
        available_quantity=inv.available_quantity,
        reserved_quantity=inv.reserved_quantity,
        message="Inventory released successfully",
    )
