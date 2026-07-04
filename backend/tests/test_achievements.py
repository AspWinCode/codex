import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_achievements_empty(client: AsyncClient, admin_headers):
    resp = await client.get("/api/achievements", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_seed_achievements(client: AsyncClient, admin_headers):
    resp = await client.post("/api/achievements/seed", headers=admin_headers)
    assert resp.status_code == 201
    assert resp.json()["seeded"] >= 1

    # Second seed should add 0 (idempotent)
    resp2 = await client.post("/api/achievements/seed", headers=admin_headers)
    assert resp2.json()["seeded"] == 0


@pytest.mark.asyncio
async def test_list_achievements_after_seed(client: AsyncClient, admin_headers):
    await client.post("/api/achievements/seed", headers=admin_headers)
    resp = await client.get("/api/achievements", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 10


@pytest.mark.asyncio
async def test_my_achievements_empty(client: AsyncClient, admin_headers):
    resp = await client.get("/api/achievements/my", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_profile(client: AsyncClient, admin_headers, admin_user):
    resp = await client.get(f"/api/achievements/profile/{admin_user.id}", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == admin_user.id
    assert data["rating"] == 1200
    assert "achievements" in data


@pytest.mark.asyncio
async def test_profile_nonexistent(client: AsyncClient, admin_headers):
    resp = await client.get("/api/achievements/profile/99999", headers=admin_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_student_cannot_seed(client: AsyncClient, student_headers):
    resp = await client.post("/api/achievements/seed", headers=student_headers)
    assert resp.status_code == 403
