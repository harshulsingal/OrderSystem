from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.inventory import InventoryResponse
from app.schemas.product import ProductResponse


class DemoProduct(BaseModel):
    name: str = Field(..., min_length=1, description="Name of the product")
    sku: str = Field(..., min_length=1, description="Unique SKU")
    price: Decimal = Field(
        ..., gt=Decimal("0"), description="Product price in INR"
    )
    initial_inventory: int = Field(
        ..., ge=0, description="Initial stock quantity"
    )

    @field_validator("name", "sku", mode="before")
    @classmethod
    def check_not_empty(cls, v: str) -> str:
        if isinstance(v, str) and not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v.strip() if isinstance(v, str) else v


class DemoProductList(BaseModel):
    products: list[DemoProduct] = Field(
        ..., description="List of generated products"
    )


class DemoGenerateRequest(BaseModel):
    count: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Number of demo products to generate (1 to 20)",
    )


class DemoProductItemResponse(BaseModel):
    product: ProductResponse
    inventory: InventoryResponse

    model_config = ConfigDict(from_attributes=True)


class DemoGenerateResponse(BaseModel):
    message: str
    count: int
    items: list[DemoProductItemResponse]

    model_config = ConfigDict(from_attributes=True)
