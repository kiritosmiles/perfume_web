from neo4j._async.work.session import AsyncSession


async def search_fragrance_by_emotion(
    session: AsyncSession,
    emotion_vector: dict[str, float],
    scene_tag: str | None = None,
    limit: int = 10,
) -> list[dict]:
    # Multi-accord aggregation query: instead of taking MAX (which loses
    # differentiation when many perfumes share the same top accord at score 100),
    # SUM all emotion→accord→perfume path scores. A perfume matching citrus(0.81)
    # + fruity(0.64) + floral(0.49) = 1.94 beats one matching only citrus(0.81).
    # Rating is added as a small tiebreaker (max 2.5 points for rating=5).
    query = """
        UNWIND $emotions AS ed
        MATCH (e:Emotion {name: ed.name})-[r:SOOTHES]->(a:Accord)<-[ha:HAS_ACCORD]-(p:Perfume)
        WITH p, a, ed, r, ha,
             (ed.weight * r.weight * ha.score / 100.0) AS path_score
        WITH p,
             SUM(path_score) AS total_accord_score,
             COLLECT(DISTINCT a.name) AS matched_accords
        OPTIONAL MATCH (p)-[:BY]->(b:Brand)
        WITH p, b, total_accord_score, matched_accords,
             total_accord_score + COALESCE(toFloat(p.rating), 3.0) * 0.5 AS score
        WHERE total_accord_score > 0
        RETURN DISTINCT p.name AS name,
               b.name AS brand,
               p.rating AS rating,
               matched_accords[0] AS accord,
               total_accord_score AS accord_score,
               score
        ORDER BY score DESC
        LIMIT $limit
    """

    # Pass emotion names with their vector weights for weighted scoring
    sorted_emotions = sorted(emotion_vector.items(), key=lambda x: x[1], reverse=True)
    emotions_param = [
        {"name": e[0], "weight": e[1]}
        for e in sorted_emotions[:2] if e[1] > 0.3
    ]
    if not emotions_param:
        emotions_param = [{"name": sorted_emotions[0][0], "weight": sorted_emotions[0][1]}]

    result = await session.run(query, emotions=emotions_param, limit=limit)
    records = await result.data()
    return records
