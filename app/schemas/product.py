from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Name of the product")
    sku: str = Field(..., min_length=1, description="Unique stock keeping unit")
    price: Decimal = Field(..., gt=Decimal("0"), description="Product price")

    @field_validator("name", "sku", mode="before")
    @classmethod
    def check_not_empty(cls, v: str) -> str:
        if isinstance(v, str) and not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v.strip() if isinstance(v, str) else v


class ProductResponse(BaseModel):
    id: int
    name: str
    sku: str
    price: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
