"""Tier-based user daily quota management (Phase 4: free/premium cut).

Tier limits:
  - free:     sessions=10, generations=15, deep=3  (per day)
  - premium:  unlimited (represented as 999_999)

Admin users (configured by email) always bypass all quotas regardless of tier.
"""

from app.core.pg import get_pg_pool

# ── Tier quota limits ─────────────────────────────────────────────────────────

TIER_QUOTA_LIMITS: dict[str, dict[str, int]] = {
    "free": {
        "sessions": 10,
        "generations": 15,
        "deep": 3,
    },
    "premium": {
        "sessions": 999_999,
        "generations": 999_999,
        "deep": 999_999,
    },
}

# Admin users bypass all quota checks
ADMIN_EMAILS: set[str] = {"admin@perfume.ai"}

UNLIMITED = 999_999


# ── Helpers ────────────────────────────────────────────────────────────────────


async def _get_user_tier(user_id: str) -> str | None:
    """Get the user's feature_tier. Returns None if user not found or PG unavailable."""
    try:
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT email, feature_tier FROM users WHERE id = $1::uuid", user_id,
            )
            if row is None:
                return None
            if row["email"] in ADMIN_EMAILS:
                return "premium"  # Admin = unlimited
            return row["feature_tier"] or "free"
    except Exception:
        return None  # PG down → fall through gracefully


def _get_quota_max(user_tier: str | None, quota_type: str) -> int:
    """Get the max quota for a user tier and quota type.

    Defaults to free limits when tier is None (PG unavailable).
    """
    tier = user_tier or "free"
    limits = TIER_QUOTA_LIMITS.get(tier, TIER_QUOTA_LIMITS["free"])
    return limits.get(quota_type, 10)


# ── Public API ─────────────────────────────────────────────────────────────────


async def check_free_quota(user_id: str, quota_type: str) -> bool:
    """Return True if quota is available (used < max for today)."""
    tier = await _get_user_tier(user_id)
    max_q = _get_quota_max(tier, quota_type)
    if max_q >= UNLIMITED:
        return True

    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT used FROM user_quota
               WHERE user_id = $1::uuid AND quota_type = $2 AND reset_at = CURRENT_DATE""",
            user_id, quota_type,
        )
        if row is None:
            return True  # No usage yet today
        return row["used"] < max_q


async def consume_free_quota(user_id: str, quota_type: str) -> None:
    """Increment quota usage for today. Idempotent (upsert).

    Premium users skip the increment entirely (no counter needed).
    """
    tier = await _get_user_tier(user_id)
    if tier == "premium":
        return

    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO user_quota (user_id, quota_type, used, reset_at)
               VALUES ($1::uuid, $2, 1, CURRENT_DATE)
               ON CONFLICT (user_id, quota_type, reset_at)
               DO UPDATE SET used = user_quota.used + 1""",
            user_id, quota_type,
        )


async def get_remaining_quota(user_id: str) -> dict:
    """Return all quotas with {quota_type: {used, max, remaining}} and tier info."""
    tier = await _get_user_tier(user_id)
    if tier is None:
        tier = "free"  # fallback when PG unavailable

    result: dict = {"tier": tier, "quotas": {}}
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        for qt in ["sessions", "generations", "deep"]:
            max_q = _get_quota_max(tier, qt)
            if max_q >= UNLIMITED:
                result["quotas"][qt] = {"used": 0, "max": UNLIMITED, "remaining": UNLIMITED}
                continue
            row = await conn.fetchrow(
                """SELECT used FROM user_quota
                   WHERE user_id = $1::uuid AND quota_type = $2 AND reset_at = CURRENT_DATE""",
                user_id, qt,
            )
            used = row["used"] if row else 0
            result["quotas"][qt] = {"used": used, "max": max_q, "remaining": max(0, max_q - used)}
    return result
