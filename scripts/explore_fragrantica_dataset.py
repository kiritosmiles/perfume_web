"""拉取 FragDBnet 香水数据集并输出探索结果到文档

Usage: python scripts/explore_fragrantica_dataset.py
Output: docs/superpowers/specs/fragrantica-dataset-exploration.md
"""

from pathlib import Path
from datasets import load_dataset

OUTPUT = Path(__file__).parent.parent / "docs/superpowers/specs/fragrantica-dataset-exploration.md"

ds = load_dataset("FragDBnet/fragrance-database")
s = ds["train"]  # 通常只有一个 split

lines = []
lines.append("# FragDBnet Fragrance Database — 数据集探索")
lines.append("")
lines.append(f"> 生成时间: {__import__('datetime').datetime.now().isoformat(timespec='seconds')}")
lines.append(f"> 数据集: FragDBnet/fragrance-database")
lines.append("")
lines.append("## 概览")
lines.append("")
lines.append(f"- **Split 数量**: {len(ds.keys())} — {list(ds.keys())}")
lines.append(f"- **训练集行数**: {len(s)}")
lines.append(f"- **字段数量**: {len(s.column_names)}")
lines.append("")

lines.append("## 字段列表")
lines.append("")
for i, col in enumerate(s.column_names):
    lines.append(f"{i+1}. `{col}`")
lines.append("")

# 全部字段抽样展示
N_SAMPLE = 20
sample = s[:N_SAMPLE]
for col in s.column_names:
    lines.append(f"## 字段 `{col}`")
    lines.append("")
    unique = set()
    for v in sample[col]:
        if v is not None:
            unique.add(str(v)[:120])
    lines.append(f"- 唯一值数 (前{N_SAMPLE}条): {len(unique)}")
    for j, v in enumerate(sample[col]):
        if v is not None:
            lines.append(f"  [{j}] {str(v)[:300]}")
    lines.append("")

# 单条完整样本
lines.append("## 第1条完整样本")
lines.append("")
lines.append("```json")
import json
try:
    lines.append(json.dumps(s[0], indent=2, ensure_ascii=False, default=str))
except Exception:
    lines.append(str(s[0]))
lines.append("```")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("\n".join(lines), encoding="utf-8")
print(f"✅ 已写入 {OUTPUT}")
print(f"   {len(s)} 行 × {len(s.column_names)} 列")
