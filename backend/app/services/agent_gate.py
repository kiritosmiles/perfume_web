"""Agent Gate: Information Completeness Check (FR-5.11).

A hard-boundary decision node inserted before generation that evaluates whether
the current context is sufficient for a high-quality recommendation. If not,
it either supplements with tool calls (partial) or generates clarifying
questions for the user (insufficient).

Design: TRD §2.2 Call #8 — 500ms budget, 1 retry, degrade-to-sufficient on timeout.
"""

import json as _json
import logging
import time
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GATE_TIMEOUT = 0.5  # 500ms hard boundary
GATE_LLM_TIMEOUT = 0.2  # 200ms for LLM question generation (subset of 500ms)

# ── Rule-based thresholds ─────────────────────────────────────────────────────
MIN_GRAPHRAG_CANDIDATES = 5
MIN_GIFT_RECIPIENT_TAGS = 2  # recipient attributes needed for gift mode


def _rule_based_verdict(
    intent: str,
    has_emotion: bool,
    has_scene: bool,
    graphrag_count: int,
    has_user_text: bool,
    user_text_length: int = 0,
    refine_count: int = 0,
    has_gate_answer: bool = False,
) -> str:
    """Fast rule-based verdict (<1ms). Returns 'sufficient' | 'partial' | 'insufficient'.

    Gate is skipped entirely (returns 'sufficient') when:
    - refine_count > 0 (user already iterating — don't interrupt)
    - has_gate_answer (user already answered gate questions)
    """
    # Don't interrupt refinement or already-answered sessions
    if refine_count > 0 or has_gate_answer:
        return "sufficient"

    # explore intent allows sparse information
    if intent == "explore":
        return "sufficient"

    # self_use: emotion + (scene or substantive text) is sufficient
    if intent == "self_use":
        if has_emotion and (has_scene or (has_user_text and user_text_length >= 10)):
            return "sufficient" if graphrag_count >= MIN_GRAPHRAG_CANDIDATES else "partial"
        if has_emotion:
            return "partial"
        return "insufficient"

    # gift: needs recipient context
    if intent == "gift":
        if has_emotion and has_scene and graphrag_count >= MIN_GRAPHRAG_CANDIDATES:
            return "sufficient"
        if has_emotion and has_scene:
            return "partial"
        return "insufficient"

    return "sufficient"


async def _generate_questions_via_llm(
    intent: str,
    emotion_cn: str,
    user_text: str | None,
    api_key_override: str | None = None,
    base_url_override: str | None = None,
) -> list[str] | None:
    """Generate ≤3 natural-language clarifying questions via LLM.

    Returns list of questions, or None on failure/timeout.
    """
    api_key = api_key_override or settings.LLM_API_KEY
    if not api_key:
        return None
    base_url = base_url_override or settings.LLM_BASE_URL

    context_line = f"用户说了：{user_text}" if user_text else "用户选择了情绪卡片"
    system_prompt = (
        "你是一个温和的香水顾问。用户的信息不够完整，你需要提出 1-3 个问题来了解TA的需求。\n"
        "要求：\n"
        "- 问题简短（每问 ≤ 20 字）\n"
        "- 对话式语气，自然温和\n"
        "- 不涉及任何个人隐私信息（PII）\n"
        "- 不要问年龄、收入、住址、真实姓名\n"
        f"- 意图类型：{intent}（self_use=为自己选，gift=为他人选礼物，explore=随便逛逛）\n"
        "请以 JSON 数组格式输出，不要其他内容。\n"
        '示例: ["日常上班用还是特殊场合？","之前用过哪些让你印象深刻的香水？"]'
    )

    try:
        async with httpx.AsyncClient(timeout=GATE_LLM_TIMEOUT) as client:
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
                        {"role": "user", "content": context_line},
                    ],
                    "max_tokens": 120,
                    "temperature": 0.7,
                    "response_format": {"type": "json_object"},
                },
            )
            if response.status_code != 200:
                logger.warning("Agent Gate LLM error %d", response.status_code)
                return None

            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            # Handle both array and object responses
            result = _json.loads(content)
            if isinstance(result, list):
                questions = [str(q) for q in result[:3]]
            elif isinstance(result, dict):
                questions = [
                    str(v) for v in list(result.values())[:3]
                    if isinstance(v, str)
                ]
            else:
                return None
            return questions[:3] if questions else None

    except Exception as e:
        logger.warning("Agent Gate LLM question generation failed: %s", e)
        return None


def _fallback_questions(intent: str, emotion_cn: str) -> list[str]:
    """Hardcoded fallback questions when LLM is unavailable."""
    if intent == "gift":
        return [
            f"TA平时喜欢什么风格的香水？",
            "收礼人的年龄范围大概是？",
            "TA之前用过让你印象深刻的香水吗？",
        ]
    # self_use
    return [
        "你平时偏好清新还是温暖的风格？",
        "这次选香水是日常用还是特别场合？",
    ]


async def agent_gate_check(
    intent: str,
    emotion_cn: str,
    has_scene: bool,
    graphrag_candidates: int = 0,
    user_text: str | None = None,
    refine_count: int = 0,
    gate_answer: str | None = None,
    api_key_override: str | None = None,
    base_url_override: str | None = None,
) -> dict[str, Any]:
    """Evaluate information completeness and decide whether to gate.

    Args:
        intent: "self_use" | "gift" | "explore"
        emotion_cn: Primary emotion in Chinese (e.g. "喜悦")
        has_scene: Whether user provided a scene tag
        graphrag_candidates: Number of GraphRAG candidate perfumes found
        user_text: Raw user free-text input
        refine_count: Current refinement iteration (0 = first pass)
        gate_answer: User's answer to previous gate questions (if any)
        api_key_override: User-provided LLM API key
        base_url_override: User-provided LLM base URL

    Returns:
        {"verdict": "sufficient"|"partial"|"insufficient",
         "latency_ms": float,
         "bypassed": bool,
         "questions": list[str] | None,
         "hint": str | None}
    """
    t0 = time.perf_counter()

    has_emotion = bool(emotion_cn)
    has_user_text = bool(user_text and user_text.strip())
    user_text_length = len(user_text.strip()) if user_text else 0

    # Fast path: rule-based verdict (<1ms)
    verdict = _rule_based_verdict(
        intent=intent,
        has_emotion=has_emotion,
        has_scene=has_scene,
        graphrag_count=graphrag_candidates,
        has_user_text=has_user_text,
        user_text_length=user_text_length,
        refine_count=refine_count,
        has_gate_answer=bool(gate_answer),
    )

    latency_ms = (time.perf_counter() - t0) * 1000

    if verdict == "sufficient":
        return {
            "verdict": "sufficient",
            "latency_ms": round(latency_ms, 1),
            "bypassed": True,
            "questions": None,
            "hint": None,
        }

    if verdict == "partial":
        return {
            "verdict": "partial",
            "latency_ms": round(latency_ms, 1),
            "bypassed": False,
            "questions": None,
            "hint": None,
            "message": "正在查找相关信息...",
        }

    # insufficient — generate questions (with remaining time budget)
    questions = None
    try:
        questions = await _generate_questions_via_llm(
            intent=intent,
            emotion_cn=emotion_cn,
            user_text=user_text,
            api_key_override=api_key_override,
            base_url_override=base_url_override,
        )
    except Exception:
        logger.warning("Agent Gate question generation failed, using fallback", exc_info=True)

    if not questions:
        questions = _fallback_questions(intent, emotion_cn)

    total_latency = (time.perf_counter() - t0) * 1000
    return {
        "verdict": "insufficient",
        "latency_ms": round(total_latency, 1),
        "bypassed": False,
        "questions": questions[:3],
        "hint": "你可以回答这些问题，或直接说「先推荐看看」",
    }
