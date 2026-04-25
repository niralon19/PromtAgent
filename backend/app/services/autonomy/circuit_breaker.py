"""Per-action+host circuit breaker for autonomous execution."""
from __future__ import annotations

import structlog

log = structlog.get_logger(__name__)

_FAILURE_THRESHOLD = 3
_WINDOW_SECONDS = 3600  # 1 hour


class CircuitBreaker:
    """Track failures per (action_key, hostname) and block if threshold exceeded."""

    def __init__(self, redis_client=None) -> None:
        self._redis = redis_client

    async def is_open(self, action_key: str, hostname: str) -> bool:
        """Return True if circuit is open (too many recent failures)."""
        if self._redis is None:
            return False
        try:
            key = f"cb:{action_key}:{hostname}"
            count = await self._redis.get(key)
            return int(count or 0) >= _FAILURE_THRESHOLD
        except Exception:
            return False

    async def record_failure(self, action_key: str, hostname: str) -> None:
        if self._redis is None:
            return
        try:
            key = f"cb:{action_key}:{hostname}"
            await self._redis.incr(key)
            await self._redis.expire(key, _WINDOW_SECONDS)
            count = await self._redis.get(key)
            if int(count or 0) >= _FAILURE_THRESHOLD:
                log.warning("circuit_breaker_tripped", action=action_key, hostname=hostname)
        except Exception:
            pass

    async def reset(self, action_key: str, hostname: str) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.delete(f"cb:{action_key}:{hostname}")
        except Exception:
            pass
