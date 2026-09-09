from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.payment import PaymentCreateRequest, PaymentResponse
from app.services import payment_service

router = APIRouter()


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an idempotent payment for an order",
)
def create_payment(
    payment_in: PaymentCreateRequest, db: Session = Depends(get_db)
):
    return payment_service.create_payment_intent(
        db, order_id=payment_in.order_id, idempotency_key=payment_in.idempotency_key
    )


@router.get(
    "",
    response_model=list[PaymentResponse],
    summary="Get all payments",
)
def get_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return payment_service.get_payments(db, skip=skip, limit=limit)


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    summary="Get a payment by ID",
)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    return payment_service.get_payment_by_id(db, payment_id)
