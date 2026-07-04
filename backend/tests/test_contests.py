from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient


def _future(hours=1):
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _past(hours=1):
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


@pytest.mark.asyncio
async def test_create_contest(client: AsyncClient, admin_headers):
    resp = await client.post("/api/contests", json={
        "title": "Weekly Contest #1",
        "description": "First test contest",
        "start_at": _future(1),
        "end_at": _future(3),
    }, headers=admin_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Weekly Contest #1"
    assert data["status"] == "upcoming"


@pytest.mark.asyncio
async def test_list_contests(client: AsyncClient, admin_headers):
    await client.post("/api/contests", json={
        "title": "C1", "start_at": _future(1), "end_at": _future(2),
    }, headers=admin_headers)
    resp = await client.get("/api/contests", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_get_contest_detail(client: AsyncClient, admin_headers):
    create = await client.post("/api/contests", json={
        "title": "Detail", "start_at": _future(1), "end_at": _future(2),
    }, headers=admin_headers)
    cid = create.json()["id"]
    resp = await client.get(f"/api/contests/{cid}", headers=admin_headers)
    assert resp.status_code == 200
    assert "contest_tasks" in resp.json()


@pytest.mark.asyncio
async def test_create_contest_with_tasks(client: AsyncClient, admin_headers):
    task = await client.post("/api/tasks", json={
        "title": "Contest Task", "task_type": "python_io", "runner_type": "stdin_runner",
    }, headers=admin_headers)
    tid = task.json()["id"]

    resp = await client.post("/api/contests", json={
        "title": "With Tasks",
        "start_at": _future(1),
        "end_at": _future(3),
        "tasks": [{"task_id": tid, "order_index": 0, "max_score": 100}],
    }, headers=admin_headers)
    assert resp.status_code == 201

    detail = await client.get(f"/api/contests/{resp.json()['id']}", headers=admin_headers)
    assert len(detail.json()["contest_tasks"]) == 1


@pytest.mark.asyncio
async def test_join_contest(client: AsyncClient, admin_headers):
    create = await client.post("/api/contests", json={
        "title": "Join Me", "start_at": _future(1), "end_at": _future(2),
    }, headers=admin_headers)
    cid = create.json()["id"]

    resp = await client.post(f"/api/contests/{cid}/join", headers=admin_headers)
    assert resp.status_code == 201

    # Joining again should fail
    resp2 = await client.post(f"/api/contests/{cid}/join", headers=admin_headers)
    assert resp2.status_code == 400


@pytest.mark.asyncio
async def test_leaderboard(client: AsyncClient, admin_headers):
    create = await client.post("/api/contests", json={
        "title": "LB", "start_at": _future(1), "end_at": _future(2),
    }, headers=admin_headers)
    cid = create.json()["id"]
    await client.post(f"/api/contests/{cid}/join", headers=admin_headers)

    resp = await client.get(f"/api/contests/{cid}/leaderboard", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_update_contest(client: AsyncClient, admin_headers):
    create = await client.post("/api/contests", json={
        "title": "Old", "start_at": _future(1), "end_at": _future(2),
    }, headers=admin_headers)
    cid = create.json()["id"]

    resp = await client.put(f"/api/contests/{cid}", json={"title": "New"}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "New"


@pytest.mark.asyncio
async def test_delete_contest(client: AsyncClient, admin_headers):
    create = await client.post("/api/contests", json={
        "title": "Del", "start_at": _future(1), "end_at": _future(2),
    }, headers=admin_headers)
    cid = create.json()["id"]
    resp = await client.delete(f"/api/contests/{cid}", headers=admin_headers)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_student_cannot_create_contest(client: AsyncClient, student_headers):
    resp = await client.post("/api/contests", json={
        "title": "Nope", "start_at": _future(1), "end_at": _future(2),
    }, headers=student_headers)
    assert resp.status_code == 403
