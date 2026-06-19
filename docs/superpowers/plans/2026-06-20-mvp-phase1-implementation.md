# MVP Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Build guest emotion-card perfume recommendation loop: Landing -> pick emotion cards -> SSE streaming fragrance cards

**Architecture:** Docker Compose (PG+Redis+Neo4j) -> FastAPI (SSE+GraphRAG 1-hop) -> React (Apple glassmorphism+Zustand+EventSource)

**Tech Stack:** Python 3.11+ / FastAPI / Neo4j 5 / React 18+ / TypeScript strict / Vite / Tailwind CSS / Zustand / Framer Motion

## Global Constraints

- API prefix: /api/v1/
- SSE event naming: {domain}.{phase}[:{subtype}] (TRD 7.1)
- 8 predefined emotion cards with preset vectors, no BERT/LLM in MVP
- GraphRAG: 1-hop only (Emotion->SOOTHES->Accord->HAS_ACCORD->Perfume)
- UI: Apple minimalism, backdrop-blur(20px) saturate(180%), rgba(255,255,255,0.72)
- Colors: text #292524 (stone-800), secondary #78716c (stone-500), bg #fafaf9 (stone-50)
- Font: -apple-system, BlinkMacSystemFont, "SF Pro Display", "PingFang SC", sans-serif
- gen.skeleton TTFB target: <200ms (no LLM path)
- NOT in scope: registration/login, text emotion input, BERT, LLM calls, Layer 2/3 memory, gift mode, deep mode, refinement, multi-tab

---

## Task 1: Docker + PG Schema + Makefile (Infrastructure)

**Files:** docker/docker-compose.yml, docker/postgres/init/001-mvp-schema.sql, Makefile, .env.example, package.json (root)

**Produces:** 3 running containers, 5 PG tables with seeds, make commands

- [ ] **Step 1: Create docker-compose.yml** — Postgres 15-alpine + Redis 7-alpine + Neo4j 5-community, with healthchecks and named volumes
- [ ] **Step 2: Create 001-mvp-schema.sql** — 5 tables: temp_conversations, emotion_cards (8 seed rows), scene_tags (6), fragrance_templates, guest_quota
- [ ] **Step 3: Create Makefile** — docker-up, docker-down, install, dev-backend, dev-frontend, neo4j-init targets
- [ ] **Step 4: Create .env.example + root package.json** — npm workspaces config
- [ ] **Step 5: Verify** — `make docker-up` -> 3 healthy containers; psql shows 8 emotion cards
- [ ] **Step 6: Commit**

---

## Task 2: Shared Types Package (@perfume/shared)

**Files:** packages/shared/ — package.json, tsconfig.json, src/index.ts, src/types/*.ts, src/sse/events.ts

**Produces:** EmotionVector, FragranceCard, RecommendationSkeleton, SSEEvent (discriminated union, 8 MVP + 14 placeholder events), GuestSessionInput, ApiError

- [ ] **Step 1: Create package.json + tsconfig.json** — strict TS, ES2022, bundler resolution
- [ ] **Step 2: Create types/emotion.ts** — EmotionVector (8-dim), EmotionResult, SceneTag
- [ ] **Step 3: Create types/generation.ts** — RecommendationSkeleton (is_partial:true), FragranceCard (extends with copy_text, expanded_fields)
- [ ] **Step 4: Create types/session.ts + types/api.ts** — SessionIntent ("self_use"|"gift"|"explore"), GuestSessionInput, ApiError, HealthResponse
- [ ] **Step 5: Create sse/events.ts** — SSEEvent discriminated union with 22 event variants, first 8 fully typed, rest as placeholders
- [ ] **Step 6: Create index.ts** — re-export all
- [ ] **Step 7: Verify** — `cd packages/shared && npm install && npx tsc --noEmit` passes
- [ ] **Step 8: Commit**

---

## Task 3: FastAPI Skeleton + Config + Neo4j Client

**Files:** backend/pyproject.toml, backend/app/main.py, backend/app/core/config.py, backend/app/core/deps.py, backend/app/graph/client.py, backend/app/api/v1/router.py, backend/app/api/v1/health.py, backend/tests/test_health.py

**Produces:** Running FastAPI with /api/v1/health endpoint, Neo4j driver lifecycle via lifespan

- [ ] **Step 1: Create pyproject.toml** — Poetry, deps: fastapi, uvicorn, neo4j, asyncpg, redis, pydantic-settings, httpx, pytest
- [ ] **Step 2: Create core/config.py** — Settings(BaseSettings): pg_dsn property, neo4j_uri, redis_url, cors_origins, debug flag
- [ ] **Step 3: Create graph/client.py** — AsyncGraphDatabase driver singleton, get_neo4j_session() async generator, close_neo4j() cleanup
- [ ] **Step 4: Create core/deps.py** — get_db_neo4j() dependency forwarding to get_neo4j_session
- [ ] **Step 5: Create api/v1/health.py + router.py** — GET /api/v1/health returns {"status":"ok|degraded","neo4j":bool,"postgres":bool,"redis":bool}
- [ ] **Step 6: Create main.py** — FastAPI() with CORS middleware, lifespan context manager, include_router
- [ ] **Step 7: Write test_health.py** — async test with httpx ASGITransport, confirms 200 + "status" key
- [ ] **Step 8: Verify** — `poetry install && poetry run pytest tests/test_health.py -v` passes with Neo4j running
- [ ] **Step 9: Commit**

---

## Task 4: Backend Services — Emotion + Safety + Fragrance + Generation

**Files:** backend/app/models/guest.py, backend/app/services/emotion.py, backend/app/services/safety.py, backend/app/services/fragrance.py, backend/app/services/generation.py, backend/tests/test_services.py

**Produces:** 4 service modules with test coverage

- [ ] **Step 1: Write test_services.py** — tests for resolve_emotion (single card, 2-card merge), crisis_check (crisis hit, normal text), build_skeleton (3 cards from candidates), build_copy_stream (non-empty string chunks)
- [ ] **Step 2: Create models/guest.py** — GuestSessionInput(BaseModel): emotion_card_ids (list[str], 1-2), scene_tag (str|None), browser_id (str|None)
- [ ] **Step 3: Create services/emotion.py** — CARD_VECTORS dict (8 cards x 8-dim), resolve_emotion_from_cards(): single card returns its vector, 2 cards returns averaged vector, max dimension = primary_emotion
- [ ] **Step 4: Create services/safety.py** — CRISIS_KEYWORDS list (9 Chinese keywords), crisis_check() returns CrisisResult(is_crisis, severity, matched_keyword)
- [ ] **Step 5: Create services/fragrance.py** — search_fragrance_by_emotion() executes Cypher: MATCH Emotion->SOOTHES->Accord<-HAS_ACCORD-Perfume, weighted score = r.weight * ha.score/100 + rating*0.1, LIMIT 10, returns list[dict]
- [ ] **Step 6: Create services/generation.py** — build_skeleton(): Top 3 candidates -> notes split into 3rds (top/mid/base), match_score = int(score*100) capped at 95. build_copy_stream(): STORY_TEMPLATES dict per emotion, split into sentence chunks
- [ ] **Step 7: Verify** — `poetry run pytest tests/test_services.py -v -k "not search"` -> 4 PASS
- [ ] **Step 8: Commit**

---

## Task 5: SSE Protocol + Streaming Endpoint

**Files:** backend/app/sse/protocol.py, backend/app/sse/stream.py, backend/app/api/v1/guest.py, backend/tests/test_guest_session.py

**Produces:** POST + GET /api/v1/guest/sessions returning SSE with 7-event sequence

- [ ] **Step 1: Write test_guest_session.py** — test POST returns 200 + text/event-stream, test all 7 event types present in body (chat.ack, chat.emotion, gen.start, gen.skeleton, gen.detail, gen.copy, gen.complete), test invalid input returns 422
- [ ] **Step 2: Create sse/protocol.py** — sse(event_type, data) helper formats "event: TYPE\ndata: JSON\n\n", now_iso() helper
- [ ] **Step 3: Create sse/stream.py** — sse_event_stream() async generator: 1) ack, 2) emotion (resolve_emotion_from_cards), 3) gen.start, 4) GraphRAG search (try/except degrade), 5) skeleton (build_skeleton), 6) detail per card, 7) copy chunks per card (build_copy_stream iteration), 8) gen.complete. On no candidates: gen.error with NO_MATCH code
- [ ] **Step 4: Create api/v1/guest.py** — POST endpoint accepts GuestSessionInput, runs crisis_check, returns StreamingResponse. ADDITIONAL GET endpoint for browser EventSource (params: card_ids=joy,calm&scene=work)
- [ ] **Step 5: Verify** — `poetry run pytest tests/test_guest_session.py -v` -> validation test PASS, SSE test PASS (with Neo4j)
- [ ] **Step 6: Commit**

---

## Task 6: Vite + React + Tailwind Scaffold + Design System

**Files:** packages/frontend/ — package.json, vite.config.ts, tsconfig.json, tailwind.config.ts, postcss.config.js, index.html, src/main.tsx, src/App.tsx, src/styles/index.css, src/components/ui/Button.tsx, src/components/ui/Chip.tsx, src/components/ui/Skeleton.tsx

**Produces:** Running Vite dev server at :5173 with Tailwind + custom glass design tokens

- [ ] **Step 1: Create package.json** — react 18, react-router-dom, zustand, framer-motion, tailwindcss, vite
- [ ] **Step 2: Create config files** — vite.config.ts (proxy /api->:8000), tailwind.config.ts (extended glass bg/shadow/blur/font), tsconfig.json (strict, jsx react-jsx, path alias to @perfume/shared)
- [ ] **Step 3: Create styles/index.css** — Tailwind directives + @layer components: .glass-card, .glass-nav, .glass-input with backdrop-blur(20px) saturate(180%) + @keyframes shimmer
- [ ] **Step 4: Create index.html** — lang=zh-CN, bg-stone-50, SF font stack
- [ ] **Step 5: Create main.tsx + App.tsx** — ReactDOM.createRoot, BrowserRouter with single "/" -> LandingPage route
- [ ] **Step 6: Create UI primitives** — Button (glass/primary variants, rounded-full), Chip (selected state, rounded-full), Skeleton (shimmer animation, rounded-lg)
- [ ] **Step 7: Verify** — `npm install && npm run dev`, open :5173 -> no console errors, bg-stone-50 visible
- [ ] **Step 8: Commit**

---

## Task 7: Zustand Stores + SSE Client + useSSE Hook

**Files:** packages/frontend/src/stores/sessionStore.ts, packages/frontend/src/stores/generationStore.ts, packages/frontend/src/stores/uiStore.ts, packages/frontend/src/lib/sseClient.ts, packages/frontend/src/lib/apiClient.ts, packages/frontend/src/hooks/useSSE.ts

**Produces:** 3 Zustand stores, native EventSource wrapper with retry, useSSE hook dispatching events to stores

- [ ] **Step 1: Create sessionStore.ts** — {sessionId, emotion:EmotionResult|null, sseStatus, crisis}, setEmotion(), setSSEStatus()
- [ ] **Step 2: Create generationStore.ts** — {generationId, phase:"idle"|"skeleton"|"detail"|"copy"|"complete"|"error", mode, cards:FragranceCard[], error}, startGeneration(id,mode), setSkeleton(recs->cards with empty copy_text), addDetail(rank,fields->merge expanded_fields), addCopyChunk(rank,chunk->concat), completeGeneration(), interruptGeneration(), setError()
- [ ] **Step 3: Create uiStore.ts** — {loading, mobileMenuOpen}, setLoading(), toggleMobileMenu()
- [ ] **Step 4: Create sseClient.ts** — createSSEConnection(url, onEvent, onStatus): native EventSource, addEventListener for all 8 MVP event types, exponential backoff [1s,2s,4s,4s,4s], 30s heartbeat timeout, returns cleanup function
- [ ] **Step 5: Create apiClient.ts** — apiPost<T>(path, body): fetch wrapper, JSON parse error into {code,message,retryable}
- [ ] **Step 6: Create useSSE.ts** — useEffect hook: checks url param, creates EventSource, registers event handlers dispatching to sessionStore.setEmotion/generationStore.*, returns cleanup on unmount/url change
- [ ] **Step 7: Verify** — `npx tsc --noEmit` passes
- [ ] **Step 8: Commit**

---

## Task 8: Core UI Components — Emotion + Chat + Fragrance Cards

**Files:** packages/frontend/src/components/ — emotion/EmotionCard.tsx, emotion/EmotionCardPicker.tsx, emotion/EmotionConfirmation.tsx, chat/SceneTagChips.tsx, chat/ChatBody.tsx, chat/ChatInput.tsx, chat/ThinkingIndicator.tsx, fragrance/ScoreBar.tsx, fragrance/NotesCombination.tsx, fragrance/ActionBar.tsx, fragrance/FragranceCard.tsx

**Produces:** Complete component tree for GuestChatPage with Apple glassmorphism styling

- [ ] **Step 1: Emotion components** — EmotionCard (glass-card, 80x96px, ring on selected, framer-motion whileTap, disabled+unselected=opacity-40), EmotionCardPicker (grid of 8, max 2 selected, toggle logic), EmotionConfirmation (glass-card banner: "I sense you're feeling... [emotion label]", correct button)
- [ ] **Step 2: Chat components** — SceneTagChips (6 scene chips using Chip component), ChatBody (flex-1 overflow-y-auto spacer), ChatInput (sticky bottom glass-input, disabled prop, children slot + "Start Exploring" button), ThinkingIndicator (3 bouncing dots + text)
- [ ] **Step 3: Fragrance components** — ScoreBar (h-1 progress bar + percentage + source label), NotesCombination (3 rows: top/mid/base with Chip tags), ActionBar (3 icon buttons: heart/share/shuffle), FragranceCard (motion.div fade-in, conditional: null card -> Skeleton placeholders, skeleton phase -> shimmer, detail/copy -> real content, typing cursor "|" during copy, ActionBar only in complete phase)
- [ ] **Step 4: Verify** — `npx tsc --noEmit` passes
- [ ] **Step 5: Commit**

---

## Task 9: Page Routes — Landing + GuestChat + Fallback

**Files:** packages/frontend/src/routes/LandingPage.tsx, packages/frontend/src/routes/GuestChatPage.tsx, packages/frontend/src/routes/FallbackPage.tsx, packages/frontend/src/App.tsx (update)

**Produces:** Complete 4-route SPA: / (Landing), /guest (Chat), /fallback, * (404->Fallback)

- [ ] **Step 1: Create LandingPage.tsx** — Full-screen hero: "Discover your scent through emotions" (text-5xl font-light), CTA "Free Experience" -> navigate(/guest), HowItWorks 3-step section (glass-card grid), stone-50 background
- [ ] **Step 2: Create GuestChatPage.tsx** — Full-page layout: GlassNavHeader (SSE status dot: green/amber/red), ChatBody (EmotionConfirmation|null, FragranceCard[]|Skeleton[], ThinkingIndicator), GlassInputBar (EmotionCardPicker+SceneTagChips+SendButton). State: cardIds[], sceneTag, sseUrl. handleSend: build GET url with card_ids and scene params, set sseUrl triggering useSSE hook. Conditional: after start, hide input during generation, show again on complete/error
- [ ] **Step 3: Create FallbackPage.tsx** — Centered glass-card with "Come back later" message + leaf emoji
- [ ] **Step 4: Update App.tsx** — Add /guest, /fallback, * routes
- [ ] **Step 5: Verify** — `npx tsc --noEmit` passes; `npm run dev` -> Landing renders, navigate to /guest shows EmotionCardPicker
- [ ] **Step 6: Commit**

---

## Task 10: End-to-End Integration & Acceptance

**Files:** No new files. Verify full flow works.

- [ ] **Step 1: Start infrastructure** — `make docker-up`, wait for all healthy
- [ ] **Step 2: Load Neo4j graph** — `make neo4j-init` (25,863 lines Cypher)
- [ ] **Step 3: Start backend** — `make dev-backend` (uvicorn :8000)
- [ ] **Step 4: Start frontend** — `make dev-frontend` (vite :5173)
- [ ] **Step 5: Manual E2E test** — Open :5173 -> Landing renders -> Click "Free Experience" -> Select 2 emotion cards -> Click "Start Exploring" -> Verify ThinkingIndicator -> 3 skeleton cards appear -> Cards fade in with notes+scores -> Story copy streams with cursor -> ActionBar appears on complete -> SSE dot is green
- [ ] **Step 6: Performance check** — `time curl "http://localhost:8000/api/v1/guest/sessions?card_ids=anxiety&scene=work"` -> gen.skeleton frame < 200ms
- [ ] **Step 7: Commit** (any fixups)
