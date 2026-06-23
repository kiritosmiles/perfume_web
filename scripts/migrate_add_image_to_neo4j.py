"""One-shot migration: add `image` property to existing Perfume nodes.

Reads all dataset_fragrantica_*.json files, builds a url→image_url map,
then updates Neo4j Perfume nodes matched by url.
"""

import json
import glob
import re
import asyncio
from pathlib import Path
from neo4j import AsyncGraphDatabase

ROOT = Path(__file__).parent.parent

NEO4J_URI = "bolt://localhost:17687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "perfume_dev"


def build_url_image_map() -> dict[str, str]:
    """Build a map of fragrantica_url → primaryImageUrl from all dataset JSONs."""
    json_files = sorted(glob.glob(str(ROOT / "docs/dataset_fragrantica_*.json")))
    url_image_map = {}
    total = 0
    for jf in json_files:
        with open(jf, encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            url = item.get("url", "")
            image = item.get("primaryImageUrl", "")
            if url and image:
                url_image_map[url] = image
            total += 1
    print(f"Built map: {len(url_image_map)} urls with images from {total} items ({len(json_files)} files)")
    return url_image_map


async def migrate():
    url_image_map = build_url_image_map()
    if not url_image_map:
        print("No images to migrate.")
        return

    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        # First count how many nodes already have image
        async with driver.session() as session:
            result = await session.run(
                "MATCH (p:Perfume) RETURN count(p) AS total, "
                "count(p.image) AS have_image"
            )
            record = await result.single()
            total = record["total"]
            have = record["have_image"]
            print(f"\nNeo4j state: {total} Perfume nodes, {have} have image, {total - have} missing")

            if have == total:
                print("All nodes already have images. Nothing to do.")
                return

            # Update in batches by matching url
            updated = 0
            not_found = 0
            batch_size = 50
            urls = list(url_image_map.keys())

            for i in range(0, len(urls), batch_size):
                batch_urls = urls[i:i + batch_size]
                params = {f"u{j}": url for j, url in enumerate(batch_urls)}
                params["images"] = {f"u{j}": url_image_map[url] for j, url in enumerate(batch_urls)}

                # Use UNWIND for batch matching
                pairs = [{"url": url, "img": url_image_map[url]} for url in batch_urls]
                result = await session.run(
                    """
                    UNWIND $pairs AS pair
                    MATCH (p:Perfume {url: pair.url})
                    WHERE p.image IS NULL
                    SET p.image = pair.img
                    RETURN count(p) AS cnt
                    """,
                    pairs=pairs,
                    timeout=10.0,
                )
                record = await result.single()
                cnt = record["cnt"]
                updated += cnt
                not_found += len(batch_urls) - cnt
                if cnt > 0:
                    print(f"  Batch {i // batch_size + 1}: updated {cnt} nodes")

            print(f"\nDone: {updated} nodes updated, {not_found} URLs not matched in Neo4j")

            # Verify
            result = await session.run(
                "MATCH (p:Perfume) RETURN count(p) AS total, "
                "count(p.image) AS have_image"
            )
            record = await result.single()
            print(f"After migration: {record['total']} total, {record['have_image']} have image")

    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(migrate())
