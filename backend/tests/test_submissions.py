from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.config import settings


@pytest.mark.asyncio
async def test_submit_solution(client: AsyncClient, admin_headers):
    task = await client.post("/api/tasks", json={
        "title": "Sub Task", "task_type": "python_io", "runner_type": "stdin_runner",
        "tests": [{"input_data": "1", "expected_output": "1"}],
    }, headers=admin_headers)
    tid = task.json()["id"]

    with patch("app.services.submission_service.celery") as mock_celery:
        mock_celery.send_task.return_value = None
        resp = await client.post("/api/submissions", json={"task_id": tid, "code": "print(input())"}, headers=admin_headers)

    assert resp.status_code == 201
    data = resp.json()
    assert data["task_id"] == tid
    assert data["status"] == "queued"
    assert data["verdict"] is None


@pytest.mark.asyncio
async def test_submit_nonexistent_task(client: AsyncClient, admin_headers):
    with patch("app.services.submission_service.celery"):
        resp = await client.post("/api/submissions", json={"task_id": 99999, "code": "x"}, headers=admin_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_submission(client: AsyncClient, admin_headers):
    task = await client.post("/api/tasks", json={
        "title": "Get Sub", "task_type": "python_io", "runner_type": "stdin_runner",
    }, headers=admin_headers)
    tid = task.json()["id"]

    with patch("app.services.submission_service.celery") as mock_celery:
        mock_celery.send_task.return_value = None
        sub = await client.post("/api/submissions", json={"task_id": tid, "code": "pass"}, headers=admin_headers)
    sid = sub.json()["id"]

    resp = await client.get(f"/api/submissions/{sid}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == sid


@pytest.mark.asyncio
async def test_list_submissions(client: AsyncClient, admin_headers):
    task = await client.post("/api/tasks", json={
        "title": "List Sub", "task_type": "python_io", "runner_type": "stdin_runner",
    }, headers=admin_headers)
    tid = task.json()["id"]

    with patch("app.services.submission_service.celery") as mock_celery:
        mock_celery.send_task.return_value = None
        await client.post("/api/submissions", json={"task_id": tid, "code": "a"}, headers=admin_headers)
        await client.post("/api/submissions", json={"task_id": tid, "code": "b"}, headers=admin_headers)

    resp = await client.get("/api/submissions", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


@pytest.mark.asyncio
async def test_internal_routes_require_token(client: AsyncClient, admin_headers):
    task = await client.post("/api/tasks", json={
        "title": "Token Check", "task_type": "python_io", "runner_type": "stdin_runner",
    }, headers=admin_headers)
    tid = task.json()["id"]

    with patch("app.services.submission_service.celery"):
        sub = await client.post("/api/submissions", json={"task_id": tid, "code": "pass"}, headers=admin_headers)
    sid = sub.json()["id"]

    start_resp = await client.post(f"/api/submissions/internal/{sid}/start")
    complete_resp = await client.post(
        f"/api/submissions/internal/{sid}/complete",
        json={"verdict": "AC", "test_results": []},
    )

    assert start_resp.status_code == 403
    assert complete_resp.status_code == 403


@pytest.mark.asyncio
async def test_internal_complete_updates_progress(client: AsyncClient, admin_headers):
    task = await client.post("/api/tasks", json={
        "title": "Finalize Sub", "task_type": "python_io", "runner_type": "stdin_runner",
        "tests": [{"input_data": "1", "expected_output": "1", "order_index": 1}],
    }, headers=admin_headers)
    task_json = task.json()
    tid = task_json["id"]
    test_id = task_json["tests"][0]["id"]

    with patch("app.services.submission_service.celery"):
        sub = await client.post("/api/submissions", json={"task_id": tid, "code": "print(input())"}, headers=admin_headers)
    sid = sub.json()["id"]

    internal_headers = {"X-Judger-Token": settings.JUDGER_INTERNAL_TOKEN}
    start_resp = await client.post(f"/api/submissions/internal/{sid}/start", headers=internal_headers)
    assert start_resp.status_code == 204

    complete_resp = await client.post(
        f"/api/submissions/internal/{sid}/complete",
        headers=internal_headers,
        json={
            "verdict": "AC",
            "runtime": 0.11,
            "memory": 5.2,
            "test_results": [
                {
                    "test_id": test_id,
                    "verdict": "AC",
                    "runtime": 0.11,
                    "actual_output": "1",
                }
            ],
        },
    )
    assert complete_resp.status_code == 204

    sub_resp = await client.get(f"/api/submissions/{sid}", headers=admin_headers)
    assert sub_resp.status_code == 200
    sub_data = sub_resp.json()
    assert sub_data["status"] == "finished"
    assert sub_data["verdict"] == "AC"
    assert len(sub_data["test_results"]) == 1

    progress_resp = await client.get(f"/api/progress?task_id={tid}", headers=admin_headers)
    assert progress_resp.status_code == 200
    progress = progress_resp.json()
    assert len(progress) == 1
    assert progress[0]["attempts"] == 1
    assert progress[0]["best_verdict"] == "AC"
