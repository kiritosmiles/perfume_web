"""Degradation fallback when Neo4j is unavailable or GraphRAG returns no matches.

Two layers per the design doc:
  1. Neo4j down → query fragrance_templates PG table → Top 10 card wall
  2. No matches → generic gift-appropriate Top 5

When the PG table is empty (MVP seed not yet populated), hardcoded classical
perfume data supplies the fallback.
"""

from app.core.pg import get_pg_pool

# ── Hardcoded fallback when PG table is empty ────────────────────────────────

_GENERIC_TOP_FRAGRANCES: list[dict] = [
    {"name": "No.5 Chanel", "brand": "Chanel",
     "notes_top": ["醛香 Aldehydes", "依兰 Ylang-Ylang", "橙花 Neroli"],
     "notes_middle": ["玫瑰 Rose", "茉莉 Jasmine", "鸢尾 Iris"],
     "notes_base": ["檀木 Sandalwood", "香草 Vanilla", "岩兰草 Vetiver"],
     "mood_tags": ["romance", "calm", "nostalgia"]},
    {"name": "J'adore Dior", "brand": "Dior",
     "notes_top": ["柑橘 Citrus", "香柠檬 Bergamot", "蜜瓜 Melon"],
     "notes_middle": ["玫瑰 Rose", "茉莉 Jasmine", "铃兰 Lily-of-the-Valley"],
     "notes_base": ["麝香 Musk", "黑莓 Blackberry", "雪松 Cedar"],
     "mood_tags": ["joy", "romance", "excitement"]},
    {"name": "Light Blue Dolce & Gabbana", "brand": "Dolce & Gabbana",
     "notes_top": ["柠檬 Lemon", "青苹果 Green Apple", "风信子 Bellflower"],
     "notes_middle": ["茉莉 Jasmine", "竹子 Bamboo", "白玫瑰 White Rose"],
     "notes_base": ["雪松 Cedar", "琥珀 Amber", "麝香 Musk"],
     "mood_tags": ["joy", "calm", "excitement"]},
    {"name": "L'Eau d'Issey Issey Miyake", "brand": "Issey Miyake",
     "notes_top": ["莲花 Lotus", "小苍兰 Freesia", "仙客来 Cyclamen"],
     "notes_middle": ["百合 Lily", "牡丹 Peony", "康乃馨 Carnation"],
     "notes_base": ["麝香 Musk", "琥珀 Amber", "雪松 Cedar"],
     "mood_tags": ["calm", "nostalgia", "romance"]},
    {"name": "Shalimar Guerlain", "brand": "Guerlain",
     "notes_top": ["佛手柑 Bergamot", "柑橘 Citrus", "柠檬 Lemon"],
     "notes_middle": ["玫瑰 Rose", "茉莉 Jasmine", "鸢尾 Iris"],
     "notes_base": ["香草 Vanilla", "零陵香豆 Tonka Bean", "檀木 Sandalwood"],
     "mood_tags": ["romance", "nostalgia", "melancholy"]},
    {"name": "Black Orchid Tom Ford", "brand": "Tom Ford",
     "notes_top": ["黑加仑 Blackcurrant", "依兰 Ylang-Ylang", "佛手柑 Bergamot"],
     "notes_middle": ["黑兰花 Black Orchid", "莲花 Lotus", "茉莉 Jasmine"],
     "notes_base": ["广藿香 Patchouli", "琥珀 Amber", "檀木 Sandalwood"],
     "mood_tags": ["romance", "melancholy", "excitement"]},
    {"name": "L'Homme Yves Saint Laurent", "brand": "Yves Saint Laurent",
     "notes_top": ["生姜 Ginger", "佛手柑 Bergamot", "柠檬 Lemon"],
     "notes_middle": ["紫罗兰 Violet", "罗勒 Basil", "白胡椒 White Pepper"],
     "notes_base": ["雪松 Cedar", "零陵香豆 Tonka Bean", "麝香 Musk"],
     "mood_tags": ["calm", "excitement", "joy"]},
    {"name": "Acqua di Giò Giorgio Armani", "brand": "Giorgio Armani",
     "notes_top": ["柑橘 Citrus", "佛手柑 Bergamot", "青柠 Lime"],
     "notes_middle": ["茉莉 Jasmine", "迷迭香 Rosemary", "牡丹 Peony"],
     "notes_base": ["广藿香 Patchouli", "雪松 Cedar", "橡苔 Oakmoss"],
     "mood_tags": ["joy", "calm", "excitement"]},
    {"name": "La Vie Est Belle Lancôme", "brand": "Lancôme",
     "notes_top": ["黑加仑 Blackcurrant", "梨 Pear", "佛手柑 Bergamot"],
     "notes_middle": ["鸢尾 Iris", "茉莉 Jasmine", "橙花 Orange Blossom"],
     "notes_base": ["广藿香 Patchouli", "零陵香豆 Tonka Bean", "香草 Vanilla"],
     "mood_tags": ["joy", "romance", "nostalgia"]},
    {"name": "Sauvage Dior", "brand": "Dior",
     "notes_top": ["佛手柑 Bergamot", "粉红胡椒 Pink Pepper", "四川花椒 Sichuan Pepper"],
     "notes_middle": ["薰衣草 Lavender", "天竺葵 Geranium", "广藿香 Patchouli"],
     "notes_base": ["雪松 Cedar", "琥珀 Ambroxan", "麝香 Musk"],
     "mood_tags": ["excitement", "calm", "anxiety"]},
]

_GIFT_TOP_5 = [
    "No.5 Chanel", "J'adore Dior", "La Vie Est Belle Lancôme",
    "Light Blue Dolce & Gabbana", "L'Homme Yves Saint Laurent",
]


async def _get_pg_templates(emotion_labels: list[str], limit: int) -> list[dict]:
    """Query fragrance_templates PG table. Returns [] if table is empty."""
    try:
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT name, '' AS brand,
                       notes_top, notes_middle, notes_base,
                       mood_tags, scene_tags, story_copy
                FROM fragrance_templates
                WHERE mood_tags && $1::text[]
                LIMIT $2
                """,
                emotion_labels,
                limit,
            )
            return [
                {
                    "name": r["name"],
                    "brand": r["brand"] or "Classic",
                    "notes_top": r["notes_top"] or [],
                    "notes_middle": r["notes_middle"] or [],
                    "notes_base": r["notes_base"] or [],
                    "mood_tags": r["mood_tags"] or [],
                }
                for r in rows
            ]
    except Exception:
        return []


def _select_by_mood(hardcoded: list[dict], emotion_labels: list[str]) -> list[dict]:
    """Score hardcoded fragrances by mood tag overlap."""
    scored = []
    for f in hardcoded:
        overlap = len(set(f["mood_tags"]) & set(emotion_labels))
        scored.append((overlap, f))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [s[1] for s in scored]


def _fragrance_to_candidate(f: dict, rank: int) -> dict:
    """Convert a fallback fragrance dict to the format expected by build_skeleton."""
    all_notes = (f.get("notes_top", []) + f.get("notes_middle", []) + f.get("notes_base", []))
    return {
        "name": f["name"],
        "brand": f["brand"],
        "notes_combination": all_notes[:3] if all_notes else ["花香 Floral", "柑橘 Citrus", "木质 Woody"],
        "score": 0.72 - (rank * 0.02),  # Lower base score to reflect fallback source
        "rating": 4.2,
        "accord": f["mood_tags"][0] if f.get("mood_tags") else "floral",
        "accord_score": 0.7,
        "relation_weight": 0.8,
    }


async def search_fallback_fragrances(
    emotion_vector: dict[str, float],
    scene_tag: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Degradation path: PG fragrance_templates → hardcoded classics.

    Returns candidates in the Neo4j-compatible dict format so the
    rest of the SSE pipeline works unchanged.
    """
    # Map Chinese emotion labels → English keys for DB query
    emotion_keys = sorted(
        [(k, v) for k, v in emotion_vector.items() if v > 0.2],
        key=lambda x: x[1], reverse=True,
    )
    emotion_labels = [k for k, _ in emotion_keys[:3]]

    # Layer 1: Try PG
    pg_results = await _get_pg_templates(emotion_labels, limit)
    if pg_results:
        return [
            _fragrance_to_candidate(f, i)
            for i, f in enumerate(pg_results[:limit])
        ]

    # Layer 2: Hardcoded classics scored by mood overlap
    ranked = _select_by_mood(_GENERIC_TOP_FRAGRANCES, emotion_labels)
    return [
        _fragrance_to_candidate(f, i)
        for i, f in enumerate(ranked[:limit])
    ]


def get_generic_gift_top5() -> list[str]:
    """Return the 5 most gift-appropriate perfume names."""
    return list(_GIFT_TOP_5)
