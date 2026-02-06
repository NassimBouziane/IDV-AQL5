"""Unit tests for the Redis repository."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from throttlex.models import Algorithm, Policy, Scope
from throttlex.repository import RedisRepository


class TestRedisRepository:
    """Tests for RedisRepository."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        client = AsyncMock()
        client.ping = AsyncMock()
        client.script_load = AsyncMock(return_value="sha123")
        client.get = AsyncMock(return_value=None)
        client.set = AsyncMock()
        client.setex = AsyncMock()
        client.delete = AsyncMock(return_value=1)
        client.sadd = AsyncMock()
        client.srem = AsyncMock()
        client.smembers = AsyncMock(return_value=set())
        client.evalsha = AsyncMock(return_value=[1, 99, 1234567890])
        client.aclose = AsyncMock()
        return client

    @pytest.fixture
    def repository(self, mock_redis):
        """Create repository with mock Redis."""
        repo = RedisRepository()
        repo._client = mock_redis
        repo._sliding_window_sha = "sha_sliding"
        repo._token_bucket_sha = "sha_token"
        return repo

    @pytest.mark.asyncio
    async def test_health_check_connected(self, repository, mock_redis):
        """Test health check when connected."""
        result = await repository.health_check()
        assert result is True
        mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_disconnected(self):
        """Test health check when disconnected."""
        repo = RedisRepository()
        result = await repo.health_check()
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_error(self, repository, mock_redis):
        """Test health check on error."""
        mock_redis.ping.side_effect = Exception("Connection error")
        result = await repository.health_check()
        assert result is False

    @pytest.mark.asyncio
    async def test_disconnect(self, repository, mock_redis):
        """Test disconnect."""
        await repository.disconnect()
        mock_redis.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_policy_without_ttl(self, repository, mock_redis):
        """Test saving policy without TTL."""
        policy = Policy(
            tenantId="t-test",
            scope=Scope.TENANT,
            algorithm=Algorithm.SLIDING_WINDOW,
            limit=100,
            windowSeconds=60,
        )
        
        result = await repository.save_policy(policy)
        
        assert result.tenant_id == "t-test"
        mock_redis.set.assert_called_once()
        mock_redis.sadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_policy_with_ttl(self, repository, mock_redis):
        """Test saving policy with TTL."""
        policy = Policy(
            tenantId="t-test",
            scope=Scope.TENANT,
            algorithm=Algorithm.SLIDING_WINDOW,
            limit=100,
            windowSeconds=60,
            ttlSeconds=3600,
        )
        
        await repository.save_policy(policy)
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_policy_not_connected(self):
        """Test save policy when not connected."""
        repo = RedisRepository()
        policy = Policy(
            tenantId="t-test",
            scope=Scope.TENANT,
            algorithm=Algorithm.SLIDING_WINDOW,
            limit=100,
            windowSeconds=60,
        )
        
        with pytest.raises(RuntimeError, match="Redis not connected"):
            await repo.save_policy(policy)

    @pytest.mark.asyncio
    async def test_get_policies_empty(self, repository, mock_redis):
        """Test getting policies when none exist."""
        mock_redis.smembers.return_value = set()
        
        result = await repository.get_policies("t-test")
        
        assert result == []

    @pytest.mark.asyncio
    async def test_get_policies_not_connected(self):
        """Test get policies when not connected."""
        repo = RedisRepository()
        
        with pytest.raises(RuntimeError, match="Redis not connected"):
            await repo.get_policies("t-test")

    @pytest.mark.asyncio
    async def test_get_matching_policy_found(self, repository, mock_redis):
        """Test getting matching policy when it exists."""
        import json
        policy_data = {
            "tenantId": "t-test",
            "route": "/api",
            "scope": "TENANT_ROUTE",
            "algorithm": "SLIDING_WINDOW",
            "limit": 100,
            "windowSeconds": 60,
        }
        mock_redis.get.return_value = json.dumps(policy_data)
        
        result = await repository.get_matching_policy("t-test", "/api")
        
        assert result is not None
        assert result.tenant_id == "t-test"

    @pytest.mark.asyncio
    async def test_get_matching_policy_not_found(self, repository, mock_redis):
        """Test getting matching policy when none exists."""
        mock_redis.get.return_value = None
        
        result = await repository.get_matching_policy("t-test", "/api")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_matching_policy_not_connected(self):
        """Test get matching policy when not connected."""
        repo = RedisRepository()
        
        with pytest.raises(RuntimeError, match="Redis not connected"):
            await repo.get_matching_policy("t-test", "/api")

    @pytest.mark.asyncio
    async def test_delete_policy_with_route(self, repository, mock_redis):
        """Test deleting policy with route."""
        result = await repository.delete_policy("t-test", "/api")
        
        assert result is True
        mock_redis.delete.assert_called_once()
        mock_redis.srem.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_policy_without_route(self, repository, mock_redis):
        """Test deleting policy without route."""
        result = await repository.delete_policy("t-test")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_policy_not_connected(self):
        """Test delete policy when not connected."""
        repo = RedisRepository()
        
        with pytest.raises(RuntimeError, match="Redis not connected"):
            await repo.delete_policy("t-test")

    @pytest.mark.asyncio
    async def test_evaluate_sliding_window(self, repository, mock_redis):
        """Test sliding window evaluation."""
        mock_redis.evalsha.return_value = [1, 99, 1234567890]
        
        allow, remaining, reset_at = await repository.evaluate_sliding_window(
            "t-test", "/api", 100, 60, 10
        )
        
        assert allow is True
        assert remaining == 99
        assert reset_at == 1234567890

    @pytest.mark.asyncio
    async def test_evaluate_sliding_window_blocked(self, repository, mock_redis):
        """Test sliding window evaluation when blocked."""
        mock_redis.evalsha.return_value = [0, 0, 1234567890]
        
        allow, remaining, reset_at = await repository.evaluate_sliding_window(
            "t-test", "/api", 100, 60
        )
        
        assert allow is False
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_evaluate_sliding_window_not_connected(self):
        """Test sliding window when not connected."""
        repo = RedisRepository()
        
        with pytest.raises(RuntimeError, match="Redis not connected"):
            await repo.evaluate_sliding_window("t-test", "/api", 100, 60)

    @pytest.mark.asyncio
    async def test_evaluate_token_bucket(self, repository, mock_redis):
        """Test token bucket evaluation."""
        mock_redis.evalsha.return_value = [1, 49, 0]
        
        allow, remaining, reset_at = await repository.evaluate_token_bucket(
            "t-test", "/api", 50, 1.0, 1
        )
        
        assert allow is True
        assert remaining == 49

    @pytest.mark.asyncio
    async def test_evaluate_token_bucket_blocked(self, repository, mock_redis):
        """Test token bucket evaluation when blocked."""
        mock_redis.evalsha.return_value = [0, 0, 1234567890]
        
        allow, remaining, reset_at = await repository.evaluate_token_bucket(
            "t-test", "/api", 50, 1.0, 1
        )
        
        assert allow is False
        assert reset_at == 1234567890

    @pytest.mark.asyncio
    async def test_evaluate_token_bucket_not_connected(self):
        """Test token bucket when not connected."""
        repo = RedisRepository()
        
        with pytest.raises(RuntimeError, match="Redis not connected"):
            await repo.evaluate_token_bucket("t-test", "/api", 50, 1.0)

    @pytest.mark.asyncio
    async def test_get_counter(self, repository, mock_redis):
        """Test getting counter value."""
        mock_redis.get.return_value = "42"
        
        result = await repository.get_counter("t-test", "/api", 60)
        
        assert result == 42

    @pytest.mark.asyncio
    async def test_get_counter_empty(self, repository, mock_redis):
        """Test getting counter when empty."""
        mock_redis.get.return_value = None
        
        result = await repository.get_counter("t-test", "/api", 60)
        
        assert result == 0

    @pytest.mark.asyncio
    async def test_get_counter_not_connected(self):
        """Test get counter when not connected."""
        repo = RedisRepository()
        
        with pytest.raises(RuntimeError, match="Redis not connected"):
            await repo.get_counter("t-test", "/api", 60)
