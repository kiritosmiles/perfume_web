"""Tests for /api/v1/share endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_create_share_returns_id():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/share", json={
            "recommendations": [
                {"rank": 1, "name": "No.5 Chanel", "brand": "Chanel", "match_score": 92}
            ],
            "emotion": {"primary_emotion": "开心", "confidence": 0.85},
        })
    assert res.status_code == 200
    data = res.json()
    assert "share_id" in data
    assert len(data["share_id"]) == 8
    assert data["share_url"].startswith("/s/")


@pytest.mark.asyncio
async def test_get_share_returns_payload():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_res = await client.post("/api/v1/share", json={
            "recommendations": [
                {"rank": 1, "name": "Test Perfume", "brand": "Test Brand", "match_score": 88}
            ],
            "emotion": {"primary_emotion": "平静", "confidence": 0.75},
            "scene_tag": "home",
        })
        share_id = create_res.json()["share_id"]
        res = await client.get(f"/api/v1/share/{share_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["payload"]["emotion"]["primary_emotion"] == "平静"
    assert data["payload"]["recommendations"][0]["name"] == "Test Perfume"


@pytest.mark.asyncio
async def test_get_nonexistent_share_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/share/abcd1234")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_get_invalid_share_id_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/share/abc")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_create_share_empty_recommendations_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/share", json={
            "recommendations": [],
            "emotion": {"primary_emotion": "开心", "confidence": 0.9},
        })
    assert res.status_code == 422
