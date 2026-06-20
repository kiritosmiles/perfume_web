"""Analyze why only 268/1198 perfumes were imported into Neo4j."""
import json, glob
from pathlib import Path

ROOT = Path(__file__).parent.parent
json_files = sorted(glob.glob(str(ROOT / "docs/dataset_fragrantica_*.json")))

seen_urls = set()
dupe_urls = 0
total = 0
no_brand = 0
no_notes = 0
has_pyramid = 0
has_html = 0

for jf in json_files:
    with open(jf, encoding="utf-8") as f:
        data = json.load(f)
    for item in data:
        total += 1
        if item.get("brandName") is None:
            no_brand += 1
            continue
        if "404 - Page Not Found" in (item.get("title") or ""):
            continue
        url = item.get("url", "")
        if url in seen_urls:
            dupe_urls += 1
        seen_urls.add(url)

print(f"Total raw records:      {total}")
print(f"No brand:               {no_brand}")
print(f"Unique URLs (imported): {len(seen_urls)}")
print(f"Duplicate URLs skipped: {dupe_urls}")
print(f"Expected import:        {total - no_brand - dupe_urls}")
