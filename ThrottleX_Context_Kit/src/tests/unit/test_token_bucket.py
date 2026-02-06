"""Unit tests for Token Bucket algorithm."""

from unittest.mock import AsyncMock

import pytest

from throttlex.algorithms.token_bucket import TokenBucket


class TestTokenBucket:
    """Tests for TokenBucket class."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        client = AsyncMock()
        client.script_load = AsyncMock(return_value="sha123")
        client.evalsha = AsyncMock(return_value=[1, 49, 0])
        return client

    @pytest.fixture
    def bucket(self, mock_redis):
        """Create TokenBucket instance."""
        return TokenBucket(
            redis_client=mock_redis,
            capacity=50,
            refill_rate=1.0,
        )

    @pytest.mark.asyncio
    async def test_load_script(self, bucket, mock_redis):
        """Test loading Lua script."""
        await bucket.load_script()

        assert bucket._script_sha == "sha123"
        mock_redis.script_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_consume_allowed(self, bucket, mock_redis):
        """Test consuming tokens when allowed."""
        mock_redis.evalsha.return_value = [1, 49, 0]

        allowed, remaining, reset_at = await bucket.consume("t-test", "/api", 1)

        assert allowed is True
        assert remaining == 49

    @pytest.mark.asyncio
    async def test_consume_blocked(self, bucket, mock_redis):
        """Test consuming tokens when blocked."""
        mock_redis.evalsha.return_value = [0, 0, 1234567890]

        allowed, remaining, reset_at = await bucket.consume("t-test", "/api", 10)

        assert allowed is False
        assert remaining == 0
        assert reset_at == 1234567890

    @pytest.mark.asyncio
    async def test_consume_loads_script_on_first_call(self, bucket, mock_redis):
        """Test that script is loaded on first consume."""
        mock_redis.evalsha.return_value = [1, 49, 0]

        await bucket.consume("t-test", "/api")

        mock_redis.script_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_consume_multiple_tokens(self, bucket, mock_redis):
        """Test consuming multiple tokens at once."""
        mock_redis.evalsha.return_value = [1, 45, 0]

        allowed, remaining, _ = await bucket.consume("t-test", "/api", 5)

        assert allowed is True
        assert remaining == 45

    @pytest.mark.asyncio
    async def test_get_tokens(self, bucket, mock_redis):
        """Test getting current token count."""
        mock_redis.hget = AsyncMock(return_value="42")

        result = await bucket.get_tokens("t-test", "/api")

        assert result == 42

    @pytest.mark.asyncio
    async def test_get_tokens_empty(self, bucket, mock_redis):
        """Test getting tokens when bucket doesn't exist."""
        mock_redis.hget = AsyncMock(return_value=None)

        result = await bucket.get_tokens("t-test", "/api")

        assert result == 50  # capacity

    @pytest.mark.asyncio
    async def test_reset(self, bucket, mock_redis):
        """Test resetting bucket to full capacity."""
        mock_redis.delete = AsyncMock()

        await bucket.reset("t-test", "/api")

        mock_redis.delete.assert_called_once()
