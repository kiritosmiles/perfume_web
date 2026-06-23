"""Migration: replace old SOOTHES edges (22) with expanded set (~75).

Deletes all existing [:SOOTHES] relationships and recreates them
from the expanded EMOTION_ACCORD_MAP in import_fragrantica_to_neo4j.py.
"""

import asyncio
from neo4j import AsyncGraphDatabase

NEO4J_URI = "bolt://localhost:17687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "perfume_dev"

# Mirror of expanded EMOTION_ACCORD_MAP from import_fragrantica_to_neo4j.py
EMOTION_ACCORD_MAP = [
    # ── joy 开心 (10 accords) ──
    ("joy", "citrus", 0.94), ("joy", "fruity", 0.85), ("joy", "floral", 0.82),
    ("joy", "sweet", 0.75), ("joy", "fresh", 0.65), ("joy", "aromatic", 0.60),
    ("joy", "tropical", 0.55), ("joy", "green", 0.50), ("joy", "white floral", 0.48),
    ("joy", "aquatic", 0.45),
    # ── calm 平静 (10 accords) ──
    ("calm", "woody", 0.93), ("calm", "musky", 0.82), ("calm", "powdery", 0.78),
    ("calm", "fresh", 0.70), ("calm", "green", 0.65), ("calm", "aquatic", 0.58),
    ("calm", "herbal", 0.55), ("calm", "lavender", 0.50), ("calm", "amber", 0.48),
    ("calm", "soft spicy", 0.45),
    # ── sadness 难过 (9 accords) ──
    ("sadness", "amber", 0.90), ("sadness", "warm spicy", 0.82), ("sadness", "woody", 0.78),
    ("sadness", "vanilla", 0.72), ("sadness", "powdery", 0.62), ("sadness", "musky", 0.58),
    ("sadness", "floral", 0.52), ("sadness", "soft spicy", 0.48), ("sadness", "balsamic", 0.45),
    # ── anxiety 焦虑 (9 accords) ──
    ("anxiety", "vanilla", 0.92), ("anxiety", "citrus", 0.83), ("anxiety", "lavender", 0.80),
    ("anxiety", "fresh", 0.72), ("anxiety", "powdery", 0.62), ("anxiety", "green", 0.58),
    ("anxiety", "musky", 0.52), ("anxiety", "sweet", 0.48), ("anxiety", "aquatic", 0.45),
    # ── excitement 兴奋 (9 accords) ──
    ("excitement", "sweet", 0.88), ("excitement", "aromatic", 0.82), ("excitement", "citrus", 0.78),
    ("excitement", "fruity", 0.72), ("excitement", "warm spicy", 0.65), ("excitement", "amber", 0.60),
    ("excitement", "vanilla", 0.55), ("excitement", "woody", 0.50), ("excitement", "tropical", 0.48),
    # ── nostalgia 怀旧 (9 accords) ──
    ("nostalgia", "woody", 0.92), ("nostalgia", "leather", 0.82), ("nostalgia", "earthy", 0.78),
    ("nostalgia", "amber", 0.72), ("nostalgia", "warm spicy", 0.65), ("nostalgia", "oud", 0.60),
    ("nostalgia", "patchouli", 0.55), ("nostalgia", "tobacco", 0.50), ("nostalgia", "smoky", 0.48),
    # ── romance 浪漫 (9 accords) ──
    ("romance", "floral", 0.94), ("romance", "rose", 0.85), ("romance", "powdery", 0.82),
    ("romance", "sweet", 0.75), ("romance", "vanilla", 0.65), ("romance", "fruity", 0.60),
    ("romance", "musky", 0.55), ("romance", "amber", 0.50), ("romance", "white floral", 0.48),
    # ── melancholy 忧郁 (9 accords) ──
    ("melancholy", "oud", 0.90), ("melancholy", "smoky", 0.82), ("melancholy", "marine", 0.75),
    ("melancholy", "woody", 0.72), ("melancholy", "amber", 0.62), ("melancholy", "leather", 0.58),
    ("melancholy", "earthy", 0.55), ("melancholy", "aquatic", 0.50), ("melancholy", "patchouli", 0.48),
]


async def migrate():
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    async with driver.session() as session:
        # 1. Count and delete old edges
        result = await session.run("MATCH ()-[r:SOOTHES]->() RETURN count(r) AS cnt")
        old_count = (await result.single())["cnt"]
        print(f"Old SOOTHES edges: {old_count}")

        if old_count > 0:
            await session.run("MATCH ()-[r:SOOTHES]->() DELETE r")
            print("Deleted old edges.")

        # 2. Count accord nodes to verify they exist
        result = await session.run("MATCH (a:Accord) RETURN count(a) AS cnt")
        accord_count = (await result.single())["cnt"]
        print(f"Accord nodes available: {accord_count}")

        # 3. Create new edges
        created = 0
        skipped = 0
        for emotion, accord, weight in EMOTION_ACCORD_MAP:
            result = await session.run(
                """
                MATCH (e:Emotion {name: $emotion}), (a:Accord {name: $accord})
                CREATE (e)-[:SOOTHES {weight: $weight}]->(a)
                RETURN count(*) AS cnt
                """,
                emotion=emotion, accord=accord, weight=weight,
            )
            row = await result.single()
            if row and row["cnt"] > 0:
                created += 1
            else:
                skipped += 1
                if skipped <= 5:
                    print(f"  ⚠ skipped: emotion={emotion}, accord={accord} (Accord node not found?)")

        print(f"\nCreated: {created} edges, Skipped: {skipped}")

        # 4. Verify
        result = await session.run("MATCH ()-[r:SOOTHES]->() RETURN count(r) AS cnt")
        new_count = (await result.single())["cnt"]
        result = await session.run(
            "MATCH (e:Emotion)-[:SOOTHES]->(a:Accord) "
            "RETURN e.name AS emotion, count(a) AS accords ORDER BY emotion"
        )
        rows = await result.data()
        print(f"\nNew SOOTHES edges: {new_count}")
        print("Per emotion:")
        for row in rows:
            print(f"  {row['emotion']:12s} → {row['accords']} accords")

    await driver.close()


if __name__ == "__main__":
    asyncio.run(migrate())
