from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.product import Product
from app.schemas.product import ProductCreate


def create_product(db: Session, product_in: ProductCreate) -> Product:
    existing = db.query(Product).filter(Product.sku == product_in.sku).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product with SKU '{product_in.sku}' already exists",
        )

    product = Product(
        name=product_in.name,
        sku=product_in.sku,
        price=product_in.price,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def get_products(
    db: Session, skip: int = 0, limit: int = 100
) -> list[Product]:
    return db.query(Product).offset(skip).limit(limit).all()


def get_product_by_id(db: Session, product_id: int) -> Product:
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found",
        )
    return product
