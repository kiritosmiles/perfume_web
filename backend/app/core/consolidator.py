"""Memory consolidation prompts + LLM calls for L1/L2/L3 + recall planner/gating."""

import json as _json
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)
_CONSOLIDATION_TIMEOUT = 8.0

# ── System Prompts ──────────────────────────────────────────────────────────────

L1_CONSOLIDATION_PROMPT = """你是一个记忆编码器。将用户对话转为第三人称事实摘要。
输入：本轮用户输入 + Agent 回复
规则：
1. 保留：香调名称、品牌、产品名、情绪状态、场景、偏好反馈（喜欢/讨厌/太甜/太浓）
2. 排除：问候语、确认词、纯功能词
3. 时间：保持原始相对时间（不说日期）
4. 格式：纯句子，单一自然段，中文
5. 不重复同会话历史片段中已有的事实
6. 特别标记：如果用户表达了明确的喜欢/不喜欢 → 以"[偏好]"开头
输出：单一自然段，中文。"""

L2_CONSOLIDATION_PROMPT = """你是一个会话记忆整合器。合并多个片段为无冗余的会话摘要。
输入：本轮会话的全部 L1 片段列表 + 最近 3 次历史 L2 摘要
规则：
1. 去重：同一事实只保留一次
2. 合并：相关联的事实合并为一个事件（如"用户查看了TF乌木"+"用户说TF乌木太浓"→"用户对TF乌木不满意，认为过于浓郁"）
3. 偏好稳定性：标记反复出现的偏好（同一香调被提及≥2次 → 标注[稳定偏好]）
4. 情绪轨迹：概述会话内情绪变化（开始→结束）
5. 格式：2-4 个自然段，中文，按主题分组"""

L3_CONSOLIDATION_PROMPT = """你是一个日级记忆整合器。从一天的交互中提取偏好模式。
输入：当日所有 L2 摘要 + 最近 7 天 L3 摘要
规则：
1. 模式识别：识别重复≥2天的行为模式 → 标注[日级模式]
2. 新鲜度标记：首次出现的新偏好 → 标注[新发现]
3. 季节性：识别与季节相关的偏好变化
4. 关键词提取：输出 3-8 个核心偏好关键词（香调、品牌、场景）
5. 格式：2-3 个自然段 + JSON 关键词列表，中文
输出格式：JSON {"text": "摘要文本...", "keywords": ["关键词1", ...]}"""

RECALL_PLANNER_PROMPT = """判断用户查询的复杂度，输出标签和关键词。
输入：用户原始文字 + 情绪识别结果
复杂度判断规则：
- 需要回忆历史偏好/习惯/性格 → complex
- 需要总结多个历史事实 → hybrid
- 简单事实询问 → simple
输出格式：JSON { "complexity": "simple"|"hybrid"|"complex", "keywords": [...] }"""

RECALL_GATE_PROMPT = """你是一个记忆门控器。过滤与当前查询不相关或冗余的记忆。
输入：候选记忆列表 + 用户查询 + 复杂度标签
规则：
- simple: 激进过滤（仅直接相关，3-8 条）
- hybrid: 适度过滤（允许 1 度间接相关，8-15 条）
- complex: 宽松保留（广泛上下文，15-25 条）
输出：JSON { "kept": [...], "rejected_reason": "简述为何过滤" }"""


# ── Shared LLM helper ───────────────────────────────────────────────────────────

async def _call_llm(system_prompt: str, user_msg: str, expect_json: bool = False) -> str | dict | None:
    api_key = settings.LLM_API_KEY
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=_CONSOLIDATION_TIMEOUT) as client:
            body = {
                "model": settings.LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                "max_tokens": 512,
                "temperature": 0.3,
            }
            if expect_json:
                body["response_format"] = {"type": "json_object"}
            resp = await client.post(
                f"{settings.LLM_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=body,
            )
            if resp.status_code != 200:
                logger.warning("LLM consolidation error %d", resp.status_code)
                return None
            content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            return _json.loads(content) if expect_json else content.strip()
    except Exception as e:
        logger.warning("LLM consolidation failed: %s", e)
        return None


# ── Consolidation calls ─────────────────────────────────────────────────────────

async def consolidate_l1(user_input: str, agent_reply: str, history_facts: list[str]) -> str | None:
    hist = "\n".join(f"- {f}" for f in history_facts[-10:]) if history_facts else "（无历史）"
    return await _call_llm(L1_CONSOLIDATION_PROMPT,
        f"## 本轮对话\n用户：{user_input}\n系统：{agent_reply}\n\n## 历史事实（不要重复）\n{hist}")


async def consolidate_l2(l1_fragments: list[str], recent_l2: list[str]) -> str | None:
    l1t = "\n".join(f"{i+1}. {f}" for i, f in enumerate(l1_fragments))
    l2t = "\n".join(f"- {s}" for s in recent_l2) if recent_l2 else "（无历史摘要）"
    return await _call_llm(L2_CONSOLIDATION_PROMPT,
        f"## 当前会话片段列表\n{l1t}\n\n## 最近历史会话摘要\n{l2t}")


async def consolidate_l3(l2_summaries: list[str], recent_l3: list[str]) -> dict | None:
    l2t = "\n".join(f"- {s}" for s in l2_summaries)
    l3t = "\n".join(f"- {s}" for s in recent_l3) if recent_l3 else "（无历史日级摘要）"
    return await _call_llm(L3_CONSOLIDATION_PROMPT,
        f"## 当日会话摘要\n{l2t}\n\n## 最近 7 天日级摘要\n{l3t}", expect_json=True)


# ── Recall planner & gate ───────────────────────────────────────────────────────

async def call_llm_planner(user_text: str, emotion_result: dict) -> dict | None:
    msg = f"用户查询：{user_text}\n情绪：{emotion_result.get('primary_emotion', '')}"
    return await _call_llm(RECALL_PLANNER_PROMPT, msg, expect_json=True)


async def call_llm_gate(candidates: list[dict], query: str, complexity: str) -> dict | None:
    cand_text = _json.dumps(candidates, ensure_ascii=False, default=str)
    msg = f"候选记忆：{cand_text}\n用户查询：{query}\n复杂度：{complexity}"
    return await _call_llm(RECALL_GATE_PROMPT, msg, expect_json=True)
