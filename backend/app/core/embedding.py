"""bge-small-zh embedding model — local CPU inference, 512d vectors."""

import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)
_model: Optional["SentenceTransformer"] = None


def _get_model() -> "SentenceTransformer":
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(settings.BGE_MODEL_PATH)
        logger.info("bge-small-zh loaded from %s", settings.BGE_MODEL_PATH)
    return _model


async def encode(text: str) -> list[float]:
    """Encode text to 512-d float vector. ~5ms on CPU.
    Returns zeros (512) if model unavailable — caller should handle.
    """
    try:
        model = _get_model()
        import asyncio
        result = await asyncio.get_running_loop().run_in_executor(
            None, model.encode, [text]
        )
        return result[0].tolist()
    except Exception as e:
        logger.warning("bge-small-zh encode failed: %s", e)
        return [0.0] * 512


def encode_sync(text: str) -> list[float]:
    """Synchronous variant for non-async contexts (e.g. cron scripts)."""
    try:
        model = _get_model()
        result = model.encode([text])
        return result[0].tolist()
    except Exception as e:
        logger.warning("bge-small-zh sync encode failed: %s", e)
        return [0.0] * 512
