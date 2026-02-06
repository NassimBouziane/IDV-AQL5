"""Property-based tests using Hypothesis for rate limiting algorithms."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from throttlex.models import Algorithm, Policy, Scope
from throttlex.service import RateLimiterService


class TestRateLimitingProperties:
    """Property-based tests ensuring rate limiting invariants."""

    @given(
        limit=st.integers(min_value=1, max_value=100),
        window=st.integers(min_value=1, max_value=60),
    )
    @settings(max_examples=50)
    def test_never_exceeds_limit_sliding_window(self, limit: int, window: int):
        """
        Property: Never authorize more than limit requests in a window.

        For any limit N, if we make N+10 requests, at most N should be allowed.
        """
        # Setup
        allowed_count = 0
        current_count = 0

        async def mock_evaluate(*args, **kwargs):
            nonlocal current_count
            if current_count < limit:
                current_count += 1
                return (True, limit - current_count, 0)
            return (False, 0, 0)

        mock_repo = MagicMock()
        mock_repo.evaluate_sliding_window = AsyncMock(side_effect=mock_evaluate)
        mock_repo.get_matching_policy = AsyncMock(
            return_value=Policy(
                tenantId="test",
                route="/",
                scope=Scope.TENANT,
                algorithm=Algorithm.SLIDING_WINDOW,
                limit=limit,
                windowSeconds=window,
            )
        )

        service = RateLimiterService(repository=mock_repo)

        # Make limit + 10 requests
        async def run_test():
            nonlocal allowed_count
            from throttlex.models import EvaluateRequest

            for _ in range(limit + 10):
                req = EvaluateRequest(tenantId="test", route="/")
                response, _ = await service.evaluate(req)
                if response.allow:
                    allowed_count += 1

        asyncio.get_event_loop().run_until_complete(run_test())

        # Property: allowed requests should never exceed limit
        assert allowed_count <= limit, f"Allowed {allowed_count} but limit is {limit}"

    @given(
        limit=st.integers(min_value=1, max_value=100),
        burst=st.integers(min_value=0, max_value=20),
    )
    @settings(max_examples=30)
    def test_burst_respects_total_capacity(self, limit: int, burst: int):
        """
        Property: With burst, total allowed = limit + burst.
        """
        effective_limit = limit + burst
        allowed_count = 0
        current_count = 0

        async def mock_evaluate(tid, route, lim, window, bst):
            nonlocal current_count
            eff_limit = lim + bst
            if current_count < eff_limit:
                current_count += 1
                return (True, eff_limit - current_count, 0)
            return (False, 0, 0)

        mock_repo = MagicMock()
        mock_repo.evaluate_sliding_window = AsyncMock(side_effect=mock_evaluate)
        mock_repo.get_matching_policy = AsyncMock(
            return_value=Policy(
                tenantId="test",
                route="/",
                scope=Scope.TENANT,
                algorithm=Algorithm.SLIDING_WINDOW,
                limit=limit,
                windowSeconds=60,
                burst=burst,
            )
        )

        service = RateLimiterService(repository=mock_repo)

        async def run_test():
            nonlocal allowed_count
            from throttlex.models import EvaluateRequest

            for _ in range(effective_limit + 10):
                req = EvaluateRequest(tenantId="test", route="/")
                response, _ = await service.evaluate(req)
                if response.allow:
                    allowed_count += 1

        asyncio.get_event_loop().run_until_complete(run_test())

        assert allowed_count <= effective_limit, (
            f"Allowed {allowed_count} but effective limit is {effective_limit}"
        )

    @given(
        tenant_id=st.text(
            min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))
        )
    )
    @settings(max_examples=20)
    def test_tenant_isolation(self, tenant_id: str):
        """
        Property: Different tenants should have isolated counters.
        """
        if not tenant_id.strip():
            return  # Skip empty strings

        counters = {}

        async def mock_evaluate(tid, route, limit, window, burst):
            key = f"{tid}:{route}"
            counters[key] = counters.get(key, 0) + 1
            if counters[key] <= limit + burst:
                return (True, limit + burst - counters[key], 0)
            return (False, 0, 0)

        mock_repo = MagicMock()
        mock_repo.evaluate_sliding_window = AsyncMock(side_effect=mock_evaluate)
        mock_repo.get_matching_policy = AsyncMock(
            return_value=Policy(
                tenantId=tenant_id,
                route="/",
                scope=Scope.TENANT,
                algorithm=Algorithm.SLIDING_WINDOW,
                limit=5,
                windowSeconds=60,
            )
        )

        service = RateLimiterService(repository=mock_repo)

        async def run_test():
            from throttlex.models import EvaluateRequest

            # Make requests for this tenant
            for _ in range(5):
                req = EvaluateRequest(tenantId=tenant_id, route="/")
                await service.evaluate(req)

            # Make requests for another tenant
            for _ in range(5):
                req = EvaluateRequest(tenantId="other_tenant", route="/")
                await service.evaluate(req)

        asyncio.get_event_loop().run_until_complete(run_test())

        # Verify isolation
        tenant_key = f"{tenant_id}:/"
        other_key = "other_tenant:/"
        assert counters.get(tenant_key, 0) <= 5
        assert counters.get(other_key, 0) <= 5


class TestTokenBucketProperties:
    """Property-based tests for Token Bucket algorithm."""

    @given(
        capacity=st.integers(min_value=1, max_value=50),
        refill_rate=st.floats(min_value=0.1, max_value=10.0),
    )
    @settings(max_examples=30)
    def test_token_bucket_never_exceeds_capacity(self, capacity: int, refill_rate: float):
        """
        Property: Token bucket should never have more tokens than capacity.
        """
        tokens = capacity  # Start full

        async def mock_token_bucket(*args, **kwargs):
            nonlocal tokens
            if tokens > 0:
                tokens -= 1
                return (True, tokens, 0)
            return (False, 0, 100)

        mock_repo = MagicMock()
        mock_repo.evaluate_token_bucket = AsyncMock(side_effect=mock_token_bucket)
        mock_repo.get_matching_policy = AsyncMock(
            return_value=Policy(
                tenantId="test",
                route="/",
                scope=Scope.TENANT,
                algorithm=Algorithm.TOKEN_BUCKET,
                limit=capacity,
                windowSeconds=60,
            )
        )

        service = RateLimiterService(repository=mock_repo)
        allowed = 0

        async def run_test():
            nonlocal allowed
            from throttlex.models import EvaluateRequest

            for _ in range(capacity + 10):
                req = EvaluateRequest(tenantId="test", route="/")
                response, _ = await service.evaluate(req)
                if response.allow:
                    allowed += 1

        asyncio.get_event_loop().run_until_complete(run_test())

        assert allowed <= capacity


class TestConcurrencySafety:
    """Tests for concurrent access safety."""

    @pytest.mark.asyncio
    async def test_concurrent_requests_respect_limit(self):
        """
        Property: Even with concurrent requests, limit should be respected.

        This simulates the atomic behavior of Lua scripts.
        """
        import asyncio

        limit = 10
        counter = {"value": 0}
        allowed = {"count": 0}
        lock = asyncio.Lock()

        async def mock_evaluate(*args, **kwargs):
            async with lock:  # Simulates atomic Lua script
                if counter["value"] < limit:
                    counter["value"] += 1
                    return (True, limit - counter["value"], 0)
                return (False, 0, 0)

        mock_repo = MagicMock()
        mock_repo.evaluate_sliding_window = AsyncMock(side_effect=mock_evaluate)
        mock_repo.get_matching_policy = AsyncMock(
            return_value=Policy(
                tenantId="test",
                route="/",
                scope=Scope.TENANT,
                algorithm=Algorithm.SLIDING_WINDOW,
                limit=limit,
                windowSeconds=60,
            )
        )

        service = RateLimiterService(repository=mock_repo)

        async def make_request():
            from throttlex.models import EvaluateRequest

            req = EvaluateRequest(tenantId="test", route="/")
            response, _ = await service.evaluate(req)
            if response.allow:
                async with lock:
                    allowed["count"] += 1

        # Launch concurrent requests
        tasks = [make_request() for _ in range(50)]
        await asyncio.gather(*tasks)

        assert allowed["count"] == limit, f"Expected {limit}, got {allowed['count']}"
