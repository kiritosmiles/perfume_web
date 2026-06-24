"""User profile extraction and management (FR-1.1, FR-1.3).

Builds structured user profiles from TiMem memory data and recommendation
history. Progressive: first 3 conversations → light mode (emotion only);
conversation 4+ → full mode (personality tags, preferred accords/notes).

Profile extraction runs asynchronously after gen.complete to avoid
blocking the SSE stream.
"""

import json as _json
import logging
from typing import Any

import httpx

from app.core.config import settings
from app.core.pg import get_pg_pool

logger = logging.getLogger(__name__)

# Threshold for switching from light to full profile mode
FULL_PROFILE_THRESHOLD = 3


async def get_user_profile(user_id: str) -> dict[str, Any] | None:
    """Fetch a user's profile data (or None if not yet created)."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT profile_data, conversation_count, updated_at FROM user_profiles WHERE user_id = $1",
            user_id,
        )
        if row is None:
            return None
        return {
            "profile_data": _json.loads(row["profile_data"]) if isinstance(row["profile_data"], str) else dict(row["profile_data"]),
            "conversation_count": row["conversation_count"],
            "updated_at": row["updated_at"].isoformat(),
        }


async def ensure_profile_exists(user_id: str) -> None:
    """Create a light profile row if one doesn't already exist."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO user_profiles (user_id, conversation_count)
            VALUES ($1, 0)
            ON CONFLICT (user_id) DO NOTHING
            """,
            user_id,
        )


async def increment_conversation_count(user_id: str) -> int:
    """Increment the conversation count and return the new value."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE user_profiles
            SET conversation_count = conversation_count + 1,
                updated_at = now()
            WHERE user_id = $1
            RETURNING conversation_count
            """,
            user_id,
        )
        return row["conversation_count"] if row else 0


async def update_emotion_tendency(
    user_id: str,
    emotion_vector: dict[str, float],
) -> None:
    """Incrementally update the user's emotion tendency profile.

    Uses exponential moving average: new = old * 0.7 + current * 0.3.
    This gives recent emotions more weight while keeping history.
    """
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        current = _json.dumps(emotion_vector, ensure_ascii=False)
        await conn.execute(
            """
            UPDATE user_profiles
            SET profile_data = jsonb_set(
                profile_data,
                '{emotion_tendency}',
                CASE
                    WHEN profile_data->'emotion_tendency' = '{}'::jsonb
                    THEN $1::jsonb
                    ELSE (
                        SELECT jsonb_object_agg(
                            key,
                            GREATEST(0, LEAST(1,
                                COALESCE((profile_data->'emotion_tendency'->>key)::float, 0) * 0.7
                                + COALESCE(($1::jsonb->>key)::float, 0) * 0.3
                            ))
                        )
                        FROM jsonb_each_text(profile_data->'emotion_tendency' || $1::jsonb)
                    )
                END
            ),
                updated_at = now()
            WHERE user_id = $2
            """,
            current,
            user_id,
        )


async def update_full_profile(
    user_id: str,
    profile_data: dict[str, Any],
) -> None:
    """Write a complete profile snapshot (from LLM extraction)."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE user_profiles
            SET profile_data = $1::jsonb,
                updated_at = now()
            WHERE user_id = $2
            """,
            _json.dumps(profile_data, ensure_ascii=False),
            user_id,
        )


async def submit_onboarding(
    user_id: str,
    answers: list[dict[str, Any]],
) -> dict[str, Any]:
    """Process onboarding questionnaire answers and produce initial profile.

    Each answer dict: {"question": int, "option": str, "mapped_vector": dict | None, "mapped_tags": list[str] | None}

    Returns the newly created profile.
    """
    # Aggregate vectors from answers
    accumulated: dict[str, float] = {}
    tag_contributions: dict[str, float] = {}

    for ans in answers:
        vector = ans.get("mapped_vector")
        tags = ans.get("mapped_tags") or []
        if vector:
            for dim, val in vector.items():
                accumulated[dim] = accumulated.get(dim, 0) + val
        for tag in tags:
            tag_contributions[tag] = tag_contributions.get(tag, 0) + 1

    # Normalize vector
    total = sum(accumulated.values()) or 1
    emotion_tendency = {k: round(v / total, 2) for k, v in accumulated.items()}

    # Top 5 tags by contribution
    sorted_tags = sorted(tag_contributions.items(), key=lambda x: -x[1])
    personality_tags = [t for t, _ in sorted_tags[:5]]

    profile = {
        "personality_tags": personality_tags,
        "emotion_tendency": emotion_tendency,
        "preferred_accords": [],
        "preferred_notes": [],
        "gift_history": [],
        "profile_level": "full",
        "questionnaire_completed": True,
    }

    await ensure_profile_exists(user_id)
    await update_full_profile(user_id, profile)

    return profile


async def should_extract_full_profile(user_id: str) -> bool:
    """Return True if this user should get full profile extraction."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                COALESCE((profile_data->>'questionnaire_completed')::bool, false) AS q_done,
                conversation_count
            FROM user_profiles
            WHERE user_id = $1
            """,
            user_id,
        )
        if row is None:
            return False
        if row["q_done"]:
            return True
        return row["conversation_count"] >= FULL_PROFILE_THRESHOLD


# ── FR-1.6: Dynamic tag update via LLM async extraction ────────────

PROFILE_EXTRACTION_SYSTEM_PROMPT = """你是一个用户画像提取专家。根据用户的近期对话和当前画像，提取更新的个性标签、偏好香调和偏好香原料。

规则：
- personality_tags: 3-5个中文标签，描述用户的性格和气味偏好（如"清新自然"、"成熟稳重"、"甜美可爱"、"低调优雅"）
- preferred_accords: 3-5个香调类型（如"花香调"、"木质调"、"柑橘调"、"东方调"、"绿叶调"）
- preferred_notes: 3-5个具体香原料（如"玫瑰"、"檀木"、"佛手柑"、"茉莉"、"雪松"）
- 如果当前已有标签且与近期对话无矛盾，保留现有标签
- 标签应基于实际对话内容，不要臆造
- 只输出 JSON，不要其他内容"""


async def get_recent_memory_for_extraction(user_id: str) -> str:
    """Fetch recent L3 memory summaries for LLM extraction context."""
    try:
        from app.services.memory import get_l3_summaries
        summaries = await get_l3_summaries("user", user_id, 7)
        if not summaries:
            return "（暂无近期记忆摘要）"
        return "\n".join(f"- {s}" for s in summaries)
    except Exception:
        logger.warning("Failed to fetch L3 memory for user=%s", user_id, exc_info=True)
        return "（记忆获取失败）"


async def _should_re_extract(user_id: str) -> bool:
    """Throttle: only re-extract every PROFILE_EXTRACTION_THROTTLE conversations."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                conversation_count,
                COALESCE((profile_data->>'extraction_count')::int, 0) AS extraction_count,
                COALESCE((profile_data->>'last_extraction_conv')::int, 0) AS last_extraction_conv
            FROM user_profiles
            WHERE user_id = $1
            """,
            user_id,
        )
        if row is None:
            return False
        current = row["conversation_count"]
        last = row["last_extraction_conv"]
        return (current - last) >= settings.PROFILE_EXTRACTION_THROTTLE


async def extract_full_profile_llm(user_id: str) -> dict[str, Any] | None:
    """LLM-powered full profile extraction: personality_tags + accords + notes.

    Follows the same pattern as llm_emotion.py:
    - httpx.AsyncClient with timeout
    - settings.LLM_API_KEY check → graceful None fallback
    - JSON response_format
    - Merge results into existing profile

    Returns updated profile_data dict, or None if extraction skipped/failed.
    """
    # Check throttle
    if not await _should_re_extract(user_id):
        logger.debug("Profile extraction throttled for user=%s", user_id[:8])
        return None

    api_key = settings.LLM_API_KEY
    if not api_key:
        logger.debug("Profile extraction skipped: no LLM_API_KEY configured")
        return None

    # Fetch current profile
    current_profile = await get_user_profile(user_id)
    if not current_profile:
        return None

    current_data = current_profile["profile_data"]
    recent_memory = await get_recent_memory_for_extraction(user_id)

    # Build LLM prompt
    current_tags = current_data.get("personality_tags", [])
    current_accords = current_data.get("preferred_accords", [])
    current_notes = current_data.get("preferred_notes", [])
    emotion_tendency = current_data.get("emotion_tendency", {})

    top3 = sorted(emotion_tendency.items(), key=lambda x: -x[1])[:3] if emotion_tendency else []

    user_message = _json.dumps({
        "current_tags": current_tags,
        "current_accords": current_accords,
        "current_notes": current_notes,
        "emotion_tendency_top3": top3,
        "recent_memory_summaries": recent_memory,
    }, ensure_ascii=False)

    try:
        base_url = settings.LLM_BASE_URL
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": PROFILE_EXTRACTION_SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "max_tokens": 300,
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"},
                },
            )
            if response.status_code != 200:
                logger.warning("Profile extraction API error %d for user=%s", response.status_code, user_id[:8])
                return None

            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            result = _json.loads(content)

            # Validate and sanitize
            new_tags: list[str] = [str(t).strip() for t in result.get("personality_tags", [])[:5] if t]
            new_accords: list[str] = [str(a).strip() for a in result.get("preferred_accords", [])[:5] if a]
            new_notes: list[str] = [str(n).strip() for n in result.get("preferred_notes", [])[:5] if n]

            if not new_tags and not new_accords and not new_notes:
                logger.warning("Profile extraction returned empty results for user=%s", user_id[:8])
                return None

            # Merge: keep existing values if LLM returned empty for a field
            merged_tags = new_tags if new_tags else current_tags
            merged_accords = new_accords if new_accords else current_accords
            merged_notes = new_notes if new_notes else current_notes

            # Build updated profile data
            updated_data = {
                **current_data,
                "personality_tags": merged_tags,
                "preferred_accords": merged_accords,
                "preferred_notes": merged_notes,
                "extraction_count": current_data.get("extraction_count", 0) + 1,
                "last_extraction_conv": current_profile["conversation_count"],
                "profile_level": "full",
            }

            # Write back to DB
            await update_full_profile(user_id, updated_data)

            logger.info("Profile extraction success: user=%s tags=%s accords=%s",
                        user_id[:8], merged_tags, merged_accords)
            return updated_data

    except Exception as e:
        logger.warning("Profile extraction failed for user=%s: %s", user_id[:8], e)
        return None
