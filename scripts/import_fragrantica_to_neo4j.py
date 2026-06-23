"""导入 Fragrantica 数据集到 Neo4j 图谱初始化 Cypher 文件（合并去重版）

Usage: python scripts/import_fragrantica_to_neo4j.py
Input: docs/dataset_fragrantica_*.json (全部文件合并去重)
Output: docker/neo4j/import/init-fragrances.cypher
"""

import json
import re
import glob
from pathlib import Path
from html import unescape

ROOT = Path(__file__).parent.parent

# 1. 加载所有 JSON，合并去重
json_files = sorted(glob.glob(str(ROOT / "docs/dataset_fragrantica_*.json")))
if not json_files:
    print("❌ 未找到 dataset_fragrantica_*.json")
    exit(1)

seen_urls = set()
perfumes_all = []
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
    fname = Path(jf).name
    print(f"  {fname[:35]:40s} {len(raw):>4} raw  →  {added:>4} new")

print(f"\n📊 合并: {total_raw} raw → {len(perfumes_all)} unique ({total_raw - len(perfumes_all)} dupes)\n")


# 2. 解析 description 中的前中后调
def parse_notes_from_desc(desc: str):
    """从 HTML description 中提取 top/middle/base notes 名称"""
    text = unescape(re.sub(r"<[^>]+>", " ", desc))
    result = {"top": [], "middle": [], "base": []}

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


# 3. 生成 Cypher
cypher_lines = []
cypher_lines.append("// 香水图谱初始化脚本 — 全量合并去重版")
cypher_lines.append(f"// 来源文件: {len(json_files)} 个")
cypher_lines.append(f"// 生成时间: {__import__('datetime').datetime.now().isoformat(timespec='seconds')}")
cypher_lines.append(f"// 输入: {total_raw} raw → {len(perfumes_all)} unique perfumes")
cypher_lines.append("")
cypher_lines.append("// 清空旧数据")
cypher_lines.append("MATCH (n) DETACH DELETE n;")
cypher_lines.append("")
cypher_lines.append("// 索引")
cypher_lines.append("CREATE INDEX IF NOT EXISTS FOR (p:Perfume) ON (p.name);")
cypher_lines.append("CREATE INDEX IF NOT EXISTS FOR (b:Brand) ON (b.name);")
cypher_lines.append("CREATE INDEX IF NOT EXISTS FOR (n:Note) ON (n.name);")
cypher_lines.append("CREATE INDEX IF NOT EXISTS FOR (a:Accord) ON (a.name);")
cypher_lines.append("")

# 情绪节点
EMOTIONS = [
    ("joy", "开心"), ("sadness", "难过"), ("anxiety", "焦虑"), ("calm", "平静"),
    ("excitement", "兴奋"), ("nostalgia", "怀旧"), ("romance", "浪漫"), ("melancholy", "忧郁"),
]
cypher_lines.append("// === 情绪节点 ===")
for eid, elabel in EMOTIONS:
    cypher_lines.append(f"CREATE (:Emotion {{name: '{eid}', label: '{elabel}'}});")
cypher_lines.append("")

# 场景节点
SCENES = [
    ("work", "通勤工作"), ("date", "约会之夜"), ("home", "宅家放松"),
    ("party", "聚会社交"), ("gift", "挑选礼物"), ("explore", "随便看看"),
]
cypher_lines.append("// === 场景节点 ===")
for sid, slabel in SCENES:
    cypher_lines.append(f"CREATE (:Scene {{name: '{sid}', label: '{slabel}'}});")
cypher_lines.append("")

# 品牌 + 香水 + 香调 + 香韵
brands_seen = set()
notes_seen = set()
accords_seen = set()
perfume_count = 0
skipped_no_notes = 0

cypher_lines.append("// === 品牌节点 ===")
for item in perfumes_all:
    brand_name = (item.get("brandName") or "").replace("'", "\\'")
    brand_id = re.sub(r"[^a-z0-9_]", "_", brand_name.lower().strip())
    if brand_name and brand_id not in brands_seen:
        brands_seen.add(brand_id)
        cypher_lines.append(f"CREATE (b_{brand_id}:Brand {{name: '{brand_name}'}});")

cypher_lines.append("")
cypher_lines.append("// === 香水 + 香调 + 香韵 ===")

for item in perfumes_all:
    brand_name = (item.get("brandName") or "").replace("'", "\\'")
    perfume_title = (item.get("title") or "").replace("'", "\\'")[:100]
    perfume_url = (item.get("url") or "").replace("'", "\\'")
    brand_id = re.sub(r"[^a-z0-9_]", "_", brand_name.lower().strip())

    # 解析 notes
    desc = item.get("description") or ""
    notes = parse_notes_from_desc(desc)
    all_notes = notes["top"] + notes["middle"] + notes["base"]

    # fallback: pyramid.allNotes
    if not all_notes:
        pyramid = item.get("pyramid")
        if pyramid and pyramid.get("allNotes"):
            all_notes = [n["name"] for n in pyramid["allNotes"] if n.get("name")]

    if not all_notes:
        skipped_no_notes += 1
        continue

    perfume_count += 1
    pid = item.get("id", perfume_count)
    safe_name = perfume_title.replace("'", "").replace('"', '')[:80]

    image_url = (item.get("primaryImageUrl") or "").replace("'", "\\'")
    cypher_lines.append(f"// {brand_name} — {safe_name}")
    cypher_lines.append(
        f"CREATE (p_{pid}:Perfume {{"
        f"name: '{safe_name}', "
        f"url: '{perfume_url}', "
        f"image: '{image_url}', "
        f"rating: {item.get('perfumeRating') or 'null'}, "
        f"longevity: {item.get('longevityAverage') or 'null'}, "
        f"sillage: {item.get('sillageAverage') or 'null'}"
        f"}});"
    )
    cypher_lines.append(f"MATCH (p_{pid}:Perfume), (b_{brand_id}:Brand) CREATE (p_{pid})-[:BY]->(b_{brand_id});")

    # 香调节点 + 连接
    note_ids = []
    for note_name in all_notes:
        note_name_clean = note_name.strip().replace("'", "\\'")
        if len(note_name_clean) < 2:
            continue
        nid = re.sub(r"[^a-z0-9_]", "_", note_name_clean.lower())
        note_ids.append(nid)
        if nid not in notes_seen:
            notes_seen.add(nid)
            cypher_lines.append(f"CREATE (n_{nid}:Note {{name: '{note_name_clean}'}});")

    top_len = len(notes["top"])
    mid_len = len(notes["middle"])
    for i, nid in enumerate(note_ids):
        if i < top_len:
            layer = "top"
        elif i < top_len + mid_len:
            layer = "middle"
        else:
            layer = "base"
        cypher_lines.append(f"MATCH (p_{pid}:Perfume), (n_{nid}:Note) CREATE (p_{pid})-[:HAS_NOTE {{layer: '{layer}'}}]->(n_{nid});")

    # 香韵节点 + 连接
    accords = item.get("mainAccords") or []
    for acc in accords:
        acc_name = acc["accord"].replace("'", "\\'")
        acc_value = acc.get("value", 50)
        aid = re.sub(r"[^a-z0-9_]", "_", acc_name.lower())
        if aid not in accords_seen:
            accords_seen.add(aid)
            cypher_lines.append(f"CREATE (a_{aid}:Accord {{name: '{acc_name}'}});")
        cypher_lines.append(
            f"MATCH (p_{pid}:Perfume), (a_{aid}:Accord) "
            f"CREATE (p_{pid})-[:HAS_ACCORD {{score: {acc_value}}}]->(a_{aid});"
        )

    # 季节关系
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
            scene_map = {"winter": "home", "spring": "work", "summer": "explore", "autumn": "party"}
            scene_id = scene_map.get(top_season, "explore")
            cypher_lines.append(
                f"MATCH (p_{pid}:Perfume), (s:Scene {{name: '{scene_id}'}}) "
                f"CREATE (p_{pid})-[:SUITS_SEASON {{season: '{top_season}'}}]->(s);"
            )

    # 时间关系
    day_score = seasonal.get("day", 0)
    night_score = seasonal.get("night", 0)
    if day_score > night_score:
        cypher_lines.append(f"MATCH (p_{pid}:Perfume), (s:Scene {{name: 'work'}}) CREATE (p_{pid})-[:BEST_AT {{time: 'day'}}]->(s);")
    elif night_score > 0:
        cypher_lines.append(f"MATCH (p_{pid}:Perfume), (s:Scene {{name: 'date'}}) CREATE (p_{pid})-[:BEST_AT {{time: 'night'}}]->(s);")

cypher_lines.append("")

# 情绪→香韵映射
cypher_lines.append("// === 情绪→香韵知识边 ===")
# Expanded emotion→accord mapping (Tier 1/2/3, ~75 edges total)
# Goal: break recommendation monotony by giving each emotion 8-10 accord paths
# instead of 2-3, so that low-weight emotions and different scenes pull in diverse
# perfumes from across the full accord spectrum.
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
for emo, accord, weight in EMOTION_ACCORD_MAP:
    aid = re.sub(r"[^a-z0-9_]", "_", accord.lower())
    cypher_lines.append(
        f"MATCH (e:Emotion {{name: '{emo}'}}), (a:Accord {{name: '{accord}'}}) "
        f"CREATE (e)-[:SOOTHES {{weight: {weight}}}]->(a);"
    )
cypher_lines.append("")

# 统计
cypher_lines.append("// === 导入统计 ===")
cypher_lines.append(f"// Brands: {len(brands_seen)}")
cypher_lines.append(f"// Perfumes: {perfume_count}")
cypher_lines.append(f"// Skipped (no notes): {skipped_no_notes}")
cypher_lines.append(f"// Unique Notes: {len(notes_seen)}")
cypher_lines.append(f"// Unique Accords: {len(accords_seen)}")
cypher_lines.append(f"// Emotion-Accord edges: {len(EMOTION_ACCORD_MAP)}")

# 写入
output_dir = ROOT / "docker/neo4j/import"
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / "init-fragrances.cypher"

with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(cypher_lines))

print(f"✅ 输出: {output_path}")
print(f"   Brands:     {len(brands_seen)}")
print(f"   Perfumes:   {perfume_count}  (skipped {skipped_no_notes} with no notes)")
print(f"   Notes:      {len(notes_seen)}")
print(f"   Accords:    {len(accords_seen)}")
print(f"   情绪映射:   {len(EMOTION_ACCORD_MAP)} 条")
print(f"   Cypher:     {len(cypher_lines)} 行")
