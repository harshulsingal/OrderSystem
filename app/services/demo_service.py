import uuid
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.inventory import Inventory
from app.models.product import Product
from app.schemas.demo import (
    DemoGenerateResponse,
    DemoProductItemResponse,
)
from app.schemas.inventory import InventoryResponse
from app.schemas.product import ProductResponse
from app.services import openai_service


def generate_and_insert_demo_data(
    db: Session, count: int = 10
) -> DemoGenerateResponse:
    if count < 1 or count > 20:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Count must be between 1 and 20 products",
        )

    # 1. Call OpenAI service to get structured candidate products
    raw_products = openai_service.generate_demo_products(count=count)

    # 2. Prepare and validate data before database operations
    created_items: list[DemoProductItemResponse] = []
    seen_skus: set[str] = set()

    try:
        for candidate in raw_products:
            # Validate basic constraints
            name = candidate.name.strip()
            sku = candidate.sku.strip().upper()
            price = Decimal(str(candidate.price))
            initial_inv = int(candidate.initial_inventory)

            if not name or not sku or price <= Decimal("0") or initial_inv < 0:
                continue

            # Ensure SKU is unique within this batch
            if sku in seen_skus:
                sku = f"{sku}-{uuid.uuid4().hex[:4].upper()}"
            seen_skus.add(sku)

            # Check if SKU exists in DB; if so, make unique
            existing = db.query(Product).filter(Product.sku == sku).first()
            if existing:
                sku = f"{sku}-{uuid.uuid4().hex[:4].upper()}"

            # Create Product model
            product = Product(name=name, sku=sku, price=price)
            db.add(product)
            db.flush()  # Acquire product.id

            # Create Inventory model
            inventory = Inventory(
                product_id=product.id,
                available_quantity=initial_inv,
                reserved_quantity=0,
            )
            db.add(inventory)
            db.flush()

            # Record item response
            created_items.append(
                DemoProductItemResponse(
                    product=ProductResponse.model_validate(product),
                    inventory=InventoryResponse.model_validate(inventory),
                )
            )

        # Commit all products and inventories in a single atomic transaction
        db.commit()

        return DemoGenerateResponse(
            message=f"{len(created_items)} products generated successfully.",
            count=len(created_items),
            items=created_items,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save demo data to database",
        ) from e
