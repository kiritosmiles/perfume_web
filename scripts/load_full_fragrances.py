"""加载 FragDBnet 全部香水数据（fragrances config）"""

from datasets import load_dataset

print("Loading 'fragrances' config...")
ds = load_dataset("FragDBnet/fragrance-database", "fragrances", split="train", streaming=True)

count = 0
pids = []
for i, row in enumerate(ds):
    count += 1
    pids.append(row.get("pid"))
    if count <= 5:
        print(f"  [{count}] pid={row.get('pid')}, name={row.get('name')}, brand={row.get('brand')}")
    if count % 5000 == 0:
        print(f"  ... {count} rows loaded so far ...")

print(f"\n✅ fragrances config: {count} rows total")
