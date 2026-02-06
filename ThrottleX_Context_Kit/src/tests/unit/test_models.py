"""Unit tests for domain models."""

import pytest
from pydantic import ValidationError

from throttlex.models import Algorithm, EvaluateRequest, EvaluateResponse, Policy, Scope


class TestPolicy:
    """Tests for Policy model."""

    def test_create_valid_policy(self):
        """Test creating a valid policy."""
        policy = Policy(
            tenantId="t-test-01",
            route="/api/v1",
            scope=Scope.TENANT_ROUTE,
            algorithm=Algorithm.SLIDING_WINDOW,
            limit=100,
            windowSeconds=60,
            burst=10,
        )

        assert policy.tenant_id == "t-test-01"
        assert policy.route == "/api/v1"
        assert policy.scope == Scope.TENANT_ROUTE
        assert policy.algorithm == Algorithm.SLIDING_WINDOW
        assert policy.limit == 100
        assert policy.window_seconds == 60
        assert policy.burst == 10

    def test_policy_with_alias(self):
        """Test policy creation with alias names."""
        policy = Policy(
            tenantId="tenant1",
            scope="TENANT",
            algorithm="SLIDING_WINDOW",
            limit=50,
            windowSeconds=30,
        )

        assert policy.tenant_id == "tenant1"
        assert policy.window_seconds == 30

    def test_policy_defaults(self):
        """Test policy default values."""
        policy = Policy(
            tenantId="tenant1",
            scope=Scope.TENANT,
            algorithm=Algorithm.SLIDING_WINDOW,
            limit=100,
            windowSeconds=60,
        )

        assert policy.route is None
        assert policy.burst == 0
        assert policy.ttl_seconds is None

    def test_policy_invalid_limit(self):
        """Test that limit must be >= 1."""
        with pytest.raises(ValidationError):
            Policy(
                tenantId="tenant1",
                scope=Scope.TENANT,
                algorithm=Algorithm.SLIDING_WINDOW,
                limit=0,
                windowSeconds=60,
            )

    def test_policy_invalid_window(self):
        """Test that windowSeconds must be >= 1."""
        with pytest.raises(ValidationError):
            Policy(
                tenantId="tenant1",
                scope=Scope.TENANT,
                algorithm=Algorithm.SLIDING_WINDOW,
                limit=100,
                windowSeconds=0,
            )

    def test_policy_empty_tenant_id(self):
        """Test that tenantId cannot be empty."""
        with pytest.raises(ValidationError):
            Policy(
                tenantId="",
                scope=Scope.TENANT,
                algorithm=Algorithm.SLIDING_WINDOW,
                limit=100,
                windowSeconds=60,
            )

    def test_policy_get_key_with_route(self):
        """Test key generation with route."""
        policy = Policy(
            tenantId="tenant1",
            route="/api/v1",
            scope=Scope.TENANT_ROUTE,
            algorithm=Algorithm.SLIDING_WINDOW,
            limit=100,
            windowSeconds=60,
        )

        assert policy.get_key() == "policy:tenant1:/api/v1"

    def test_policy_get_key_without_route(self):
        """Test key generation without route."""
        policy = Policy(
            tenantId="tenant1",
            scope=Scope.TENANT,
            algorithm=Algorithm.SLIDING_WINDOW,
            limit=100,
            windowSeconds=60,
        )

        assert policy.get_key() == "policy:tenant1:*"


class TestEvaluateRequest:
    """Tests for EvaluateRequest model."""

    def test_create_valid_request(self):
        """Test creating a valid evaluate request."""
        request = EvaluateRequest(tenantId="t-test", route="/api")

        assert request.tenant_id == "t-test"
        assert request.route == "/api"

    def test_request_empty_tenant_id(self):
        """Test that tenantId cannot be empty."""
        with pytest.raises(ValidationError):
            EvaluateRequest(tenantId="", route="/api")

    def test_request_empty_route(self):
        """Test that route cannot be empty."""
        with pytest.raises(ValidationError):
            EvaluateRequest(tenantId="tenant1", route="")


class TestEvaluateResponse:
    """Tests for EvaluateResponse model."""

    def test_create_allowed_response(self):
        """Test creating an allowed response."""
        response = EvaluateResponse(allow=True, remaining=99, resetAt=1707264060)

        assert response.allow is True
        assert response.remaining == 99
        assert response.reset_at == 1707264060

    def test_create_blocked_response(self):
        """Test creating a blocked response."""
        response = EvaluateResponse(allow=False, remaining=0, resetAt=1707264060)

        assert response.allow is False
        assert response.remaining == 0

    def test_response_serialization(self):
        """Test response serialization with aliases."""
        response = EvaluateResponse(allow=True, remaining=50, resetAt=1234567890)
        data = response.model_dump(by_alias=True)

        assert "allow" in data
        assert "remaining" in data
        assert "resetAt" in data
        assert data["resetAt"] == 1234567890


class TestAlgorithm:
    """Tests for Algorithm enum."""

    def test_algorithm_values(self):
        """Test algorithm enum values."""
        assert Algorithm.SLIDING_WINDOW.value == "SLIDING_WINDOW"
        assert Algorithm.TOKEN_BUCKET.value == "TOKEN_BUCKET"

    def test_algorithm_from_string(self):
        """Test creating algorithm from string."""
        assert Algorithm("SLIDING_WINDOW") == Algorithm.SLIDING_WINDOW
        assert Algorithm("TOKEN_BUCKET") == Algorithm.TOKEN_BUCKET


class TestScope:
    """Tests for Scope enum."""

    def test_scope_values(self):
        """Test scope enum values."""
        assert Scope.TENANT.value == "TENANT"
        assert Scope.TENANT_ROUTE.value == "TENANT_ROUTE"
