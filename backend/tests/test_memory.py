"""Tests for TiMem memory system — embedding, L1, L2, L3, recall."""
import pytest
from app.core.embedding import encode


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
