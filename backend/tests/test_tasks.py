import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_task_with_tests_and_hints(client: AsyncClient, admin_headers):
    resp = await client.post("/api/tasks", json={
        "title": "Sum Two Numbers",
        "description": "Read two ints, print sum",
        "task_type": "python_io",
        "runner_type": "stdin_runner",
        "tests": [
            {"test_type": "public", "input_data": "2 3", "expected_output": "5"},
            {"test_type": "hidden", "input_data": "10 20", "expected_output": "30"},
        ],
        "hints": [
            {"hint_level": 1, "unlock_attempts": 3, "content": "Use input().split()"},
        ],
    }, headers=admin_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Sum Two Numbers"
    assert len(data["tests"]) == 2
    assert len(data["hints"]) == 1


@pytest.mark.asyncio
async def test_list_tasks(client: AsyncClient, admin_headers):
    await client.post("/api/tasks", json={
        "title": "T1", "task_type": "python_io", "runner_type": "stdin_runner",
    }, headers=admin_headers)
    resp = await client.get("/api/tasks", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_get_task_detail(client: AsyncClient, admin_headers):
    create = await client.post("/api/tasks", json={
        "title": "Detail", "task_type": "python_oop", "runner_type": "pytest_runner",
        "tests": [{"test_type": "public", "expected_output": "import solution\ndef test_x(): pass"}],
    }, headers=admin_headers)
    tid = create.json()["id"]
    resp = await client.get(f"/api/tasks/{tid}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["task_type"] == "python_oop"
    assert len(resp.json()["tests"]) == 1


@pytest.mark.asyncio
async def test_update_task(client: AsyncClient, admin_headers):
    create = await client.post("/api/tasks", json={
        "title": "V1", "task_type": "python_io", "runner_type": "stdin_runner",
    }, headers=admin_headers)
    tid = create.json()["id"]
    resp = await client.put(f"/api/tasks/{tid}", json={"title": "V2", "status": "published"}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "V2"
    assert resp.json()["version"] == 2


@pytest.mark.asyncio
async def test_delete_task(client: AsyncClient, admin_headers):
    create = await client.post("/api/tasks", json={
        "title": "Del", "task_type": "sql_query", "runner_type": "sql_runner",
    }, headers=admin_headers)
    tid = create.json()["id"]
    resp = await client.delete(f"/api/tasks/{tid}", headers=admin_headers)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_add_and_delete_test(client: AsyncClient, admin_headers):
    task = await client.post("/api/tasks", json={
        "title": "TT", "task_type": "python_io", "runner_type": "stdin_runner",
    }, headers=admin_headers)
    tid = task.json()["id"]

    test = await client.post(f"/api/tasks/{tid}/tests", json={"input_data": "1", "expected_output": "1"}, headers=admin_headers)
    assert test.status_code == 201
    test_id = test.json()["id"]

    delete = await client.delete(f"/api/tasks/tests/{test_id}", headers=admin_headers)
    assert delete.status_code == 204


@pytest.mark.asyncio
async def test_student_cannot_create_task(client: AsyncClient, student_headers):
    resp = await client.post("/api/tasks", json={
        "title": "X", "task_type": "python_io", "runner_type": "stdin_runner",
    }, headers=student_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_filter_tasks_by_type(client: AsyncClient, admin_headers):
    await client.post("/api/tasks", json={"title": "IO", "task_type": "python_io", "runner_type": "stdin_runner"}, headers=admin_headers)
    await client.post("/api/tasks", json={"title": "SQL", "task_type": "sql_query", "runner_type": "sql_runner"}, headers=admin_headers)

    resp = await client.get("/api/tasks?task_type=sql_query", headers=admin_headers)
    assert resp.status_code == 200
    for t in resp.json():
        assert t["task_type"] == "sql_query"
