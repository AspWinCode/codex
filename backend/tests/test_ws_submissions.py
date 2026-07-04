from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.config import settings


class DummyWebSocket:
    def __init__(self) -> None:
        self.messages = []

    async def send_json(self, payload: dict) -> None:
        self.messages.append(payload)


@pytest.fixture(autouse=True)
def clear_ws_state():
    from app.api import ws as ws_api

    ws_api._connections.clear()
    ws_api._subscriptions.clear()
    yield
    ws_api._connections.clear()
    ws_api._subscriptions.clear()


async def _create_submission(client: AsyncClient, admin_headers: dict) -> int:
    task_resp = await client.post(
        "/api/tasks",
        headers=admin_headers,
        json={
            "title": "ws-sub-test",
            "task_type": "python_io",
            "runner_type": "stdin_runner",
            "tests": [{"input_data": "1", "expected_output": "1", "order_index": 1}],
        },
    )
    assert task_resp.status_code == 201
    task_id = task_resp.json()["id"]

    with patch("app.services.submission_service.celery"):
        sub_resp = await client.post(
            "/api/submissions",
            headers=admin_headers,
            json={"task_id": task_id, "code": "print(input())"},
        )

    assert sub_resp.status_code == 201
    return sub_resp.json()["id"]


@pytest.mark.asyncio
async def test_ws_subscribe_returns_current_submission_state(client: AsyncClient, admin_headers, admin_user):
    from app.api import ws as ws_api

    submission_id = await _create_submission(client, admin_headers)
    ws = DummyWebSocket()

    await ws_api._send_current_submission_state(ws, admin_user.id, submission_id)

    assert ws.messages[0]["type"] == "submission_update"
    assert ws.messages[0]["submission_id"] == submission_id
    assert ws.messages[0]["status"] == "queued"


@pytest.mark.asyncio
async def test_ws_receives_running_and_finished_updates(client: AsyncClient, admin_headers, admin_user, monkeypatch):
    from app.api import submissions as submissions_api
    from app.api import ws as ws_api

    async def _direct_publish(payload: dict) -> None:
        await ws_api._broadcast_submission_event(payload)

    monkeypatch.setattr(submissions_api, "publish_submission_update", _direct_publish)

    submission_id = await _create_submission(client, admin_headers)
    ws = DummyWebSocket()
    ws_api._connections.setdefault(admin_user.id, set()).add(ws)
    ws_api._subscriptions[ws] = {submission_id}

    internal_headers = {"X-Judger-Token": settings.JUDGER_INTERNAL_TOKEN}

    start_resp = await client.post(f"/api/submissions/internal/{submission_id}/start", headers=internal_headers)
    assert start_resp.status_code == 204

    complete_resp = await client.post(
        f"/api/submissions/internal/{submission_id}/complete",
        headers=internal_headers,
        json={"verdict": "AC", "test_results": []},
    )
    assert complete_resp.status_code == 204

    statuses = [msg["status"] for msg in ws.messages if msg.get("type") == "submission_update"]
    assert "running" in statuses
    assert "finished" in statuses
    assert ws.messages[-1]["verdict"] == "AC"


@pytest.mark.asyncio
async def test_ws_subscribe_unknown_submission_returns_error_message(admin_user):
    from app.api import ws as ws_api

    ws = DummyWebSocket()
    await ws_api._send_current_submission_state(ws, admin_user.id, 999999)

    assert ws.messages[0]["type"] == "error"
    assert ws.messages[0]["detail"] == "Submission not found"


@pytest.mark.asyncio
async def test_ws_subscribe_after_missed_events_returns_latest_state(client: AsyncClient, admin_headers, admin_user):
    from app.api import submissions as submissions_api
    from app.api import ws as ws_api

    async def _noop_publish(_: dict) -> None:
        return

    submission_id = await _create_submission(client, admin_headers)
    internal_headers = {"X-Judger-Token": settings.JUDGER_INTERNAL_TOKEN}

    with patch.object(submissions_api, "publish_submission_update", _noop_publish):
        start_resp = await client.post(f"/api/submissions/internal/{submission_id}/start", headers=internal_headers)
        assert start_resp.status_code == 204

        complete_resp = await client.post(
            f"/api/submissions/internal/{submission_id}/complete",
            headers=internal_headers,
            json={"verdict": "AC", "test_results": []},
        )
        assert complete_resp.status_code == 204

    ws = DummyWebSocket()
    await ws_api._send_current_submission_state(ws, admin_user.id, submission_id)

    assert ws.messages[0]["type"] == "submission_update"
    assert ws.messages[0]["status"] == "finished"
    assert ws.messages[0]["verdict"] == "AC"