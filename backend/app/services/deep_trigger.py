"""Deep mode trigger evaluation (Phase 4 optimization — FR-3.12 trigger tuning).

Rule-engine-based (non-LLM, <1ms) evaluation of the 5 trigger conditions
for deep mode. Returns a boolean indicator and reason string.

Per TRD §2.5: Supervisor is de-LLM-ified — all trigger conditions can be
mapped via a hardcoded policy matrix without LLM involvement.
"""

from typing import Any

# ── Trigger definitions ────────────────────────────────────────────────────────

TRIGGER_REFINEMENT_EXHAUSTED = "refinement_exhausted"
TRIGGER_CROSS_STYLE = "cross_style_jump"
TRIGGER_COMPLEX_GIFT = "complex_gift"
TRIGGER_EMOTION_SCENE_CONFLICT = "emotion_scene_conflict"
TRIGGER_USER_EXPLICIT = "user_explicit"

# Emotion-scene conflict pairs: emotion dimensions that clash with certain scenes
# e.g., anxiety + party = conflict (anxious → calm scent, party → bold scent)
EMOTION_SCENE_CONFLICTS: dict[str, set[str]] = {
    "anxiety": {"party", "date"},
    "sadness": {"party"},
    "melancholy": {"party", "work"},
}


def evaluate_deep_triggers(
    intent: str = "self_use",
    diversity: float = 0.0,
    refine_count: int = 0,
    emotion_vector: dict[str, float] | None = None,
    scene_tag: str | None = None,
    recipient_info: dict[str, Any] | None = None,
    user_requested_deep: bool = False,
) -> tuple[bool, str | None]:
    """Evaluate all 5 deep mode trigger conditions via deterministic rules.

    Returns (should_use_deep: bool, trigger_reason: str | None).

    Trigger conditions (TRD §2.5):
      1. refinement_exhausted: >= 3 refinement rounds still unsatisfied
      2. cross_style_jump: diversity >= 0.5 (cross-style exploration)
      3. complex_gift: gift intent + missing/contradictory recipient info
      4. emotion_scene_conflict: high-anxiety emotion + social scene
      5. user_explicit: user explicitly requests more options

    All conditions evaluated in < 1ms (pure Python dict lookups, no I/O).
    """
    if user_requested_deep:
        return True, TRIGGER_USER_EXPLICIT

    # 1) Refinement exhaustion
    if refine_count >= 3:
        return True, TRIGGER_REFINEMENT_EXHAUSTED

    # 2) Cross-style exploration (FR-3.8)
    if diversity >= 0.5:
        return True, TRIGGER_CROSS_STYLE

    # 3) Complex gift — recipient info contradictory or very sparse
    if intent == "gift":
        if recipient_info:
            has_age = bool(recipient_info.get("age_range"))
            has_relationship = bool(recipient_info.get("relationship"))
            has_gender = bool(recipient_info.get("gender_pref"))
            tag_count = sum([has_age, has_relationship, has_gender])
            if tag_count < 1:
                return True, TRIGGER_COMPLEX_GIFT
        else:
            # No recipient info at all for gift intent
            return True, TRIGGER_COMPLEX_GIFT

    # 4) Emotion-scene conflict
    if emotion_vector and scene_tag:
        primary = max(emotion_vector, key=emotion_vector.get)  # type: ignore[arg-type]
        if primary in EMOTION_SCENE_CONFLICTS:
            if scene_tag in EMOTION_SCENE_CONFLICTS[primary]:
                return True, TRIGGER_EMOTION_SCENE_CONFLICT

    return False, None


def get_deep_trigger_description(reason: str) -> str:
    """Return Chinese description for a trigger reason."""
    descriptions = {
        TRIGGER_REFINEMENT_EXHAUSTED: "连续3轮精炼仍不满意，需要换个角度重新推荐",
        TRIGGER_CROSS_STYLE: "跨风格探索，需要深度模式支持多角度推荐",
        TRIGGER_COMPLEX_GIFT: "送礼场景信息不足，需要深度模式综合分析",
        TRIGGER_EMOTION_SCENE_CONFLICT: "情绪与场景存在冲突，需要多角度平衡",
        TRIGGER_USER_EXPLICIT: "用户请求更多选择",
    }
    return descriptions.get(reason, reason)
