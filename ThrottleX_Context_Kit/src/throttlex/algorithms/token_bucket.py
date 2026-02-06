"""Token Bucket algorithm implementation."""

from __future__ import annotations

import time
from typing import Any

import structlog

logger = structlog.get_logger()

# Lua script for Token Bucket (atomic operation)
BUCKET_REFILL_SCRIPT = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4]) or 1

-- Get current bucket state
local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens = tonumber(bucket[1])
local last_refill = tonumber(bucket[2])

-- Initialize if not exists
if tokens == nil then
    tokens = capacity
    last_refill = now
end

-- Refill tokens based on elapsed time
local elapsed = now - last_refill
local refill = math.floor(elapsed * refill_rate)
tokens = math.min(capacity, tokens + refill)

-- Check if we can consume
if tokens >= requested then
    tokens = tokens - requested
    redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
    redis.call('EXPIRE', key, 3600)
    return {1, tokens, 0}
else
    redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
    redis.call('EXPIRE', key, 3600)
    local wait_time = math.ceil((requested - tokens) / refill_rate)
    return {0, tokens, now + wait_time}
end
"""


class TokenBucket:
    """Token Bucket rate limiter implementation."""

    def __init__(self, redis_client: Any, capacity: int, refill_rate: float):
        """
        Initialize Token Bucket.

        Args:
            redis_client: Redis async client
            capacity: Maximum tokens in bucket (burst capacity)
            refill_rate: Tokens per second to add
        """
        self._client = redis_client
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._script_sha: str | None = None

    async def load_script(self) -> None:
        """Load the Lua script into Redis."""
        self._script_sha = await self._client.script_load(BUCKET_REFILL_SCRIPT)
        logger.info("token_bucket_script_loaded")

    async def consume(self, tenant_id: str, route: str, tokens: int = 1) -> tuple[bool, int, int]:
        """
        Try to consume tokens from the bucket.

        Args:
            tenant_id: Tenant identifier
            route: API route
            tokens: Number of tokens to consume (default 1)

        Returns:
            (allowed, remaining, reset_at)
        """
        if not self._script_sha:
            await self.load_script()

        now = int(time.time())
        key = f"tokenbucket:{tenant_id}:{route}"

        try:
            result = await self._client.evalsha(
                self._script_sha,
                1,
                key,
                str(self._capacity),
                str(self._refill_rate),
                str(now),
                str(tokens),
            )

            allow = result[0] == 1
            remaining = int(result[1])
            reset_at = int(result[2]) if result[2] > 0 else 0

            logger.debug(
                "token_bucket_evaluated",
                tenant_id=tenant_id,
                route=route,
                allow=allow,
                remaining=remaining,
            )

            return allow, remaining, reset_at

        except Exception as e:
            logger.error("token_bucket_error", error=str(e))
            # Fail open in case of error
            return True, 0, 0

    async def get_tokens(self, tenant_id: str, route: str) -> int:
        """Get current token count for a bucket."""
        key = f"tokenbucket:{tenant_id}:{route}"
        tokens = await self._client.hget(key, "tokens")
        return int(tokens) if tokens else self._capacity

    async def reset(self, tenant_id: str, route: str) -> None:
        """Reset bucket to full capacity."""
        key = f"tokenbucket:{tenant_id}:{route}"
        await self._client.delete(key)
