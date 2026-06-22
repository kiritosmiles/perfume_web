#!/usr/bin/env python3
"""L2 memory consolidation worker — BRPOP loop, retry 3x, dead-letter on failure.

Usage: python -m scripts.worker_l2
"""

import asyncio, logging, signal

logger = logging.getLogger("worker_l2")
stop = False


async def main():
    global stop
    from app.core.redis import init_redis, close_redis
    from app.core.pg import init_pg_pool, close_pg_pool
    from app.core.memory_queue import dequeue_l2, dead_letter_l2, MAX_RETRIES
    from app.services.memory import consolidate_session_to_l2

    await init_redis()
    await init_pg_pool()
    logger.info("L2 worker started")

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: setattr(__import__("sys").modules[__name__], "stop", True))
        except NotImplementedError:
            pass

    while not stop:
        try:
            task = await dequeue_l2(timeout_seconds=5)
            if task is None:
                continue
            sid = task.get("session_id", "?")
            logger.info("L2 processing: session=%s", sid)
            ok = False
            for attempt in range(1, MAX_RETRIES + 1):
                ok = await consolidate_session_to_l2(task["owner_type"], task["owner_id"], task["session_id"])
                if ok:
                    break
                logger.warning("L2 retry %d/%d: session=%s", attempt, MAX_RETRIES, sid)
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** attempt)
            if not ok:
                await dead_letter_l2(task)
        except Exception:
            logger.warning("L2 worker error", exc_info=True)
            await asyncio.sleep(5)

    await close_redis()
    await close_pg_pool()
    logger.info("L2 worker stopped")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    asyncio.run(main())
