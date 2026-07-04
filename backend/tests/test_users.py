import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_user(client: AsyncClient, admin_headers):
    resp = await client.post("/api/users", json={"login": "newstudent", "password": "pass123", "role": "student"}, headers=admin_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["login"] == "newstudent"
    assert data["role"] == "student"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_create_user_duplicate(client: AsyncClient, admin_headers, admin_user):
    resp = await client.post("/api/users", json={"login": "admin", "password": "pass"}, headers=admin_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_users(client: AsyncClient, admin_headers, admin_user):
    resp = await client.get("/api/users", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_get_user(client: AsyncClient, admin_headers, admin_user):
    resp = await client.get(f"/api/users/{admin_user.id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["login"] == "admin"


@pytest.mark.asyncio
async def test_update_user(client: AsyncClient, admin_headers, student_user):
    resp = await client.put(f"/api/users/{student_user.id}", json={"status": "blocked"}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "blocked"


@pytest.mark.asyncio
async def test_reset_password(client: AsyncClient, admin_headers, student_user):
    resp = await client.post(f"/api/users/{student_user.id}/reset-password", json={"new_password": "newpass"}, headers=admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_user(client: AsyncClient, admin_headers):
    create = await client.post("/api/users", json={"login": "todelete", "password": "pass1234"}, headers=admin_headers)
    uid = create.json()["id"]
    resp = await client.delete(f"/api/users/{uid}", headers=admin_headers)
    assert resp.status_code == 204
    get = await client.get(f"/api/users/{uid}", headers=admin_headers)
    assert get.status_code == 404


@pytest.mark.asyncio
async def test_student_cannot_create_user(client: AsyncClient, student_headers):
    resp = await client.post("/api/users", json={"login": "hacker", "password": "x"}, headers=student_headers)
    assert resp.status_code == 403
