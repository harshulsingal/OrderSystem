from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class PaymentCreateRequest(BaseModel):
    order_id: int = Field(..., gt=0, description="Order ID to charge payment for")
    idempotency_key: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description=(
            "Client-supplied key that makes retried payment requests safe. "
            "Reusing the same key always returns the original payment instead "
            "of creating a duplicate charge."
        ),
    )


class PaymentResponse(BaseModel):
    id: int
    order_id: int
    status: str
    amount: Decimal
    payment_reference: str | None = None
    idempotency_key: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
