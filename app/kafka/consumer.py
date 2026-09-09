"""Background Kafka consumer that drives event-driven payment processing.

Consumes `payment.requested` events and asynchronously invokes
`payment_service.process_payment`, decoupled from the original API request.
`process_payment` is idempotent (guarded by Payment.status), so redelivery of
the same event (e.g. after a consumer crash/restart) never causes a duplicate
charge - this is the "reliable failure recovery" half of the workflow.

If the broker is unreachable, the consumer logs a warning and stays idle;
the API still works because `payment_service.create_payment_intent` also
processes payments inline as a synchronous fallback.
"""

import asyncio
import json
import logging
import threading

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

from app.core.config import settings
from app.core.database import SessionLocal
from app.kafka.events import TOPIC_PAYMENT_EVENTS

logger = logging.getLogger(__name__)


class PaymentEventConsumer:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run, name="kafka-payment-consumer", daemon=True
        )
        self._thread.start()

    def _run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._consume())
        finally:
            loop.close()

    async def _consume(self) -> None:
        consumer = AIOKafkaConsumer(
            TOPIC_PAYMENT_EVENTS,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id="payment-processor",
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            enable_auto_commit=True,
            auto_offset_reset="earliest",
        )
        try:
            await consumer.start()
            logger.info(
                "Kafka consumer connected to %s (group=payment-processor)",
                settings.KAFKA_BOOTSTRAP_SERVERS,
            )
        except KafkaError as e:
            logger.warning(
                "Kafka consumer failed to connect (%s); event-driven payment "
                "processing is disabled, falling back to inline processing",
                e,
            )
            return

        try:
            async for msg in consumer:
                await self._handle_message(msg.value)
        finally:
            await consumer.stop()

    async def _handle_message(self, event: dict) -> None:
        if event.get("event_type") != "payment.requested":
            return
        payment_id = event.get("payment_id")
        logger.info("Consumed payment.requested event for payment_id=%s", payment_id)
        # Offload blocking DB work so the consumer's event loop stays responsive
        await asyncio.to_thread(self._process_in_new_session, payment_id)

    def _process_in_new_session(self, payment_id: int) -> None:
        from app.services import payment_service  # avoid import cycle at module load

        db = SessionLocal()
        try:
            payment_service.process_payment(db, payment_id)
        except Exception as e:
            logger.error("Failed processing payment_id=%s: %s", payment_id, e)
        finally:
            db.close()


payment_event_consumer = PaymentEventConsumer()
