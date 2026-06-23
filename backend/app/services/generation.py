from app.services.emotion import EMOTION_LABEL_TO_KEY


STORY_TEMPLATES: dict[str, list[str]] = {
    "joy": [
        "这款香水如同阳光洒落的瞬间",
        "前调明亮活泼，像春日清晨的第一缕风",
        "中调绽放出温暖花香，仿佛笑容在心间荡漾",
        "尾韵柔和悠长，让幸福感久久停留",
    ],
    "sadness": [
        "这是一款懂得倾听的香氛",
        "微苦的前调轻轻包裹你的情绪",
        "中调渐渐舒展，如雨后的第一抹晴空",
        "温暖的尾韵像无声的拥抱，陪伴你慢慢好起来",
    ],
    "anxiety": [
        "闭上眼，让香气带你回归内心的宁静",
        "清新的前调如深呼吸般舒展开来",
        "中调平衡沉稳，像一双坚定的手",
        "木质尾韵给你脚踏实地的安全感",
    ],
    "calm": [
        "静谧而深邃，如午后禅园的微风",
        "前调淡雅，不争不抢却悠然自得",
        "中调层次丰富，适合独处的美好时光",
        "尾韵绵长，让平静成为你的底色",
    ],
    "excitement": [
        "这是一场香氛的狂欢",
        "前调活力四射，瞬间点燃你的感官",
        "中调热情奔放，像派对中的闪光时刻",
        "尾韵余韵不绝，让精彩持续到最后一秒",
    ],
    "nostalgia": [
        "香气是时光的容器",
        "前调温柔复古，唤起记忆中美好的片段",
        "中调醇厚绵密，像老唱片缓缓转动",
        "尾韵深沉悠远，让回忆在心底流淌",
    ],
    "romance": [
        "这是一封用香气书写的情书",
        "前调甜蜜而克制，如初见时的心跳",
        "中调绽放玫瑰与茉莉，爱意在空气中弥漫",
        "尾韵温柔缱绻，像月光下的私语",
    ],
    "melancholy": [
        "美有时藏在淡淡的忧伤里",
        "前调微微清苦，如诗人的独白",
        "中调复杂而迷人，像雨夜窗上的水痕",
        "尾韵深邃悠长，让忧郁也成为美的注解",
    ],
}


def _check_allergens(notes: list[str], allergens: list[str]) -> list[str]:
    """Return a list of allergen keywords found (case-insensitive substring match)."""
    if not allergens:
        return []
    search_text = " ".join(n.lower() for n in notes)
    return [a for a in allergens if a.lower().strip() in search_text]


def build_skeleton(
    candidates: list[dict],
    emotion_vector: dict[str, float],
    allergens: list[str] | None = None,
) -> list[dict]:
    # Normalize scores: Cypher returns raw weighted scores (max ~1.3).
    # Scale relative to the top result so the best match anchors at ~90-95
    # and trailing results show real differentiation.
    if not candidates:
        return []

    raw_scores = [c.get("score", 0) for c in candidates[:3]]
    top_raw = max(raw_scores) if raw_scores else 1.0

    skeletons = []
    for i, c in enumerate(candidates[:3]):
        raw = c.get("score", 0)
        # Normalize: 85–95 range anchored on the top result
        normalized = 85 + int((raw / top_raw) * 10) if top_raw > 0 else 85
        score = min(normalized, 95)

        name = c.get("name", "Unknown")
        notes = _estimate_notes(name, emotion_vector)

        # Extract dynamic properties from Neo4j (or fallback for degraded path)
        seasons = c.get("seasons") or []
        season = seasons[0] if seasons else "all"

        skeletons.append({
            "rank": i + 1,
            "name": name,
            "brand": c.get("brand") or "Niche Brand",
            "notes_combination": notes,
            "match_score": score,
            "source": "graphrag_match",
            "allergen_warnings": _check_allergens(notes, allergens or []),
            "is_partial": True,
            "longevity": round(c.get("longevity") or 3.0, 1),
            "sillage": round(c.get("sillage") or 2.5, 1),
            "season": season,
        })
    return skeletons


def _estimate_notes(name: str, emotion_vector: dict[str, float]) -> list[str]:
    # Simplified: return generic note categories based on dominant emotion
    primary = max(emotion_vector.items(), key=lambda x: x[1])[0]
    note_map = {
        "joy":       ["柑橘 Citrus", "花香 Floral", "果香 Fruity"],
        "sadness":   ["佛手柑 Bergamot", "鸢尾 Iris", "檀木 Sandalwood"],
        "anxiety":   ["薰衣草 Lavender", "洋甘菊 Chamomile", "雪松 Cedar"],
        "calm":      ["绿茶 Green Tea", "竹子 Bamboo", "白麝香 White Musk"],
        "excitement":["粉红胡椒 Pink Pepper", "琥珀 Amber", "香草 Vanilla"],
        "nostalgia": ["佛手柑 Bergamot", "广藿香 Patchouli", "沉香 Oud"],
        "romance":   ["玫瑰 Rose", "茉莉 Jasmine", "麝香 Musk"],
        "melancholy":["紫罗兰 Violet", "鸢尾 Iris", "皮革 Leather"],
    }
    return note_map.get(primary, ["佛手柑 Bergamot", "茉莉 Jasmine", "檀木 Sandalwood"])


def build_copy_stream(rank: int, generation_id: str, primary_emotion: str) -> list[str]:
    emotion_key = EMOTION_LABEL_TO_KEY.get(primary_emotion, "calm")
    templates = STORY_TEMPLATES.get(emotion_key, STORY_TEMPLATES["calm"])
    return list(templates)
