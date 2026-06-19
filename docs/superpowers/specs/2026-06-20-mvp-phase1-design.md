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

### 6.1 设计风格: Apple 极简主义

整体风格遵循 Apple 设计语言——纯白基底、毛玻璃透明层、极简阴影、SF 风格字体排印。

#### 设计原则

| 原则 | 说明 | 体现 |
|------|------|------|
| **留白呼吸** | 大量留白，内容稀疏排布 | 卡片间距 ≥ 16px，页边距 ≥ 20px |
| **毛玻璃层次** | `backdrop-blur` + 半透明背景分离信息层级 | 导航栏、卡片、浮层均使用毛玻璃 |
| **微妙的深度** | 极淡阴影 + 极细描边，不用强对比 | `shadow-sm` + `border-white/20` |
| **柔软圆角** | 大圆角减少视觉攻击性 | 卡片 `rounded-2xl`，按钮 `rounded-full` |
| **SF 风格字体** | 系统字体栈，优先 SF Pro / PingFang SC | `font-sans` 系统栈，字重变化表达层级 |
| **克制动效** | 柔和过渡，不突兀 | `duration-500` + `ease-out`，骨架闪光用 CSS animation |

#### 色彩体系

```
基色:
  bg-primary:      #fafaf9 (stone-50)   — 页面底色
  bg-card:         rgba(255,255,255,0.72) — 卡片毛玻璃
  bg-nav:          rgba(250,250,249,0.72) — 导航毛玻璃

文字:
  text-primary:    #292524 (stone-800)   — 标题/正文
  text-secondary:  #78716c (stone-500)   — 辅助说明
  text-tertiary:   #a8a29e (stone-400)   — 占位/禁用

强调:
  accent:          #78716c (warm stone)  — 按钮/选中态
  accent-soft:     rgba(120,113,108,0.08)— 选中态背景

描边:
  border-card:     rgba(255,255,255,0.6) — 卡片边缘
  border-subtle:   rgba(0,0,0,0.04)     — 分割线
```

#### 毛玻璃 CSS 模式

```css
/* 标准毛玻璃卡片 */
.glass-card {
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 8px 24px rgba(0, 0, 0, 0.04);
}

/* 导航栏毛玻璃 */
.glass-nav {
  background: rgba(250, 250, 249, 0.72);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}

/* 浮层/模态框 */
.glass-modal {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(40px) saturate(200%);
  -webkit-backdrop-filter: blur(40px) saturate(200%);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.12);
}
```

#### Tailwind 配置扩展

```typescript
// tailwind.config.ts
export default {
  theme: {
    extend: {
      backdropBlur: {
        glass: '20px',
        'glass-heavy': '40px',
      },
      backgroundColor: {
        glass: 'rgba(255, 255, 255, 0.72)',
        'glass-nav': 'rgba(250, 250, 249, 0.72)',
        'glass-strong': 'rgba(255, 255, 255, 0.85)',
      },
      borderColor: {
        glass: 'rgba(255, 255, 255, 0.6)',
        subtle: 'rgba(0, 0, 0, 0.04)',
      },
      boxShadow: {
        glass: '0 1px 3px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.04)',
        'glass-lg': '0 25px 50px -12px rgba(0,0,0,0.12)',
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', '"SF Pro Display"', '"PingFang SC"', '"Helvetica Neue"', 'sans-serif'],
      },
    },
  },
};
```

### 6.2 前端技术栈

| 层 | 选择 |
|---|------|
| 框架 | React 18+ |
| 语言 | TypeScript (strict) |
| 构建 | Vite |
| 样式 | Tailwind CSS + 自定义 glass plugin |
| 动画 | Framer Motion (卡片过渡、打字机效果) |
| 状态管理 | Zustand (3 个 store: session, generation, ui) |
| SSE 客户端 | 原生 EventSource + 自定义重连封装 |

### 6.3 MVP 路由

```
/           → LandingPage
/guest       → GuestChatPage
/fallback    → FallbackPage    (服务降级静态页)
*            → NotFoundPage
```

### 6.4 组件树 (`/guest`)

```
GuestChatPage
├── GlassNavHeader               # 毛玻璃顶栏
│   ├── PageTitle ("你的免费体验 🌿")
│   └── SSEStatusIndicator       # 连接状态圆点
│
├── ChatBody                     # 可滚动对话区（浅色渐变底）
│   ├── EmotionConfirmation      # 毛玻璃情绪确认浮层
│   │   ├── EmotionChip[]         # 柔和圆角胶囊
│   │   └── CorrectButton         # 「不对 ✏️」文字链接
│   ├── FragranceCard[]           # 骨架→完整 过渡
│   │   ├── ScoreBar              # 细线进度条
│   │   ├── NotesCombination      # 三层香调标签
│   │   ├── StoryCopy             # 文案（打字机流式）
│   │   └── ActionBar             # complete 阶段可交互
│   └── ThinkingIndicator         # 柔光呼吸动画
│
├── GlassInputBar                 # 毛玻璃底部输入区
│   ├── EmotionCardPicker         # 8 张卡片，毛玻璃选中态
│   ├── SceneTagChips            # 6 场景，胶囊标签
│   └── SendButton               # 圆形图标按钮，毛玻璃
│
└── NetworkStatusBar              # 顶部细条提示
```

### 6.5 关键组件设计规格

#### LandingPage

```
全屏垂直居中布局，柔和渐变背景（stone-50 → warm-100）

HeroSection:
  - 大型标题: "用香氛，读懂你的情绪" (text-5xl, font-light, tracking-tight)
  - 副标题: 浅色文字 (text-stone-500, 最大宽度 480px)
  - 情绪卡片旋转展示: 8 张卡片 3D 缓慢旋转 (Framer Motion)
  - CTA 按钮: glass-card 样式，"✨ 免费体验" (rounded-full, px-8, py-3)

HowItWorksSection:
  - 3 步卡片，每步: glass-card + 图标 + 标题 + 描述
  - 水平排列，间距 24px
```

#### GuestChatPage

```
ChatBody 背景:
  - 微妙的径向渐变: stone-50 中心 → 边缘微暖色调
  - 可选: 极淡的几何纹理 (SVG pattern, opacity 0.03)

GlassNavHeader:
  - 固定在顶部 (sticky top-0, z-10)
  - glass-nav 样式
  - 左侧: 页面标题（font-medium, text-stone-600）
  - 右侧: SSE 状态圆点 (green=active, amber=retrying, red=disconnected)

GlassInputBar:
  - 固定在底部 (sticky bottom-0, z-10)
  - glass-card + backdrop-blur-glass
  - 内边距: py-4 px-5
  - EmotionCardPicker + SceneTagChips + SendButton 水平排列
```

#### EmotionCardPicker

```
8 张卡片网格 (2 行 × 4 列)

单张 EmotionCard:
  - 默认: glass-card, rounded-2xl, 80×96px
  - 选中: bg-stone-100/80, border-stone-300, scale: 1.03
  - emoji 顶部 (text-2xl)
  - 标签文字底部 (text-xs, text-stone-500)
  - 超限提示: 选第 3 张时，卡片轻微抖动 (Framer Motion)
```

#### FragranceCard

```
FragranceCardSkeleton (gen.skeleton 到达前):
  - glass-card 骨架，内部 3 条闪光条 (CSS shimmer animation)
  - shimmer: 从左到右的白色渐变扫过

FragranceCard (gen.skeleton 到达后):
  - glass-card, rounded-2xl, p-5, mb-4
  - 入场动画: Framer Motion fade-in + slide-up (duration 0.5, ease-out)

  卡片内部:
  ┌─────────────────────────────────────┐
  │  Rank Badge · MatchScore            │
  │  ─────────────────────────────────  │
  │  名称: "晨雾花园" (text-lg, semibold)│
  │  品牌: "Brand" (text-xs, stone-400)  │
  │                                      │
  │  NotesCombination:                    │
  │   [前调] 柑橘 佛手柑                   │
  │   [中调] 白花 茉莉                     │
  │   [后调] 木质 麝香                     │
  │                                      │
  │  StoryCopy (text-sm, stone-600):      │
  │   "像清晨的第一缕阳光——" ▍             │
  │                                      │
  │  ActionBar (gen.complete 后):          │
  │   [❤️]  [📤]  [🔀]                     │
  └─────────────────────────────────────┘

ScoreBar:
  - 极简单行: "87% 匹配" + 细线进度条 (h-1, rounded-full, bg-stone-200)
  - 进度填充 bg-stone-500

NotesCombination:
  - 三层标签行，每层: 层级名 (text-xs, stone-500) + 成分标签
  - 成分标签: glass-chip (bg-stone-100/60, rounded-full, px-2 py-0.5)

ActionBar:
  - 三个图标按钮，glass-chip 样式
  - hover: bg-stone-100, transition
  - disabled (gen.complete 前): opacity-50, cursor-not-allowed
```

#### 对话气泡

```
UserMessage:
  - 右对齐，bg-stone-100, rounded-2xl rounded-br-sm
  - 轻量玻璃效果 (bg-white/80)

AgentMessage:
  - 左对齐，无背景，直接内含 FragranceCard
  - 纯文本回复: text-stone-700, leading-relaxed
```

### 6.6 前端状态分层 (Zustand)

```
Global State
├── sessionStore: {session_id, emotion, intent, sseStatus, crisis}
├── generationStore: {generationId, phase, mode, cards[], error}
└── uiStore: {loading, modal}
```

### 6.7 SSE 客户端

- 事件分发: `chat.*` → sessionStore / `gen.*` → generationStore / `safety.*` → interrupt
- 重连: 指数退避 [1s, 2s, 4s, 4s, 4s]，最多 5 次
- 心跳: 30s 无消息 → 主动断连
- 断点续传: MVP 不实现（Phase 2 `generation_id + phase` 协议）

### 6.8 FragranceCard 渲染阶段

| SSE 事件 | phase 状态 | UI 表现 |
|---------|:---:|------|
| `gen.skeleton` 到达前 | — | glass-card 骨架 + shimmer 闪光 |
| `gen.skeleton` 到达 | `skeleton` → `detail` | 香调组合 + 匹配度可见，fade-in 入场 |
| `gen.detail` 到达 | `detail` | 补充详情字段滑入 |
| `gen.copy` 到达 | `copy` | 文案逐 chunk 打字机追加 + 光标 ▍ |
| `gen.complete` 到达 | `complete` | ActionBar fade-in，卡片完整交互 |

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
