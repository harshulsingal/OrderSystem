import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.redis_client import cache_get, cache_set, release_lock, try_acquire_lock
from app.kafka.events import (
    TOPIC_PAYMENT_EVENTS,
    PaymentCompletedEvent,
    PaymentFailedEvent,
    PaymentRequestedEvent,
)
from app.kafka.producer import kafka_producer
from app.models.order import Order
from app.models.payment import Payment
from app.services.inventory_service import release_reservation_for_order_items

logger = logging.getLogger(__name__)

# Orders can be paid the first time, or retried after a previous payment failure
ORDER_STATUSES_ELIGIBLE_FOR_PAYMENT = {"INVENTORY_RESERVED", "PAYMENT_FAILED"}


class PaymentGatewayError(Exception):
    """Raised by the simulated payment gateway on a declined charge."""


def get_payment_by_id(db: Session, payment_id: int) -> Payment:
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with id {payment_id} not found",
        )
    return payment


def get_payments(
    db: Session, skip: int = 0, limit: int = 100
) -> list[Payment]:
    return db.query(Payment).offset(skip).limit(limit).all()


def create_payment_intent(
    db: Session, order_id: int, idempotency_key: str | None
) -> Payment:
    """Creates (or replays) a payment for an order and kicks off processing.

    Idempotency is guaranteed at three layers:
      1. Redis cache lookup (fast path, best-effort).
      2. A DB lookup by the unique `idempotency_key` column (authoritative).
      3. A DB unique-constraint violation is caught and treated as a replay,
         covering the race where two requests with the same key arrive at once.
    """
    idempotency_key = idempotency_key or f"auto-{uuid.uuid4().hex}"

    cached_payment_id = cache_get(f"idempotency:payment:{idempotency_key}")
    if cached_payment_id:
        existing = db.query(Payment).filter(Payment.id == int(cached_payment_id)).first()
        if existing:
            return existing

    existing = (
        db.query(Payment).filter(Payment.idempotency_key == idempotency_key).first()
    )
    if existing:
        return existing

    lock_token = uuid.uuid4().hex
    lock_key = f"lock:payment-intent:{idempotency_key}"
    if not try_acquire_lock(lock_key, lock_token, ttl_seconds=10):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A payment request with this idempotency key is already being processed",
        )

    try:
        order = (
            db.query(Order)
            .options(selectinload(Order.order_items))
            .filter(Order.id == order_id)
            .with_for_update()
            .first()
        )
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order with id {order_id} not found",
            )
        if order.status not in ORDER_STATUSES_ELIGIBLE_FOR_PAYMENT:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Order {order_id} is not eligible for payment (status={order.status})",
            )

        payment = Payment(
            order_id=order.id,
            status="PENDING",
            amount=order.total_amount,
            idempotency_key=idempotency_key,
        )
        db.add(payment)
        try:
            db.commit()
        except IntegrityError:
            # Lost a race against a concurrent request using the same idempotency key
            db.rollback()
            existing = (
                db.query(Payment)
                .filter(Payment.idempotency_key == idempotency_key)
                .first()
            )
            if existing:
                return existing
            raise
        db.refresh(payment)
        logger.info(
            "Payment %d created (PENDING) for order %d, idempotency_key=%s",
            payment.id,
            order.id,
            idempotency_key,
        )

        cache_set(f"idempotency:payment:{idempotency_key}", str(payment.id))

        kafka_producer.publish(
            TOPIC_PAYMENT_EVENTS,
            PaymentRequestedEvent(
                payment_id=payment.id,
                order_id=order.id,
                idempotency_key=idempotency_key,
                amount=str(payment.amount),
            ).model_dump(),
        )
    except HTTPException:
        db.rollback()
        raise
    finally:
        release_lock(lock_key, lock_token)

    # Process inline as a reliability fallback for when no Kafka consumer is
    # running; process_payment is idempotent so a later event redelivery
    # (or duplicate inline call) is a safe no-op.
    processed = process_payment(db, payment.id)
    return processed if processed is not None else payment


def process_payment(db: Session, payment_id: int) -> Payment | None:
    """Executes (or safely re-executes) the charge for a pending payment.

    Guards against duplicate charges by checking `status == PENDING` under a
    row lock before calling the gateway - safe to call multiple times for the
    same payment_id, whether from the inline fallback or the Kafka consumer.
    """
    payment = (
        db.query(Payment).filter(Payment.id == payment_id).with_for_update().first()
    )
    if not payment:
        logger.warning("process_payment called for unknown payment_id=%d", payment_id)
        return None

    if payment.status != "PENDING":
        logger.info(
            "Payment %d already processed with status=%s; skipping duplicate processing",
            payment.id,
            payment.status,
        )
        return payment

    order = (
        db.query(Order)
        .options(selectinload(Order.order_items))
        .filter(Order.id == payment.order_id)
        .with_for_update()
        .first()
    )

    try:
        reference = _simulate_gateway_charge(payment)
        payment.status = "SUCCESS"
        payment.payment_reference = reference
        if order:
            order.status = "PAID"
        db.commit()
        db.refresh(payment)
        logger.info("Payment %d succeeded for order %d", payment.id, payment.order_id)
        kafka_producer.publish(
            TOPIC_PAYMENT_EVENTS,
            PaymentCompletedEvent(
                payment_id=payment.id,
                order_id=payment.order_id,
                payment_reference=reference,
            ).model_dump(),
        )
    except PaymentGatewayError as e:
        payment.status = "FAILED"
        if order:
            order.status = "PAYMENT_FAILED"
            # Compensating transaction: give back the stock reserved at order creation
            release_reservation_for_order_items(db, order.order_items)
        db.commit()
        db.refresh(payment)
        logger.warning(
            "Payment %d failed for order %d: %s", payment.id, payment.order_id, e
        )
        kafka_producer.publish(
            TOPIC_PAYMENT_EVENTS,
            PaymentFailedEvent(
                payment_id=payment.id, order_id=payment.order_id, reason=str(e)
            ).model_dump(),
        )
    except Exception as e:
        # Leave payment PENDING so a retry/event redelivery can safely reprocess it
        db.rollback()
        logger.error("Unexpected error processing payment_id=%d: %s", payment_id, e)
        raise

    return payment


def _simulate_gateway_charge(payment: Payment) -> str:
    """Stand-in for a real payment gateway call.

    Deterministic failure trigger (idempotency key prefixed with "FAIL") makes
    the failure/recovery path reproducible for demos and tests.
    """
    if payment.idempotency_key.upper().startswith("FAIL"):
        raise PaymentGatewayError("Simulated gateway decline")
    return f"txn_{uuid.uuid4().hex[:12]}"
