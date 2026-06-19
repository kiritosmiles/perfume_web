# MVP Phase 1 实现设计文档

> **文档版本**: v1.0
> **编制日期**: 2026-06-20
> **文档定位**: MVP Phase 1（核心推荐体验闭环）的架构设计、数据流、组件规格和分步实施计划
> **来源**: PRD §5 + TRD §1-§9 + Wireframe §1-§8 + 业务流设计 §1-§5
> **关联文档**:
> - `docs/superpowers/specs/2026-06-19-A-产品需求文档.md`
> - `docs/superpowers/specs/2026-06-19-B-技术需求文档.md`
> - `docs/superpowers/specs/2026-06-19-C-线框图.md`
> - `docs/superpowers/specs/2026-06-19-D-质量准则.md`
> - `docs/superpowers/specs/2026-06-19-业务流设计.md`

---

## 目录

1. [技术决策确认](#1-技术决策确认)
2. [项目结构 (Monorepo)](#2-项目结构-monorepo)
3. [第一条垂直切片: 游客情绪卡片推荐](#3-第一条垂直切片游客情绪卡片推荐)
4. [Docker Compose + 数据库 Schema + Neo4j 图谱](#4-docker-compose--数据库-schema--neo4j-图谱)
5. [FastAPI 后端骨架 + 核心 SSE 端点](#5-fastapi-后端骨架--核心-sse-端点)
6. [React 前端 + SSE 消费端 + 核心组件](#6-react-前端--sse-消费端--核心组件)
7. [分步实施计划](#7-分步实施计划)
8. [Phase 1 简化策略](#8-phase-1-简化策略)
9. [延迟预算](#9-延迟预算)

---

## 1. 技术决策确认

| 决策项 | 选择 | 理由 |
|--------|------|------|
| **前端框架** | React 18+ | SSE EventSource 生态成熟，Zustand 适合三层状态架构 |
| **语言** | TypeScript (strict) | 22 个 SSE 事件类型需要类型系统保障 |
| **开发环境** | Docker Compose 全容器化 | PG 15 + Redis 7 + Neo4j 5，一键拉起 |
| **后端框架** | Python FastAPI | TRD 指定，异步 SSE 原生支持 |
| **GraphRAG 数据源** | Fragrantica 爬虫数据集 | 已获取 1,182 条香水，556 品牌，893 香调，70 香韵 |
| **MVP LLM 策略** | 规则引擎（不调 LLM） | Phase 1 用图谱检索 + 模板，延迟 ~165ms，Phase 1.5 接入 LLM |
| **实施策略** | 方案 A — 垂直切片先行 | 游客情绪卡片推荐 → 横向扩展 |

---

## 2. 项目结构 (Monorepo)

```
perfume_web/
├── CLAUDE.md
├── docs/                           # 规格文档 + 数据集
├── docker/
│   ├── docker-compose.yml          # PG 15 + Redis 7 + Neo4j 5
│   ├── postgres/
│   │   └── init/
│   │       └── 001-mvp-schema.sql
│   └── neo4j/
│       └── import/
│           └── init-fragrances.cypher  # 1,182 条香水图谱
├── scripts/
│   ├── import_fragrantica_to_neo4j.py
│   └── explore_fragrantica_dataset.py
├── packages/
│   ├── shared/                     # @perfume/shared — 类型 + SSE 契约
│   │   └── src/
│   │       ├── types/
│   │       │   ├── emotion.ts
│   │       │   ├── generation.ts
│   │       │   ├── session.ts
│   │       │   └── api.ts
│   │       └── sse/
│   │           └── events.ts       # 22 个 SSE 事件 discriminated union
│   ├── frontend/                   # React + Vite + Tailwind
│   │   └── src/
│   │       ├── routes/             # LandingPage, GuestChatPage, FallbackPage
│   │       ├── components/
│   │       │   ├── emotion/        # EmotionCardPicker, EmotionConfirmation
│   │       │   ├── chat/           # ChatBody, ChatInput, ThinkingIndicator
│   │       │   ├── fragrance/      # FragranceCard, ScoreBar, ActionBar
│   │       │   └── ui/            # Button, Chip, Badge, Skeleton
│   │       ├── hooks/              # useSSE, useGeneration
│   │       ├── stores/             # Zustand: session, generation, ui
│   │       └── lib/                # sseClient, apiClient
│   └── (backend types only — TS 侧契约)
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 入口
│   │   ├── core/
│   │   │   ├── config.py           # BaseSettings
│   │   │   └── deps.py             # 依赖注入
│   │   ├── api/v1/
│   │   │   ├── router.py
│   │   │   ├── guest.py            # POST /guest/sessions + SSE
│   │   │   └── health.py
│   │   ├── services/
│   │   │   ├── emotion.py          # 情绪卡片预设向量
│   │   │   ├── fragrance.py        # GraphRAG 检索
│   │   │   ├── generation.py       # 规则引擎骨架生成
│   │   │   └── safety.py           # 本地关键词危机检测
│   │   ├── graph/
│   │   │   └── client.py           # Neo4j driver
│   │   ├── sse/
│   │   │   ├── protocol.py         # SSE 事件构造器
│   │   │   └── stream.py           # StreamingResponse 封装
│   │   └── models/
│   │       └── guest.py            # Pydantic models
│   ├── alembic/
│   ├── pyproject.toml
│   └── Dockerfile
├── .env.example
├── Makefile
└── package.json                    # monorepo root (npm workspaces)
```

---

## 3. 第一条垂直切片: 游客情绪卡片推荐

### 3.1 用户旅程 (4 步)

```
① Landing → 点击「✨ 免费体验」
② 游客对话页 → 选最多 2 张情绪卡片 + 场景标签 → 发送
③ SSE 流式:
   chat.ack → chat.emotion → gen.start → gen.skeleton ⭐
   → gen.detail → gen.copy → gen.complete
④ FragranceCard 完整呈现
```

### 3.2 SSE 数据流时序

```
前端 (React + EventSource)                    后端 (FastAPI)
─────────────────────────                    ─────────────────
POST /api/v1/guest/sessions
   emotion_card_ids + scene_tag
                                 → 安全检查 (本地关键词, <1ms)
                                 → 情绪卡片预设向量注入 (<5ms)
                                 → GraphRAG 1跳: 情绪→香韵→香水 (~50ms)
                                 → 规则骨架生成 (~10ms)
                                 ← SSE stream 开始

SSE: chat.ack                    ← {message_id, server_ts}
SSE: chat.emotion                ← {emotion_vector, primary_emotion,
                                     confidence: 1.0, source: "card_preset"}
SSE: gen.start                   ← {generation_id, mode: "fast"}
SSE: gen.skeleton ⭐             ← {recommendations: [{rank, name,
  → 首屏可见 (~165ms)               notes_combination, match_score}]}
SSE: gen.detail                  ← {rank, expanded_fields}
SSE: gen.copy (streaming)       ← {rank, copy_text_chunk, is_final}
SSE: gen.complete                ← {generation_id, total_cards, metadata}
```

### 3.3 后端关键数据流

```
                      POST /api/v1/guest/sessions
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
      M5: 安全检查      M2: 情绪         M3: GraphRAG
      crisis_detect    card_preset       emotion→fragrance
      (<1ms)           vector (<5ms)     mapping (~50ms)
            │              │              │
            └──────────────┼──────────────┘
                           ▼
                  融合上下文（游客无记忆层）
                           │
                           ▼
            ┌─────────────────────────┐
            │  M3: 规则骨架生成 (~10ms)│
            │  Top 3 图谱候选          │
            │  + 模板文案插值          │
            └───────────┬─────────────┘
                        ▼
                   SSE 流式输出
            skeleton → detail → copy
```

---

## 4. Docker Compose + 数据库 Schema + Neo4j 图谱

### 4.1 Docker Compose 服务

```yaml
# docker/docker-compose.yml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: perfume
      POSTGRES_PASSWORD: ${DB_PASSWORD:-perfume_dev}
      POSTGRES_DB: perfume
    ports: ["5432:5432"]
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./postgres/init:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U perfume"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]

  neo4j:
    image: neo4j:5-community
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:-perfume_dev}
    ports:
      - "7474:7474"   # HTTP
      - "7687:7687"   # Bolt
    volumes:
      - neo4jdata:/data
      - ./neo4j/import:/var/lib/neo4j/import

volumes:
  pgdata:
  neo4jdata:
```

### 4.2 MVP 数据库 Schema (仅 Phase 1 需要的表)

```sql
-- temp_conversations     — 游客临时对话
-- emotion_cards          — 情绪卡片定义 (8 条种子数据)
-- scene_tags             — 场景标签定义 (6 条种子数据)
-- fragrance_templates    — 配方模板（图谱降级兜底，从 Fragrantica 导入）
-- guest_quota            — 游客配额 (browser_id, used, expires_at)
```

**Phase 1 不需要的表** (延后到 Phase 2+):
`users`, `profiles`, `safety_profiles`, `conversations`, `layer2_summaries`, `perfumer_queue`, `crisis_logs`, `feedback_events`

### 4.3 Neo4j 图谱规模

| 节点类型 | 数量 |
|---------|:---:|
| Emotion (情绪) | 8 |
| Scene (场景) | 6 |
| Brand (品牌) | 556 |
| Perfume (香水) | 1,182 |
| Note (香调成分) | 893 |
| Accord (香韵) | 70 |

| 关系类型 | 说明 |
|---------|------|
| `SOOTHES / HARMONIZES / AMPLIFIES` | 情绪→香韵知识边 (22 条) |
| `HAS_ACCORD {score}` | 香水→香韵 (70×1182 条) |
| `HAS_NOTE {layer}` | 香水→香调 (893×1182 条，含前中后调层级) |
| `BY` | 香水→品牌 |
| `SUITS_SEASON {season}` | 香水→场景（季节匹配） |
| `BEST_AT {time}` | 香水→场景（日/夜） |

**GraphRAG 查询模式**: 1跳 — 情绪→SOOTHES→香韵→HAS_ACCORD→香水，按 `(r.weight × ha.score/100 + rating×0.1)` 综合得分排序。

Cypher 初始化文件: `docker/neo4j/import/init-fragrances.cypher` (25,863 行)

---

## 5. FastAPI 后端骨架 + 核心 SSE 端点

### 5.1 后端目录结构

```
backend/
├── app/
│   ├── main.py                 # FastAPI() + CORS + router 挂载
│   ├── core/
│   │   ├── config.py           # Settings(BaseSettings): PG/Redis/Neo4j URI
│   │   └── deps.py             # get_neo4j_session 依赖注入
│   ├── api/v1/
│   │   ├── router.py           # /api/v1/* 聚合
│   │   ├── guest.py            # POST /guest/sessions + SSE stream
│   │   └── health.py           # GET /health
│   ├── services/
│   │   ├── emotion.py          # 情绪卡片预设向量（无 BERT/LLM）
│   │   ├── fragrance.py        # GraphRAG 检索
│   │   ├── generation.py       # 规则骨架生成
│   │   └── safety.py           # 本地关键词危机检测
│   ├── graph/
│   │   └── client.py           # Neo4j driver 封装
│   ├── sse/
│   │   ├── protocol.py         # 22 事件类型构造器 + sse() helper
│   │   └── stream.py           # StreamingResponse + sse_event_stream()
│   └── models/
│       └── guest.py            # GuestSessionInput, 8 情绪卡片 ID 常量
├── alembic/
├── pyproject.toml
└── Dockerfile
```

### 5.2 核心端点

**`POST /api/v1/guest/sessions`**

输入:
```json
{
  "emotion_card_ids": ["anxiety", "calm"],
  "scene_tag": "work"
}
```

流程:
1. 安全检查 — `safety.crisis_check()` 本地关键词, <1ms
2. 情绪解析 — `emotion.resolve_emotion_from_cards()` 预设向量注入, <5ms
3. GraphRAG 检索 — `fragrance.search_fragrance_by_emotion()` Neo4j 1跳, ~50ms
4. 规则骨架 — `generation.build_skeleton()` Top 3 图谱候选 + 模板, ~10ms
5. SSE 流式输出 — `sse_event_stream()` → StreamingResponse

### 5.3 SSE 事件序列

```
chat.ack       — 服务端确认
chat.emotion   — 情绪识别结果（游客始终 source="card_preset"）
gen.start      — 生成开始 (generation_id + mode)
gen.skeleton   — 骨架阶段 ⭐ 首屏可见点
gen.detail     — 逐卡片补充详情
gen.copy       — 文案流式（打字机效果）
gen.complete   — 生成完成
gen.error      — 降级/失败
safety.crisis  — 危机中断（如触发）
```

### 5.4 MVP 降级策略

| 异常场景 | 行为 |
|---------|------|
| Neo4j 不可用 | 降级到 `fragrance_templates` PG 表 → 通用 Top 10 卡片墙 |
| 无匹配香水 | 返回通用礼物香调 Top 5 |
| 危机检测命中 | SSE `safety.crisis` 事件 → 中断生成 → 展示热线 |
| 游客配额耗尽 | 返回 `{"error": {"code": "GUEST_QUOTA_EXHAUSTED"}}` |

---

## 6. React 前端 + SSE 消费端 + 核心组件

### 6.1 前端技术栈

| 层 | 选择 |
|---|------|
| 框架 | React 18+ |
| 语言 | TypeScript (strict) |
| 构建 | Vite |
| 样式 | Tailwind CSS |
| 状态管理 | Zustand (3 个 store: session, generation, ui) |
| SSE 客户端 | 原生 EventSource + 自定义重连封装 |

### 6.2 MVP 路由

```
/           → LandingPage
/guest       → GuestChatPage
/fallback    → FallbackPage    (服务降级静态页)
*            → NotFoundPage
```

### 6.3 组件树 (`/guest`)

```
GuestChatPage
├── ChatBody
│   ├── EmotionConfirmation      # 情绪确认微交互
│   ├── FragranceCard[]          # 骨架→完整 过渡
│   │   ├── ScoreBar
│   │   ├── NotesCombination
│   │   └── ActionBar            # complete 阶段可交互
│   └── ThinkingIndicator        # 生成中动画
├── ChatInput
│   ├── EmotionCardPicker        # 8 选 最多 2 张
│   ├── SceneTagChips            # 6 场景 单选
│   └── SendButton
└── NetworkStatusBar             # 断连/重连提示
```

### 6.4 前端状态分层 (Zustand)

```
Global State
├── sessionStore: {session_id, emotion, intent, sseStatus, crisis}
├── generationStore: {generationId, phase, mode, cards[], error}
└── uiStore: {loading, modal}
```

### 6.5 SSE 客户端

- 事件分发: `chat.*` → sessionStore / `gen.*` → generationStore / `safety.*` → interrupt
- 重连: 指数退避 [1s, 2s, 4s, 4s, 4s]，最多 5 次
- 心跳: 30s 无消息 → 主动断连
- 断点续传: MVP 不实现（Phase 2 `generation_id + phase` 协议）

### 6.6 FragranceCard 渲染阶段

| SSE 事件 | phase 状态 | UI 表现 |
|---------|:---:|------|
| `gen.skeleton` 到达前 | — | FragranceCardSkeleton 闪光占位 |
| `gen.skeleton` 到达 | `skeleton` → `detail` | 香调组合 + 匹配度可见 |
| `gen.detail` 到达 | `detail` | 补充详情字段 |
| `gen.copy` 到达 | `copy` | 文案逐 chunk 打字机追加 |
| `gen.complete` 到达 | `complete` | ActionBar 可交互 |

---

## 7. 分步实施计划

```
Step 1: 项目脚手架
         ├── Makefile (make docker-up / make dev / make db-init)
         ├── docker-compose.yml + .env.example
         ├── packages/shared (类型定义)
         ├── packages/frontend (Vite + React + Tailwind + Zustand)
         └── backend (FastAPI + pyproject.toml)

Step 2: 后端核心链路
         ├── POST /api/v1/guest/sessions (一行打穿)
         ├── sse_event_stream() 完整 7 事件序列
         ├── GraphRAG 检索 + 规则骨架生成
         └── docker/neo4j/import/init-fragrances.cypher 加载

Step 3: 前端核心页面
         ├── LandingPage + 游客分流
         ├── GuestChatPage + SSE 消费
         ├── EmotionCardPicker + SceneTagChips
         └── FragranceCard (骨架→完整 过渡)

Step 4: 安全加固
         ├── 本地关键词危机检测
         ├── 游客配额 (guest_quota 表 + Redis)
         └── FallbackPage 降级页

Step 5: 验收 + 文档
         ├── 端到端测试: 游客完整推荐闭环
         ├── 性能验证: gen.skeleton < 200ms
         └── README.md 开发指南
```

---

## 8. Phase 1 简化策略

| 组件 | 正式版 | Phase 1 简化版 |
|------|--------|---------------|
| 情绪识别 | BERT ~50ms + LLM ~800ms 双路径 | **仅情绪卡片预设向量** (~5ms) |
| 记忆层 | Layer 1+2+3 完整 | **无记忆** (游客无持久化画像) |
| GraphRAG | 2跳扩展 + 3跳降级 | **1跳直接映射** (1,182 条香水) |
| LLM 推理 | 4 层降级链 | **规则引擎** (无 LLM 调用) |
| 安全 | BERT 危机 + LLM 旁路 | **本地关键词字典** |
| 画像 | 3 种 Session 模式 | **无画像** (游客模式) |
| 文案生成 | LLM 流式输出 | **模板插值** (~10ms) |

---

## 9. 延迟预算

### 9.1 MVP Phase 1 (无 LLM)

| 阶段 | 操作 | 延迟 |
|------|------|:---:|
| 安全检查 | 本地关键词匹配 | < 1ms |
| 情绪解析 | 预设向量查表 | < 5ms |
| GraphRAG | Neo4j 1跳查询 | ~50ms |
| 骨架生成 | 规则引擎 Top 3 + 模板 | ~10ms |
| SSE 首帧 | 网络 RTT + 序列化 | ~100ms |
| **gen.skeleton 首屏** | **合计** | **~165ms** |

### 9.2 正式版 (Phase 1.5+ 接入 LLM)

| 模式 | 骨架延迟 | 说明 |
|------|:---:|------|
| 情绪卡片 + 快速 | ~1.2s | TRD §11 场景 1 |
| 文本 + BERT + 快速 | ~1.5s | TRD §11 场景 6 |
| 深度模式 | ~1.7s | TRD §11 场景 7 |
| 加权平均 | ~1.37s | TRD §11.3 |

---

> **文档状态**: v1.0 — MVP Phase 1 设计完成
> **下一步**: 进入 `writing-plans` 技能，生成详细实施计划
> **关联数据**:
> - Fragrantica 数据集: 6 个 JSON 文件 (docs/dataset_fragrantica_*.json)
> - Neo4j Cypher: docker/neo4j/import/init-fragrances.cypher (25,863 行)
> - 导入脚本: scripts/import_fragrantica_to_neo4j.py
