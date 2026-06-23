"""LLM streaming copy generation — OpenAI-compatible API (DeepSeek, Claude, etc.).

Design: TRD §2.2 Call #4 (Fast-mode LLM generation).
Falls back to STORY_TEMPLATES if API key is not configured or on error.
"""

import logging
from typing import AsyncGenerator

import httpx

from app.core.config import settings
from app.services.generation import build_copy_stream

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_SELF = """你是一位香水文学作家，擅长用诗意的中文描述香水。
根据给定的香水信息，生成 4 句话的香评，每句对应一个调性层次：

第 1 句：整体印象 — 用一句话勾勒香水的性格和气质
第 2 句：前调 — 描述最初闻到的明亮、轻盈的气息
第 3 句：中调 — 描述香水展开后的温暖、丰富的核心
第 4 句：尾韵 — 描述香水沉淀后的悠长余韵和情感共鸣

要求：
- 每句话 15-30 字
- 语言温暖、有画面感、避免华丽堆砌
- 风格参考：{emotion}情绪下的香水叙事
- 用"你"称呼读者

请严格按照 4 行输出，每行一句话，不要编号，不要其他内容。"""

SYSTEM_PROMPT_GIFT = """你是一位香水文学作家，擅长用诗意的中文描述香水。
这是一瓶作为礼物送出的香水。根据给定的香水信息，生成 4 句礼物叙事，每句对应一个调性层次：

第 1 句：整体印象 — 用一句话勾勒这瓶香水的性格，融入送礼的心意
第 2 句：前调 — 描述最初闻到的明亮气息，像是拆开礼物时的第一刻惊喜
第 3 句：中调 — 描述香水展开后的温暖核心，象征送礼人与收礼人之间的情感联结
第 4 句：尾韵 — 描述香水沉淀后的余韵，表达对TA的美好祝福与期许

要求：
- 每句话 15-30 字
- 温暖、深情、有仪式感，融入送礼场景
- 风格参考：{emotion}情绪下的礼物叙事
- 用"TA"称呼收礼人

请严格按照 4 行输出，每行一句话，不要编号，不要其他内容。"""

SYSTEM_PROMPT_EXPLORE = """你是一位香水文学作家，擅长用诗意的中文描述香水。
用户正在探索不同的香调风格。根据给定的香水信息，生成 4 句探索性香评，每句对应一个调性层次：

第 1 句：整体印象 — 用一句话点出这瓶香水最独特的性格标识
第 2 句：前调 — 描述最初闻到的气息，像翻开一本新书的第一页
第 3 句：中调 — 描述香水展开后的层次变化，突出它在同类香调中的辨识度
第 4 句：尾韵 — 描述香水沉淀后的余韵，邀请用户想象穿上它的场景

要求：
- 每句话 15-30 字
- 好奇、发现、邀请探索的语气，避免主观推荐
- 风格参考：{emotion}情绪下的香调探索
- 用"你"称呼读者，但不预设用户是否喜欢

请严格按照 4 行输出，每行一句话，不要编号，不要其他内容。"""

_INTENT_PROMPTS = {
    "self_use": SYSTEM_PROMPT_SELF,
    "gift": SYSTEM_PROMPT_GIFT,
    "explore": SYSTEM_PROMPT_EXPLORE,
}


async def _stream_llm_copy(
    perfume_name: str,
    brand: str,
    emotion_cn: str,
    notes: list[str],
    intent: str = "self_use",
    api_key_override: str | None = None,
    base_url_override: str | None = None,
) -> AsyncGenerator[str, None]:
    """Call LLM API and yield sentence-level chunks."""
    api_key = api_key_override or settings.LLM_API_KEY
    if not api_key:
        return  # Caller should fall back to templates
    base_url = base_url_override or settings.LLM_BASE_URL

    system_prompt = _INTENT_PROMPTS.get(intent, SYSTEM_PROMPT_SELF).format(emotion=emotion_cn)
    user_prompt = f"香水：{perfume_name}\n品牌：{brand}\n情绪：{emotion_cn}\n香调：{', '.join(notes[:4])}"

    try:
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
            async with client.stream(
                "POST",
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 256,
                    "temperature": 0.8,
                    "stream": True,
                },
            ) as response:
                if response.status_code != 200:
                    logger.warning("LLM API error %d: %s", response.status_code,
                                   await response.aread())
                    return

                buffer = ""
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break

                    import json as _json
                    try:
                        chunk = _json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                    except Exception:
                        continue

                    if not content:
                        continue

                    buffer += content
                    # Yield complete sentences
                    while True:
                        sent_end = _find_sentence_end(buffer)
                        if sent_end == -1:
                            break
                        sentence = buffer[:sent_end + 1].strip()
                        buffer = buffer[sent_end + 1:]
                        if sentence:
                            yield sentence

                # Yield remaining buffer (final partial sentence)
                if buffer.strip():
                    yield buffer.strip()

    except Exception as e:
        logger.warning("LLM streaming failed: %s", e)
        return


def _find_sentence_end(text: str) -> int:
    """Return index of first sentence terminator, or -1."""
    for i, ch in enumerate(text):
        if ch in "。！？\n":
            return i
    return -1


async def generate_copy_for_perfume(
    rank: int,
    generation_id: str,
    perfume_name: str,
    brand: str,
    emotion_cn: str,
    notes: dict[str, list[str]] | list[str],
    intent: str = "self_use",
    api_key_override: str | None = None,
    base_url_override: str | None = None,
) -> AsyncGenerator[tuple[str, bool], None]:
    """Yield (chunk_text, is_final) for a single perfume card.

    Tries LLM first (with intent-aware prompt); falls back to template if
    no API key or on error.
    """
    # Normalize notes to flat list for LLM prompt
    if isinstance(notes, dict):
        notes_flat = notes.get("top", []) + notes.get("middle", []) + notes.get("base", [])
    else:
        notes_flat = notes

    chunks_yielded = 0

    async for chunk in _stream_llm_copy(
        perfume_name, brand, emotion_cn, notes_flat,
        intent=intent,
        api_key_override=api_key_override,
        base_url_override=base_url_override,
    ):
        chunks_yielded += 1
        yield chunk, False  # is_final determined by caller

    if chunks_yielded == 0:
        # LLM unavailable — fall back to template (also intent-aware)
        template_chunks = build_copy_stream(rank, generation_id, emotion_cn, intent=intent)
        for i, chunk in enumerate(template_chunks):
            yield chunk, (i == len(template_chunks) - 1)
    else:
        # Signal that all LLM chunks are done; caller marks last as final
        pass
