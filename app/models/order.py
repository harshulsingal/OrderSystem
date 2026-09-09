from sqlalchemy import Column, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    status = Column(String(50), nullable=False, default="PENDING")
    total_amount = Column(Numeric(10, 2), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    order_items = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    payment = relationship(
        "Payment",
        back_populates="order",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @property
    def items(self):
        return self.order_items
