"""Import Fragrantica dataset to Neo4j using the driver directly.

Fixes the original import_fragrantica_to_neo4j.py bugs:
  Bug 1: Cypher variable scope resets at each ';' in cypher-shell
         → CREATE(p_1) and MATCH(p_1) run in different transactions
  Bug 2: Backslash in names (e.g. "Tonias\\ Handmade") breaks Cypher strings
  Bug 3: CREATE duplicates nodes on re-import

This rewrite uses the Neo4j Python driver with MERGE + parameterized
queries, so every statement runs in one session and variables bind correctly.

Usage: python scripts/import_to_neo4j.py
Requires: Neo4j running at localhost:7687 (neo4j / perfume_dev)
"""

import json
import re
import glob
import asyncio
import sys
from pathlib import Path
from html import unescape

# Add backend to path so we can use its config
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

# Load settings inline to avoid circular imports
from pydantic_settings import BaseSettings


class _ImportSettings(BaseSettings):
    model_config = {"env_prefix": "", "case_sensitive": False}
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "perfume_dev"


settings = _ImportSettings()

from neo4j import AsyncGraphDatabase

# Settings defined inline above

# ── 1. Load & deduplicate JSON ──────────────────────────────────────────────

JSON_DIR = ROOT / "docs"
json_files = sorted(glob.glob(str(JSON_DIR / "dataset_fragrantica_*.json")))
if not json_files:
    print("❌ No dataset_fragrantica_*.json found in docs/")
    sys.exit(1)

seen_urls: set[str] = set()
perfumes_all: list[dict] = []
total_raw = 0
for jf in json_files:
    with open(jf, encoding="utf-8") as f:
        raw = json.load(f)
    added = 0
    for item in raw:
        total_raw += 1
        if item.get("brandName") is None:
            continue
        if "404 - Page Not Found" in (item.get("title") or ""):
            continue
        url = item.get("url", "")
        if url in seen_urls:
            continue
        seen_urls.add(url)
        perfumes_all.append(item)
        added += 1
    print(f"  {Path(jf).name:45s} {len(raw):>4} raw → {added:>4} new")

print(f"\n📊 {total_raw} raw → {len(perfumes_all)} unique\n")

# ── 2. Note extraction ──────────────────────────────────────────────────────

def parse_notes_from_desc(desc: str) -> dict[str, list[str]]:
    """Extract top/middle/base notes from HTML description."""
    text = unescape(re.sub(r"<[^>]+>", " ", desc))
    result: dict[str, list[str]] = {"top": [], "middle": [], "base": []}

    patterns = [
        (r"[Tt]op\s+notes?\s*(?:are|:)?\s*(.+?)(?:\s*;?\s*[Mm]iddle\s+notes?)", "top"),
        (r"[Mm]iddle\s+notes?\s*(?:are|:)?\s*(.+?)(?:\s*;?\s*[Bb]ase\s+notes?)", "middle"),
        (r"[Bb]ase\s+notes?\s*(?:are|:)?\s*(.+?)(?:\.\s|\s*$|\s*<)", "base"),
    ]

    for pattern, key in patterns:
        m = re.search(pattern, text)
        if m:
            segment = m.group(1).strip()
            notes = re.split(r"\s*,\s*|\s+and\s+", segment)
            notes = [n.strip(" .") for n in notes if n.strip() and len(n.strip()) > 2]
            notes = [n for n in notes if not re.match(r"^\d{4}s?$", n) and n not in ("The", "the")]
            result[key] = notes

    return result

# ── 3. Constants ─────────────────────────────────────────────────────────────

EMOTIONS = [
    ("joy", "开心"), ("sadness", "难过"), ("anxiety", "焦虑"), ("calm", "平静"),
    ("excitement", "兴奋"), ("nostalgia", "怀旧"), ("romance", "浪漫"), ("melancholy", "忧郁"),
]

SCENES = [
    ("work", "通勤工作"), ("date", "约会之夜"), ("home", "宅家放松"),
    ("party", "聚会社交"), ("gift", "挑选礼物"), ("explore", "随便看看"),
]

EMOTION_ACCORD_MAP = [
    ("anxiety", "vanilla", 0.9), ("anxiety", "citrus", 0.8), ("anxiety", "lavender", 0.7),
    ("calm", "woody", 0.9), ("calm", "musky", 0.7), ("calm", "powdery", 0.6),
    ("sadness", "amber", 0.8), ("sadness", "warm spicy", 0.7),
    ("joy", "citrus", 0.9), ("joy", "fruity", 0.8), ("joy", "floral", 0.7),
    ("excitement", "sweet", 0.8), ("excitement", "aromatic", 0.7),
    ("romance", "floral", 0.9), ("romance", "rose", 0.8), ("romance", "powdery", 0.7),
    ("nostalgia", "woody", 0.8), ("nostalgia", "leather", 0.7), ("nostalgia", "earthy", 0.7),
    ("melancholy", "oud", 0.8), ("melancholy", "smoky", 0.7), ("melancholy", "marine", 0.6),
]

# ── 4. Main import ───────────────────────────────────────────────────────────

async def main():
    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )

    try:
        async with driver.session() as session:
            # 4a. Clear old data (sub-transactions to avoid OOM)
            print("🗑️  Clearing old data...")
            await session.run("""
                MATCH (n)
                CALL { WITH n DETACH DELETE n } IN TRANSACTIONS OF 100 ROWS
            """)
            print("   all nodes cleared")

            # Drop old indexes
            for idx in ["index_f0a1cc13", "index_8605e3f1", "index_276ef52c", "index_5399ee72"]:
                try:
                    await session.run(f"DROP INDEX {idx} IF EXISTS")
                except Exception:
                    pass

            # 4b. Create indexes
            print("📇 Creating indexes...")
            await session.run("CREATE INDEX IF NOT EXISTS FOR (p:Perfume) ON (p.name)")
            await session.run("CREATE INDEX IF NOT EXISTS FOR (b:Brand) ON (b.name)")
            await session.run("CREATE INDEX IF NOT EXISTS FOR (n:Note) ON (n.name)")
            await session.run("CREATE INDEX IF NOT EXISTS FOR (a:Accord) ON (a.name)")

            # 4c. Create Emotion nodes
            print("😊 Creating emotions...")
            for eid, elabel in EMOTIONS:
                await session.run(
                    "MERGE (e:Emotion {name: $name}) SET e.label = $label",
                    name=eid, label=elabel,
                )

            # 4d. Create Scene nodes
            print("🎬 Creating scenes...")
            for sid, slabel in SCENES:
                await session.run(
                    "MERGE (s:Scene {name: $name}) SET s.label = $label",
                    name=sid, label=slabel,
                )

            # 4e. Create Brand nodes (batch)
            print("🏷️  Creating brands...")
            brands_done: set[str] = set()
            brand_count = 0
            for item in perfumes_all:
                brand_name = (item.get("brandName") or "").strip()
                if not brand_name or brand_name in brands_done:
                    continue
                brands_done.add(brand_name)
                brand_count += 1
                await session.run(
                    "MERGE (b:Brand {name: $name})",
                    name=brand_name,
                )
            print(f"   {brand_count} brands created")

            # 4f. Create Perfume nodes + relationships
            print("🧴 Creating perfumes...")
            notes_done: set[str] = set()
            accords_done: set[str] = set()
            perfume_count = 0
            skipped_no_notes = 0
            rel_counts = {"BY": 0, "HAS_NOTE": 0, "HAS_ACCORD": 0,
                          "SUITS_SEASON": 0, "BEST_AT": 0}

            for item in perfumes_all:
                brand_name = (item.get("brandName") or "").strip()
                perfume_title = (item.get("title") or "").strip()[:100]
                perfume_url = (item.get("url") or "").strip()

                # Parse notes
                desc = item.get("description") or ""
                notes = parse_notes_from_desc(desc)
                all_notes = notes["top"] + notes["middle"] + notes["base"]

                if not all_notes:
                    pyramid = item.get("pyramid")
                    if pyramid and pyramid.get("allNotes"):
                        all_notes = [n["name"] for n in pyramid["allNotes"] if n.get("name")]

                if not all_notes:
                    skipped_no_notes += 1
                    continue

                perfume_count += 1
                if perfume_count % 100 == 0:
                    print(f"   {perfume_count} perfumes...")

                rating = item.get("perfumeRating")
                longevity = item.get("longevityAverage")
                sillage = item.get("sillageAverage")

                # Create Perfume node (MERGE uses name as key since no unique id)
                await session.run("""
                    MERGE (p:Perfume {name: $name})
                    SET p.url = $url,
                        p.rating = $rating,
                        p.longevity = $longevity,
                        p.sillage = $sillage
                """, name=perfume_title, url=perfume_url,
                     rating=rating, longevity=longevity, sillage=sillage)

                # Create relationship to Brand
                await session.run("""
                    MATCH (p:Perfume {name: $perfume_name})
                    MATCH (b:Brand {name: $brand_name})
                    MERGE (p)-[:BY]->(b)
                """, perfume_name=perfume_title, brand_name=brand_name)
                rel_counts["BY"] += 1

                # Create Note nodes + HAS_NOTE relationships
                note_names = []
                for note_name in all_notes:
                    note_clean = note_name.strip()
                    if len(note_clean) < 2:
                        continue
                    note_names.append(note_clean)
                    if note_clean not in notes_done:
                        notes_done.add(note_clean)
                        await session.run(
                            "MERGE (n:Note {name: $name})",
                            name=note_clean,
                        )

                top_len = len(notes["top"])
                mid_len = len(notes["middle"])
                for i, note_clean in enumerate(note_names):
                    if i < top_len:
                        layer = "top"
                    elif i < top_len + mid_len:
                        layer = "middle"
                    else:
                        layer = "base"
                    await session.run("""
                        MATCH (p:Perfume {name: $perfume_name})
                        MATCH (n:Note {name: $note_name})
                        MERGE (p)-[:HAS_NOTE {layer: $layer}]->(n)
                    """, perfume_name=perfume_title, note_name=note_clean, layer=layer)
                    rel_counts["HAS_NOTE"] += 1

                # Create Accord nodes + HAS_ACCORD relationships
                accords = item.get("mainAccords") or []
                for acc in accords:
                    acc_name = acc["accord"].strip()
                    acc_value = acc.get("value", 50)
                    if acc_name not in accords_done:
                        accords_done.add(acc_name)
                        await session.run(
                            "MERGE (a:Accord {name: $name})",
                            name=acc_name,
                        )
                    await session.run("""
                        MATCH (p:Perfume {name: $perfume_name})
                        MATCH (a:Accord {name: $acc_name})
                        MERGE (p)-[:HAS_ACCORD {score: $score}]->(a)
                    """, perfume_name=perfume_title, acc_name=acc_name, score=acc_value)
                    rel_counts["HAS_ACCORD"] += 1

                # Season relationships
                seasonal = item.get("seasonBreakout", {})
                if seasonal:
                    season_scores = {
                        "winter": seasonal.get("winter", 0),
                        "spring": seasonal.get("spring", 0),
                        "summer": seasonal.get("summer", 0),
                        "autumn": seasonal.get("autumn", 0),
                    }
                    if any(season_scores.values()):
                        top_season = max(season_scores, key=season_scores.get)
                        scene_map = {"winter": "home", "spring": "work",
                                     "summer": "explore", "autumn": "party"}
                        scene_id = scene_map.get(top_season, "explore")
                        await session.run("""
                            MATCH (p:Perfume {name: $perfume_name})
                            MATCH (s:Scene {name: $scene_id})
                            MERGE (p)-[:SUITS_SEASON {season: $season}]->(s)
                        """, perfume_name=perfume_title, scene_id=scene_id, season=top_season)
                        rel_counts["SUITS_SEASON"] += 1

                # Time-of-day relationships
                day_score = seasonal.get("day", 0)
                night_score = seasonal.get("night", 0)
                if day_score > night_score:
                    await session.run("""
                        MATCH (p:Perfume {name: $perfume_name})
                        MATCH (s:Scene {name: 'work'})
                        MERGE (p)-[:BEST_AT {time: 'day'}]->(s)
                    """, perfume_name=perfume_title)
                    rel_counts["BEST_AT"] += 1
                elif night_score > 0:
                    await session.run("""
                        MATCH (p:Perfume {name: $perfume_name})
                        MATCH (s:Scene {name: 'date'})
                        MERGE (p)-[:BEST_AT {time: 'night'}]->(s)
                    """, perfume_name=perfume_title)
                    rel_counts["BEST_AT"] += 1

            # 4g. Create SOOTHES edges
            print("🔗 Creating emotion→accord edges...")
            for emo, accord, weight in EMOTION_ACCORD_MAP:
                await session.run("""
                    MATCH (e:Emotion {name: $emo})
                    MATCH (a:Accord {name: $accord})
                    MERGE (e)-[:SOOTHES {weight: $weight}]->(a)
                """, emo=emo, accord=accord, weight=weight)

            # 4h. Summary
            result = await session.run("""
                MATCH (n)
                RETURN labels(n)[0] AS label, count(n) AS cnt
                ORDER BY cnt DESC
            """)
            records = await result.data()

            print("\n" + "=" * 50)
            print("✅ Import complete!")
            print("=" * 50)
            print(f"{'Type':12s} {'Count':>6s}")
            print("-" * 20)
            for r in records:
                print(f"{r['label']:12s} {r['cnt']:>6d}")
            print("-" * 20)
            print(f"Perfumes imported:     {perfume_count}")
            print(f"Skipped (no notes):    {skipped_no_notes}")
            print(f"Unique accords:        {len(accords_done)}")
            print(f"Unique notes:          {len(notes_done)}")
            print(f"Relationships created:")
            for rel, cnt in rel_counts.items():
                print(f"  {rel:15s} {cnt:>6d}")

    finally:
        await driver.close()

if __name__ == "__main__":
    asyncio.run(main())
