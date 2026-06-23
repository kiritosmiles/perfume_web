"""Emotion Journal service (FR-4.9).

Provides emotion trend data and weekly journal generation from L3 daily
memory summaries. LLM is used for weekly narratives with template fallback
when unavailable.
"""

import json as _json
import logging
from datetime import date, timedelta

import httpx

from app.core.config import settings
from app.core.pg import get_pg_pool

logger = logging.getLogger(__name__)

JOURNAL_LLM_TIMEOUT = 5.0  # seconds

# ── Emotion keyword matching (for extracting primary emotion from L3 text) ────

_EMOTION_KEYWORDS: dict[str, list[str]] = {
    "joy":         ["开心", "高兴", "快乐", "喜悦", "愉悦", "欢快", "欢喜"],
    "sadness":     ["难过", "伤心", "悲伤", "低落", "沮丧", "哭泣", "哀伤"],
    "anxiety":     ["焦虑", "紧张", "不安", "担心", "害怕", "忐忑", "烦躁"],
    "calm":        ["平静", "放松", "宁静", "安静", "舒适", "平和", "淡然", "安详"],
    "excitement":  ["兴奋", "激动", "期待", "惊喜", "刺激", "雀跃", "亢奋"],
    "nostalgia":   ["怀旧", "回忆", "怀念", "思念", "想起", "追忆", "缅想"],
    "romance":     ["浪漫", "温柔", "甜蜜", "恋爱", "心动", "暧昧", "旖旎"],
    "melancholy":  ["忧郁", "伤感", "惆怅", "寂寞", "孤独", "愁绪", "怅然"],
}

WEEKLY_JOURNAL_PROMPT = """你是一个温暖的情绪日记助手。根据用户一周的情绪数据生成一段 3-5 句话的中文周记。

规则：
1. 语气温暖、平实，像朋友聊天
2. 描述情绪变化轨迹（从周初到周末）
3. 如果有明显的关键词/偏好，轻轻提及
4. 结尾给一句积极的鼓励或观察
5. 不要使用 markdown，纯文本段落

输出：纯文本段落（不要 JSON）。"""


def _extract_emotion_from_text(text: str) -> dict[str, float]:
    """Extract emotion scores from L3 summary text using keyword matching."""
    scores: dict[str, float] = {}
    for emotion, keywords in _EMOTION_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in text)
        if hits > 0:
            scores[emotion] = min(hits / 3.0, 1.0)  # normalize to 0-1
    return scores


def _primary_emotion(emotion_scores: dict[str, float]) -> str | None:
    """Return the emotion dimension with the highest score."""
    if not emotion_scores:
        return None
    return max(emotion_scores, key=emotion_scores.get)


async def get_emotion_trend(
    user_id: str,
    days: int = 30,
) -> list[dict]:
    """Fetch daily emotion data from memory_l3 for the last N days.

    Returns list of {date, primary_emotion, emotion_scores, keywords, summary_text}
    ordered by date ascending.
    """
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT date, text, preference_keywords, emotion_summary
               FROM memory_l3
               WHERE user_id = $1::uuid AND date >= $2::date
               ORDER BY date ASC""",
            user_id, date.today() - timedelta(days=days),
        )

    result: list[dict] = []
    for row in rows:
        text = row["text"] or ""
        # Prefer stored emotion_summary if populated, else derive from text
        stored = row["emotion_summary"]
        if isinstance(stored, str):
            try:
                stored = _json.loads(stored)
            except Exception:
                stored = {}
        if stored and isinstance(stored, dict) and len(stored) > 0:
            emotion_scores = {k: float(v) for k, v in stored.items()}
        else:
            emotion_scores = _extract_emotion_from_text(text)

        keywords = row["preference_keywords"] or []
        if isinstance(keywords, str):
            try:
                keywords = _json.loads(keywords)
            except Exception:
                keywords = []

        result.append({
            "date": row["date"].isoformat() if hasattr(row["date"], "isoformat") else str(row["date"]),
            "primary_emotion": _primary_emotion(emotion_scores),
            "emotion_scores": emotion_scores,
            "keywords": keywords[:8],
            "summary_text": text[:200],
        })

    return result


async def get_weekly_journal(
    user_id: str,
    week_start: str | None = None,
) -> dict:
    """Generate a weekly journal from L3 daily data.

    Args:
        user_id: The authenticated user's UUID.
        week_start: ISO date string (YYYY-MM-DD) for Monday of the target week.
                    If omitted, defaults to the most recent completed week (last Monday).

    Returns:
        {
            week_start, week_end,
            this_week: {primary_emotion, emotion_vector, top_keywords, session_count, days},
            last_week: {primary_emotion, emotion_vector, top_keywords, session_count, days} | null,
            narrative: str,
            explored_accords: [...]
        }
    """
    # Determine week boundaries
    if week_start:
        monday = date.fromisoformat(week_start)
    else:
        today = date.today()
        # Last Monday (most recent completed week starts on Monday)
        monday = today - timedelta(days=today.weekday() + 7)

    sunday = monday + timedelta(days=6)
    prev_monday = monday - timedelta(days=7)
    prev_sunday = monday - timedelta(days=1)

    pool = await get_pg_pool()
    async with pool.acquire() as conn:

        async def _fetch_week(start: date, end: date) -> dict | None:
            rows = await conn.fetch(
                """SELECT date, text, preference_keywords, emotion_summary
                   FROM memory_l3
                   WHERE user_id = $1::uuid AND date >= $2::date AND date <= $3::date
                   ORDER BY date ASC""",
                user_id, start, end,
            )
            if not rows:
                return None

            all_keywords: list[str] = []
            all_emotion: dict[str, float] = {}
            days_data: list[dict] = []

            for row in rows:
                text = row["text"] or ""
                stored = row["emotion_summary"]
                if isinstance(stored, str):
                    try:
                        stored = _json.loads(stored)
                    except Exception:
                        stored = {}
                if stored and isinstance(stored, dict) and len(stored) > 0:
                    scores = {k: float(v) for k, v in stored.items()}
                else:
                    scores = _extract_emotion_from_text(text)

                for dim, val in scores.items():
                    all_emotion[dim] = all_emotion.get(dim, 0) + val

                kw = row["preference_keywords"] or []
                if isinstance(kw, str):
                    try:
                        kw = _json.loads(kw)
                    except Exception:
                        kw = []
                all_keywords.extend(kw)

                days_data.append({
                    "date": row["date"].isoformat() if hasattr(row["date"], "isoformat") else str(row["date"]),
                    "primary_emotion": _primary_emotion(scores),
                })

            # Normalize emotion vector
            total = sum(all_emotion.values()) or 1
            emotion_vector = {k: round(v / total, 2) for k, v in all_emotion.items()}

            # Top keywords by frequency
            kw_freq: dict[str, int] = {}
            for k in all_keywords:
                kw_freq[k] = kw_freq.get(k, 0) + 1
            top_keywords = sorted(kw_freq, key=kw_freq.get, reverse=True)[:8]  # noqa: F841

            return {
                "primary_emotion": _primary_emotion(emotion_vector),
                "emotion_vector": emotion_vector,
                "top_keywords": top_keywords,
                "session_count": len(rows),
                "days": days_data,
            }

        this_week = await _fetch_week(monday, sunday)
        last_week = await _fetch_week(prev_monday, prev_sunday)

    # ── Generate LLM narrative ──────────────────────────────────────────
    narrative = await _generate_weekly_narrative(this_week, last_week)

    return {
        "week_start": monday.isoformat(),
        "week_end": sunday.isoformat(),
        "this_week": this_week,
        "last_week": last_week,
        "narrative": narrative,
    }


async def _generate_weekly_narrative(
    this_week: dict | None,
    last_week: dict | None,
) -> str:
    """Generate a weekly narrative via LLM, with template fallback."""
    if not this_week:
        return "本周暂无情绪记录。多使用几次推荐，AI 会更好地了解你的情绪轨迹。"

    # Build context for LLM
    days_desc = ""
    if this_week.get("days"):
        days_desc = " → ".join(
            f"{d['date'][-5:]}({d.get('primary_emotion', '?')})"
            for d in this_week["days"]
        )

    keywords_str = ", ".join(this_week.get("top_keywords", [])) or "无特别偏好"
    primary = this_week.get("primary_emotion", "未知")

    user_msg = (
        f"本周 ({days_desc})\n"
        f"主要情绪倾向: {primary}\n"
        f"偏好关键词: {keywords_str}\n"
        f"活跃天数: {this_week.get('session_count', 0)}"
    )
    if last_week:
        last_primary = last_week.get("primary_emotion", "未知")
        user_msg += f"\n上周主要情绪: {last_primary}"

    api_key = settings.LLM_API_KEY
    if not api_key:
        return _fallback_narrative(this_week)

    try:
        async with httpx.AsyncClient(timeout=JOURNAL_LLM_TIMEOUT) as client:
            resp = await client.post(
                f"{settings.LLM_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": WEEKLY_JOURNAL_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                    "max_tokens": 256,
                    "temperature": 0.7,
                },
            )
            if resp.status_code != 200:
                logger.warning("Journal LLM error %d", resp.status_code)
                return _fallback_narrative(this_week)
            content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            if content and content.strip():
                return content.strip()
    except Exception as e:
        logger.warning("Journal LLM call failed: %s", e)

    return _fallback_narrative(this_week)


def _fallback_narrative(this_week: dict | None) -> str:
    """Template-based weekly narrative when LLM is unavailable."""
    if not this_week:
        return "本周暂无情绪记录。多使用几次推荐，AI 会更好地了解你的情绪轨迹。"

    primary = this_week.get("primary_emotion", "")
    session_count = this_week.get("session_count", 0)
    keywords = this_week.get("top_keywords", [])

    emotion_label = {
        "joy": "喜悦", "sadness": "淡淡的忧伤", "anxiety": "些许焦虑",
        "calm": "平静", "excitement": "兴奋", "nostalgia": "怀旧",
        "romance": "浪漫", "melancholy": "一丝忧郁",
    }.get(primary, primary)

    lines = [
        f"这周的你，整体情绪偏向{emotion_label}。",
        f"本周共产生了 {session_count} 次日记，记录了你的闻香之旅。",
    ]
    if keywords:
        lines.append(f"你似乎对 {', '.join(keywords[:3])} 特别感兴趣。")

    lines.append("每一种情绪都值得被铭记，下周继续探索属于你的香气吧 🌿")
    return "".join(lines)
