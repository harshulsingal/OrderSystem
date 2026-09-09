"""Best-effort Redis helpers for idempotency caching and distributed locks.

All helpers fail open (log a warning and act as a no-op) when Redis is
unreachable, so the API never depends on Redis being available -
correctness is always guaranteed by PostgreSQL constraints/locks.
"""

import logging

import redis
from redis.backoff import NoBackoff
from redis.retry import Retry

from app.core.config import settings

logger = logging.getLogger(__name__)

redis_client: redis.Redis = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
    retry=Retry(NoBackoff(), retries=0),
    retry_on_error=[],
)


def try_acquire_lock(key: str, token: str, ttl_seconds: int = 30) -> bool:
    """Best-effort distributed lock. Returns True (fail-open) if Redis is down."""
    try:
        return bool(redis_client.set(key, token, nx=True, ex=ttl_seconds))
    except redis.RedisError as e:
        logger.warning("Redis unavailable, skipping lock acquire for key=%s: %s", key, e)
        return True


def release_lock(key: str, token: str) -> None:
    try:
        if redis_client.get(key) == token:
            redis_client.delete(key)
    except redis.RedisError as e:
        logger.warning("Redis unavailable, skipping lock release for key=%s: %s", key, e)


def cache_get(key: str) -> str | None:
    try:
        return redis_client.get(key)
    except redis.RedisError as e:
        logger.warning("Redis unavailable, cache_get skipped for key=%s: %s", key, e)
        return None


def cache_set(key: str, value: str, ttl_seconds: int = 3600) -> None:
    try:
        redis_client.set(key, value, ex=ttl_seconds)
    except redis.RedisError as e:
        logger.warning("Redis unavailable, cache_set skipped for key=%s: %s", key, e)
