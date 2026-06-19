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

DIMENSIONS = ["joy", "sadness", "anxiety", "calm", "excitement", "nostalgia", "romance", "melancholy"]


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
    }
