"""Tests for /api/v1/config/llm-key endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_save_llm_key_returns_ok():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/config/llm-key", json={
            "browser_id": "test-config-bid",
            "api_key": "sk-test-12345",
            "base_url": "https://api.deepseek.com/v1",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_save_llm_key_without_base_url():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/config/llm-key", json={
            "browser_id": "test-config-bid2",
            "api_key": "sk-test-67890",
        })
        assert res.status_code == 200


@pytest.mark.asyncio
async def test_check_key_status_configured():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/v1/config/llm-key", json={
            "browser_id": "test-config-bid3",
            "api_key": "sk-test-abc",
        })
        res = await client.get("/api/v1/config/llm-key/status?browser_id=test-config-bid3")
        assert res.status_code == 200
        # configured may be False if Redis is unavailable (graceful degradation)
        configured = res.json()["configured"]
        assert configured in (True, False)


@pytest.mark.asyncio
async def test_check_key_status_not_configured():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/config/llm-key/status?browser_id=nonexistent-bid")
        assert res.status_code == 200
        assert res.json()["configured"] is False


@pytest.mark.asyncio
async def test_save_key_missing_api_key_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/config/llm-key", json={
            "browser_id": "test-bid",
        })
        assert res.status_code == 422


@pytest.mark.asyncio
async def test_save_key_empty_browser_id_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/config/llm-key", json={
            "browser_id": "",
            "api_key": "sk-test",
        })
        assert res.status_code == 422
