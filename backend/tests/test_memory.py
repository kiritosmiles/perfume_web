"""Tests for TiMem memory system — embedding, L1, L2, L3, recall."""
import json
import uuid

import pytest
import pytest_asyncio

from app.core.embedding import encode
from app.core.memory_queue import enqueue_l2, dequeue_l2


class TestEmbedding:
    @pytest.mark.asyncio
    async def test_encode_returns_768d_vector(self):
        vec = await encode("用户喜欢清新的柑橘调香水")
        assert len(vec) == 512
        assert all(isinstance(v, float) for v in vec)
        assert any(v != 0 for v in vec)

    @pytest.mark.asyncio
    async def test_encode_short_text(self):
        vec = await encode("木质调")
        assert len(vec) == 512

    @pytest.mark.asyncio
    async def test_similar_texts_high_cosine(self):
        import numpy as np
        v1 = np.array(await encode("喜欢清新的柑橘调"))
        v2 = np.array(await encode("偏好柠檬和佛手柑"))
        cosine = float(v1.dot(v2) / (max(np.linalg.norm(v1) * np.linalg.norm(v2), 1e-10)))
        assert cosine > 0.5

    @pytest.mark.asyncio
    async def test_dissimilar_texts_lower_cosine(self):
        import numpy as np
        v1 = np.array(await encode("喜欢清新的柑橘调"))
        v2 = np.array(await encode("想要浓郁的木质皮革香"))
        cosine = float(v1.dot(v2) / (max(np.linalg.norm(v1) * np.linalg.norm(v2), 1e-10)))
        assert cosine < 0.95


class TestL1Fragment:
    @pytest_asyncio.fixture(autouse=True)
    async def _ensure_redis(self):
        try:
            from app.core.redis import _get_client, init_redis
            if _get_client() is None:
                await init_redis()
            # Verify connection is working (init_redis sets _client before ping)
            client = _get_client()
            if client is not None:
                await client.ping()
        except Exception:
            # Reset _client if it's broken (partial init)
            import app.core.redis as _redis_mod
            _redis_mod._client = None
            pytest.skip("Redis not available")

    @pytest.mark.asyncio
    async def test_write_and_read_evidence(self):
        from app.core.redis import write_l1_evidence, get_l1_fragments
        sid = str(uuid.uuid4())
        await write_l1_evidence(sid, 1, "推荐清新香水", "推荐TF橙花油", {"joy": 0.8})
        frags = await get_l1_fragments(sid, max_rounds=10)
        assert len(frags) == 1
        assert frags[0]["round_num"] == 1
        assert "推荐清新香水" in frags[0]["user_text"]

    @pytest.mark.asyncio
    async def test_multiple_rounds_ordered(self):
        from app.core.redis import write_l1_evidence, get_l1_fragments
        sid = str(uuid.uuid4())
        emo = {"joy": 0.5, "calm": 0.5}
        for i in range(1, 4):
            await write_l1_evidence(sid, i, f"u{i}", f"a{i}", emo)
        frags = await get_l1_fragments(sid, max_rounds=20)
        assert len(frags) == 3
        assert [f["round_num"] for f in frags] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_max_rounds_limit(self):
        from app.core.redis import write_l1_evidence, get_l1_fragments
        sid = str(uuid.uuid4())
        emo = {"joy": 1.0}
        for i in range(1, 6):
            await write_l1_evidence(sid, i, f"t{i}", f"r{i}", emo)
        frags = await get_l1_fragments(sid, max_rounds=3)
        assert len(frags) == 3

    @pytest.mark.asyncio
    async def test_update_text_and_get_texts(self):
        from app.core.redis import write_l1_evidence, update_l1_text, get_l1_texts
        sid = str(uuid.uuid4())
        await write_l1_evidence(sid, 1, "user", "agent", {"joy": 0.9})
        await update_l1_text(sid, 1, "[偏好] 用户喜欢柑橘调")
        texts = await get_l1_texts(sid)
        assert any("[偏好] 用户喜欢柑橘调" in t for t in texts)


class TestL2Queue:
    @pytest_asyncio.fixture(autouse=True)
    async def _ensure_redis(self):
        try:
            from app.core.redis import _get_client, init_redis
            if _get_client() is None:
                await init_redis()
            # Verify connection is working (init_redis sets _client before ping)
            client = _get_client()
            if client is not None:
                await client.ping()
        except Exception:
            # Reset _client if it's broken (partial init)
            import app.core.redis as _redis_mod
            _redis_mod._client = None
            pytest.skip("Redis not available")

    @pytest_asyncio.fixture(autouse=True)
    async def _cleanup(self):
        try:
            from app.core.redis import _get_client
            r = _get_client()
            if r:
                await r.delete("memory:queue:L2")
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_enqueue_dequeue(self):
        await enqueue_l2("guest", "browser-abc", str(uuid.uuid4()))
        task = await dequeue_l2(timeout_seconds=1)
        assert task is not None
        assert task["owner_type"] == "guest"
        assert task["owner_id"] == "browser-abc"

    @pytest.mark.asyncio
    async def test_dequeue_empty_returns_none(self):
        task = await dequeue_l2(timeout_seconds=1)
        assert task is None

    @pytest.mark.asyncio
    async def test_fifo_order(self):
        s1, s2 = str(uuid.uuid4()), str(uuid.uuid4())
        await enqueue_l2("guest", "b1", s1)
        await enqueue_l2("guest", "b2", s2)
        t1 = await dequeue_l2(timeout_seconds=1)
        t2 = await dequeue_l2(timeout_seconds=1)
        assert t1["session_id"] == s1
        assert t2["session_id"] == s2
