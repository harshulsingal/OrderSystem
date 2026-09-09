from sqlalchemy import Column, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    sku = Column(String(100), unique=True, index=True, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    inventory = relationship(
        "Inventory",
        back_populates="product",
        uselist=False,
        cascade="all, delete-orphan",
    )
    order_items = relationship("OrderItem", back_populates="product")
