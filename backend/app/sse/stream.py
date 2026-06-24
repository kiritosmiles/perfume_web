import asyncio
import contextlib
import json
import logging
import uuid
from typing import AsyncGenerator, Any

from neo4j.exceptions import Neo4jError, ServiceUnavailable, SessionExpired

from app.core.deps import get_db_neo4j
from app.core.pg import get_pg_pool
from app.models.guest import GuestSessionInput
from app.core.redis import (
    cache_emotion_vector, get_cached_emotion_vector, get_llm_key,
    build_graphrag_cache_key, cache_graphrag_result, get_cached_graphrag_result,
    build_skeleton_cache_key, cache_skeleton, get_cached_skeleton,
    increment_boundary_overstep, reset_boundary_overstep,
)
from app.services.emotion import resolve_emotion_from_cards, EMOTION_LABELS, DIMENSIONS
from app.services.fallback import search_fallback_fragrances
from app.services.fragrance import search_fragrance_by_emotion
from app.services.generation import build_skeleton, build_copy_stream
from app.services.intent import detect_intent, is_guest_intent_allowed
from app.services.llm import generate_copy_for_perfume
from app.services.llm_emotion import resolve_emotion_from_text
from app.services.safety import crisis_check, human_handoff_check
from app.services.boundary import _call_boundary_llm, check_boundary_result
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


async def _update_user_profile(user_id: str, emotion_result: dict) -> None:
    """Update user profile after generation completes (fire-and-forget).

    Progressive: first 3 conversations only update emotion tendency;
    conversation 4+ triggers full profile extraction (LLM, async).
    """
    try:
        from app.services.profile import (
            ensure_profile_exists,
            increment_conversation_count,
            update_emotion_tendency,
            should_extract_full_profile,
            extract_full_profile_llm,
        )
        await ensure_profile_exists(user_id)
        count = await increment_conversation_count(user_id)
        await update_emotion_tendency(user_id, emotion_result["emotion_vector"])
        if await should_extract_full_profile(user_id):
            logger.debug("User %s reached full profile threshold (conv=%d)", user_id, count)
            # Fire-and-forget: LLM extraction runs asynchronously (FR-1.6).
            # extract_full_profile_llm handles its own throttle + API-key checks.
            asyncio.create_task(extract_full_profile_llm(user_id))
    except Exception:
        logger.warning("Profile update failed for user=%s", user_id, exc_info=True)


async def sse_event_stream(
    input_data: GuestSessionInput,
    session_id: str | None = None,
    user_id: str | None = None,
) -> AsyncGenerator[str, None]:
    generation_id = str(uuid.uuid4())
    message_id = str(uuid.uuid4())
    sid = session_id or str(uuid.uuid4())

    # ── Heartbeat queue (background task → inline drain at each yield point) ──
    hb_queue: asyncio.Queue = asyncio.Queue(maxsize=2)

    async def _pump_heartbeats() -> None:
        while True:
            await asyncio.sleep(15)
            try:
                hb_queue.put_nowait(sse("system.heartbeat", {"ts": now_iso()}))
            except asyncio.QueueFull:
                pass

    hb_task = asyncio.create_task(_pump_heartbeats())

    def _drain_heartbeats() -> list[str]:
        events: list[str] = []
        while True:
            try:
                events.append(hb_queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return events


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
        # Check for explicit human handoff request first
        handoff = human_handoff_check(input_data.user_text)
        if handoff:
            yield sse("system.notification", {
                "kind": "human_handoff",
                "message": handoff["message"],
                "action_link": f"mailto:{handoff['contact_email']}",
            })
            yield sse("gen.complete", {
                "generation_id": "",
                "total_cards": 0,
                "metadata": {"reason": "human_handoff_requested"},
            })
            hb_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await hb_task
            return

        check = crisis_check(input_data.user_text)
        if check["is_crisis"]:
            if check["severity"] == "high":
                yield sse("safety.crisis", {
                    "severity": "high",
                    "message": "我们检测到你可能需要专业帮助。以下热线可以提供支持：",
                    "hotlines": check.get("hotlines", []),
                })
                yield sse("safety.block", {
                    "reason": "hostile",
                    "user_message": "消息已发送",
                })
                hb_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await hb_task
                return
            elif check["severity"] == "medium":
                yield sse("safety.warn", {
                    "level": "medium",
                    "message": "我注意到一些让我担心的内容，但我会继续为你服务。",
                })
        else:
            yield sse("safety.ok", {"flags": []})

    # ── FR-5.9: Boundary safety check (async, non-blocking LLM Call B) ──
    boundary_task: asyncio.Task | None = None
    if input_data.user_text and input_data.user_text.strip():
        boundary_task = asyncio.create_task(
            _call_boundary_llm(
                input_data.user_text,
                session_context={"intent": input_data.intent or "self_use"},
                api_key_override=user_api_key,
                base_url_override=user_base_url,
            )
        )

    # 1) chat.ack
    yield sse("chat.ack", {
        "message_id": message_id,
        "server_ts": now_iso(),
    })

    for _hb in _drain_heartbeats():
        yield _hb
    await asyncio.sleep(0)  # Yield event loop

    # ── 1.5) chat.intent — 3-layer detection (keyword / LLM / user toggle) ──
    intent_result = await detect_intent(
        user_text=input_data.user_text,
        user_toggle=input_data.intent,
        api_key_override=user_api_key,
        base_url_override=user_base_url,
    )
    yield sse("chat.intent", {
        "intent": intent_result["intent"],
        "confidence": intent_result["confidence"],
        "source": intent_result.get("source", "default"),
    })

    for _hb in _drain_heartbeats():
        yield _hb
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
        "synesthesia_tokens": emotion_result.get("synesthesia_tokens", []),
        "value_dimensions": emotion_result.get("value_dimensions", {}),
    })

    # Persist user message for Phase 2 registration migration (guest only)
    if input_data.browser_id and not user_id:
        await _log_guest_user_message(
            input_data.browser_id, generation_id, emotion_result,
            user_text=input_data.user_text,
        )

    for _hb in _drain_heartbeats():
        yield _hb
    await asyncio.sleep(0)

    # ── 2.5) chat.recall — Complexity-aware memory recall (~510ms)
    if user_id:
        owner_type = "user"
        owner_id = user_id
    elif input_data.browser_id:
        owner_type = "guest"
        owner_id = input_data.browser_id
    else:
        owner_type = "guest"
        owner_id = sid  # fallback: session-scoped guest
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

    # ── 2.8) Agent Gate: Information Completeness Check (FR-5.11) ──────────
    # Hard-boundary decision node: sufficient → continue, insufficient → ask user.
    # Only runs on the first pass (skip if refining or user already answered gate).
    from app.services.agent_gate import agent_gate_check
    gate_result = await agent_gate_check(
        intent=intent_result["intent"],
        emotion_cn=emotion_result["primary_emotion"],
        has_scene=bool(input_data.scene_tag),
        graphrag_candidates=0,  # Not yet searched; updated after GraphRAG below
        user_text=input_data.user_text,
        refine_count=1 if input_data.refine else 0,
        gate_answer=input_data.gate_answer,
        api_key_override=user_api_key,
        base_url_override=user_base_url,
    )

    if gate_result["verdict"] == "insufficient":
        # Emit gate verdict + questions, then stop — frontend will re-request
        # with gate_answer when the user responds.
        yield sse("gate.check", {
            "verdict": "insufficient",
            "latency_ms": gate_result["latency_ms"],
            "bypassed": False,
        })
        yield sse("gate.ask", {
            "questions": gate_result["questions"],
            "hint": gate_result["hint"],
        })
        yield sse("gen.complete", {
            "generation_id": generation_id,
            "total_cards": 0,
            "metadata": {"reason": "gate_insufficient"},
        })
        hb_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await hb_task
        return
    elif gate_result["verdict"] == "partial":
        yield sse("gate.wait", {"message": gate_result.get("message", "正在查找相关信息...")})

    yield sse("gate.check", {
        "verdict": gate_result["verdict"],
        "latency_ms": gate_result["latency_ms"],
        "bypassed": gate_result["bypassed"],
    })

    for _hb in _drain_heartbeats():
        yield _hb
    await asyncio.sleep(0)

    # ── FR-5.9: Boundary check verdict (before generation) ──────────────
    boundary_verdict: dict[str, Any] = {"verdict": "unchecked", "overstep_flag": "unchecked"}
    if boundary_task is not None and boundary_task.done():
        try:
            boundary_result = boundary_task.result()
        except Exception:
            boundary_result = None
        boundary_verdict = check_boundary_result(boundary_result)

        if boundary_verdict["verdict"] in ("overstep", "injection", "hostile"):
            reason = boundary_verdict["verdict"]

            if boundary_verdict["verdict"] == "overstep":
                count = await increment_boundary_overstep(sid)
                if count >= 3:
                    # FR-5.3 trigger #1: consecutive overstep → forced handoff
                    yield sse("system.notification", {
                        "kind": "human_handoff",
                        "message": "检测到多次超出角色范围的请求，已为你转接人工客服。",
                        "action_link": "mailto:support@perfume-ai.example.com",
                    })
                    yield sse("gen.complete", {
                        "generation_id": generation_id,
                        "total_cards": 0,
                        "metadata": {
                            "reason": "overstep_limit",
                            "overstep_flag": boundary_verdict["overstep_flag"],
                            "boundary_reasoning": boundary_verdict.get("reasoning", ""),
                        },
                    })
                    await reset_boundary_overstep(sid)
                    hb_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await hb_task
                    return
                # count < 3: block with overstep reason
                yield sse("safety.block", {
                    "reason": "overstep",
                    "user_message": "抱歉，我是香水推荐助手，只能帮你解答香水相关的问题哦 🌿",
                    "boundary_reasoning": boundary_verdict.get("reasoning", ""),
                })
                yield sse("gen.complete", {
                    "generation_id": generation_id,
                    "total_cards": 0,
                    "metadata": {
                        "reason": "overstep",
                        "overstep_flag": boundary_verdict["overstep_flag"],
                    },
                })
                hb_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await hb_task
                return
            else:
                # injection or hostile — block immediately
                yield sse("safety.block", {
                    "reason": reason,
                    "user_message": "消息已发送",
                })
                yield sse("gen.complete", {
                    "generation_id": generation_id,
                    "total_cards": 0,
                    "metadata": {
                        "reason": reason,
                        "overstep_flag": boundary_verdict["overstep_flag"],
                    },
                })
                hb_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await hb_task
                return

        if boundary_verdict["verdict"] == "borderline":
            yield sse("safety.warn", {
                "level": "low",
                "message": "我是香水推荐助手，让我帮你找到最适合的香氛吧 🌸",
                "boundary_reasoning": boundary_verdict.get("reasoning", ""),
            })

    # 3) gen.start
    yield sse("gen.start", {
        "generation_id": generation_id,
        "mode": "fast",
    })

    # ── Refinement: adjust emotion vector based on user refinement keyword ──
    if input_data.refine:
        from app.services.refinement import apply_refinement, DIMENSION_NAMES as _DIMS
        import logging as _logging
        _logger = _logging.getLogger(__name__)
        refine_keywords = [k.strip() for k in input_data.refine.split(",") if k.strip()]
        adjusted_vector = apply_refinement(emotion_result["emotion_vector"], refine_keywords)
        primary = max(_DIMS, key=lambda d: adjusted_vector[d])
        from app.services.emotion import EMOTION_LABELS as _LABELS, compute_value_dimensions as _compute_vd
        emotion_result = {
            "emotion_vector": adjusted_vector,
            "primary_emotion": _LABELS[primary],
            "confidence": adjusted_vector[primary],
            "source": "refined",
            "synesthesia_tokens": emotion_result.get("synesthesia_tokens", []),
            "value_dimensions": _compute_vd(adjusted_vector),
        }
        _logger.debug("Refinement applied: keywords=%s → primary=%s conf=%.2f",
                       refine_keywords, emotion_result["primary_emotion"], emotion_result["confidence"])

    # ── 3.5) Environment fusion (FR-2.8, weight 0.1 default / 0.2 extreme) ──
    # Always applied, not affected by user intent.
    env_meta: dict | None = None
    _has_env = any([
        input_data.season, input_data.time_of_day,
        input_data.weather_code is not None, input_data.temperature is not None,
    ])
    if _has_env:
        from app.services.environment import fuse_environment
        fused_vector, env_meta = fuse_environment(
            emotion_result["emotion_vector"],
            season=input_data.season,
            time_of_day=input_data.time_of_day,
            weather_code=input_data.weather_code,
            temperature=input_data.temperature,
        )
        emotion_result["emotion_vector"] = fused_vector
        # Update primary_emotion and confidence after fusion
        primary = max(DIMENSIONS, key=lambda d: fused_vector[d])
        emotion_result["primary_emotion"] = EMOTION_LABELS[primary]
        emotion_result["confidence"] = fused_vector[primary]
        logger.debug(
            "Environment fusion: season=%s time=%s weather=%s temp=%s weight=%.1f",
            input_data.season, input_data.time_of_day,
            input_data.weather_code, input_data.temperature,
            env_meta.get("fusion_weight", 0) if env_meta else 0,
        )

    # 4) GraphRAG search (with Redis cache for card-preset hot paths)
    candidates: list[dict] = []
    search_source = "graphrag"  # Tracked for gen.complete metadata
    cache_hit = False
    seed_notes = emotion_result.get("synesthesia_tokens") or None

    # ── Cache eligibility: card-preset source + no synesthesia tokens ──
    _cache_eligible = (
        emotion_result["source"] in ("card_preset", "llm_text_keyword")
        and not seed_notes
    )
    _cache_key: str | None = None
    if _cache_eligible:
        _cache_key = build_graphrag_cache_key(emotion_result["emotion_vector"], input_data.scene_tag)
        cached = await get_cached_graphrag_result(_cache_key)
        if cached is not None:
            candidates = cached
            search_source = "graphrag_cache"
            cache_hit = True
            logger.debug("GraphRAG cache hit key=%s candidates=%d", _cache_key, len(candidates))

    if not cache_hit:
        try:
            async for neo4j_session in get_db_neo4j():
                candidates = await search_fragrance_by_emotion(
                    neo4j_session,
                    emotion_result["emotion_vector"],
                    input_data.scene_tag,
                    limit=50,
                    seed_notes=seed_notes,
                    diversity=input_data.diversity,  # FR-3.8
                )
        except (Neo4jError, ServiceUnavailable, SessionExpired, OSError) as e:
            # Neo4j down → degrade to PG fragrance_templates or hardcoded classics
            logger.warning("GraphRAG search degraded (gen_id=%s): %s", generation_id, e)
            search_source = "degraded_backup"
            candidates = await search_fallback_fragrances(
                emotion_result["emotion_vector"],
                input_data.scene_tag,
                limit=10,
            )
            # Note: NOT yielding gen.error here — the pipeline continues
            # successfully with fallback data. Fallback flag is reported in
            # gen.complete metadata so the frontend can show a subtle notice
            # without treating it as a terminal error.

        if not candidates:
            # No GraphRAG matches → generic gift Top 5
            search_source = "generic_top5"
            candidates = await search_fallback_fragrances(
                emotion_result["emotion_vector"],
                input_data.scene_tag,
                limit=5,
            )
            # Same as above: pipeline continues, fallback source in gen.complete metadata

        # Write successful GraphRAG results to cache for future requests
        if _cache_eligible and _cache_key and candidates and search_source == "graphrag":
            await cache_graphrag_result(_cache_key, candidates)

    for _hb in _drain_heartbeats():
        yield _hb
    await asyncio.sleep(0)

    # ── Skeleton cache setup (FR: Phase 4) ──────────────────────────────
    _sk_cache_eligible = (
        emotion_result["source"] in ("card_preset", "llm_text_keyword")
        and not seed_notes
    )
    _sk_cache_key: str | None = None
    skeleton_cache_hit: bool = False
    _collected_copy_texts: list[str] = []
    cached_skeletons: list[dict] | None = None
    if _sk_cache_eligible:
        _sk_cache_key = build_skeleton_cache_key(
            emotion_result["emotion_vector"],
            intent_result["intent"],
            input_data.scene_tag,
        )
        cached_skeletons = await get_cached_skeleton(_sk_cache_key)
        if cached_skeletons is not None:
            skeleton_cache_hit = True
            logger.debug("Skeleton cache hit key=%s cards=%d", _sk_cache_key, len(cached_skeletons))

    # 5) gen.skeleton
    skeletons = build_skeleton(
        candidates, emotion_result["emotion_vector"], input_data.allergens,
        intent=intent_result["intent"],
        diversity=input_data.diversity,  # FR-3.8
    )
    yield sse("gen.skeleton", {
        "generation_id": generation_id,
        "recommendations": skeletons,
        "is_partial": True,
        "memory_context": recall_result.get("context_text", ""),
    })

    for _hb in _drain_heartbeats():
        yield _hb
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
        for _hb in _drain_heartbeats():
            yield _hb
        await asyncio.sleep(0)

    # 7) gen.copy — LLM streaming with skeleton cache + template fallback
    for sk in skeletons:
        # ── Try skeleton cache first ──────────────────────────────────
        cached_copy_text: str | None = None
        if skeleton_cache_hit and cached_skeletons:
            cached = next(
                (c for c in cached_skeletons
                 if c.get("name") == sk["name"] and c.get("brand") == sk.get("brand")),
                None,
            )
            if cached and cached.get("copy_full_text"):
                cached_copy_text = cached["copy_full_text"]

        if cached_copy_text:
            # Use cached copy text — split by lines for sentence-by-sentence streaming
            sentences = [s.strip() for s in cached_copy_text.split("\n") if s.strip()]
            for i, sentence in enumerate(sentences):
                yield sse("gen.copy", {
                    "generation_id": generation_id,
                    "rank": sk["rank"],
                    "copy_text_chunk": sentence,
                    "is_final": (i == len(sentences) - 1),
                })
                for _hb in _drain_heartbeats():
                    yield _hb
                await asyncio.sleep(0)
            continue  # Skip LLM — cache served

        # ── LLM path (existing logic) ─────────────────────────────────
        llm_chunks: list[str] = []
        async for chunk, _ in generate_copy_for_perfume(
            sk["rank"], generation_id,
            sk["name"], sk["brand"],
            emotion_result["primary_emotion"],
            sk.get("notes_combination", []),
            intent=intent_result["intent"],
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
                for _hb in _drain_heartbeats():
                    yield _hb
                await asyncio.sleep(0)
            # Collect full copy text for skeleton cache write
            if _sk_cache_eligible:
                _collected_copy_texts.append("\n".join(llm_chunks))
        else:
            # LLM unavailable → fall back to templates
            copy_chunks = build_copy_stream(
                sk["rank"], generation_id, emotion_result["primary_emotion"],
                intent=intent_result["intent"],
            )
            for i, chunk in enumerate(copy_chunks):
                yield sse("gen.copy", {
                    "generation_id": generation_id,
                    "rank": sk["rank"],
                    "copy_text_chunk": chunk,
                    "is_final": (i == len(copy_chunks) - 1),
                })
                for _hb in _drain_heartbeats():
                    yield _hb
                await asyncio.sleep(0)
            # Template text also collected for cache (as degraded copy)
            if _sk_cache_eligible:
                _collected_copy_texts.append("\n".join(copy_chunks))

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

    # Persist agent response for Phase 2 registration migration (guest only)
    if input_data.browser_id and not user_id:
        await _log_guest_agent_message(
            input_data.browser_id, generation_id, skeletons, emotion_result
        )

    # 8) gen.complete
    yield sse("gen.complete", {
        "generation_id": generation_id,
        "total_cards": len(skeletons),
        "metadata": {
            "mode": "fast",
            "emotion": emotion_result["primary_emotion"],
            "search_source": search_source,
            "cache_hit": cache_hit,
            "environment": env_meta,
            "diversity_mode": input_data.diversity > 0,
            "diversity_level": input_data.diversity,
            "cross_style": input_data.diversity >= 0.5,
            "overstep_flag": boundary_verdict.get("overstep_flag", "unchecked"),
            "skeleton_cache_hit": skeleton_cache_hit,
        },
    })

    # ── Skeleton cache write (fire-and-forget, after gen.complete) ──────
    if (
        _sk_cache_eligible
        and _sk_cache_key
        and not skeleton_cache_hit
        and skeletons
        and search_source not in ("degraded_backup", "generic_top5")
        and len(_collected_copy_texts) == len(skeletons)
    ):
        for sk, copy_text in zip(skeletons, _collected_copy_texts):
            sk["copy_full_text"] = copy_text
        asyncio.create_task(cache_skeleton(_sk_cache_key, skeletons))

    # ── FR-5.9: Final boundary check (if LLM didn't complete in time) ──
    if boundary_task is not None and not boundary_task.done():
        try:
            boundary_result = await asyncio.wait_for(boundary_task, timeout=1.0)
        except (asyncio.TimeoutError, Exception):
            boundary_result = None
        if boundary_result is not None:
            final_verdict = check_boundary_result(boundary_result)
            if final_verdict["verdict"] in ("overstep", "injection", "hostile"):
                logger.warning(
                    "Boundary violation detected post-generation sid=%s verdict=%s",
                    sid, final_verdict["verdict"],
                )
                # Increment counter for tracking; response already sent
                if final_verdict["verdict"] == "overstep":
                    await increment_boundary_overstep(sid)

    # ── L1 Async Consolidation (fire-and-forget, ~500ms) ─────────────────
    if user_msg or agent_msg:
        import asyncio as _asyncio
        _asyncio.create_task(
            trigger_l1_consolidation(sid, 1, user_msg or "", agent_msg, [])
        )

    # ── L2 enqueue (fire-and-forget, 3s delay for gen.complete flush) ──
    _owner_type = "user" if user_id else "guest"
    _owner_id = user_id or input_data.browser_id or sid
    asyncio.create_task(_enqueue_l2_after_delay(_owner_type, _owner_id, sid, 3.0))

    # ── Profile update (fire-and-forget, for authenticated users) ─────────
    if user_id:
        asyncio.create_task(_update_user_profile(user_id, emotion_result))

    # ── Heartbeat cleanup ──
    hb_task.cancel()
    try:
        await hb_task
    except asyncio.CancelledError:
        pass
