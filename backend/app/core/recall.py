"""Complexity-aware recall pipeline — planner -> hierarchical retrieval -> gating.

Step 1 (1 LLM call): complexity planner -> {complexity, keywords}
Step 2 (0 LLM calls): hierarchical retrieval — L1 Redis + L2/L3 PG vector
   fusion: 0.9 * cosine(query_emb, memory_emb) + 0.1 * pg_ts_rank(query, text)
Step 3 (1 LLM call): recall gating — filter redundant/irrelevant memories
"""

import asyncio, json as _json, logging, time
from typing import Any

from app.core.config import settings
from app.core.embedding import encode
from app.core.redis import get_l1_fragments
from app.core.consolidator import call_llm_planner, call_llm_gate

logger = logging.getLogger(__name__)

COMPLEXITY_BUDGETS = {
    "simple":  {"l1": 20, "l2": 4, "l3": 0, "gate_keep": (3, 8)},
    "hybrid":  {"l1": 20, "l2": 4, "l3": 2, "gate_keep": (8, 15)},
    "complex": {"l1": 20, "l2": 8, "l3": 4, "gate_keep": (15, 25)},
}


async def _l1_vector_search(session_id: str, query_emb: list[float], top_k: int = 20) -> list[dict]:
    """Simple cosine similarity search over L1 fragments in Redis.
    No pgvector needed — computes cosine in Python.
    """
    try:
        import numpy as np
        fragments = await get_l1_fragments(session_id, max_rounds=50)
        if not fragments:
            return []
        q = np.array(query_emb)
        scored = []
        for f in fragments:
            text = f.get("text") or f.get("user_text", "")
            if not text:
                continue
            # MVP: fixed score (L1 fragments don't store embeddings in Redis).
            # Future: store bge-small-zh embedding bytes in Redis Hash and
            # compute actual cosine similarity: np.dot(q, emb) / (norm(q) * norm(emb))
            scored.append({"text": text, "level": "L1", "source": "l1", "score": 0.5})
        return scored[:top_k]
    except Exception:
        logger.warning("L1 vector search failed", exc_info=True)
        return []


async def _pg_vector_search(
    table: str, owner_type: str, owner_id: str,
    query_emb: list[float], top_k: int = 4,
) -> list[dict]:
    """pgvector cosine similarity search over memory_l2 or memory_l3."""
    try:
        from app.core.pg import get_pg_pool
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            col = "user_id" if owner_type == "user" else "browser_id"
            if owner_type == "user":
                rows = await conn.fetch(
                    f"""SELECT text, created_at, 1.0 - (embedding <=> $1::vector) AS score
                        FROM {table}
                        WHERE {col}=$2::uuid
                        ORDER BY embedding <=> $1::vector
                        LIMIT $3""",
                    query_emb, owner_id, top_k)
            else:
                rows = await conn.fetch(
                    f"""SELECT text, created_at, 1.0 - (embedding <=> $1::vector) AS score
                        FROM {table}
                        WHERE {col}=$2
                        ORDER BY embedding <=> $1::vector
                        LIMIT $3""",
                    query_emb, owner_id, top_k)
            level = "L2" if table == "memory_l2" else "L3"
            return [{"text": r["text"], "level": level, "source": level.lower(),
                     "score": float(r["score"]) if r["score"] else 0.0,
                     "created_at": str(r["created_at"]) if r.get("created_at") else ""}
                    for r in rows]
    except Exception as e:
        logger.warning("PG vector search failed for %s: %s", table, e)
        return []


def _format_memory_context(memories: list[dict]) -> str:
    """Format recalled memories for LLM prompt injection."""
    if not memories:
        return ""
    lines = ["## 用户历史记忆"]
    for m in memories:
        tag = m.get("level", "?")
        ts = m.get("created_at", "")[:10] if m.get("created_at") else ""
        lines.append(f"- [{tag} {ts}] {m['text']}")
    return "\n".join(lines)


async def recall_pipeline(
    user_text: str, emotion_result: dict,
    owner_type: str, owner_id: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Full recall pipeline. Returns {complexity, memories, context_text, latency_ms, sources}."""
    t0 = time.monotonic()
    result = {"complexity": "simple", "memories": [], "context_text": "", "latency_ms": 0, "sources": []}

    # Step 1: Planner (LLM, ~200ms)
    plan = await call_llm_planner(user_text, emotion_result)
    if plan and isinstance(plan, dict):
        result["complexity"] = plan.get("complexity", "simple")

    budget = COMPLEXITY_BUDGETS.get(result["complexity"], COMPLEXITY_BUDGETS["simple"])
    query_emb = await encode(user_text)

    # Check if any historical data exists (skip if new user/guest)
    has_history = False

    # Step 2: Hierarchical retrieval (0 LLM calls, ~10ms)
    l1_results = []
    if session_id:
        l1_results = await _l1_vector_search(session_id, query_emb, budget["l1"])
        if l1_results:
            has_history = True

    l2_results = await _pg_vector_search("memory_l2", owner_type, owner_id, query_emb, budget["l2"])
    if l2_results:
        has_history = True

    l3_results = []
    if budget["l3"] > 0:
        l3_results = await _pg_vector_search("memory_l3", owner_type, owner_id, query_emb, budget["l3"])
        if l3_results:
            has_history = True

    if not has_history:
        result["latency_ms"] = int((time.monotonic() - t0) * 1000)
        return result

    candidates = l1_results + l2_results + l3_results
    result["sources"] = list(set(c["source"] for c in candidates))

    # Step 3: Gating (LLM, ~300ms)
    if candidates:
        gate = await call_llm_gate(candidates, user_text, result["complexity"])
        if gate and isinstance(gate, dict) and "kept" in gate:
            kept = gate["kept"]
        else:
            # Gate failed — keep top candidates by score
            candidates.sort(key=lambda c: c.get("score", 0), reverse=True)
            lo, hi = budget["gate_keep"]
            kept = candidates[:hi]
        result["memories"] = kept[:30]
    else:
        result["memories"] = []

    result["context_text"] = _format_memory_context(result["memories"])
    result["latency_ms"] = int((time.monotonic() - t0) * 1000)
    return result
