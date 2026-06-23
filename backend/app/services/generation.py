import hashlib

from app.services.emotion import EMOTION_LABEL_TO_KEY
from app.services.fragrance import ACCORD_CLUSTERS


def _image_url(name: str) -> str:
    """Deterministic placeholder image URL based on perfume name hash."""
    seed = hashlib.md5(name.encode()).hexdigest()[:8]
    return f"https://picsum.photos/seed/{seed}/400/500"


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


GIFT_STORY_TEMPLATES: dict[str, list[str]] = {
    "joy": [
        "这份香气是送给TA的阳光与笑容",
        "前调果香明亮，像拆开礼物那一刻的雀跃心跳",
        "中调花香温暖绽放，是你在卡片上写下的祝福",
        "尾韵是绵长的幸福感——愿TA每一天都有好心情",
    ],
    "sadness": [
        "有些陪伴不需要言语，香气可以替你说",
        "前调温润柔和，轻轻包裹TA的情绪",
        "中调渐渐舒展的花香，像无声的拥抱",
        "尾韵暖意绵长，让TA知道有人在默默守护",
    ],
    "anxiety": [
        "送TA一份宁静，比任何话语都熨帖",
        "前调清新舒缓，如深呼吸般放松紧绷的神经",
        "中调沉稳平衡，带来踏实的安定感",
        "尾韵是木质的温柔——愿TA每天都能睡个好觉",
    ],
    "calm": [
        "这是一份从容优雅的礼物",
        "前调淡雅不张扬，如午后茶歇的静谧时光",
        "中调层次细腻，诉说你懂TA的品味",
        "尾韵悠长温和，像老友的陪伴细水长流",
    ],
    "excitement": [
        "送TA一瓶派对，庆祝每一个高光时刻",
        "前调活力四射，像开香槟的瞬间",
        "中调热情洋溢，是你们共同的狂欢记忆",
        "尾韵余韵不绝——精彩才刚刚开始",
    ],
    "nostalgia": [
        "有些礼物，是为了纪念一段时光",
        "前调温柔复古，唤起你们共同的美好回忆",
        "中调醇厚绵长，像老照片泛黄的质感",
        "尾韵深沉温暖——最好的礼物是心意",
    ],
    "romance": [
        "香气是最美的情书，比言语更动人心",
        "前调甜蜜克制，是初见时的心动",
        "中调玫瑰与茉莉交织，爱意在每一次呼吸间弥漫",
        "尾韵温柔缱绻——你是TA最特别的人",
    ],
    "melancholy": [
        "懂得TA的细腻，是最高级的礼物",
        "前调如诗人的独白，清雅而深邃",
        "中调复杂迷人，像雨夜的钢琴曲",
        "尾韵悠长——你的礼物让美有了形状",
    ],
}

EXPLORE_STORY_TEMPLATES: dict[str, list[str]] = {
    "joy": [
        "欢迎来到香氛世界的阳光角落",
        "前调是柑橘家族的明亮开场——试试你最喜欢哪一种",
        "中调花香绽放，从玫瑰到茉莉，各有各的风情",
        "尾韵千变万化——每一次探索都是新的发现",
    ],
    "sadness": [
        "有时候，探索气味本身就是一种疗愈",
        "前调从微苦的佛手柑开始，慢慢展开",
        "中调是鸢尾与檀木的低语——每一种都有故事",
        "不妨多试几款，让香气陪你走一段路",
    ],
    "anxiety": [
        "香氛世界很广阔，不必急于选择",
        "前调从清新的薰衣草和柑橘开始探险",
        "中调有洋甘菊的温柔，也有雪松的沉稳",
        "慢慢逛，慢慢闻——总有一款让你安心",
    ],
    "calm": [
        "探索本身，就是一种沉静的快乐",
        "前调淡雅开场——绿茶、竹子、白麝香各有韵味",
        "中调层次徐徐展开，像翻阅一本香氛图鉴",
        "不赶时间，享受发现的过程",
    ],
    "excitement": [
        "欢迎进入香氛的游乐场！",
        "前调从粉红胡椒到柑橘——刺激你的嗅觉冒险",
        "中调是琥珀与香草的狂欢派对",
        "每一次探索都可能遇到你的本命香",
    ],
    "nostalgia": [
        "每一瓶香水都藏着一个时代的故事",
        "前调复古气息——佛手柑、广藿香的经典开场",
        "中调像老唱片的旋律，带你穿越时光",
        "在香氛地图上，怀旧是一扇通往过去的门",
    ],
    "romance": [
        "欢迎探索香氛中最浪漫的角落",
        "前调从玫瑰园到茉莉花园——花的世界为你展开",
        "中调麝香温柔，像月光洒在花瓣上",
        "每一瓶都是一封未寄出的情书",
    ],
    "melancholy": [
        "最美的香气往往藏在最深的情绪里",
        "前调从紫罗兰到鸢尾——忧郁也是美的注解",
        "中调皮革与沉香的对话，深邃而迷人",
        "慢慢探索，你会发现忧郁也可以很精致",
    ],
}

# ── Gift-safe cluster priority ─────────────────────────────────────────────
# For gift intent, prefer universally-appealing families and deprioritize
# polarizing ones (leather, animalic).
GIFT_CLUSTER_PRIORITY = [
    "musky", "floral", "woody", "sweet", "citrus", "aquatic", "spicy", "other", "leather",
]

# ── Common fragrance allergens ──────────────────────────────────────────────
COMMON_ALLERGENS = [
    "Linalool", "Limonene", "Citronellol", "Geraniol", "Coumarin",
    "Eugenol", "Cinnamal", "Benzyl Alcohol",
]


def _annotate_common_allergens(notes: dict[str, list[str]]) -> list[str]:
    """Check notes against common fragrance allergens and return warnings."""
    all_notes = notes.get("top", []) + notes.get("middle", []) + notes.get("base", [])
    search_text = " ".join(n.lower() for n in all_notes)
    return [a for a in COMMON_ALLERGENS if a.lower() in search_text]


def _check_allergens(notes: dict[str, list[str]], allergens: list[str]) -> list[str]:
    """Return a list of allergen keywords found (case-insensitive substring match)."""
    if not allergens:
        return []
    all_note_names = notes.get("top", []) + notes.get("middle", []) + notes.get("base", [])
    search_text = " ".join(n.lower() for n in all_note_names)
    return [a for a in allergens if a.lower().strip() in search_text]


def _diverse_top3(candidates: list[dict], intent: str = "self_use") -> list[dict]:
    """Greedy diversity selection: pick top-3 perfumes from different accord clusters.

    Sorts by score descending, then iteratively picks the highest-ranked
    perfume whose accord cluster hasn't been used yet. Falls back to
    score-only top-3 if fewer than 3 clusters are available.

    For gift intent: prioritizes universally-appealing clusters
    (musky, floral, woody) over polarizing ones (leather, animalic).
    """
    if not candidates:
        return []

    # Determine cluster order: gift=safe priority, else=score order
    if intent == "gift":
        cluster_order = {c: i for i, c in enumerate(GIFT_CLUSTER_PRIORITY)}
    else:
        cluster_order = {}

    selected: list[dict] = []
    used_clusters: set[str] = set()

    sorted_candidates = sorted(candidates, key=lambda c: c.get("score", 0), reverse=True)

    for c in sorted_candidates:
        accord = c.get("accord", "other")
        cluster = ACCORD_CLUSTERS.get(accord, "other")
        if cluster not in used_clusters:
            selected.append(c)
            used_clusters.add(cluster)
        if len(selected) >= 3:
            break

    # For explore intent: ensure max diversity by re-ranking selected items
    # to prefer the least common clusters first
    if intent == "explore" and len(selected) >= 3:
        selected.sort(key=lambda c: cluster_order.get(
            ACCORD_CLUSTERS.get(c.get("accord", "other"), "other"), 999
        ))

    # Fallback: if fewer than 3 clusters found (unlikely with 9 clusters),
    # fill remaining slots with best unused candidates
    if len(selected) < 3:
        for c in sorted_candidates:
            if c not in selected:
                selected.append(c)
            if len(selected) >= 3:
                break

    return selected


def build_skeleton(
    candidates: list[dict],
    emotion_vector: dict[str, float],
    allergens: list[str] | None = None,
    intent: str = "self_use",
) -> list[dict]:
    # Normalize scores: Cypher returns raw weighted scores.
    # Scale relative to the top result so the best match anchors at ~90-95
    # and trailing results show real differentiation.
    if not candidates:
        return []

    # Apply accord-cluster diversity before normalization
    top3 = _diverse_top3(candidates, intent=intent)

    raw_scores = [c.get("score", 0) for c in top3]
    top_raw = max(raw_scores) if raw_scores else 1.0

    skeletons = []
    for i, c in enumerate(top3):
        raw = c.get("score", 0)
        # Normalize: 85–95 range anchored on the top result
        normalized = 85 + int((raw / top_raw) * 10) if top_raw > 0 else 85
        score = min(normalized, 95)

        name = c.get("name", "Unknown")
        notes = _extract_notes(c, emotion_vector)

        # Extract dynamic properties from Neo4j (or fallback for degraded path)
        seasons = c.get("seasons") or []
        season = seasons[0] if seasons else "all"

        # Intent-gated allergen handling
        if intent == "self_use":
            allergen_warnings = _check_allergens(notes, allergens or [])
        elif intent == "gift":
            # Skip personal allergens; annotate common allergens instead
            allergen_warnings = _annotate_common_allergens(notes)
        else:  # explore
            allergen_warnings = []

        skeletons.append({
            "rank": i + 1,
            "name": name,
            "brand": c.get("brand") or "Niche Brand",
            "notes_combination": notes,
            "match_score": score,
            "source": "graphrag_match",
            "allergen_warnings": allergen_warnings,
            "is_partial": True,
            "longevity": round(c.get("longevity") or 3.0, 1),
            "sillage": round(c.get("sillage") or 2.5, 1),
            "season": season,
            "image_url": c.get("image_url") or _image_url(name),
            "fragrantica_url": c.get("fragrantica_url") or None,
        })
    return skeletons


# ── Garbage patterns from HTML note parsing (parse_notes_from_desc) ──────────
# These fragments leak into Neo4j :Note nodes; filtered out on read.
_NOTE_GARBAGE_STARTS = (
    "is ", "consist ", "which ", "include ", "adding ", "characterized ",
    "leaving ", "musk create ", "of ", "that add", "that give", "woody ",
    "patchouli provide", "give the", "provide an", "lingering", "create a",
    "add an", "adds a", "creates a", "balance", "balancing", "that are",
    "and are", "a blend", "well blen", "are perfect", "to add",
    "perfect for", "making it", "offering", "with a", "with its",
    "contrast", "combining", "combined", "evokes", "evoking", "brings",
    "giving", "makes this", "this fragrance", "the fragrance",
    "sweet aroma", "velvety tone", "comforting quality", "inviting aroma",
    "dark woodsy", "woody accords that", "longevity", "consist of",
    "of this fragrance", "of white musk", "of amber", "of cedar",
    "of agarwood", "is a", "is an",
)


def _is_valid_note(name: str) -> bool:
    """Filter out garbage HTML fragments from parse_notes_from_desc."""
    if not name or len(name) < 2 or len(name) > 50:
        return False
    name_lower = name.lower().strip()
    if name_lower.startswith(_NOTE_GARBAGE_STARTS):
        return False
    # Fragments that are long sentences (always garbage)
    if name_lower.count(" ") > 6:
        return False
    return True


def _extract_notes(candidate: dict, emotion_vector: dict[str, float]) -> dict[str, list[str]]:
    """Extract real top/middle/base notes from Neo4j notes_data.

    Returns structured dict: {"top": [...], "middle": [...], "base": [...]}.
    Falls back to emotion-based estimate if no valid notes found.
    """
    notes_data: list[dict] = candidate.get("notes_data", []) or []
    top: list[str] = []
    middle: list[str] = []
    base: list[str] = []

    seen: set[str] = set()
    for nd in notes_data:
        name = (nd.get("name") or "").strip()
        layer = nd.get("layer", "")
        if not _is_valid_note(name):
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        if layer == "top":
            top.append(name)
        elif layer == "middle":
            middle.append(name)
        elif layer == "base":
            base.append(name)

    if top or middle or base:
        return {
            "top": top[:4],
            "middle": middle[:4],
            "base": base[:4],
        }

    # Fallback: emotion-based estimate (perfume without notes in Neo4j)
    primary = max(emotion_vector.items(), key=lambda x: x[1])[0]
    note_map = {
        "joy":        (["Citrus", "Bergamot", "Fruity"], ["Floral", "Jasmine", "Rose"], ["Musk", "Sandalwood", "Amber"]),
        "sadness":    (["Bergamot", "Violet"], ["Iris", "Jasmine"], ["Sandalwood", "Vanilla", "Musk"]),
        "anxiety":    (["Lavender", "Bergamot"], ["Chamomile", "Jasmine"], ["Cedar", "Sandalwood"]),
        "calm":       (["Green Tea", "Bergamot"], ["Bamboo", "Lavender"], ["White Musk", "Sandalwood"]),
        "excitement": (["Pink Pepper", "Citrus"], ["Amber", "Jasmine"], ["Vanilla", "Patchouli"]),
        "nostalgia":  (["Bergamot", "Violet"], ["Patchouli", "Rose"], ["Oud", "Sandalwood"]),
        "romance":    (["Rose", "Bergamot"], ["Jasmine", "Ylang-Ylang"], ["Musk", "Vanilla"]),
        "melancholy": (["Violet", "Bergamot"], ["Iris", "Rose"], ["Leather", "Oud"]),
    }
    nt = note_map.get(primary, (["Bergamot"], ["Jasmine"], ["Sandalwood"]))
    return {"top": list(nt[0]), "middle": list(nt[1]), "base": list(nt[2])}


def build_copy_stream(
    rank: int,
    generation_id: str,
    primary_emotion: str,
    intent: str = "self_use",
) -> list[str]:
    emotion_key = EMOTION_LABEL_TO_KEY.get(primary_emotion, "calm")
    if intent == "gift":
        templates = GIFT_STORY_TEMPLATES.get(emotion_key, GIFT_STORY_TEMPLATES["calm"])
    elif intent == "explore":
        templates = EXPLORE_STORY_TEMPLATES.get(emotion_key, EXPLORE_STORY_TEMPLATES["calm"])
    else:
        templates = STORY_TEMPLATES.get(emotion_key, STORY_TEMPLATES["calm"])
    return list(templates)
