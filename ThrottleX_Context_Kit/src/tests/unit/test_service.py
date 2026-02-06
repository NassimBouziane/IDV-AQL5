"""Unit tests for the rate limiter service."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from throttlex.models import Algorithm, EvaluateRequest, Policy, Scope
from throttlex.service import RateLimiterService


class TestRateLimiterService:
    """Tests for RateLimiterService."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock repository."""
        repo = MagicMock()
        repo.save_policy = AsyncMock()
        repo.get_policies = AsyncMock(return_value=[])
        repo.delete_policy = AsyncMock(return_value=True)
        repo.get_matching_policy = AsyncMock(return_value=None)
        repo.evaluate_sliding_window = AsyncMock(return_value=(True, 99, 1234567890))
        repo.evaluate_token_bucket = AsyncMock(return_value=(True, 49, 0))
        return repo

    @pytest.fixture
    def service(self, mock_repository):
        """Create service with mock repository."""
        return RateLimiterService(repository=mock_repository)

    @pytest.mark.asyncio
    async def test_create_policy(self, service, mock_repository):
        """Test policy creation."""
        policy = Policy(
            tenantId="tenant1",
            scope=Scope.TENANT,
            algorithm=Algorithm.SLIDING_WINDOW,
            limit=100,
            windowSeconds=60,
        )
        mock_repository.save_policy.return_value = policy

        result = await service.create_policy(policy)

        assert result.tenant_id == "tenant1"
        mock_repository.save_policy.assert_called_once_with(policy)

    @pytest.mark.asyncio
    async def test_get_policies(self, service, mock_repository):
        """Test getting policies for a tenant."""
        expected = [
            Policy(
                tenantId="tenant1",
                scope=Scope.TENANT,
                algorithm=Algorithm.SLIDING_WINDOW,
                limit=100,
                windowSeconds=60,
            )
        ]
        mock_repository.get_policies.return_value = expected

        result = await service.get_policies("tenant1")

        assert len(result) == 1
        assert result[0].tenant_id == "tenant1"

    @pytest.mark.asyncio
    async def test_evaluate_sliding_window_allow(self, service, mock_repository):
        """Test evaluation allowing request with sliding window."""
        policy = Policy(
            tenantId="tenant1",
            route="/api",
            scope=Scope.TENANT_ROUTE,
            algorithm=Algorithm.SLIDING_WINDOW,
            limit=100,
            windowSeconds=60,
        )
        mock_repository.get_matching_policy.return_value = policy
        mock_repository.evaluate_sliding_window.return_value = (True, 99, 1234567890)

        request = EvaluateRequest(tenantId="tenant1", route="/api")
        response, headers = await service.evaluate(request)

        assert response.allow is True
        assert response.remaining == 99

    @pytest.mark.asyncio
    async def test_evaluate_sliding_window_block(self, service, mock_repository):
        """Test evaluation blocking request when limit exceeded."""
        policy = Policy(
            tenantId="tenant1",
            route="/api",
            scope=Scope.TENANT_ROUTE,
            algorithm=Algorithm.SLIDING_WINDOW,
            limit=100,
            windowSeconds=60,
        )
        mock_repository.get_matching_policy.return_value = policy
        mock_repository.evaluate_sliding_window.return_value = (False, 0, 1234567890)

        request = EvaluateRequest(tenantId="tenant1", route="/api")
        response, headers = await service.evaluate(request)

        assert response.allow is False
        assert response.remaining == 0

    @pytest.mark.asyncio
    async def test_evaluate_token_bucket_allow(self, service, mock_repository):
        """Test evaluation allowing request with token bucket."""
        policy = Policy(
            tenantId="tenant1",
            route="/api",
            scope=Scope.TENANT_ROUTE,
            algorithm=Algorithm.TOKEN_BUCKET,
            limit=50,
            windowSeconds=60,
            burst=10,
        )
        mock_repository.get_matching_policy.return_value = policy
        mock_repository.evaluate_token_bucket.return_value = (True, 59, 0)

        request = EvaluateRequest(tenantId="tenant1", route="/api")
        response, headers = await service.evaluate(request)

        assert response.allow is True
        mock_repository.evaluate_token_bucket.assert_called_once()

    @pytest.mark.asyncio
    async def test_evaluate_token_bucket_block(self, service, mock_repository):
        """Test evaluation blocking with token bucket when no tokens."""
        policy = Policy(
            tenantId="tenant1",
            route="/api",
            scope=Scope.TENANT_ROUTE,
            algorithm=Algorithm.TOKEN_BUCKET,
            limit=50,
            windowSeconds=60,
        )
        mock_repository.get_matching_policy.return_value = policy
        mock_repository.evaluate_token_bucket.return_value = (False, 0, 100)

        request = EvaluateRequest(tenantId="tenant1", route="/api")
        response, headers = await service.evaluate(request)

        assert response.allow is False

    @pytest.mark.asyncio
    async def test_evaluate_no_policy_uses_defaults(self, service, mock_repository):
        """Test that missing policy uses default settings."""
        mock_repository.get_matching_policy.return_value = None
        mock_repository.evaluate_sliding_window.return_value = (True, 59, 1234567890)

        request = EvaluateRequest(tenantId="unknown", route="/api")
        response, headers = await service.evaluate(request)

        # Should still work with default policy
        assert response.allow is True

    @pytest.mark.asyncio
    async def test_delete_policy(self, service, mock_repository):
        """Test policy deletion."""
        result = await service.delete_policy("tenant1", "/api")

        assert result is True
        mock_repository.delete_policy.assert_called_once_with("tenant1", "/api")
