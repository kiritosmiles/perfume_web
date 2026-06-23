"""Free user daily quota management."""

from app.core.pg import get_pg_pool

QUOTA_LIMITS = {
    "sessions": 10,
    "generations": 15,
    "deep": 3,
}

# Admin users bypass all quota checks
ADMIN_EMAILS: set[str] = {"admin@perfume.ai"}

UNLIMITED = 999_999


async def _is_admin(user_id: str) -> bool:
    """Check if user is an admin (unlimited quota)."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT email FROM users WHERE id = $1::uuid", user_id,
        )
        if row and row["email"] in ADMIN_EMAILS:
            return True
    return False


async def check_free_quota(user_id: str, quota_type: str) -> bool:
    """Return True if quota is available (used < max for today)."""
    if await _is_admin(user_id):
        return True
    max_q = QUOTA_LIMITS.get(quota_type, 10)
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
    """Increment quota usage for today. Idempotent (upsert)."""
    if await _is_admin(user_id):
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
    """Return all quotas with {quota_type: {used, max, remaining}}."""
    if await _is_admin(user_id):
        return {
            qt: {"used": 0, "max": UNLIMITED, "remaining": UNLIMITED}
            for qt in ["sessions", "generations", "deep"]
        }
    pool = await get_pg_pool()
    result = {}
    async with pool.acquire() as conn:
        for qt in ["sessions", "generations", "deep"]:
            max_q = QUOTA_LIMITS[qt]
            row = await conn.fetchrow(
                """SELECT used FROM user_quota
                   WHERE user_id = $1::uuid AND quota_type = $2 AND reset_at = CURRENT_DATE""",
                user_id, qt,
            )
            used = row["used"] if row else 0
            result[qt] = {"used": used, "max": max_q, "remaining": max_q - used}
    return result
