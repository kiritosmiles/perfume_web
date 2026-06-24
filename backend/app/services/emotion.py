from app.models.guest import GuestSessionInput

CARD_VECTORS: dict[str, dict[str, float]] = {
    "joy":       {"joy": 0.9, "excitement": 0.7, "calm": 0.2, "romance": 0.1, "sadness": 0.0, "anxiety": 0.0, "nostalgia": 0.0, "melancholy": 0.0},
    "sadness":   {"sadness": 0.9, "melancholy": 0.5, "nostalgia": 0.3, "calm": 0.1, "joy": 0.0, "anxiety": 0.0, "excitement": 0.0, "romance": 0.0},
    "anxiety":   {"anxiety": 0.9, "melancholy": 0.4, "sadness": 0.3, "calm": 0.1, "joy": 0.0, "excitement": 0.0, "nostalgia": 0.0, "romance": 0.0},
    "calm":      {"calm": 0.9, "nostalgia": 0.3, "joy": 0.2, "melancholy": 0.1, "sadness": 0.0, "anxiety": 0.0, "excitement": 0.0, "romance": 0.0},
    "excitement":{"excitement": 0.9, "joy": 0.8, "romance": 0.3, "calm": 0.0, "sadness": 0.0, "anxiety": 0.0, "nostalgia": 0.0, "melancholy": 0.0},
    "nostalgia": {"nostalgia": 0.9, "melancholy": 0.5, "calm": 0.4, "romance": 0.2, "joy": 0.0, "sadness": 0.0, "anxiety": 0.0, "excitement": 0.0},
    "romance":   {"romance": 0.9, "joy": 0.6, "excitement": 0.5, "nostalgia": 0.3, "sadness": 0.0, "anxiety": 0.0, "calm": 0.0, "melancholy": 0.0},
    "melancholy":{"melancholy": 0.9, "sadness": 0.6, "nostalgia": 0.4, "anxiety": 0.3, "joy": 0.0, "excitement": 0.0, "calm": 0.0, "romance": 0.0},
}

EMOTION_LABELS: dict[str, str] = {
    "joy": "开心", "sadness": "难过", "anxiety": "焦虑", "calm": "平静",
    "excitement": "兴奋", "nostalgia": "怀旧", "romance": "浪漫", "melancholy": "忧郁",
}

# Reverse mapping: Chinese label → English key
EMOTION_LABEL_TO_KEY: dict[str, str] = {v: k for k, v in EMOTION_LABELS.items()}

DIMENSIONS = ["joy", "sadness", "anxiety", "calm", "excitement", "nostalgia", "romance", "melancholy"]

# FR-2.5: Six value dimensions — 愉悦度/激活度/支配度/社交性/审美性/怀旧感
VALUE_DIMENSION_KEYS = ["pleasure", "activation", "dominance", "social", "aesthetic", "nostalgia"]
VALUE_DIMENSION_LABELS: dict[str, str] = {
    "pleasure": "愉悦度", "activation": "激活度", "dominance": "支配度",
    "social": "社交性", "aesthetic": "审美性", "nostalgia": "怀旧感",
}


def compute_value_dimensions(emotion_vector: dict[str, float]) -> dict[str, float]:
    """Map 8-dim emotion vector → 6-dim value dimensions (PRD FR-2.5).

    Deterministic mathematical mapping — no LLM required.
    All values clamped to [0, 1], rounded to 3 decimal places.
    """
    v = {d: float(emotion_vector.get(d, 0.0)) for d in DIMENSIONS}

    pleasure = max(0.0, min(1.0, (
        v["joy"] + v["excitement"] + v["romance"]
        - v["sadness"] - v["anxiety"] - v["melancholy"]
    ) / 3.0))

    activation = max(0.0, min(1.0, (
        v["excitement"] + v["anxiety"] - v["calm"] - v["melancholy"]
    ) / 2.0))

    dominance = max(0.0, min(1.0, (
        v["calm"] + v["joy"] + v["excitement"]
        - v["anxiety"] - v["sadness"] - v["melancholy"]
    ) / 3.0))

    social = max(0.0, min(1.0, (
        v["excitement"] + v["romance"] + v["joy"]
        - v["melancholy"] - v["sadness"]
    ) / 3.0))

    aesthetic = max(0.0, min(1.0, (
        v["romance"] + v["nostalgia"] + v["calm"] + v["joy"]
    ) / 2.0))

    nostalgia = max(0.0, min(1.0, (
        v["nostalgia"] + v["melancholy"] * 0.5 + v["calm"] * 0.3
    )))

    return {
        "pleasure": round(pleasure, 3),
        "activation": round(activation, 3),
        "dominance": round(dominance, 3),
        "social": round(social, 3),
        "aesthetic": round(aesthetic, 3),
        "nostalgia": round(nostalgia, 3),
    }


def resolve_emotion_from_cards(input_data: GuestSessionInput) -> dict:
    card_ids = input_data.emotion_card_ids
    if not card_ids:
        # Fallback to calm when no cards provided
        card_ids = ["calm"]
    vectors = [CARD_VECTORS[cid] for cid in card_ids]

    # Average vectors if multiple cards
    if len(vectors) == 1:
        merged = dict(vectors[0])
    else:
        merged = {}
        for dim in DIMENSIONS:
            merged[dim] = sum(v[dim] for v in vectors) / len(vectors)

    # Find primary emotion (max dimension)
    primary = max(DIMENSIONS, key=lambda d: merged[d])

    return {
        "emotion_vector": merged,
        "primary_emotion": EMOTION_LABELS[primary],
        "confidence": merged[primary],
        "source": "card_preset",
        "value_dimensions": compute_value_dimensions(merged),
    }
