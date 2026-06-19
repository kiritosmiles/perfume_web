from neo4j._async.work.session import AsyncSession


async def search_fragrance_by_emotion(
    session: AsyncSession,
    emotion_vector: dict[str, float],
    scene_tag: str | None = None,
    limit: int = 10,
) -> list[dict]:
    # Build the matching query: 1-hop Emotion -> SOOTHES -> Accord <- HAS_ACCORD - Perfume
    query = """
        MATCH (e:Emotion)-[r:SOOTHES]->(a:Accord)<-[ha:HAS_ACCORD]-(p:Perfume)
        OPTIONAL MATCH (p)-[:BY_BRAND]->(b:Brand)
        WHERE e.id IN $emotion_ids
        WITH p, a, b, r, ha,
             (r.weight * ha.score / 100.0 + COALESCE(p.rating, 0) * 0.1) AS score
        RETURN p.name AS name,
               b.name AS brand,
               p.rating AS rating,
               a.name AS accord,
               ha.score AS accord_score,
               r.weight AS relation_weight,
               score
        ORDER BY score DESC
        LIMIT $limit
    """

    # Map primary emotion to Neo4j emotion node ids
    # Find the top 2 emotions from the vector
    sorted_emotions = sorted(emotion_vector.items(), key=lambda x: x[1], reverse=True)
    emotion_ids = [e[0] for e in sorted_emotions[:2] if e[1] > 0.3]

    if not emotion_ids:
        emotion_ids = [sorted_emotions[0][0]]  # fallback to top emotion

    result = await session.run(query, emotion_ids=emotion_ids, limit=limit)
    records = await result.data()
    return records
