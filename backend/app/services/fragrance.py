from neo4j._async.work.session import AsyncSession


async def search_fragrance_by_emotion(
    session: AsyncSession,
    emotion_vector: dict[str, float],
    scene_tag: str | None = None,
    limit: int = 10,
) -> list[dict]:
    # Build the matching query: 1-hop Emotion -> SOOTHES -> Accord <- HAS_ACCORD - Perfume
    # Score formula weights each emotion by its vector value so the primary emotion
    # dominates (e.g. romance=0.9 gets 1.5× the weight of joy=0.6)
    query = """
        UNWIND $emotions AS ed
        MATCH (e:Emotion {name: ed.name})-[r:SOOTHES]->(a:Accord)<-[ha:HAS_ACCORD]-(p:Perfume)
        WITH p, a, r, ha, ed,
             (ed.weight * r.weight * ha.score / 100.0
              + COALESCE(toFloat(p.rating), 0) * 0.1) AS score
        ORDER BY score DESC
        WITH p, MAX(score) AS max_score, HEAD(COLLECT(a.name)) AS best_accord,
             HEAD(COLLECT(ha.score)) AS best_accord_score,
             HEAD(COLLECT(r.weight)) AS best_weight
        OPTIONAL MATCH (p)-[:BY]->(b:Brand)
        RETURN DISTINCT p.name AS name,
               b.name AS brand,
               p.rating AS rating,
               best_accord AS accord,
               best_accord_score AS accord_score,
               best_weight AS relation_weight,
               max_score AS score
        ORDER BY max_score DESC
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
