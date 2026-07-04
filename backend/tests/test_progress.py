import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_progress_empty(client: AsyncClient, student_headers):
    resp = await client.get("/api/progress", headers=student_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_hints_empty(client: AsyncClient, admin_headers):
    task = await client.post("/api/tasks", json={
        "title": "Hint Task", "task_type": "python_io", "runner_type": "stdin_runner",
        "hints": [{"hint_level": 1, "unlock_attempts": 3, "content": "Hint 1"}],
    }, headers=admin_headers)
    tid = task.json()["id"]

    resp = await client.get(f"/api/progress/hints/{tid}", headers=admin_headers)
    assert resp.status_code == 200
    # No attempts yet, hint with unlock_attempts=3 should not be available
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_hints_with_zero_unlock(client: AsyncClient, admin_headers):
    task = await client.post("/api/tasks", json={
        "title": "Free Hint", "task_type": "python_io", "runner_type": "stdin_runner",
        "hints": [{"hint_level": 1, "unlock_attempts": 0, "content": "Always visible"}],
    }, headers=admin_headers)
    tid = task.json()["id"]

    resp = await client.get(f"/api/progress/hints/{tid}", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["content"] == "Always visible"
