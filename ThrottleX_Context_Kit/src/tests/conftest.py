"""Pytest configuration and fixtures."""

import pytest
from unittest.mock import AsyncMock, MagicMock

import fakeredis.aioredis


@pytest.fixture
def mock_redis():
    """Create a fake Redis client for testing."""
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def mock_repository(mock_redis):
    """Create a mock repository with fake Redis."""
    from throttlex.repository import RedisRepository

    repo = RedisRepository()
    repo._client = mock_redis
    repo._sliding_window_sha = "fake_sha"
    return repo


@pytest.fixture
def sample_policy():
    """Create a sample policy for testing."""
    from throttlex.models import Algorithm, Policy, Scope

    return Policy(
        tenantId="t-test-01",
        route="/api/v1",
        scope=Scope.TENANT_ROUTE,
        algorithm=Algorithm.SLIDING_WINDOW,
        limit=100,
        windowSeconds=60,
        burst=10,
    )


@pytest.fixture
def sample_policies():
    """Create multiple sample policies for testing."""
    from throttlex.models import Algorithm, Policy, Scope

    return [
        Policy(
            tenantId="t-free-01",
            scope=Scope.TENANT,
            algorithm=Algorithm.SLIDING_WINDOW,
            limit=60,
            windowSeconds=60,
            burst=20,
        ),
        Policy(
            tenantId="t-pro-01",
            route="/inference/text",
            scope=Scope.TENANT_ROUTE,
            algorithm=Algorithm.SLIDING_WINDOW,
            limit=600,
            windowSeconds=60,
            burst=100,
        ),
        Policy(
            tenantId="t-ent-01",
            scope=Scope.TENANT,
            algorithm=Algorithm.TOKEN_BUCKET,
            limit=3000,
            windowSeconds=60,
            burst=600,
        ),
    ]
