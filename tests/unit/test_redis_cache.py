import pickle
from unittest.mock import MagicMock, patch
import pytest
from fastapi import Request
from src.redis_cache import redis_cache, cache_invalidate


@pytest.mark.asyncio
async def test_redis_cache_hit():
    mock_redis = MagicMock()
    mock_redis.get.return_value = pickle.dumps({"test": "data"})

    with patch('src.redis_cache.redis_client', mock_redis):
        @redis_cache()
        async def test_func(request: Request):
            return {"test": "data"}

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/test"

        result = await test_func(request=mock_request)
        assert result == {"test": "data"}
        mock_redis.get.assert_called_once()


@pytest.mark.asyncio
async def test_redis_cache_miss():
    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    with patch('src.redis_cache.redis_client', mock_redis):
        @redis_cache()
        async def test_func(request: Request):
            return {"test": "data"}

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/test"

        result = await test_func(request=mock_request)
        assert result == {"test": "data"}
        mock_redis.get.assert_called_once()
        mock_redis.setex.assert_called_once()


def test_cache_invalidate_sync():
    mock_redis = MagicMock()
    mock_redis.keys.return_value = [b"key1", b"key2"]

    with patch('src.redis_cache.redis_client', mock_redis):
        @cache_invalidate()
        def test_func():
            return "result"

        result = test_func()
        assert result == "result"
        assert mock_redis.delete.call_count == 2


@pytest.mark.asyncio
async def test_cache_invalidate_async():
    mock_redis = MagicMock()
    mock_redis.keys.return_value = [b"key1", b"key2"]

    with patch('src.redis_cache.redis_client', mock_redis):
        @cache_invalidate()
        async def test_func():
            return "result"

        result = await test_func()
        assert result == "result"
        assert mock_redis.delete.call_count == 2