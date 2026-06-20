"""End-to-end integration test: full guest recommendation flow.

Verifies the complete SSE 7-event protocol within a single async test
(AVOIDS multi-test Neo4j driver sharing — Windows ProactorEventLoop bug).

Requires Docker services (Neo4j, Redis, PG) to be running.
"""

import json
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_full_guest_flow():
    """Single test: full flow → quota exhausted → verify all 7 events."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # ── Phase 1: Normal recommendation ──────────────────────────────
        response = await client.post(
            "/api/v1/guest/sessions",
            json={
                "emotion_card_ids": ["joy", "romance"],
                "scene_tag": "date",
                "browser_id": "e2e-full-flow",
            },
            timeout=30,
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

        events_seen: dict[str, int] = {}
        copy_chunks = 0
        detail_count = 0

        raw = response.text
        for line in raw.split("\n"):
            if line.startswith("event: "):
                event_type = line[7:].strip()
                events_seen[event_type] = events_seen.get(event_type, 0) + 1
            elif line.startswith("data: "):
                payload = json.loads(line[6:])
                if events_seen.get("gen.skeleton", 0) == 1 and "recommendations" in payload:
                    skeleton_cards = len(payload["recommendations"])
                    for rec in payload["recommendations"]:
                        assert rec["match_score"] <= 95
                        assert rec["match_score"] >= 85
                        assert "name" in rec and "brand" in rec
                if "copy_text_chunk" in payload:
                    copy_chunks += 1
                    assert not payload["copy_text_chunk"].startswith("[")
                if "expanded_fields" in payload:
                    detail_count += 1
                    ef = payload["expanded_fields"]
                    assert "longevity" in ef and "sillage" in ef and "season" in ef

        # 7-event protocol
        assert events_seen.get("chat.ack") == 1
        assert events_seen.get("chat.emotion") == 1
        assert events_seen.get("gen.start") == 1
        assert events_seen.get("gen.skeleton") == 1
        assert events_seen.get("gen.complete") == 1
        assert detail_count == 3, f"Expected 3 gen.detail events, got {detail_count}"
        assert copy_chunks == 12, f"Expected 12 copy chunks, got {copy_chunks}"
        assert skeleton_cards == 3

        # ── Phase 2: Second request → quota exhausted ───────────────────
        response2 = await client.post(
            "/api/v1/guest/sessions",
            json={
                "emotion_card_ids": ["joy"],
                "browser_id": "e2e-full-flow",
            },
            timeout=10,
        )

        assert response2.status_code == 200
        raw2 = response2.text
        assert "GUEST_QUOTA_EXHAUSTED" in raw2, f"Expected quota exhausted, got: {raw2[:200]}"
        assert '"total_cards": 0' in raw2
