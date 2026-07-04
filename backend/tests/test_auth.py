import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, admin_user):
    resp = await client.post("/api/auth/login", json={"login": "admin", "password": "admin123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert "refresh_token" in data
    assert data["user"]["login"] == "admin"
    assert data["user"]["role"] == "admin"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, admin_user):
    resp = await client.post("/api/auth/login", json={"login": "admin", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    resp = await client.post("/api/auth/login", json={"login": "nobody", "password": "pass"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_no_token(client: AsyncClient):
    resp = await client.get("/api/users")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_protected_endpoint_invalid_token(client: AsyncClient):
    resp = await client.get("/api/users", headers={"Authorization": "Bearer fake.token.here"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, admin_user):
    login_resp = await client.post("/api/auth/login", json={"login": "admin", "password": "admin123"})
    refresh = login_resp.json()["refresh_token"]

    resp = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_invalid_token(client: AsyncClient):
    resp = await client.post("/api/auth/refresh", json={"refresh_token": "invalid"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_access_token_cannot_be_used_as_refresh(client: AsyncClient, admin_user):
    login_resp = await client.post("/api/auth/login", json={"login": "admin", "password": "admin123"})
    access = login_resp.json()["token"]

    resp = await client.post("/api/auth/refresh", json={"refresh_token": access})
    assert resp.status_code == 401
