from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.product import ProductCreate, ProductResponse
from app.services import product_service

router = APIRouter()


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product",
)
def create_product(
    product_in: ProductCreate, db: Session = Depends(get_db)
):
    return product_service.create_product(db, product_in)


@router.get(
    "",
    response_model=list[ProductResponse],
    summary="Get all products",
)
def get_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return product_service.get_products(db, skip=skip, limit=limit)


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get a product by ID",
)
def get_product(product_id: int, db: Session = Depends(get_db)):
    return product_service.get_product_by_id(db, product_id)
