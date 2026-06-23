"""Tests for feedback API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_explicit_feedback_returns_200():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/feedback/explicit",
            json={
                "generation_id": "00000000-0000-0000-0000-000000000001",
                "card_rank": 1,
                "reaction": "like",
            },
            headers={"X-Browser-Id": "test-browser-001"},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "recorded"
        assert "feedback_id" in data


@pytest.mark.asyncio
async def test_explicit_feedback_dislike():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/feedback/explicit",
            json={
                "generation_id": "00000000-0000-0000-0000-000000000002",
                "card_rank": 2,
                "reaction": "dislike",
                "reason": "too floral",
            },
            headers={"X-Browser-Id": "test-browser-002"},
        )
        assert resp.status_code == 202


@pytest.mark.asyncio
async def test_implicit_feedback_batch():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/feedback/implicit",
            json={
                "generation_id": "00000000-0000-0000-0000-000000000003",
                "events": [
                    {"event_name": "dwell_card", "payload": {"card_rank": 1, "dwell_ms": 4200}},
                    {"event_name": "share_clicked", "payload": {"card_rank": 2}},
                ],
            },
            headers={"X-Browser-Id": "test-browser-003"},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "recorded"
        assert data["events_recorded"] == 2


@pytest.mark.asyncio
async def test_explicit_feedback_invalid_reaction_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/feedback/explicit",
            json={
                "generation_id": "00000000-0000-0000-0000-000000000004",
                "card_rank": 1,
                "reaction": "invalid",
            },
            headers={"X-Browser-Id": "test-browser-004"},
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_explicit_feedback_invalid_rank_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/feedback/explicit",
            json={
                "generation_id": "00000000-0000-0000-0000-000000000005",
                "card_rank": 5,
                "reaction": "like",
            },
            headers={"X-Browser-Id": "test-browser-005"},
        )
        assert resp.status_code == 422
