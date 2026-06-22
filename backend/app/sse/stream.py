import asyncio
import json
import logging
import uuid
from typing import AsyncGenerator

from neo4j.exceptions import Neo4jError, ServiceUnavailable, SessionExpired

from app.core.deps import get_db_neo4j
from app.core.pg import get_pg_pool
from app.models.guest import GuestSessionInput
from app.core.redis import cache_emotion_vector, get_cached_emotion_vector, get_llm_key
from app.services.emotion import resolve_emotion_from_cards, EMOTION_LABELS, DIMENSIONS
from app.services.fallback import search_fallback_fragrances
from app.services.fragrance import search_fragrance_by_emotion
from app.services.generation import build_skeleton, build_copy_stream
from app.services.llm import generate_copy_for_perfume
from app.services.llm_emotion import resolve_emotion_from_text
from app.services.safety import crisis_check
from app.services.memory import trigger_l1_consolidation
from app.core.recall import recall_pipeline
from app.sse.protocol import sse, now_iso

logger = logging.getLogger(__name__)


async def _log_guest_user_message(
    browser_id: str,
    generation_id: str,
    emotion_result: dict,
    user_text: str | None = None,
) -> None:
    """Persist the user's card pick or text to temp_conversations."""
    try:
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            content = {
                "primary_emotion": emotion_result["primary_emotion"],
                "confidence": emotion_result["confidence"],
                "source": emotion_result["source"],
            }
            if user_text:
                content["user_text"] = user_text
            await conn.execute(
                """
                INSERT INTO temp_conversations
                    (browser_id, round, role, content, emotion_tags, created_at)
                VALUES ($1, 0, 'user', $2, $3, now())
                """,
                browser_id,
                json.dumps(content, ensure_ascii=False),
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


async def _resolve_emotion(
    input_data: GuestSessionInput,
    api_key_override: str | None = None,
    base_url_override: str | None = None,
) -> dict:
    """3-channel emotion resolution: text, cards, or dual-channel blend."""
    has_cards = bool(input_data.emotion_card_ids)
    has_text = bool(input_data.user_text and input_data.user_text.strip())

    if has_text and has_cards:
        text_result = await resolve_emotion_from_text(
            input_data.user_text,  # type: ignore[arg-type]
            api_key_override=api_key_override,
            base_url_override=base_url_override,
        )
        card_result = resolve_emotion_from_cards(input_data)
        blended = {}
        for dim in DIMENSIONS:
            blended[dim] = (
                card_result["emotion_vector"].get(dim, 0) * 0.3
                + text_result["emotion_vector"].get(dim, 0) * 0.7
            )
        primary = max(DIMENSIONS, key=lambda d: blended[d])
        return {
            "emotion_vector": blended,
            "primary_emotion": EMOTION_LABELS[primary],
            "confidence": blended[primary],
            "source": "llm_text",
        }
    elif has_text:
        return await resolve_emotion_from_text(
            input_data.user_text,  # type: ignore[arg-type]
            api_key_override=api_key_override,
            base_url_override=base_url_override,
        )
    else:
        return resolve_emotion_from_cards(input_data)


async def _enqueue_l2_after_delay(owner_type: str, owner_id: str, session_id: str, delay: float = 3.0) -> None:
    """Enqueue L2 consolidation after a short delay for gen.complete flush."""
    await asyncio.sleep(delay)
    try:
        from app.core.memory_queue import enqueue_l2 as _e
        await _e(owner_type, owner_id, session_id)
    except Exception:
        logger.warning("L2 enqueue failed session=%s", session_id, exc_info=True)


async def sse_event_stream(
    input_data: GuestSessionInput,
    session_id: str | None = None,
) -> AsyncGenerator[str, None]:
    generation_id = str(uuid.uuid4())
    message_id = str(uuid.uuid4())
    sid = session_id or str(uuid.uuid4())

    # Look up user-provided LLM key (if any)
    user_api_key: str | None = None
    user_base_url: str | None = None
    if input_data.browser_id:
        key_data = await get_llm_key(input_data.browser_id)
        if key_data:
            user_api_key = key_data.get("api_key")
            user_base_url = key_data.get("base_url") or None

    # 0) Safety check for text input
    if input_data.user_text and input_data.user_text.strip():
        check = crisis_check(input_data.user_text)
        if check["is_crisis"] and check["severity"] == "high":
            yield sse("safety.crisis", {
                "severity": "high",
                "message": "我们检测到你可能需要专业帮助。以下热线可以提供支持：",
                "hotlines": check.get("hotlines", []),
            })
            yield sse("safety.block", {
                "reason": "crisis_content",
                "user_message": "请拨打心理援助热线寻求专业帮助。",
            })
            return

    # 1) chat.ack
    yield sse("chat.ack", {
        "message_id": message_id,
        "server_ts": now_iso(),
    })

    await asyncio.sleep(0)  # Yield event loop

    # 2) chat.emotion — 3-channel resolution (text / cards / dual)
    card_key = ",".join(sorted(input_data.emotion_card_ids))
    has_text = bool(input_data.user_text and input_data.user_text.strip())

    if card_key and not has_text:
        # Card-only: try Redis cache
        cached_vector = await get_cached_emotion_vector(card_key)
        if cached_vector is not None:
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
    else:
        # Text or dual-channel (no cache — text is unique per request)
        emotion_result = await _resolve_emotion(
            input_data,
            api_key_override=user_api_key,
            base_url_override=user_base_url,
        )
    yield sse("chat.emotion", {
        "emotion_vector": emotion_result["emotion_vector"],
        "primary_emotion": emotion_result["primary_emotion"],
        "confidence": emotion_result["confidence"],
        "source": emotion_result["source"],
    })

    # Persist user message for Phase 2 registration migration
    if input_data.browser_id:
        await _log_guest_user_message(
            input_data.browser_id, generation_id, emotion_result,
            user_text=input_data.user_text,
        )

    await asyncio.sleep(0)

    # ── 2.5) chat.recall — Complexity-aware memory recall (~510ms)
    owner_type = "guest"
    owner_id = input_data.browser_id or ""
    if not owner_id:
        owner_id = sid  # fallback to session_id
    recall_result = await recall_pipeline(
        user_text=input_data.user_text or "",
        emotion_result=emotion_result,
        owner_type=owner_type,
        owner_id=owner_id,
        session_id=sid,
    )
    yield sse("chat.recall", {
        "generation_id": generation_id,
        "complexity": recall_result["complexity"],
        "recalled_count": len(recall_result["memories"]),
        "memory_sources": recall_result.get("sources", []),
        "latency_ms": recall_result["latency_ms"],
    })

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
        "memory_context": recall_result.get("context_text", ""),
    })

    await asyncio.sleep(0)

    # 6) gen.detail per card — dynamic longevity/sillage/season from Neo4j
    for sk in skeletons:
        yield sse("gen.detail", {
            "generation_id": generation_id,
            "rank": sk["rank"],
            "expanded_fields": {
                "graph_path": f"Emotion→{emotion_result['primary_emotion']}→Accord→{sk['name']}",
                "longevity": sk.get("longevity", 3.0),
                "sillage": sk.get("sillage", 2.5),
                "season": sk.get("season", "all"),
            },
        })
        await asyncio.sleep(0)

    # 7) gen.copy — LLM streaming with template fallback
    for sk in skeletons:
        llm_chunks: list[str] = []
        async for chunk, _ in generate_copy_for_perfume(
            sk["rank"], generation_id,
            sk["name"], sk["brand"],
            emotion_result["primary_emotion"],
            sk.get("notes_combination", []),
            api_key_override=user_api_key,
            base_url_override=user_base_url,
        ):
            llm_chunks.append(chunk)

        if llm_chunks:
            for i, chunk in enumerate(llm_chunks):
                yield sse("gen.copy", {
                    "generation_id": generation_id,
                    "rank": sk["rank"],
                    "copy_text_chunk": chunk,
                    "is_final": (i == len(llm_chunks) - 1),
                })
                await asyncio.sleep(0)
        else:
            # LLM unavailable → fall back to templates
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

    # ── L1 Evidence Write (sync, <2ms) ──────────────────────────────────
    user_msg = input_data.user_text or ",".join(input_data.emotion_card_ids) if not input_data.user_text else input_data.user_text
    agent_msg = "\n".join(
        f"推荐{s['rank']}: {s['name']} by {s.get('brand','')}" for s in skeletons
    )
    if user_msg or agent_msg:
        try:
            from app.core.redis import write_l1_evidence as _w
            await _w(sid, 1, user_msg or "", agent_msg, emotion_result["emotion_vector"])
        except Exception:
            logger.warning("L1 evidence write failed", exc_info=True)

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

    # ── L1 Async Consolidation (fire-and-forget, ~500ms) ─────────────────
    if user_msg or agent_msg:
        import asyncio as _asyncio
        _asyncio.create_task(
            trigger_l1_consolidation(sid, 1, user_msg or "", agent_msg, [])
        )

    # ── L2 enqueue (fire-and-forget, 3s delay for gen.complete flush) ──
    owner_type = "guest"
    owner_id = input_data.browser_id or sid
    asyncio.create_task(_enqueue_l2_after_delay(owner_type, owner_id, sid, 3.0))
