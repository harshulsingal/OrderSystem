from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.order import OrderCreate, OrderResponse
from app.services import order_service

router = APIRouter()


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an order",
)
def create_order(order_in: OrderCreate, db: Session = Depends(get_db)):
    return order_service.create_order(db, order_in)


@router.get(
    "",
    response_model=list[OrderResponse],
    summary="Get all orders (optionally filter by user_id)",
)
def get_orders(
    user_id: int | None = Query(
        None, description="Filter orders by customer user ID"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return order_service.get_orders(
        db, user_id=user_id, skip=skip, limit=limit
    )


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get an order by ID",
)
def get_order(order_id: int, db: Session = Depends(get_db)):
    return order_service.get_order_by_id(db, order_id)
