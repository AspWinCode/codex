from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.config import settings

log = logging.getLogger(__name__)

_redis = None


def _get_redis():
    global _redis
    if _redis is None:
        try:
            import redis
            _redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
            _redis.ping()
        except Exception:
            log.warning("Redis cache unavailable, caching disabled")
            _redis = None
    return _redis


def cache_get(key: str) -> Optional[Any]:
    r = _get_redis()
    if r is None:
        return None
    try:
        val = r.get(key)
        if val is not None:
            return json.loads(val)
    except Exception:
        log.warning("Cache read error for key %s", key)
    return None


def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    r = _get_redis()
    if r is None:
        return
    try:
        r.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        log.warning("Cache write error for key %s", key)


def cache_delete(key: str) -> None:
    r = _get_redis()
    if r is None:
        return
    try:
        r.delete(key)
    except Exception:
        pass


def cache_delete_pattern(pattern: str) -> None:
    r = _get_redis()
    if r is None:
        return
    try:
        keys = r.keys(pattern)
        if keys:
            r.delete(*keys)
    except Exception:
        pass
