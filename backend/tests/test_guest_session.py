import json

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_post_session_returns_sse():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/guest/sessions",
            json={"emotion_card_ids": ["joy"], "scene_tag": "work"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    # Verify key event types present (without Neo4j, we should at least see ack + emotion + error)
    assert "chat.ack" in body
    assert "chat.emotion" in body
    assert "gen.start" in body
    # gen.error or gen.skeleton will follow depending on Neo4j availability


@pytest.mark.asyncio
async def test_post_session_422_on_invalid_input():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/guest/sessions",
            json={},  # Missing required field
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_session_parses_query_params():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/guest/sessions?card_ids=joy,calm&scene=work&browser_id=test123"
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert "chat.ack" in body
    assert "chat.emotion" in body


@pytest.mark.asyncio
async def test_sse_protocol_helper():
    from app.sse.protocol import sse, now_iso

    # Test dict data
    result = sse("test.event", {"key": "value"})
    assert result.startswith("event: test.event\n")
    assert "data:" in result
    assert '"key"' in result

    # Test string data
    result2 = sse("test.raw", "plain text")
    assert "data: plain text" in result2

    # now_iso returns ISO format
    ts = now_iso()
    assert "T" in ts
    # Should parse correctly
    from datetime import datetime
    parsed = datetime.fromisoformat(ts)
    assert parsed.tzinfo is not None
