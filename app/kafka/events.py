"""Kafka event schemas exchanged between the order and payment workflows."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

TOPIC_ORDER_EVENTS = "order-events"
TOPIC_PAYMENT_EVENTS = "payment-events"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class OrderCreatedEvent(BaseModel):
    event_type: Literal["order.created"] = "order.created"
    order_id: int
    user_id: int
    total_amount: str
    timestamp: str = Field(default_factory=_utcnow_iso)


class PaymentRequestedEvent(BaseModel):
    event_type: Literal["payment.requested"] = "payment.requested"
    payment_id: int
    order_id: int
    idempotency_key: str
    amount: str
    timestamp: str = Field(default_factory=_utcnow_iso)


class PaymentCompletedEvent(BaseModel):
    event_type: Literal["payment.completed"] = "payment.completed"
    payment_id: int
    order_id: int
    payment_reference: str
    timestamp: str = Field(default_factory=_utcnow_iso)


class PaymentFailedEvent(BaseModel):
    event_type: Literal["payment.failed"] = "payment.failed"
    payment_id: int
    order_id: int
    reason: str
    timestamp: str = Field(default_factory=_utcnow_iso)
