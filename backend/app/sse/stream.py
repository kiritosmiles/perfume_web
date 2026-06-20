import asyncio
import uuid
from typing import AsyncGenerator

from app.core.deps import get_db_neo4j
from app.models.guest import GuestSessionInput
from app.services.emotion import resolve_emotion_from_cards
from app.services.fragrance import search_fragrance_by_emotion
from app.services.generation import build_skeleton, build_copy_stream
from app.sse.protocol import sse, now_iso


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
    except Exception:
        # If Neo4j unavailable, return gen.error with NO_MATCH
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

    # 8) gen.complete
    yield sse("gen.complete", {
        "generation_id": generation_id,
        "total_cards": len(skeletons),
        "metadata": {"mode": "fast", "emotion": emotion_result["primary_emotion"]},
    })
