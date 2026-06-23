"""Rule engine for recommendation refinement (FR-3.7 — Round 1).

Maps user refinement keywords (e.g. "sweeter", "fresher") to emotion vector
adjustments. The adjusted vector is re-normalized to [0,1] and fed back into
the GraphRAG query as a new SSE session with the `refine` param.
"""

REFINEMENT_RULES: dict[str, dict[str, float]] = {
    # ── 甜度 (Sweetness) ─────────────────────────
    "sweeter":       {"joy": 0.15, "romance": 0.10},
    "less_sweet":    {"joy": -0.10, "romance": -0.05},

    # ── 浓度 (Intensity) ─────────────────────────
    "lighter":       {"excitement": -0.10, "anxiety": -0.05},
    "stronger":      {"excitement": 0.10, "nostalgia": 0.10},

    # ── 清新度 (Freshness) ───────────────────────
    "fresher":       {"calm": 0.15, "joy": 0.05, "melancholy": -0.10},

    # ── 性别倾向 (Gender) ────────────────────────
    "more_masculine": {"melancholy": 0.10, "calm": 0.05, "romance": -0.10},
    "more_feminine":  {"romance": 0.10, "joy": 0.05, "melancholy": -0.05},

    # ── 温暖度 (Warmth) ──────────────────────────
    "warmer":        {"nostalgia": 0.15, "calm": -0.05},
    "cooler":        {"calm": 0.10, "nostalgia": -0.05},

    # ── 香调切换 (Accord shift) ──────────────────
    "more_floral":    {"romance": 0.15, "joy": 0.10},
    "more_woody":     {"calm": 0.10, "melancholy": 0.10, "romance": -0.05},
    "more_citrus":    {"joy": 0.15, "excitement": 0.10, "melancholy": -0.05},
    "more_oriental":  {"nostalgia": 0.15, "romance": 0.05, "calm": -0.05},

    # ── 年龄 (Age) ───────────────────────────────
    "younger":       {"excitement": 0.10, "joy": 0.10, "melancholy": -0.05},
    "mature":        {"calm": 0.10, "nostalgia": 0.10, "excitement": -0.05},

    # ── 场合/季节 (Scene/Season) ──────────────────
    "office_friendly": {"calm": 0.10, "excitement": -0.05},
    "date_night":      {"romance": 0.15, "excitement": 0.05},
    "summer":          {"joy": 0.10, "calm": 0.10, "nostalgia": -0.05},
    "winter":          {"nostalgia": 0.10, "melancholy": 0.05, "joy": -0.05},
}

DIMENSION_NAMES = [
    "joy", "sadness", "anxiety", "calm",
    "excitement", "nostalgia", "romance", "melancholy",
]


def apply_refinement(
    emotion_vector: dict[str, float],
    refine_keywords: list[str],
) -> dict[str, float]:
    """Apply refinement rules to an emotion vector. Clamp and re-normalize to [0,1].

    Args:
        emotion_vector: 8-D emotion vector (values in [0,1])
        refine_keywords: list of refinement keys (e.g. ["sweeter", "fresher"])

    Returns:
        Adjusted and re-normalized 8-D vector
    """
    adjusted = dict(emotion_vector)

    for kw in refine_keywords:
        kw_clean = kw.strip().lower().replace(" ", "_")
        if kw_clean in REFINEMENT_RULES:
            for dim, delta in REFINEMENT_RULES[kw_clean].items():
                if dim in adjusted:
                    adjusted[dim] = max(0.0, min(1.0, adjusted[dim] + delta))

    # Re-normalize so values sum to ~1.0 (preserving proportion)
    total = sum(adjusted.get(d, 0.0) for d in DIMENSION_NAMES)
    if total > 0:
        return {d: round(max(0.0, min(1.0, adjusted.get(d, 0.0) / total)), 4)
                for d in DIMENSION_NAMES}
    return {d: 0.125 for d in DIMENSION_NAMES}  # uniform fallback
