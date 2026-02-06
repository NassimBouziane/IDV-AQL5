"""Redis repository for rate limiting counters and policies."""

import json
import time

import redis.asyncio as redis
import structlog
from redis.exceptions import NoScriptError

from throttlex.config import get_settings
from throttlex.models import Policy

logger = structlog.get_logger()

# Lua script for sliding window rate limiting (atomic operation)
SLIDING_WINDOW_SCRIPT = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local burst = tonumber(ARGV[4])

local effective_limit = limit + burst

local current = redis.call('GET', key)
if current == false then
    current = 0
else
    current = tonumber(current)
end

if current < effective_limit then
    redis.call('INCR', key)
    redis.call('EXPIRE', key, window)
    return {1, effective_limit - current - 1, now + window}
else
    local ttl = redis.call('TTL', key)
    if ttl < 0 then ttl = window end
    return {0, 0, now + ttl}
end
"""

# Lua script for Token Bucket (atomic operation)
BUCKET_REFILL_SCRIPT = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4]) or 1

local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens = tonumber(bucket[1])
local last_refill = tonumber(bucket[2])

if tokens == nil then
    tokens = capacity
    last_refill = now
end

local elapsed = now - last_refill
local refill = math.floor(elapsed * refill_rate)
tokens = math.min(capacity, tokens + refill)

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


class RedisRepository:
    """Repository for Redis operations."""

    def __init__(self) -> None:
        self._client: redis.Redis | None = None
        self._sliding_window_sha: str | None = None
        self._token_bucket_sha: str | None = None

    async def connect(self) -> None:
        """Connect to Redis."""
        settings = get_settings()
        self._client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password or None,
            db=settings.redis_db,
            decode_responses=True,
            max_connections=settings.redis_pool_size,
        )
        # Test connection
        await self._client.ping()
        logger.info("redis_connected", host=settings.redis_host, port=settings.redis_port)

        # Load Lua scripts
        self._sliding_window_sha = await self._client.script_load(SLIDING_WINDOW_SCRIPT)
        self._token_bucket_sha = await self._client.script_load(BUCKET_REFILL_SCRIPT)
        logger.info("lua_scripts_loaded", scripts=["sliding_window", "token_bucket"])

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client:
            await self._client.aclose()
            logger.info("redis_disconnected")

    async def health_check(self) -> bool:
        """Check if Redis is healthy."""
        try:
            if self._client:
                await self._client.ping()
                return True
        except Exception as e:
            logger.error("redis_health_check_failed", error=str(e))
        return False

    # === Policy operations ===

    async def save_policy(self, policy: Policy) -> Policy:
        """Save a policy to Redis."""
        if not self._client:
            raise RuntimeError("Redis not connected")

        key = policy.get_key()
        data = policy.model_dump(by_alias=True)

        if policy.ttl_seconds:
            await self._client.setex(key, policy.ttl_seconds, json.dumps(data))
        else:
            await self._client.set(key, json.dumps(data))

        # Also add to tenant's policy set for listing
        await self._client.sadd(f"policies:{policy.tenant_id}", key)  # type: ignore[misc]

        logger.info("policy_saved", tenant_id=policy.tenant_id, route=policy.route)
        return policy

    async def get_policies(self, tenant_id: str) -> list[Policy]:
        """Get all policies for a tenant."""
        if not self._client:
            raise RuntimeError("Redis not connected")

        policy_keys = await self._client.smembers(f"policies:{tenant_id}")  # type: ignore[misc]
        policies = []

        for key in policy_keys:
            data = await self._client.get(key)
            if data:
                policies.append(Policy.model_validate(json.loads(data)))

        return policies

    async def get_matching_policy(self, tenant_id: str, route: str) -> Policy | None:
        """Get the most specific policy matching tenant and route."""
        if not self._client:
            raise RuntimeError("Redis not connected")

        # Try route-specific policy first
        route_key = f"policy:{tenant_id}:{route}"
        data = await self._client.get(route_key)
        if data:
            return Policy.model_validate(json.loads(data))

        # Fall back to tenant-level policy
        tenant_key = f"policy:{tenant_id}:*"
        data = await self._client.get(tenant_key)
        if data:
            return Policy.model_validate(json.loads(data))

        return None

    async def delete_policy(self, tenant_id: str, route: str | None = None) -> bool:
        """Delete a policy."""
        if not self._client:
            raise RuntimeError("Redis not connected")

        if route:
            key = f"policy:{tenant_id}:{route}"
        else:
            key = f"policy:{tenant_id}:*"

        deleted = await self._client.delete(key)
        await self._client.srem(f"policies:{tenant_id}", key)  # type: ignore[misc]

        logger.info("policy_deleted", tenant_id=tenant_id, route=route, deleted=deleted > 0)
        return bool(deleted > 0)

    # === Rate limiting operations ===

    async def evaluate_sliding_window(
        self, tenant_id: str, route: str, limit: int, window_seconds: int, burst: int = 0
    ) -> tuple[bool, int, int]:
        """
        Evaluate rate limit using sliding window algorithm.

        Returns: (allow, remaining, reset_at)
        """
        if not self._client or not self._sliding_window_sha:
            raise RuntimeError("Redis not connected")

        now = int(time.time())
        window_start = now - (now % window_seconds)
        key = f"ratelimit:{tenant_id}:{route}:{window_start}"

        try:
            result = await self._client.evalsha(  # type: ignore[misc]
                self._sliding_window_sha,
                1,
                key,
                str(limit),
                str(window_seconds),
                str(now),
                str(burst),
            )
            allow = result[0] == 1
            remaining = int(result[1])
            reset_at = int(result[2])

            logger.debug(
                "rate_limit_evaluated",
                tenant_id=tenant_id,
                route=route,
                allow=allow,
                remaining=remaining,
            )

            return allow, remaining, reset_at

        except NoScriptError:
            # Script was flushed, reload it
            self._sliding_window_sha = await self._client.script_load(SLIDING_WINDOW_SCRIPT)
            return await self.evaluate_sliding_window(
                tenant_id, route, limit, window_seconds, burst
            )

    async def evaluate_token_bucket(
        self, tenant_id: str, route: str, capacity: int, refill_rate: float, tokens: int = 1
    ) -> tuple[bool, int, int]:
        """
        Evaluate rate limit using token bucket algorithm.

        Args:
            tenant_id: Tenant identifier
            route: API route
            capacity: Maximum tokens (bucket size)
            refill_rate: Tokens per second
            tokens: Tokens to consume

        Returns: (allow, remaining, reset_at)
        """
        if not self._client or not self._token_bucket_sha:
            raise RuntimeError("Redis not connected")

        now = int(time.time())
        key = f"tokenbucket:{tenant_id}:{route}"

        try:
            result = await self._client.evalsha(  # type: ignore[misc]
                self._token_bucket_sha,
                1,
                key,
                str(capacity),
                str(refill_rate),
                str(now),
                str(tokens),
            )

            allow = result[0] == 1
            remaining = int(result[1])
            reset_at = int(result[2]) if result[2] > 0 else now

            logger.debug(
                "token_bucket_evaluated",
                tenant_id=tenant_id,
                route=route,
                allow=allow,
                remaining=remaining,
            )

            return allow, remaining, reset_at

        except NoScriptError:
            self._token_bucket_sha = await self._client.script_load(BUCKET_REFILL_SCRIPT)
            return await self.evaluate_token_bucket(tenant_id, route, capacity, refill_rate, tokens)

    async def get_counter(self, tenant_id: str, route: str, window_seconds: int) -> int:
        """Get current counter value for a tenant/route."""
        if not self._client:
            raise RuntimeError("Redis not connected")

        now = int(time.time())
        window_start = now - (now % window_seconds)
        key = f"ratelimit:{tenant_id}:{route}:{window_start}"

        value = await self._client.get(key)
        return int(value) if value else 0


# Singleton instance
_repository: RedisRepository | None = None


def get_repository() -> RedisRepository:
    """Get the repository singleton."""
    global _repository
    if _repository is None:
        _repository = RedisRepository()
    return _repository
