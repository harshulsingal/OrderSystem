from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.demo import DemoGenerateRequest, DemoGenerateResponse
from app.services import demo_service

router = APIRouter()


@router.post(
    "/generate",
    response_model=DemoGenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate demo products and inventory using OpenAI",
)
def generate_demo_data(
    request: DemoGenerateRequest | None = None,
    db: Session = Depends(get_db),
):
    count = request.count if request else 10
    return demo_service.generate_and_insert_demo_data(db, count=count)
