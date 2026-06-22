"""Tests for /api/v1/auth endpoints."""

import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def register_payload():
    return {
        "email": f"test-{uuid.uuid4().hex[:8]}@example.com",
        "password": "testpass123",
    }


@pytest.mark.asyncio
async def test_register_creates_user(register_payload):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/auth/register", json=register_payload)
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == register_payload["email"]


@pytest.mark.asyncio
async def test_register_duplicate_email_409(register_payload):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/v1/auth/register", json=register_payload)
        res = await client.post("/api/v1/auth/register", json=register_payload)
        assert res.status_code == 409


@pytest.mark.asyncio
async def test_register_invalid_email_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/auth/register", json={
            "email": "not-an-email", "password": "testpass123",
        })
        assert res.status_code == 422


@pytest.mark.asyncio
async def test_register_short_password_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/auth/register", json={
            "email": "test@example.com", "password": "short",
        })
        assert res.status_code == 422


@pytest.mark.asyncio
async def test_login_returns_tokens(register_payload):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/v1/auth/register", json=register_payload)
        res = await client.post("/api/v1/auth/login", json={
            "email": register_payload["email"],
            "password": register_payload["password"],
        })
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password_401(register_payload):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/v1/auth/register", json=register_payload)
        res = await client.post("/api/v1/auth/login", json={
            "email": register_payload["email"],
            "password": "wrong-password",
        })
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user_401():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/auth/login", json={
            "email": "nobody@example.com", "password": "testpass123",
        })
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_refresh_returns_new_tokens(register_payload):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post("/api/v1/auth/register", json=register_payload)
        refresh = reg.json()["refresh_token"]

        res = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["refresh_token"] != refresh  # Rotation!


@pytest.mark.asyncio
async def test_refresh_reused_token_401(register_payload):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post("/api/v1/auth/register", json=register_payload)
        refresh = reg.json()["refresh_token"]

        await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
        res = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_user(register_payload):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post("/api/v1/auth/register", json=register_payload)
        token = reg.json()["access_token"]

        res = await client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["email"] == register_payload["email"]


@pytest.mark.asyncio
async def test_me_no_token_401():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/auth/me")
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_me_invalid_token_401():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/auth/me", headers={
            "Authorization": "Bearer this.is.not.valid",
        })
        assert res.status_code == 401
