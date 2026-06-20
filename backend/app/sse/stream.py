import asyncio
import json
import logging
import uuid
from typing import AsyncGenerator

from neo4j.exceptions import Neo4jError, ServiceUnavailable, SessionExpired

from app.core.deps import get_db_neo4j
from app.core.pg import get_pg_pool
from app.models.guest import GuestSessionInput
from app.core.redis import cache_emotion_vector, get_cached_emotion_vector
from app.services.emotion import resolve_emotion_from_cards
from app.services.fallback import search_fallback_fragrances
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

    # 2) chat.emotion (with Redis cache)
    card_key = ",".join(sorted(input_data.emotion_card_ids))
    cached_vector = await get_cached_emotion_vector(card_key)
    if cached_vector is not None:
        # Use cached vector directly — deterministic from card IDs
        from app.services.emotion import EMOTION_LABELS, DIMENSIONS
        primary = max(DIMENSIONS, key=lambda d: cached_vector[d])
        emotion_result = {
            "emotion_vector": cached_vector,
            "primary_emotion": EMOTION_LABELS[primary],
            "confidence": cached_vector[primary],
            "source": "card_preset",
        }
    else:
        emotion_result = resolve_emotion_from_cards(input_data)
        await cache_emotion_vector(card_key, emotion_result["emotion_vector"])
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
        # Neo4j down → degrade to PG fragrance_templates or hardcoded classics
        logger.warning("GraphRAG search degraded (gen_id=%s): %s", generation_id, e)
        candidates = await search_fallback_fragrances(
            emotion_result["emotion_vector"],
            input_data.scene_tag,
            limit=10,
        )
        yield sse("gen.error", {
            "generation_id": generation_id,
            "code": "DEGRADED",
            "user_message": "正在从备用知识库为你推荐经典香氛",
            "degraded": True,
        })
        # Continue to normal pipeline with fallback candidates

    if not candidates:
        # No GraphRAG matches → generic gift Top 5
        candidates = await search_fallback_fragrances(
            emotion_result["emotion_vector"],
            input_data.scene_tag,
            limit=5,
        )
        yield sse("gen.error", {
            "generation_id": generation_id,
            "code": "GENERIC_FALLBACK",
            "user_message": "为你推荐广受欢迎的经典香氛",
            "degraded": False,
        })
        # Continue to normal pipeline with fallback candidates

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
