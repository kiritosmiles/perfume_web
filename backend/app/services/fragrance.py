"""GraphRAG fragrance search — multi-accord weighted scoring with scene boost.

The query scores perfumes by summing all emotion→accord→perfume path scores
across ALL 8 emotion dimensions (not just top 2), adds a scene-match bonus,
and returns enough candidates for downstream diversity selection.
"""

from neo4j._async.work.session import AsyncSession

# ── Accord clusters for downstream diversity selection ─────────────────────
# Maps each Neo4j Accord name to a broader olfactory cluster.
# Used by generation._diverse_top3() to ensure 3 recommendations come from
# different clusters rather than all being citrus variants.
ACCORD_CLUSTERS: dict[str, str] = {
    # citrus family
    "citrus": "citrus", "fruity": "citrus", "tropical": "citrus", "fresh": "citrus",
    # floral family
    "floral": "floral", "rose": "floral", "white floral": "floral",
    "yellow floral": "floral", "violet": "floral", "iris": "floral",
    "tuberose": "floral",
    # woody family
    "woody": "woody", "earthy": "woody", "mossy": "woody",
    "patchouli": "woody", "oud": "woody", "conifer": "woody", "green": "woody",
    # spicy family
    "amber": "spicy", "warm spicy": "spicy", "fresh spicy": "spicy",
    "soft spicy": "spicy", "aromatic": "spicy", "cinnamon": "spicy",
    "herbal": "spicy", "anis": "spicy",
    # sweet family
    "sweet": "sweet", "vanilla": "sweet", "caramel": "sweet",
    "honey": "sweet", "chocolate": "sweet", "cacao": "sweet",
    "almond": "sweet", "coconut": "sweet", "gourmand": "sweet",
    # musky family
    "musky": "musky", "powdery": "musky", "soapy": "musky",
    "aldehydic": "musky", "balsamic": "musky", "lactonic": "musky",
    "milky": "musky",
    # leather family
    "leather": "leather", "animalic": "leather", "smoky": "leather",
    "tobacco": "leather",
    # aquatic family
    "aquatic": "aquatic", "marine": "aquatic", "ozonic": "aquatic",
    "lavender": "aquatic",
    # everything else
    "metallic": "other", "mineral": "other", "salty": "other",
    "alcohol": "other", "coffee": "other", "rum": "other",
    "camphor": "other", "beeswax": "other", "cherry": "other",
    "wine": "other", "whiskey": "other", "champagne": "other",
    "vodka": "other", "rubber": "other", "sand": "other",
    "sour": "other", "bitter": "other", "terpenic": "other",
    "nutty": "other", "savory": "other",
}


async def search_fragrance_by_emotion(
    session: AsyncSession,
    emotion_vector: dict[str, float],
    scene_tag: str | None = None,
    limit: int = 50,
    seed_notes: list[str] | None = None,
) -> list[dict]:
    """Search perfumes by weighted multi-emotion→accord→perfume path scoring.

    All 8 emotion dimensions participate — even low-weight emotions (e.g.
    sadness=0.05) contribute small scores that pull in different accord
    families, breaking the previous monotony where only top-2 emotions
    (with only 2-3 accords each) drove the entire result set.

    Scene tag (if provided) adds a +0.25 bonus for perfumes linked to that
    scene via SUITS_SEASON.

    Seed notes (if provided, from synesthesia decoding) add a +0.15 bonus
    per matching note name in the perfume, steering results toward the
    decoded sensory concepts.
    """
    query = """
        UNWIND $emotions AS ed
        MATCH (e:Emotion {name: ed.name})-[r:SOOTHES]->(a:Accord)<-[ha:HAS_ACCORD]-(p:Perfume)
        WITH p, a, ed, r, ha,
             (ed.weight * r.weight * ha.score / 100.0) AS path_score
        WITH p,
             SUM(path_score) AS total_accord_score,
             COLLECT(DISTINCT a.name) AS matched_accords
        OPTIONAL MATCH (p)-[:BY]->(b:Brand)
        OPTIONAL MATCH (p)-[ss:SUITS_SEASON]->(:Scene)
        WITH p, b, ss, total_accord_score, matched_accords,
             total_accord_score
             + COALESCE(toFloat(p.rating), 3.0) * 0.5
             + CASE WHEN $scene_tag IS NOT NULL AND $scene_tag <> ''
                    AND ss IS NOT NULL THEN 0.25
                    ELSE 0 END AS score
        WHERE total_accord_score > 0
        RETURN DISTINCT p.name AS name,
               b.name AS brand,
               p.rating AS rating,
               p.longevity AS longevity,
               p.sillage AS sillage,
               p.url AS fragrantica_url,
               p.image AS image_url,
               COLLECT(DISTINCT ss.season) AS seasons,
               matched_accords[0] AS accord,
               total_accord_score AS accord_score,
               score,
               [(p)-[hn:HAS_NOTE]->(n:Note) | {name: n.name, layer: hn.layer}] AS notes_data
        ORDER BY score DESC
        LIMIT $limit
    """

    # All 8 emotions participate — floor weight 0.05 ensures even the
    # weakest emotion dimension can pull in at least one distinct accord path.
    emotions_param: list[dict] = [
        {"name": name, "weight": max(weight or 0.0, 0.05)}
        for name, weight in emotion_vector.items()
    ]

    result = await session.run(
        query,
        emotions=emotions_param,
        scene_tag=scene_tag or "",
        limit=limit,
        timeout=3.0,  # 3s hard timeout — TRD §2.2: GraphRAG < 200ms typical
    )
    records = await result.data()

    # Post-process: apply seed note bonus from synesthesia decoding (FR-5.8)
    if seed_notes and records:
        records = _apply_seed_note_boost(records, seed_notes)

    return records


def _apply_seed_note_boost(
    records: list[dict],
    seed_notes: list[str],
) -> list[dict]:
    """Boost perfumes whose notes match synesthesia-decoded seed terms.

    Adds +0.15 per matching seed note to the score, then re-sorts.
    This keeps the Cypher query simple while making synesthesia tokens
    effective steering signals for GraphRAG results.
    """
    seed_lower = [s.lower().strip() for s in seed_notes]
    for rec in records:
        notes_data: list[dict] = rec.get("notes_data", []) or []
        note_names_lower = [(nd.get("name") or "").lower().strip() for nd in notes_data]
        accords_lower = [(rec.get("accord") or "").lower()]

        matches = 0
        for seed in seed_lower:
            for nl in note_names_lower:
                if seed in nl or nl in seed:
                    matches += 1
                    break
            else:
                # Also check accord name
                for al in accords_lower:
                    if seed in al or al in seed:
                        matches += 1
                        break

        rec["score"] = rec.get("score", 0) + matches * 0.15

    records.sort(key=lambda r: r.get("score", 0), reverse=True)
    return records
