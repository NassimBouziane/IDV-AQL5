"""Unit tests for FastAPI app endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from throttlex.models import EvaluateResponse, Policy


class TestHealthEndpoints:
    """Tests for health endpoints."""

    @pytest.fixture
    def mock_repo(self):
        """Create mock repository."""
        with patch("throttlex.app.get_repository") as mock:
            repo = MagicMock()
            repo.health_check = AsyncMock(return_value=True)
            repo.connect = AsyncMock()
            repo.disconnect = AsyncMock()
            mock.return_value = repo
            yield repo

    def test_health_healthy(self, mock_repo):
        """Test health endpoint when healthy."""
        from throttlex.app import app

        with patch("throttlex.app.get_repository") as mock_get:
            mock_get.return_value = mock_repo
            client = TestClient(app, raise_server_exceptions=False)

            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

    def test_health_degraded(self, mock_repo):
        """Test health endpoint when degraded."""
        from throttlex.app import app

        mock_repo.health_check = AsyncMock(return_value=False)

        with patch("throttlex.app.get_repository") as mock_get:
            mock_get.return_value = mock_repo
            client = TestClient(app, raise_server_exceptions=False)

            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"

    def test_ready_ok(self, mock_repo):
        """Test ready endpoint when OK."""
        from throttlex.app import app

        with patch("throttlex.app.get_repository") as mock_get:
            mock_get.return_value = mock_repo
            client = TestClient(app, raise_server_exceptions=False)

            response = client.get("/ready")

            assert response.status_code == 200

    def test_ready_not_available(self, mock_repo):
        """Test ready endpoint when Redis not available."""
        from throttlex.app import app

        mock_repo.health_check = AsyncMock(return_value=False)

        with patch("throttlex.app.get_repository") as mock_get:
            mock_get.return_value = mock_repo
            client = TestClient(app, raise_server_exceptions=False)

            response = client.get("/ready")

            assert response.status_code == 503


class TestMetricsEndpoint:
    """Tests for metrics endpoint."""

    def test_metrics(self):
        """Test Prometheus metrics endpoint."""
        from throttlex.app import app

        with patch("throttlex.app.get_repository") as mock_get:
            repo = MagicMock()
            repo.connect = AsyncMock()
            repo.disconnect = AsyncMock()
            mock_get.return_value = repo
            client = TestClient(app, raise_server_exceptions=False)

            response = client.get("/metrics")

            assert response.status_code == 200
            assert "text/plain" in response.headers.get("content-type", "")


class TestPolicyEndpoints:
    """Tests for policy endpoints."""

    @pytest.fixture
    def mock_service(self):
        """Create mock service."""
        with patch("throttlex.app.get_service") as mock:
            service = MagicMock()
            service.create_policy = AsyncMock()
            service.get_policies = AsyncMock(return_value=[])
            service.delete_policy = AsyncMock(return_value=True)
            mock.return_value = service
            yield service

    @pytest.fixture
    def mock_repo(self):
        """Create mock repository."""
        with patch("throttlex.app.get_repository") as mock:
            repo = MagicMock()
            repo.connect = AsyncMock()
            repo.disconnect = AsyncMock()
            repo.health_check = AsyncMock(return_value=True)
            mock.return_value = repo
            yield repo

    def test_create_policy(self, mock_service, mock_repo):
        """Test policy creation."""
        from throttlex.app import app

        policy_data = {
            "tenantId": "t-test",
            "scope": "TENANT",
            "algorithm": "SLIDING_WINDOW",
            "limit": 100,
            "windowSeconds": 60,
        }

        mock_service.create_policy.return_value = Policy(**policy_data)

        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/policies", json=policy_data)

        assert response.status_code == 201

    def test_get_policies(self, mock_service, mock_repo):
        """Test getting policies."""
        from throttlex.app import app

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/policies/t-test")

        assert response.status_code == 200
        assert response.json() == []

    def test_delete_policy_found(self, mock_service, mock_repo):
        """Test deleting existing policy."""
        from throttlex.app import app

        client = TestClient(app, raise_server_exceptions=False)
        response = client.delete("/policies/t-test")

        assert response.status_code == 204

    def test_delete_policy_not_found(self, mock_service, mock_repo):
        """Test deleting non-existing policy."""
        from throttlex.app import app

        mock_service.delete_policy.return_value = False

        client = TestClient(app, raise_server_exceptions=False)
        response = client.delete("/policies/t-test")

        assert response.status_code == 404


class TestEvaluateEndpoint:
    """Tests for evaluate endpoint."""

    @pytest.fixture
    def mock_service(self):
        """Create mock service."""
        with patch("throttlex.app.get_service") as mock:
            service = MagicMock()
            mock.return_value = service
            yield service

    @pytest.fixture
    def mock_repo(self):
        """Create mock repository."""
        with patch("throttlex.app.get_repository") as mock:
            repo = MagicMock()
            repo.connect = AsyncMock()
            repo.disconnect = AsyncMock()
            repo.health_check = AsyncMock(return_value=True)
            mock.return_value = repo
            yield repo

    def test_evaluate_allowed(self, mock_service, mock_repo):
        """Test evaluate when request allowed."""
        from throttlex.app import app

        eval_response = EvaluateResponse(
            allow=True,
            remaining=99,
            limit=100,
            resetAt=1234567890,
        )
        mock_service.evaluate = AsyncMock(return_value=(eval_response, {}))

        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/evaluate",
            json={
                "tenantId": "t-test",
                "route": "/api",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["allow"] is True

    def test_evaluate_blocked(self, mock_service, mock_repo):
        """Test evaluate when request blocked."""
        from throttlex.app import app

        eval_response = EvaluateResponse(
            allow=False,
            remaining=0,
            limit=100,
            resetAt=1234567890,
        )
        mock_service.evaluate = AsyncMock(return_value=(eval_response, {}))

        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/evaluate",
            json={
                "tenantId": "t-test",
                "route": "/api",
            },
        )

        assert response.status_code == 429
