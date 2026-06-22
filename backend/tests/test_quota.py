"""Tests for Free user daily quota."""

import uuid
import pytest
from app.core.quota import check_free_quota, consume_free_quota, get_remaining_quota
from app.core.pg import get_pg_pool


async def _create_user(uid: str, email: str) -> None:
    """Insert a minimal user record so FK constraints are satisfied."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (id, email, password_hash) VALUES ($1::uuid, $2, 'test-hash')",
            uid, email,
        )


@pytest.mark.asyncio
async def test_new_user_has_full_quota():
    uid = str(uuid.uuid4())
    result = await get_remaining_quota(uid)
    assert result["sessions"]["remaining"] == 10
    assert result["generations"]["remaining"] == 15
    assert result["deep"]["remaining"] == 3


@pytest.mark.asyncio
async def test_consume_reduces_remaining():
    uid = str(uuid.uuid4())
    await _create_user(uid, f"test-{uid[:8]}@example.com")
    await consume_free_quota(uid, "sessions")
    await consume_free_quota(uid, "sessions")
    result = await get_remaining_quota(uid)
    assert result["sessions"]["used"] == 2
    assert result["sessions"]["remaining"] == 8


@pytest.mark.asyncio
async def test_check_quota_when_available():
    uid = str(uuid.uuid4())
    assert await check_free_quota(uid, "sessions") is True


@pytest.mark.asyncio
async def test_check_quota_when_exhausted():
    uid = str(uuid.uuid4())
    await _create_user(uid, f"test-{uid[:8]}@example.com")
    for _ in range(10):
        await consume_free_quota(uid, "sessions")
    assert await check_free_quota(uid, "sessions") is False
