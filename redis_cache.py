import asyncio
from functools import wraps
from fastapi import Request
from fastapi.responses import RedirectResponse
import redis
import pickle
from datetime import timedelta

redis_client = redis.Redis(host="redis", port=6379, db=0)


def redis_cache(expire: int = 60):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if 'request' in kwargs and isinstance(kwargs['request'], Request):
                request = kwargs['request']
                cache_key = f"{func.__name__}:{request.url.path}"

                cached_result = redis_client.get(cache_key)
                if cached_result:
                    return pickle.loads(cached_result)

                result = await func(*args, **kwargs)

                if not isinstance(result, RedirectResponse):
                    redis_client.setex(cache_key, timedelta(seconds=expire), pickle.dumps(result))

                return result

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def cache_invalidate(pattern: str = "*"):
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            for key in redis_client.keys(pattern):
                redis_client.delete(key)
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            for key in redis_client.keys(pattern):
                redis_client.delete(key)
            return result

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator