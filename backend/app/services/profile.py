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
