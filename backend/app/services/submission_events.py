from __future__ import annotations

import json
import logging
from typing import Any

from app.config import settings

log = logging.getLogger(__name__)

_CHANNEL = "submission_updates"


async def publish_submission_update(payload: dict[str, Any]) -> None:
    try:
        import redis.asyncio as redis

        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            await client.publish(_CHANNEL, json.dumps(payload, default=str))
        finally:
            await client.aclose()
    except Exception:
        log.warning("Failed to publish submission update", exc_info=True)


def submission_updates_channel() -> str:
    return _CHANNEL
