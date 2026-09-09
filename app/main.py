from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

import app.models  # noqa: F401 - Register all models with Base metadata
from app.api import (
    demo_router,
    inventory_router,
    order_router,
    payment_router,
    product_router,
)
from app.core.database import Base, engine, get_db
from app.kafka.consumer import payment_event_consumer
from app.kafka.producer import kafka_producer


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    kafka_producer.start()
    payment_event_consumer.start()
    yield
    kafka_producer.stop()


app = FastAPI(
    title="Order & Inventory Management System",
    description="Distributed Order & Inventory Management System Backend",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration restricted specifically to frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(product_router, prefix="/api/products", tags=["Products"])
app.include_router(
    inventory_router, prefix="/api/inventory", tags=["Inventory"]
)
app.include_router(order_router, prefix="/api/orders", tags=["Orders"])
app.include_router(payment_router, prefix="/api/payments", tags=["Payments"])
app.include_router(demo_router, prefix="/api/demo", tags=["Demo Data"])


@app.get("/", tags=["Health"])
def read_root():
    return {"message": "Order System is running"}


@app.get("/health/db", tags=["Health"])
def health_check_db(db: Session = Depends(get_db)):
    try:
        result = db.execute(text("SELECT 1")).scalar()
        return {
            "status": "healthy",
            "database": "connected",
            "result": result,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database connection failed: {e}",
        ) from e
