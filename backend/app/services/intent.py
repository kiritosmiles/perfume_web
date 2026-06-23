"""Intent detection from free-text input.

Classifies user intent as self_use / gift / explore via keyword matching
with LLM fallback on keyword miss. Mirrors the pattern in llm_emotion.py.
"""

import json as _json
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

INTENT_TIMEOUT = 2.5  # seconds — sub-timeout for intent classification

# ── Intent keywords ──────────────────────────────────────────────────────────
# Higher-priority keywords sorted first; first match wins per intent.

INTENT_KEYWORDS: list[tuple[str, str]] = [
    # gift — strongest signals
    ("送给", "gift"),
    ("送礼", "gift"),
    ("礼物", "gift"),
    ("给朋友", "gift"),
    ("给男朋友", "gift"),
    ("给女朋友", "gift"),
    ("给对象", "gift"),
    ("给妈妈", "gift"),
    ("给爸爸", "gift"),
    ("给老公", "gift"),
    ("给老婆", "gift"),
    ("给同事", "gift"),
    ("送TA", "gift"),
    ("帮别人", "gift"),
    ("帮朋友", "gift"),
    ("for someone", "gift"),
    ("for him", "gift"),
    ("for her", "gift"),
    ("gift", "gift"),
    # self_use
    ("给自己", "self_use"),
    ("自己用", "self_use"),
    ("我自用", "self_use"),
    ("自用", "self_use"),
    ("自己买", "self_use"),
    ("推荐给我", "self_use"),
    ("适合我", "self_use"),
    ("for myself", "self_use"),
    ("for me", "self_use"),
    # explore
    ("逛逛", "explore"),
    ("随便看看", "explore"),
    ("看看", "explore"),
    ("了解", "explore"),
    ("探索", "explore"),
    ("有什么", "explore"),
    ("browse", "explore"),
    ("explore", "explore"),
]


def _keyword_detect(text: str) -> dict | None:
    """Detect intent via keyword matching. Returns {intent, confidence, source} or None."""
    text_lower = text.lower()
    for keyword, intent in INTENT_KEYWORDS:
        if keyword.lower() in text_lower:
            return {"intent": intent, "confidence": 1.0, "source": "keyword"}
    return None


async def _call_llm_intent(
    text: str,
    api_key_override: str | None = None,
    base_url_override: str | None = None,
) -> dict | None:
    """Call LLM to classify intent. Returns {intent, confidence, source} or None."""
    api_key = api_key_override or settings.LLM_API_KEY
    if not api_key:
        return None
    base_url = base_url_override or settings.LLM_BASE_URL

    system_prompt = (
        "你是一个用户意图分类器。根据用户描述，判断TA是想：\n"
        "1. self_use — 为自己挑选香水\n"
        "2. gift — 为他人挑选礼物\n"
        "3. explore — 随便逛逛、了解香水\n\n"
        "请以 JSON 格式输出，不要其他内容。"
        '示例: {"intent":"self_use","confidence":0.85}'
    )

    try:
        async with httpx.AsyncClient(timeout=INTENT_TIMEOUT) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"用户描述：{text}"},
                    ],
                    "max_tokens": 80,
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
            )
            if response.status_code != 200:
                logger.warning("LLM intent API error %d", response.status_code)
                return None

            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            result = _json.loads(content)
            intent = result.get("intent", "self_use")
            if intent not in ("self_use", "gift", "explore"):
                intent = "self_use"
            confidence = float(result.get("confidence", 0.7))
            return {"intent": intent, "confidence": min(confidence, 1.0), "source": "llm"}

    except Exception as e:
        logger.warning("LLM intent detection failed: %s", e)
        return None


async def detect_intent(
    user_text: str | None,
    user_toggle: str = "self_use",
    api_key_override: str | None = None,
    base_url_override: str | None = None,
) -> dict:
    """Detect intent from user_text or user_toggle.

    Resolution order:
      1. User toggle (always authoritative if explicitly provided and not default)
      2. Keyword match on user_text (<1ms)
      3. LLM classification (~800ms)
      4. Default: "self_use"

    Returns:
        {"intent": "self_use"|"gift"|"explore", "confidence": float, "source": str}
    """
    # If user explicitly toggled to non-default intent, trust it
    if user_toggle != "self_use":
        return {"intent": user_toggle, "confidence": 1.0, "source": "user_toggle"}

    if not user_text or not user_text.strip():
        return {"intent": "self_use", "confidence": 1.0, "source": "default"}

    # Layer 1: keyword
    kw_result = _keyword_detect(user_text)
    if kw_result:
        return kw_result

    # Layer 2: LLM
    llm_result = await _call_llm_intent(
        user_text,
        api_key_override=api_key_override,
        base_url_override=base_url_override,
    )
    if llm_result:
        return llm_result

    # Layer 3: default
    return {"intent": "self_use", "confidence": 0.5, "source": "default"}


def is_guest_intent_allowed(intent: str) -> bool:
    """Guest users are restricted to self_use only."""
    return intent == "self_use"
