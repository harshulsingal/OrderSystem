"""Async Kafka producer running on a dedicated background event loop.

Runs its own event loop in a background thread so synchronous service/route
code (SQLAlchemy Session-based) can publish events without needing to be async.
Publishing is best-effort: if the broker is unreachable, events are dropped
and a warning is logged instead of failing the request - the API request
path never depends on Kafka being up.
"""

import asyncio
import json
import logging
import threading

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from app.core.config import settings

logger = logging.getLogger(__name__)


class KafkaEventProducer:
    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._producer: AIOKafkaProducer | None = None
        self._ready = threading.Event()

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run_loop, name="kafka-producer", daemon=True
        )
        self._thread.start()
        self._ready.wait(timeout=5)

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._start_producer())
        self._ready.set()
        self._loop.run_forever()

    async def _start_producer(self) -> None:
        producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        try:
            await producer.start()
            self._producer = producer
            logger.info(
                "Kafka producer connected to %s", settings.KAFKA_BOOTSTRAP_SERVERS
            )
        except KafkaError as e:
            logger.warning(
                "Kafka producer failed to connect (%s); events will be dropped", e
            )

    def publish(self, topic: str, event: dict) -> None:
        if not self._loop or not self._producer:
            logger.warning("Kafka producer unavailable; dropping event on topic=%s", topic)
            return

        async def _send() -> None:
            assert self._producer is not None
            try:
                await self._producer.send_and_wait(topic, event)
            except KafkaError as e:
                logger.warning("Failed to publish event to topic=%s: %s", topic, e)

        asyncio.run_coroutine_threadsafe(_send(), self._loop)

    def stop(self) -> None:
        if self._loop and self._producer:
            fut = asyncio.run_coroutine_threadsafe(self._producer.stop(), self._loop)
            try:
                fut.result(timeout=5)
            except Exception:
                pass
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=5)


kafka_producer = KafkaEventProducer()
