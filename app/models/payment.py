from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(
        Integer, ForeignKey("orders.id"), unique=True, index=True, nullable=False
    )
    status = Column(String(50), nullable=False, default="PENDING")
    amount = Column(Numeric(10, 2), nullable=False)
    payment_reference = Column(String(255), nullable=True)
    idempotency_key = Column(
        String(255), unique=True, index=True, nullable=False
    )
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
    order = relationship("Order", back_populates="payment")
