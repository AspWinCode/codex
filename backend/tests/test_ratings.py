import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_leaderboard_empty(client: AsyncClient, admin_headers):
    resp = await client.get("/api/ratings/leaderboard", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_my_rating_default(client: AsyncClient, admin_headers):
    resp = await client.get("/api/ratings/me", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["rating"] == 1200
    assert data["solved_total"] == 0


@pytest.mark.asyncio
async def test_rating_history_empty(client: AsyncClient, admin_headers, admin_user):
    resp = await client.get(f"/api/ratings/history/{admin_user.id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() == []
