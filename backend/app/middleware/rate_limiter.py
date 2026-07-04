from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Dict, Tuple

from fastapi import HTTPException, Request, status

from app.config import settings

log = logging.getLogger(__name__)


class RedisRateLimiter:
    """Sliding window rate limiter backed by Redis.
    Falls back to in-memory if Redis is unavailable."""

    def __init__(self, max_requests: int = 20, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._redis = None
        self._fallback: Dict[str, list] = defaultdict(list)

    def _get_redis(self):
        if self._redis is None:
            try:
                import redis
                self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
                self._redis.ping()
            except Exception:
                self._redis = None
        return self._redis

    def check(self, key: str) -> Tuple[bool, int]:
        r = self._get_redis()
        if r is not None:
            return self._check_redis(r, key)
        return self._check_memory(key)

    def _check_redis(self, r, key: str) -> Tuple[bool, int]:
        try:
            now = time.time()
            pipe = r.pipeline()
            pipe.zremrangebyscore(key, 0, now - self.window)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, self.window + 1)
            results = pipe.execute()
            count = results[1]
            if count >= self.max_requests:
                return False, 0
            return True, self.max_requests - count - 1
        except Exception:
            log.warning("Redis rate limiter error, falling back to memory")
            self._redis = None
            return self._check_memory(key)

    def _check_memory(self, key: str) -> Tuple[bool, int]:
        now = time.time()
        cutoff = now - self.window
        self._fallback[key] = [t for t in self._fallback[key] if t > cutoff]
        if len(self._fallback[key]) >= self.max_requests:
            return False, 0
        self._fallback[key].append(now)
        return True, self.max_requests - len(self._fallback[key])


submission_limiter = RedisRateLimiter(max_requests=20, window_seconds=60)
login_limiter = RedisRateLimiter(max_requests=5, window_seconds=60)


async def check_submission_rate(request: Request) -> None:
    user = getattr(request.state, "user", None)
    key = str(user.id) if user else (request.client.host if request.client else "unknown")
    allowed, remaining = submission_limiter.check("ratelimit:submission:{}".format(key))
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many submissions. Please wait before trying again.",
        )


async def check_login_rate(request: Request) -> None:
    """5 attempts per minute per IP to prevent brute-force attacks on login."""
    ip = request.client.host if request.client else "unknown"
    allowed, _ = login_limiter.check("ratelimit:login:{}".format(ip))
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please wait before trying again.",
        )
