from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class InventoryCreate(BaseModel):
    product_id: int = Field(..., gt=0, description="Associated product ID")
    available_quantity: int = Field(
        ..., ge=0, description="Available stock quantity"
    )


class InventoryResponse(BaseModel):
    id: int
    product_id: int
    available_quantity: int
    reserved_quantity: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventoryReservationRequest(BaseModel):
    quantity: int = Field(
        ..., gt=0, description="Quantity to reserve or release"
    )


class InventoryReservationResponse(BaseModel):
    product_id: int
    available_quantity: int
    reserved_quantity: int
    message: str

    model_config = ConfigDict(from_attributes=True)
