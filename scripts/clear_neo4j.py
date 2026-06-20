"""Clear Neo4j data in tiny batches to avoid OOM."""
import requests

URL = "http://localhost:7474/db/neo4j/tx/commit"
AUTH = ("neo4j", "perfume_dev")
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


def run_query(stmt: str) -> list:
    r = requests.post(URL, auth=AUTH, headers=HEADERS, json={"statements": [{"statement": stmt}]}, timeout=30)
    data = r.json()
    if data.get("errors"):
        raise RuntimeError(data["errors"][0]["message"])
    return data["results"][0]["data"]


# Phase 1: Delete all relationships
print("Phase 1: Deleting relationships...")
total = 0
for i in range(2000):
    rows = run_query("MATCH ()-[r]->() WITH r LIMIT 20 DELETE r RETURN count(r) AS c")
    c = rows[0]["row"][0]
    total += c
    if c == 0:
        break
    if total % 200 == 0:
        print(f"  {total} relationships deleted")
print(f"  Total: {total} relationships")

# Phase 2: Delete all nodes
print("Phase 2: Deleting nodes...")
total = 0
for i in range(2000):
    rows = run_query("MATCH (n) WITH n LIMIT 10 DELETE n RETURN count(n) AS c")
    c = rows[0]["row"][0]
    total += c
    if c == 0:
        break
    if total % 100 == 0:
        print(f"  {total} nodes deleted")
print(f"  Total: {total} nodes")

# Verify
rows = run_query("MATCH (n) RETURN count(n) AS c")
print(f"\nRemaining nodes: {rows[0]['row'][0]}")
print("Clear complete!")
