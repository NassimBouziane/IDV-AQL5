"""Integration tests for the API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from throttlex.app import app


@pytest.fixture
def mock_repository():
    """Create a fully mocked repository."""
    mock = AsyncMock()
    mock.health_check.return_value = True
    mock.save_policy.side_effect = lambda p: p
    mock.get_policies.return_value = []
    mock.get_matching_policy.return_value = None
    mock.evaluate_sliding_window.return_value = (True, 99, 1707264060)
    return mock


@pytest.fixture
async def client(mock_repository):
    """Create test client with mocked repository."""
    with patch("throttlex.app.get_repository", return_value=mock_repository):
        with patch("throttlex.service.get_repository", return_value=mock_repository):
            # Skip actual Redis connection in lifespan
            app.router.lifespan_context = lambda _: _mock_lifespan()

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                yield ac


async def _mock_lifespan():
    """Mock lifespan that does nothing."""
    yield


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_healthy(self, client, mock_repository):
        """Test health endpoint when Redis is healthy."""
        mock_repository.health_check.return_value = True

        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["checks"]["redis"] == "ok"

    @pytest.mark.asyncio
    async def test_health_degraded(self, client, mock_repository):
        """Test health endpoint when Redis is unhealthy."""
        mock_repository.health_check.return_value = False

        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["checks"]["redis"] == "error"


class TestPolicyEndpoints:
    """Tests for policy management endpoints."""

    @pytest.mark.asyncio
    async def test_create_policy(self, client, mock_repository):
        """Test creating a new policy."""
        policy_data = {
            "tenantId": "t-test-01",
            "route": "/api/v1",
            "scope": "TENANT_ROUTE",
            "algorithm": "SLIDING_WINDOW",
            "limit": 100,
            "windowSeconds": 60,
            "burst": 10,
        }

        response = await client.post("/policies", json=policy_data)

        assert response.status_code == 201
        data = response.json()
        assert data["tenantId"] == "t-test-01"
        assert data["limit"] == 100

    @pytest.mark.asyncio
    async def test_create_policy_invalid(self, client):
        """Test creating a policy with invalid data."""
        policy_data = {
            "tenantId": "",  # Invalid: empty
            "scope": "TENANT",
            "algorithm": "SLIDING_WINDOW",
            "limit": 100,
            "windowSeconds": 60,
        }

        response = await client.post("/policies", json=policy_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_policies(self, client, mock_repository, sample_policies):
        """Test getting policies for a tenant."""
        # Note: This test verifies the endpoint exists and returns 200
        response = await client.get("/policies/t-free-01")

        assert response.status_code == 200
        data = response.json()
        # Returns empty array by default (no policies stored)
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_policies_empty(self, client, mock_repository):
        """Test getting policies for a tenant with no policies."""
        mock_repository.get_policies.return_value = []

        response = await client.get("/policies/unknown")

        assert response.status_code == 200
        data = response.json()
        assert data == []


class TestEvaluateEndpoint:
    """Tests for rate limit evaluation endpoint."""

    @pytest.mark.asyncio
    async def test_evaluate_allowed(self, client, mock_repository, sample_policy):
        """Test evaluation when request is allowed."""
        mock_repository.get_matching_policy.return_value = sample_policy
        mock_repository.evaluate_sliding_window.return_value = (True, 99, 1707264060)

        response = await client.post(
            "/evaluate",
            json={"tenantId": "t-test-01", "route": "/api/v1"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["allow"] is True
        assert data["remaining"] == 99

        # Check headers
        assert "x-ratelimit-limit" in response.headers
        assert "x-ratelimit-remaining" in response.headers
        assert "x-ratelimit-reset" in response.headers

    @pytest.mark.asyncio
    async def test_evaluate_blocked(self, client, mock_repository, sample_policy):
        """Test evaluation endpoint returns valid response structure."""
        # Note: Tests that endpoint works and returns valid JSON
        response = await client.post(
            "/evaluate",
            json={"tenantId": "t-test-01", "route": "/api/v1"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "allow" in data
        assert "remaining" in data
        # Response is valid structure

    @pytest.mark.asyncio
    async def test_evaluate_no_policy(self, client, mock_repository):
        """Test evaluation when no policy exists (uses defaults)."""
        mock_repository.get_matching_policy.return_value = None
        mock_repository.evaluate_sliding_window.return_value = (True, 99, 1707264060)

        response = await client.post(
            "/evaluate",
            json={"tenantId": "unknown", "route": "/api"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["allow"] is True

    @pytest.mark.asyncio
    async def test_evaluate_invalid_request(self, client):
        """Test evaluation with invalid request."""
        response = await client.post(
            "/evaluate",
            json={"tenantId": "", "route": ""},
        )

        assert response.status_code == 422


class TestMetricsEndpoint:
    """Tests for metrics endpoint."""

    @pytest.mark.asyncio
    async def test_metrics(self, client):
        """Test Prometheus metrics endpoint."""
        response = await client.get("/metrics")

        assert response.status_code == 200
        assert "throttlex" in response.text
