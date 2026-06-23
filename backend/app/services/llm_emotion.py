"""LLM-based emotion recognition from free-text input.

Produces 8-dimensional emotion vectors compatible with the downstream
GraphRAG query pipeline. Falls back to keyword mapping when LLM is
unavailable (no API key or call fails).

Also handles synesthesia decoding (FR-5.8) — converting abstract
descriptions like "rain smell" into concrete note/accord seed terms
for GraphRAG search.
"""

import json as _json
import logging
import re as _re

import httpx

from app.core.config import settings
from app.services.emotion import DIMENSIONS, EMOTION_LABELS, CARD_VECTORS

logger = logging.getLogger(__name__)

LLM_EMOTION_TIMEOUT = 3.0  # seconds — sub-timeout for emotion classification
LLM_SYNESTHESIA_TIMEOUT = 2.0  # seconds — sub-timeout for synesthesia decoding

SYSTEM_PROMPT = """你是一个情绪识别专家。根据用户用中文或英文描述的心情，输出一个8维情绪向量（0-1范围，不需要总和为1）。

维度: joy, sadness, anxiety, calm, excitement, nostalgia, romance, melancholy

规则:
- 主要情绪维度给 0.7-1.0
- 辅助/次要有 0.3-0.6
- 不相关维度给 0-0.1
- 每个维度独立评估，不要为了凑总和而调整

请以 JSON 格式输出，不要其他内容。示例:
{"joy":0.9,"sadness":0,"anxiety":0.1,"calm":0.2,"excitement":0.7,"nostalgia":0,"romance":0.3,"melancholy":0}"""

# ── Keywords fallback (no LLM required) ──────────────────────────────────────

KEYWORD_MAP: dict[str, dict[str, float]] = {
    "开心": CARD_VECTORS["joy"],
    "高兴": CARD_VECTORS["joy"],
    "快乐": CARD_VECTORS["joy"],
    "兴奋": CARD_VECTORS["excitement"],
    "激动": CARD_VECTORS["excitement"],
    "期待": CARD_VECTORS["excitement"],
    "难过": CARD_VECTORS["sadness"],
    "伤心": CARD_VECTORS["sadness"],
    "哭": CARD_VECTORS["sadness"],
    "焦虑": CARD_VECTORS["anxiety"],
    "紧张": CARD_VECTORS["anxiety"],
    "不安": CARD_VECTORS["anxiety"],
    "平静": CARD_VECTORS["calm"],
    "安静": CARD_VECTORS["calm"],
    "放松": CARD_VECTORS["calm"],
    "怀旧": CARD_VECTORS["nostalgia"],
    "怀念": CARD_VECTORS["nostalgia"],
    "回忆": CARD_VECTORS["nostalgia"],
    "浪漫": CARD_VECTORS["romance"],
    "爱": CARD_VECTORS["romance"],
    "心动": CARD_VECTORS["romance"],
    "忧郁": CARD_VECTORS["melancholy"],
    "低落": CARD_VECTORS["melancholy"],
    "孤独": CARD_VECTORS["melancholy"],
    "happy": CARD_VECTORS["joy"],
    "excited": CARD_VECTORS["excitement"],
    "sad": CARD_VECTORS["sadness"],
    "anxious": CARD_VECTORS["anxiety"],
    "calm": CARD_VECTORS["calm"],
    "relaxed": CARD_VECTORS["calm"],
    "romantic": CARD_VECTORS["romance"],
    "nostalgic": CARD_VECTORS["nostalgia"],
    "melancholy": CARD_VECTORS["melancholy"],
}


def _keyword_fallback(text: str) -> dict[str, float] | None:
    """Match text against keyword map. Returns vector or None."""
    text_lower = text.lower()
    vectors = []
    for kw, vec in KEYWORD_MAP.items():
        if kw.lower() in text_lower:
            vectors.append(vec)
    if not vectors:
        return None
    # Average all matched vectors
    result: dict[str, float] = {}
    for dim in DIMENSIONS:
        result[dim] = sum(v[dim] for v in vectors) / len(vectors)
    return result


# ── Synesthesia decoding (FR-5.8) ──────────────────────────────────────────────

# Patterns that suggest abstract/synesthetic descriptions needing decoding
_SYNESTHESIA_PATTERNS = [
    r"(?:的|那种|像|像那种|有.*感觉)(?:味道|气味|气息|香气|感觉)",
    r"(?:闻|嗅)起来像",
    r"(?:的)?颜色",
    r"(?:的)?画",
    r"(?:一|下)(?:场|阵)(?:雨|风|海洋|森林|花园|草地|雪)",
    r"下雨|雨林|海洋|森林|沙漠|草原|星空|月光|阳光|清晨|黄昏|夜晚",
    r"(?:像|跟).*(?:一样|似的)",
    r"抽象|超现实|通感|画面|音乐|诗歌|故事|电影",
]


def _is_synesthetic(text: str) -> bool:
    """Detect if text contains abstract/synesthetic descriptions needing decoding."""
    text_clean = text.strip()
    for pattern in _SYNESTHESIA_PATTERNS:
        if _re.search(pattern, text_clean):
            return True
    return False


SYNESTHESIA_SYSTEM_PROMPT = """你是一个嗅觉通感解码器。用户用抽象或跨感官的方式描述了一种气味感受。
请将用户的描述解码为 3-5 个具体的香调或香原料词汇。

要求：
- 每个词必须是香水行业常用的香调或原料名称（中文或英文）
- 优先使用标准分类：花香、果香、柑橘、木质、辛辣、水生、绿叶、粉质、麝香等
- 也可以给出具体原料：佛手柑、茉莉、玫瑰、檀木、香根草、臭氧等
- 按关联度从高到低排列

请以 JSON 数组格式输出，不要其他内容。
示例输入: "下雨的味道"
示例输出: ["臭氧", "湿润木质", "青草", "泥土", "水生"]"""


async def _decode_synesthesia(
    text: str,
    api_key_override: str | None = None,
    base_url_override: str | None = None,
) -> list[str] | None:
    """Decode abstract sensory descriptions into concrete note/accord terms via LLM."""
    api_key = api_key_override or settings.LLM_API_KEY
    if not api_key:
        return None
    base_url = base_url_override or settings.LLM_BASE_URL

    try:
        async with httpx.AsyncClient(timeout=LLM_SYNESTHESIA_TIMEOUT) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": SYNESTHESIA_SYSTEM_PROMPT},
                        {"role": "user", "content": f"用户描述：{text}"},
                    ],
                    "max_tokens": 120,
                    "temperature": 0.4,
                    "response_format": {"type": "json_object"},
                },
            )
            if response.status_code != 200:
                logger.warning("Synesthesia decoding API error %d", response.status_code)
                return None

            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            result = _json.loads(content)

            tokens: list[str] = []
            if isinstance(result, list):
                tokens = [str(t) for t in result[:5]]
            elif isinstance(result, dict):
                for v in result.values():
                    if isinstance(v, list):
                        tokens = [str(t) for t in v[:5]]
                        break
            return [t for t in tokens if len(t) > 0 and len(t) < 30][:5] or None

    except Exception as e:
        logger.warning("Synesthesia decoding failed: %s", e)
        return None


async def _call_llm_emotion(text: str, api_key_override: str | None = None, base_url_override: str | None = None) -> dict[str, float] | None:
    """Call LLM API to classify emotion. Returns vector or None on failure."""
    api_key = api_key_override or settings.LLM_API_KEY
    if not api_key:
        return None
    base_url = base_url_override or settings.LLM_BASE_URL

    try:
        async with httpx.AsyncClient(timeout=LLM_EMOTION_TIMEOUT) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"用户描述：{text}"},
                    ],
                    "max_tokens": 200,
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"},
                },
            )
            if response.status_code != 200:
                logger.warning("LLM emotion API error %d: %s", response.status_code,
                               await response.aread())
                return None

            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            result = _json.loads(content)

            # Validate all 8 dimensions present
            vector = {dim: float(result.get(dim, 0)) for dim in DIMENSIONS}
            if all(v == 0 for v in vector.values()):
                return None  # All-zero rejected
            return vector

    except Exception as e:
        logger.warning("LLM emotion recognition failed: %s", e)
        return None


async def resolve_emotion_from_text(
    user_text: str,
    api_key_override: str | None = None,
    base_url_override: str | None = None,
) -> dict:
    """Classify emotion from free-text, with LLM → keyword → calm fallback chain.

    Also performs synesthesia decoding (FR-5.8) when the input contains
    abstract sensory descriptions.

    Returns:
        {
            "emotion_vector": dict[str, float],  # 8-D, not normalized
            "primary_emotion": str,               # Chinese label
            "confidence": float,
            "source": "llm_text" | "card_preset",
            "synesthesia_tokens": list[str],       # decoded note/accord terms
        }
    """
    # Layer 1: LLM classification
    vector = await _call_llm_emotion(
        user_text,
        api_key_override=api_key_override,
        base_url_override=base_url_override,
    )

    # Synesthesia detection (runs alongside emotion, not after)
    synesthesia_tokens: list[str] = []
    if _is_synesthetic(user_text):
        decoded = await _decode_synesthesia(
            user_text,
            api_key_override=api_key_override,
            base_url_override=base_url_override,
        )
        if decoded:
            synesthesia_tokens = decoded
            logger.debug("Synesthesia decoded: %s -> %s", user_text[:60], decoded)

    if vector is not None:
        primary_dim = max(DIMENSIONS, key=lambda d: vector[d])
        return {
            "emotion_vector": vector,
            "primary_emotion": EMOTION_LABELS[primary_dim],
            "confidence": vector[primary_dim],
            "source": "llm_text",
            "synesthesia_tokens": synesthesia_tokens,
        }

    # Layer 2: Keyword fallback
    vector = _keyword_fallback(user_text)
    if vector is not None:
        primary_dim = max(DIMENSIONS, key=lambda d: vector[d])
        return {
            "emotion_vector": vector,
            "primary_emotion": EMOTION_LABELS[primary_dim],
            "confidence": vector[primary_dim],
            "source": "card_preset",  # keyword fallback uses card vectors
            "synesthesia_tokens": synesthesia_tokens,
        }

    # Layer 3: Ultimate default
    default = dict(CARD_VECTORS["calm"])
    return {
        "emotion_vector": default,
        "primary_emotion": EMOTION_LABELS["calm"],
        "confidence": 0.5,
        "source": "card_preset",
        "synesthesia_tokens": synesthesia_tokens,
    }
