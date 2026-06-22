#!/usr/bin/env python3
"""L3 daily memory consolidation — run via cron daily at 3am.

Finds all owners (users + guests) with L2 data from today,
consolidates each into memory_l3.

Usage: python -m scripts.consolidate_l3 [--date YYYY-MM-DD]
"""

import asyncio, logging, sys
from datetime import date

logger = logging.getLogger("consolidate_l3")


async def main(date_str: str):
    from app.core.redis import init_redis, close_redis
    from app.core.pg import init_pg_pool, close_pg_pool, get_pg_pool
    from app.services.memory import consolidate_daily_to_l3

    await init_redis()
    await init_pg_pool()
    logger.info("L3 consolidation started: date=%s", date_str)

    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        # Find distinct owners with L2 data today
        user_rows = await conn.fetch(
            "SELECT DISTINCT user_id::text AS owner_id FROM memory_l2 WHERE user_id IS NOT NULL AND created_at::date = $1::date",
            date_str)
        guest_rows = await conn.fetch(
            "SELECT DISTINCT browser_id AS owner_id FROM memory_l2 WHERE browser_id IS NOT NULL AND created_at::date = $1::date",
            date_str)

    owners = ([(r["owner_id"], "user") for r in user_rows] +
              [(r["owner_id"], "guest") for r in guest_rows])
    logger.info("L3 owners to process: %d", len(owners))

    ok = fail = 0
    for owner_id, otype in owners:
        success = await consolidate_daily_to_l3(otype, owner_id, date_str)
        if success:
            ok += 1
        else:
            fail += 1
            logger.warning("L3 failed: %s:%s", otype, owner_id)

    await close_redis()
    await close_pg_pool()
    logger.info("L3 consolidation complete: %d ok, %d failed", ok, fail)
    return fail == 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    dt = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--date" else date.today().isoformat()
    success = asyncio.run(main(dt))
    sys.exit(0 if success else 1)
