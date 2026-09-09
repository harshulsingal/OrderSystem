from datetime import datetime
from decimal import Decimal
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class OrderItemCreate(BaseModel):
    product_id: int = Field(..., gt=0, description="Product ID to order")
    quantity: int = Field(..., gt=0, description="Quantity to order")


class OrderCreate(BaseModel):
    user_id: int = Field(..., gt=0, description="Customer user ID")
    items: list[OrderItemCreate] = Field(
        ..., min_length=1, description="List of items in the order"
    )


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    price: Decimal

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: int
    user_id: int
    status: str
    total_amount: Decimal
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse] = Field(
        default_factory=list,
        validation_alias=AliasChoices("items", "order_items"),
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
