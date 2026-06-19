"""诊断 FragDBnet 数据集真实大小——为什么只有 10 条？"""

from datasets import load_dataset, get_dataset_config_names, get_dataset_split_names

print("=" * 60)
print("数据集诊断")
print("=" * 60)

# 1. 列出所有 configurations
try:
    configs = get_dataset_config_names("FragDBnet/fragrance-database")
    print(f"\n可用 Configs: {configs}")
except Exception as e:
    print(f"\nConfigs 查询失败: {e}")

# 2. 用默认 config
ds = load_dataset("FragDBnet/fragrance-database")
print(f"\n默认加载 — Splits: {list(ds.keys())}")
for k in ds:
    print(f"  {k}: {len(ds[k])} rows")

# 3. stream 模式——查看是否文件更大
print("\n" + "=" * 60)
print("Stream 模式探测（前 200 行）")
print("=" * 60)
ds_stream = load_dataset("FragDBnet/fragrance-database", split="train", streaming=True)
count = 0
for row in ds_stream:
    count += 1
    if count <= 3:
        print(f"  [{count}] pid={row.get('pid')}, name={row.get('name')}")
    if count >= 200:
        break
print(f"Stream 模式实际读取: {count}+ 行")

# 4. 尝试用 parquet/json 直接读
print("\n" + "=" * 60)
print("底层文件探测")
print("=" * 60)
import requests
api_url = "https://huggingface.co/api/datasets/FragDBnet/fragrance-database"
try:
    resp = requests.get(api_url, timeout=10)
    if resp.status_code == 200:
        info = resp.json()
        print(f"  ID: {info.get('id')}")
        # 查看 siblings (文件列表)
        siblings = info.get("siblings", [])
        data_files = [s for s in siblings if s['rfilename'].endswith(('.parquet','.jsonl','.csv','.json'))]
        print(f"  数据文件数: {len(data_files)}")
        for f in data_files[:10]:
            print(f"    {f['rfilename']}  ({f.get('size', '?')} bytes)")
except Exception as e:
    print(f"  API 探测失败: {e}")

print("\n✅ 诊断完成")
