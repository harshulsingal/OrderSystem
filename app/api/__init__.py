from app.api.demo_routes import router as demo_router
from app.api.inventory_routes import router as inventory_router
from app.api.order_routes import router as order_router
from app.api.payment_routes import router as payment_router
from app.api.product_routes import router as product_router

__all__ = [
    "product_router",
    "inventory_router",
    "order_router",
    "payment_router",
    "demo_router",
]
