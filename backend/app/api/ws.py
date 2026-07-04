from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.config import settings
from app.database import get_session_factory
from app.models.submission import Submission
from app.services.auth_service import decode_access_token
from app.services.submission_events import submission_updates_channel

router = APIRouter()
log = logging.getLogger(__name__)

_connections: Dict[int, Set[WebSocket]] = {}
_subscriptions: Dict[WebSocket, Set[int]] = {}
_listener_task: Optional[asyncio.Task] = None


async def _safe_send(ws: WebSocket, payload: dict) -> bool:
    try:
        await ws.send_json(payload)
        return True
    except Exception:
        return False


async def _broadcast_submission_event(data: dict) -> None:
    user_id = data.get("user_id")
    submission_id = data.get("submission_id")
    if not isinstance(user_id, int) or user_id not in _connections:
        return

    dead: list[WebSocket] = []
    for ws in _connections[user_id]:
        watched = _subscriptions.get(ws, set())
        if watched and submission_id not in watched:
            continue
        ok = await _safe_send(ws, data)
        if not ok:
            dead.append(ws)

    for ws in dead:
        _disconnect_ws(user_id, ws)


def _disconnect_ws(user_id: int, ws: WebSocket) -> None:
    _connections.get(user_id, set()).discard(ws)
    _subscriptions.pop(ws, None)
    if user_id in _connections and not _connections[user_id]:
        del _connections[user_id]


async def _listen_submission_events() -> None:
    channel = submission_updates_channel()

    while True:
        client = None
        pubsub = None
        try:
            import redis.asyncio as redis

            client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            pubsub = client.pubsub()
            await pubsub.subscribe(channel)
            log.info("Subscribed to Redis channel: %s", channel)

            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                raw = message.get("data")
                if not isinstance(raw, str):
                    continue
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    await _broadcast_submission_event(payload)

        except asyncio.CancelledError:
            break
        except Exception:
            log.warning("Submission event listener disconnected, retrying", exc_info=True)
            await asyncio.sleep(1)
        finally:
            if pubsub is not None:
                try:
                    await pubsub.aclose()
                except Exception:
                    pass
            if client is not None:
                try:
                    await client.aclose()
                except Exception:
                    pass


def start_submission_event_listener() -> None:
    global _listener_task
    if _listener_task is None or _listener_task.done():
        _listener_task = asyncio.create_task(_listen_submission_events())


async def stop_submission_event_listener() -> None:
    global _listener_task
    if _listener_task is None:
        return

    _listener_task.cancel()
    try:
        await _listener_task
    except asyncio.CancelledError:
        pass
    finally:
        _listener_task = None


async def _send_current_submission_state(ws: WebSocket, user_id: int, submission_id: int) -> None:
    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(
            select(Submission).where(
                Submission.id == submission_id,
                Submission.user_id == user_id,
            )
        )
        sub = result.scalar_one_or_none()

    if sub is None:
        await ws.send_json({"type": "error", "detail": "Submission not found"})
        return

    await ws.send_json(
        {
            "type": "submission_update",
            "submission_id": sub.id,
            "user_id": user_id,
            "status": sub.status.value,
            "verdict": sub.verdict.value if sub.verdict else None,
            "runtime": sub.runtime,
            "memory": sub.memory,
            "error_output": sub.error_output,
        }
    )


@router.websocket("/submissions/{token}")
async def ws_submissions(websocket: WebSocket, token: str):
    payload = decode_access_token(token)
    if payload is None:
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = int(payload["sub"])
    await websocket.accept()

    if user_id not in _connections:
        _connections[user_id] = set()
    _connections[user_id].add(websocket)
    _subscriptions[websocket] = set()

    try:
        while True:
            msg = await websocket.receive_json()
            action = msg.get("action")

            if action == "subscribe":
                sid = msg.get("submission_id")
                if sid is None:
                    continue
                try:
                    submission_id = int(sid)
                except (TypeError, ValueError):
                    continue
                _subscriptions[websocket].add(submission_id)
                await _send_current_submission_state(websocket, user_id, submission_id)

            elif action == "unsubscribe":
                sid = msg.get("submission_id")
                try:
                    submission_id = int(sid)
                except (TypeError, ValueError):
                    continue
                _subscriptions[websocket].discard(submission_id)

            elif action == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("WebSocket error for user %d", user_id)
    finally:
        _disconnect_ws(user_id, websocket)
