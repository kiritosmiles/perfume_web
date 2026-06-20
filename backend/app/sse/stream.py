import asyncio
import json
import logging
import uuid
from typing import AsyncGenerator

from neo4j.exceptions import Neo4jError, ServiceUnavailable, SessionExpired

from app.core.deps import get_db_neo4j
from app.core.pg import get_pg_pool
from app.models.guest import GuestSessionInput
from app.services.emotion import resolve_emotion_from_cards
from app.services.fragrance import search_fragrance_by_emotion
from app.services.generation import build_skeleton, build_copy_stream
from app.sse.protocol import sse, now_iso

logger = logging.getLogger(__name__)


async def _log_guest_user_message(
    browser_id: str,
    generation_id: str,
    emotion_result: dict,
) -> None:
    """Persist the user's card pick to temp_conversations for Phase 2 migration."""
    try:
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO temp_conversations
                    (browser_id, round, role, content, emotion_tags, created_at)
                VALUES ($1, 0, 'user', $2, $3, now())
                """,
                browser_id,
                json.dumps({
                    "primary_emotion": emotion_result["primary_emotion"],
                    "confidence": emotion_result["confidence"],
                    "source": emotion_result["source"],
                }, ensure_ascii=False),
                json.dumps(emotion_result["emotion_vector"], ensure_ascii=False),
            )
    except Exception:
        logger.warning("Failed to persist user message for %s", browser_id, exc_info=True)


async def _log_guest_agent_message(
    browser_id: str,
    generation_id: str,
    skeletons: list[dict],
    emotion_result: dict,
) -> None:
    """Persist the agent's recommendations to temp_conversations."""
    try:
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO temp_conversations
                    (browser_id, round, role, content, emotion_tags, recommendation, created_at)
                VALUES ($1, 0, 'agent', $2, $3, $4, now())
                """,
                browser_id,
                json.dumps({
                    "primary_emotion": emotion_result["primary_emotion"],
                    "recommendations": [
                        {"rank": s["rank"], "name": s["name"], "brand": s["brand"],
                         "match_score": s["match_score"]}
                        for s in skeletons
                    ],
                }, ensure_ascii=False),
                json.dumps(emotion_result["emotion_vector"], ensure_ascii=False),
                json.dumps(skeletons, ensure_ascii=False),
            )
    except Exception:
        logger.warning("Failed to persist agent message for %s", browser_id, exc_info=True)


async def sse_event_stream(
    input_data: GuestSessionInput,
) -> AsyncGenerator[str, None]:
    generation_id = str(uuid.uuid4())
    message_id = str(uuid.uuid4())

    # 1) chat.ack
    yield sse("chat.ack", {
        "message_id": message_id,
        "server_ts": now_iso(),
    })

    await asyncio.sleep(0)  # Yield event loop

    # 2) chat.emotion
    emotion_result = resolve_emotion_from_cards(input_data)
    yield sse("chat.emotion", {
        "emotion_vector": emotion_result["emotion_vector"],
        "primary_emotion": emotion_result["primary_emotion"],
        "confidence": emotion_result["confidence"],
        "source": emotion_result["source"],
    })

    # Persist user message for Phase 2 registration migration
    if input_data.browser_id:
        await _log_guest_user_message(input_data.browser_id, generation_id, emotion_result)

    await asyncio.sleep(0)

    # 3) gen.start
    yield sse("gen.start", {
        "generation_id": generation_id,
        "mode": "fast",
    })

    # 4) GraphRAG search (with try/except degrade)
    candidates: list[dict] = []
    try:
        async for neo4j_session in get_db_neo4j():
            candidates = await search_fragrance_by_emotion(
                neo4j_session,
                emotion_result["emotion_vector"],
                input_data.scene_tag,
                limit=50,  # Fetch more — top scores dominated by duplicate name variants
            )
    except (Neo4jError, ServiceUnavailable, SessionExpired, OSError) as e:
        # Neo4j connectivity issues — graceful degradation
        logger.warning("GraphRAG search degraded (gen_id=%s): %s", generation_id, e)
        yield sse("gen.error", {
            "generation_id": generation_id,
            "code": "NO_MATCH",
            "user_message": "暂时无法连接到香水知识库，请稍后再试",
            "degraded": True,
        })
        yield sse("gen.complete", {
            "generation_id": generation_id,
            "total_cards": 0,
        })
        return

    if not candidates:
        yield sse("gen.error", {
            "generation_id": generation_id,
            "code": "NO_MATCH",
            "user_message": "没有找到匹配的香水，试试换一种心情？",
            "degraded": False,
        })
        yield sse("gen.complete", {
            "generation_id": generation_id,
            "total_cards": 0,
        })
        return

    await asyncio.sleep(0)

    # 5) gen.skeleton
    skeletons = build_skeleton(candidates, emotion_result["emotion_vector"])
    yield sse("gen.skeleton", {
        "generation_id": generation_id,
        "recommendations": skeletons,
        "is_partial": True,
    })

    await asyncio.sleep(0)

    # 6) gen.detail per card
    for sk in skeletons:
        yield sse("gen.detail", {
            "generation_id": generation_id,
            "rank": sk["rank"],
            "expanded_fields": {
                "graph_path": f"Emotion→{emotion_result['primary_emotion']}→Accord→{sk['name']}",
                "longevity": 6,
                "sillage": 5,
                "season": "all",
            },
        })
        await asyncio.sleep(0)

    # 7) gen.copy chunks per card
    for sk in skeletons:
        copy_chunks = build_copy_stream(
            sk["rank"], generation_id, emotion_result["primary_emotion"]
        )
        for i, chunk in enumerate(copy_chunks):
            yield sse("gen.copy", {
                "generation_id": generation_id,
                "rank": sk["rank"],
                "copy_text_chunk": chunk,
                "is_final": (i == len(copy_chunks) - 1),
            })
            await asyncio.sleep(0)

    # Persist agent response for Phase 2 registration migration
    if input_data.browser_id:
        await _log_guest_agent_message(
            input_data.browser_id, generation_id, skeletons, emotion_result
        )

    # 8) gen.complete
    yield sse("gen.complete", {
        "generation_id": generation_id,
        "total_cards": len(skeletons),
        "metadata": {"mode": "fast", "emotion": emotion_result["primary_emotion"]},
    })
