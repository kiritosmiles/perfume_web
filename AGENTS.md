# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

**情绪人格×香水 AI Agent** — A perfume recommendation AI agent web app for C-end users. Uses LLM + GraphRAG + three-layer memory to match user emotions, personality, and context with fragrance formulas.

**Current phase:** Pre-implementation. Documentation and design only. No code has been written.

## Document Map

### Primary Specs (authoritative for implementation)

| Document | For | Content |
|----------|:---:|---------|
| `docs/superpowers/specs/2026-06-19-A-产品需求文档.md` | PM, Designers | Project overview, user personas, core features (35 FRs), user journeys, MVP phases |
| `docs/superpowers/specs/2026-06-19-B-技术需求文档.md` | Backend, Architects | Tech stack, LLM architecture (9-call constraint matrix), database design (8-layer cache), 5 interface schemas, 18 APIs + 22 SSE events |
| `docs/superpowers/specs/2026-06-19-C-线框图.md` | Frontend, UI/UX | 16 routes, 30+ component tree, 6 page wireframes, SSE interaction timing, frontend state flows |
| `docs/superpowers/specs/2026-06-19-D-质量准则.md` | QA, Tech Lead | 18 performance metrics, 4-layer security, LLM reliability contracts, 19 boundary constraints, 13 risk items |

### Reference Documents (complete but cross-cutting)

| Document | Description |
|----------|-------------|
| `docs/需求分析文档-按业务模块.md` (v2.7) | Original requirements doc — 9 modules, 64 FRs. Kept as complete reference. |
| `docs/superpowers/specs/2026-06-19-业务流设计.md` (v1.1) | Business flow design — full-link journeys, cross-module data flow, frontend-backend interaction protocol, user tier quotas. |

### Document Relationships

```
需求分析文档 v2.7 ──┬──→ A. PRD
                   ├──→ B. TRD
  (complete ref)   ├──→ C. Wireframe
                   └──→ D. Quality

业务流设计 v1.1 ────┴──→ (same 4 docs, cross-referenced)
```

## Key Technical Decisions (from requirements)

- **LLM Strategy:** Dual-path (BERT ~50ms for 70% text + LLM fallback ~800ms for 30%), 9 call points each with timeout/retry/degrade contract. Cumulative cap: 10s per request.
- **Reasoning:** Fast mode (~88%, single LLM) vs Deep mode (~12%, Supervisor rule engine + 2 parallel Subagents). Weighted avg skeleton latency ~1.37s.
- **Memory:** 3-layer architecture — Layer 1 (Redis 1+5 sliding window), Layer 2 hot (Redis + PG dual-write), Layer 2 cold archive (S3 + FAISS daily rebuild), Layer 3 (external preferences, intent-gated).
- **Agent Gate:** Two hard-boundary decision nodes (info completeness gate before generation, semantic gate on 2nd refinement). 500ms budget each.
- **User Tiers:** Guest (1 session), Free (10 sessions + 15 gens + 3 deep/day), Premium (unlimited + priority queue).
- **MVP Scope:** Recommendation experience loop only. No purchase/payment/order management, no B-end perfumer platform.
- **Tech Stack:** Python FastAPI backend, Neo4j GraphRAG, React/Vue frontend with SSE streaming, PostgreSQL + Redis + object storage.

## Git Conventions

- Branch: `master` (main, single branch for now)
- Commit messages in Chinese, co-authored by Codex
- Commit format: `docs: <description in Chinese>`

## Working in This Repo

- All specs are in `docs/superpowers/specs/`. New design docs follow the `YYYY-MM-DD-<topic>-design.md` naming convention.
- The brainstorming skill should be used before any implementation task.
- When implementation begins, follow the 4-spec split: PRD defines what to build, TRD defines how, Wireframe defines the UI, Quality defines the bar.
- Cross-reference between docs using `详见 xxx 文档 §x.x` format.
