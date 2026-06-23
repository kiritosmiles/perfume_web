# 情绪人格×香水 AI Agent

[English](README.en.md)

> 用香氛，读懂你的情绪 🌿

**情绪人格×香水 AI Agent** 是一款面向 C 端用户的智能香氛推荐 Web 应用。系统以大语言模型（LLM）为核心推理引擎，结合 GraphRAG 图结构推理、情感分析和三层分层记忆架构，将用户的情绪状态、人格特征、使用场景与香调知识图谱进行匹配，生成个性化香氛推荐与文字解读，实现「情绪驱动型香水推荐」。
![img.png](img.png)
---

## 项目定位

| 维度 | 说明 |
|------|------|
| **核心价值** | 让用户不需要懂香调术语 —— 说说话、选卡片，AI 为你找到专属气味 |
| **目标用户** | C 端消费者（为自己挑选 / 为他人送礼） |
| **部署平台** | Web 主力（桌面+移动端响应式），App 预留扩展 |
| **当前阶段** | Phase 3 — 用户画像深化（Phase 1 ✅ → Phase 2 ✅ → Phase 3 ✅） |

### 整体完成状态

| 指标 | 数值 |
|------|:---:|
| FR 覆盖率 | **27/27 (100%)** |
| 后端测试 | **138 passed**, 0 failed |
| 前端 vitest | **20 passed** |
| TypeScript | **零错误** |
| SSE 事件 | **10 域 25 事件** (chat.* / gen.* / gate.* / safety.* / lifecycle.* / system.*) |
| 后端 API 端点 | **20 端点** (auth 4 + guest 2 + recommend 3 + config 2 + share 2 + memory 1 + feedback 2 + profile 2 + journal 2 + health 1) |
| Neo4j 知识图谱 | **1,179 款香水 / 70 种香韵 / 74 条情绪→香韵边** |
| LLM 管线 | **9 调用点** (emotion / intent / gate / copy × 3 / synesthesia / profile) |

> 剩余 7 项 FR 属于 Phase 4 规划（FR-3.10 调香师协作桥、FR-1.4 社交授权导入 等）。

### C 端核心设计原则

| 原则 | 说明 |
|------|------|
| **低门槛** | 游客模式、情绪卡片、场景化引导 —— 不需要懂香调术语 |
| **低延迟** | 全链路并行化、预加载、骨架流式 —— 首字优先 |
| **低摩擦** | 隐式反馈、选项化反问、异步尾量 —— 减少操作负担 |
| **被理解感** | 情绪确认微交互、精炼对话、主动回访 |
| **可掌控** | 记忆透明化、安全档案维护、意图手动切换 |
| **安全感** | 本地敏感词过滤、危机差异化响应、数据删除权 |
| **场景智能** | 自动识别「自用/送礼/探索」三种意图，差异化推荐策略 |
| **可回溯** | 全量会话持久化、历史浏览、情绪时间线 |

---

## 角色分类

系统设计了 **五类角色**，覆盖 C 端消费者、B 端调香师和系统运维三个维度：

```
                    ┌──────────────────┐
                    │    系统管理员     │
                    │   (Admin/Ops)    │
                    └────────┬─────────┘
                             │ 监控、限流、安全
                             │
    ┌────────────────────────┼────────────────────────┐
    │                        │                        │
    ▼                        ▼                        ▼
┌──────────┐          ┌──────────┐            ┌──────────┐
│   游客    │  注册    │ 免费用户  │   升级     │ 付费用户  │
│  Guest   │ ──────→ │   Free   │ ────────→  │ Premium  │
└────┬─────┘          └────┬─────┘            └────┬─────┘
     │                     │                       │
     │ ① 单次体验          │ ② 日常使用            │ ③ 深度使用
     │ 仅自用模式          │ 全意图 + 配额限制     │ 无限制 + 优先
     │                     │                       │
     └─────────────────────┼───────────────────────┘
                           │
                           │ 请求制作实体卡片
                           ▼
                    ┌──────────┐
                    │  调香师   │
                    │ Perfumer │
                    └──────────┘
                     ④ 接收协作请求 → 调制 → 交付实体香氛卡片
```

---

## 各角色功能详解

### ① 游客 (Guest)

> **定位：** 零门槛初次体验，无需注册即可完整体验一次推荐闭环。

| 能力 | 说明 |
|------|------|
| 🎭 **情绪输入** | 支持情绪卡片挑选（8 张预设），可选文字补充 |
| 🧠 **意图支持** | 仅「自用 (self_use)」模式 |
| 💬 **推荐对话** | 1 次完整会话（含情绪识别 → 香调匹配 → 骨架生成 → 流式文案） |
| 🔄 **精炼对话** | 8 个精炼 Chip（更甜/更清新/木质调…）+ 18 条规则引擎调整情绪向量重新推荐 |
| 🛡️ **安全兜底** | 危机关键词检测 → CrisisOverlay 全屏遮罩 + 心理热线；转人工关键词 → 通知 + 联系邮箱 |
| ⚠️ **过敏原管理** | SettingsPage 输入过敏原 → 后端匹配 note 名称 → FragranceCard 红色徽章警告 |
| 🔍 **反问确认** | 置信度 < 85% 时追问 UI："是这种感觉吗？" → 确认 / 重新描述 |
| 📝 **动态笔记** | 会话中可记录灵感笔记，支持 PNG 导出 |
| 🔗 **分享** | 可生成分享链接，将推荐结果分享给朋友 |
| ⏰ **数据保留** | 游客对话存储在临时表，30 天未注册自动物理删除 |
| 🔐 **升级路径** | 注册后游客数据自动迁移至正式账号 |
| ⚠️ **限制** | 不启用送礼/探索模式、不创建持久化画像、不保存历史记录 |

**典型旅程：** 访问首页 → 点击「✨ 免费体验」→ 选情绪卡片（或写心情文字）→ 查看推荐结果 → 可分享/记笔记 → 结束体验

---

### ② 免费用户 (Free)

> **定位：** 注册用户的日常使用层级，满足大多数推荐场景。

| 能力 | 说明 |
|------|------|
| 🎭 **情绪输入** | 双通道：情绪卡片 + 自由文字描述（LLM 通感解码） |
| 🧠 **意图支持** | 全部三种模式：自用 / 送礼 / 探索 |
| 💬 **推荐对话** | 10 次会话/天 |
| 🎯 **推荐生成** | 15 次/天（快速+深度合计） |
| 🧬 **深度模式** | 3 次/天（Supervisor → 3 Subagent 多角度并行推理） |
| 🔄 **精炼对话** | 不限次（8 个精炼 Chip + 18 条规则引擎） |
| 🛡️ **安全兜底** | 危机检测 + CrisisOverlay 热线遮罩 + 转人工检测 |
| ⚠️ **过敏原** | 自定义过敏原列表，推荐结果自动匹配并红色徽章提醒 |
| 📊 **历史浏览** | 最近 30 天会话记录 |
| 👤 **用户画像** | 渐进式构建（前 3 次轻量，第 4 次起完整推理链路） |
| 🃏 **卡片制作** | 1 次/月（提交配方 → 调香师协作 → 实体香氛卡片） |
| 🔗 **分享** | 支持生成分享链接 |
| 📝 **动态笔记** | 全功能笔记系统 |
| 🛡️ **安全档案** | 过敏原/不喜欢香调记录，仅自用模式生效 |
| 📈 **配额提示** | 接近 80% 限额时淡色提示剩余次数 |

**典型旅程：** 注册/登录 → 冷启动引导（≤3 题）→ 进入对话 → 选意图（自用/送礼/探索）→ 对话推荐 → 精炼 → 浏览历史 / 管理记忆

---

### ③ 付费用户 (Premium)

> **定位：** 深度用户的无限体验层级，解锁全部能力与优先服务。

**包含免费用户全部功能，额外享有：**

| 增强能力 | 说明 |
|------|------|
| ♾️ **对话次数** | 不限次 |
| ♾️ **推荐生成** | 不限次 |
| ♾️ **深度模式** | 不限次（所有场景均可触发多角度并行推理） |
| ⚡ **优先级** | 高峰期 LLM 调用优先排队 |
| 📊 **历史** | 全量历史会话，无时间限制 |
| 🃏 **卡片制作** | 3 次/月实体香氛卡片 |
| 🔮 **优先体验** | 新功能灰度优先开放 |
| 🎯 **高级画像** | 完整五维人格建模（记忆/情绪/身份/社交/人格） |

---

### ④ 调香师 (Perfumer)

> **定位：** B 端协作角色，负责将 AI 生成的配方调制为实体香氛卡片。

| 能力 | 说明 |
|------|------|
| 📋 **协作队列** | 接收用户提交的配方制作请求 |
| 🔍 **配方查看** | 查看 AI 生成的香调组合与推荐理由 |
| 📦 **状态管理** | 更新制作进度（排队中 → 调制中 → 已完成） |
| 💬 **反馈通道** | 可对配方可行性与系统交互提供反馈 |
| 🎨 **创意输入** | 基于 AI 骨架进行人工调香创作 |

> MVP 阶段提供最简通知机制（队列写入 + 状态查询）—— 完整的 B 端调香师协作平台在后续版本实现。

---

### ⑤ 系统管理员 (Admin/Ops)

> **定位：** 保障系统稳定运行、安全合规与数据质量。

| 能力 | 说明 |
|------|------|
| 🖥️ **服务监控** | 后端健康检查、延迟监控、错误率告警 |
| 🔒 **安全防护** | 危机关键词库维护、速率限制策略配置、JWT 密钥管理 |
| 📊 **配额管理** | 用户配额策略配置与调整 |
| 🗄️ **数据运维** | 数据库迁移（Alembic）、游客数据过期清理（30 天 TTL） |
| 📈 **质量分析** | LLM 调用成功率、BERT 置信度分布、用户反馈汇总 |
| 🔑 **LLM Key 配置** | 通过后台 API 管理 LLM API Key（Redis 热存储） |
| 📦 **知识图谱** | Neo4j 香调知识图谱数据导入与维护 |

---

## 技术架构概览

```
┌─────────────────────────────────────────────────────┐
│               前端 (React 18 + Vite + Tailwind)       │
│  LandingPage / GuestChatPage / AuthChatPage / SharePage / ProfilePage │
│  EmotionCardPicker / FragranceCard / NoteCard / CrisisOverlay │
│  GateQuestionBanner / OnboardingModal / EmotionTrend          │
│  WeeklyJournal / RefinementChips                              │
│  EmotionConfirmation / SceneTagChips / IntentSelector      │
│              Zustand Stores / SSE Client               │
└────────────────────────┬────────────────────────────┘
                         │ SSE Streaming + REST
┌────────────────────────▼────────────────────────────┐
│               后端 (Python FastAPI :8000)              │
│                                                       │
│  /api/v1/guest/sessions   (游客 SSE 推荐)             │
│  /api/v1/recommend/sessions (注册用户 SSE 推荐)       │
│  /api/v1/auth/*           (注册/登录/Token刷新)       │
│  /api/v1/share/*          (分享链接)                  │
│  /api/v1/config/llm-key   (LLM Key 配置)              │
│  /api/v1/memory/*         (记忆查询)                  │
│  /api/v1/feedback/*       (反馈采集)                  │
│  /api/v1/profile/*        (用户画像)                  │
│  /api/v1/journal/*        (情绪日记)                  │
│                                                       │
│  服务层: emotion / fragrance / generation / safety    │
│         intent / agent_gate / refinement / memory     │
│         recall / profile / journal / llm_emotion      │
│  中间件: CORS / Trace-Id / RateLimit / Quota          │
└──┬──────────────┬──────────────┬────────────────────┘
   │              │              │
   ▼              ▼              ▼
┌──────┐   ┌──────────┐   ┌─────────┐
│PostgreSQL│ │  Redis 7 │   │Neo4j 2025│
│ pg15    │ │  缓存+   │   │ 图数据库 │
│+pgvector│ │  速率限制 │   │GraphRAG │
└──────┘   └──────────┘   └─────────┘

推荐管线:
  emotion_vector (8维, 全部情绪参与)
    → 74条 SOOTHES 边 × 场景加权 (+0.25)
    → GraphRAG 评分 (limit=50)
    → 香韵聚类贪心多样性 (_diverse_top3)
    → 3 款推荐 (来自不同香韵簇)
```

| 层次 | 技术 | 说明 |
|------|------|------|
| 前端 | React 18 + Vite + Tailwind CSS + Zustand | SSE 流式渲染，玻璃拟态设计 |
| 后端 | Python FastAPI | 异步 SSE 生成器，7 域 22+ 事件协议 |
| 图数据库 | Neo4j 2025 | 香调知识图谱（香韵→香水），1-hop GraphRAG，74 条情绪→香韵边，场景加权评分 |
| 关系数据库 | PostgreSQL 15 + pgvector | 用户/会话/记忆持久化，512 维向量语义检索 |
| 缓存 | Redis 7 | Layer 1 会话记忆（1+5 滑动窗口）、速率限制、LLM Key 热存储 |
| LLM | DeepSeek / Claude | 9 调用点约束矩阵，双路径（BERT 快路径 + LLM 兜底） |
| 部署 | Docker Compose | 一键启动全部基础设施 |

---

## API 端点参考

### 游客 (Guest)

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/api/v1/guest/sessions` | 创建会话（SSE 流） |
| `GET` | `/api/v1/guest/sessions?card_ids=…&text=…` | 快捷对话（SSE 流） |

### 认证 (Auth)

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/api/v1/auth/register` | 注册 `{email, password, browser_id?}` |
| `POST` | `/api/v1/auth/login` | 登录 → JWT (Access 1h + Refresh 7d) |
| `POST` | `/api/v1/auth/refresh` | Token 刷新（轮换） |
| `GET` | `/api/v1/auth/me` | 当前用户信息（需 Bearer Token） |

### 推荐 (Recommend — 需认证)

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/api/v1/recommend/sessions` | 注册用户推荐（SSE） |
| `GET` | `/api/v1/recommend/sessions?card_ids=…` | 快捷推荐（SSE） |
| `GET` | `/api/v1/recommend/quota` | 查看配额 `{sessions, generations, deep}` |

### 配置 (Config)

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/api/v1/config/llm-key` | 保存用户 LLM Key |
| `GET` | `/api/v1/config/llm-key/status?browser_id=` | 检查 Key 配置状态 |

### 分享 (Share)

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/api/v1/share` | 创建分享链接（7 天有效） |
| `GET` | `/api/v1/share/{id}` | 获取分享内容 |

### 反馈 (Feedback)

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/api/v1/feedback/explicit` | 显式反馈 (like/dislike) → 202 |
| `POST` | `/api/v1/feedback/implicit` | 隐式反馈 (dwell/share/refine) → 202 |

### 画像 (Profile — 需认证)

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/v1/profile` | 获取用户画像 (人格标签/情绪倾向/偏好香调) |
| `POST` | `/api/v1/profile/onboarding` | 提交冷启动引导问卷答案 |

### 记忆 (Memory — 需认证)

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/v1/memory/timeline` | 查询用户记忆时间线 |

### 情绪日记 (Journal — 需认证)

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/v1/journal/trend` | 获取近 N 天情绪趋势数据 |
| `GET` | `/api/v1/journal/weekly` | 获取周记（情绪对比 + AI 叙述） |

### 系统

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/v1/health` | 健康检查 `{status, neo4j, postgres, redis}` |

---

---

## 快速开始

### 前置要求

- Docker Desktop（或 Podman）
- Python 3.11+
- Node.js 20+
- Poetry（Python 包管理）

### 1. 启动基础设施

```bash
docker compose -f docker/docker-compose.yml up -d
```

启动 PostgreSQL 15 (pgvector) + Redis 7 + Neo4j 2025，全部绑定 `127.0.0.1`。

> **Windows 用户注意：** 如果遇到端口 7687 报错 `bind: An attempt was made to access a socket in a way forbidden by its access permissions`，这是 Windows 端口预留机制所致。已在 `docker-compose.yml` 中将 Neo4j Bolt 端口映射到 `17687`（避让 7681-7780 保留范围），`.env` 中 `NEO4J_URI` 需对应设为 `bolt://localhost:17687`。重启 Docker Desktop 后通常可恢复使用 7687。

### 2. 初始化知识图谱

```bash
# 初次导入：将 Fragrantica 香调数据转换为 Neo4j Cypher
python scripts/import_fragrantica_to_neo4j.py

# 数据迁移（更新已有 Neo4j）
python scripts/migrate_add_image_to_neo4j.py        # 补充香水图片
python scripts/migrate_expand_emotion_accords.py    # 扩容情绪→香韵边 (22→74)
```

### 3. 启动后端

```bash
cd backend
cp .env.example .env   # 编辑 .env 填入 LLM API Key
poetry install
poetry run alembic upgrade head    # 数据库迁移
python -m uvicorn app.main:app --reload --port 8000
```

### 4. 启动前端

```bash
npm ci
cd packages/frontend
npx vite   # 访问 http://localhost:5173
```

### 5. 运行测试

```bash
# 后端测试 (111 个测试，含 Auth/Memory/Quota/Profile/Share/Config/AgentGate)
cd backend && poetry run pytest tests/ -v

# 排除 E2E（不需要 Docker 服务）
cd backend && poetry run pytest tests/ -v -m "not e2e"

# 前端类型检查
cd packages/frontend && npx tsc --noEmit

# 前端组件测试 (20 个测试)
cd packages/frontend && npx vitest run
```

---

## 项目结构

```
perfume_web/
├── backend/                        # Python FastAPI 后端
│   ├── app/
│   │   ├── api/v1/                 # REST + SSE 端点
│   │   ├── core/                   # 配置、依赖注入、Auth、限流
│   │   ├── graph/                  # Neo4j 客户端
│   │   ├── models/                 # Pydantic 模型
│   │   ├── services/               # 业务逻辑（情绪/意图/AgentGate/香调/文案/安全/精炼/记忆/画像）
│   │   ├── sse/                    # SSE 协议与事件流生成（7域25+事件）
│   │   └── main.py                 # FastAPI 应用入口
│   └── tests/                      # pytest 测试
├── packages/
│   ├── shared/                     # 共享 TypeScript 类型定义
│   └── frontend/                   # React + Vite + Tailwind 前端
│       └── src/
│           ├── routes/             # 页面路由组件 (10 routes)
│           ├── components/         # UI（FragranceCard / GateQuestionBanner / OnboardingModal / CrisisOverlay 等）
│           ├── hooks/              # 自定义 Hooks (useSSE / useImplicitTracking)
│           ├── stores/             # Zustand (session / generation / auth / profile)
│           └── lib/                # SSE / API / Auth 客户端
├── docker/                         # Docker Compose 配置 + Neo4j 初始化脚本
├── docs/                           # 需求文档与设计规范
│   └── superpowers/specs/          # PRD / TRD / 线框图 / 质量准则 / 设计文档
└── scripts/                        # 数据导入与迁移脚本
    ├── import_fragrantica_to_neo4j.py     # 数据集 → Cypher 转换
    ├── migrate_add_image_to_neo4j.py      # 补充香水真实图片
    └── migrate_expand_emotion_accords.py  # 扩容情绪→香韵边
```

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [产品需求文档 (PRD)](docs/superpowers/specs/2026-06-19-A-产品需求文档.md) | 35 项功能需求，用户角色，MVP 阶段定义 |
| [技术需求文档 (TRD)](docs/superpowers/specs/2026-06-19-B-技术需求文档.md) | 18 API + 22 SSE 事件，LLM 架构，数据库设计 |
| [线框图/原型](docs/superpowers/specs/2026-06-19-C-线框图.md) | 16 路由 + 32 组件树，SSE 交互时序 |
| [质量准则](docs/superpowers/specs/2026-06-19-D-质量准则.md) | 18 性能指标，4 层安全，13 风险项 |
| [业务流设计](docs/superpowers/specs/2026-06-19-业务流设计.md) | 全链路旅程，跨模块数据流，用户分级配额 |
| [C路径体验深化](docs/superpowers/specs/2026-06-21-C-体验深化-design.md) | LLM Key 配置 + 动态笔记PNG导出 + 分享链接 |
| [D路径用户系统](docs/superpowers/specs/2026-06-21-D-用户系统-design.md) | 注册/登录/JWT/Free用户配额/Guest→Free迁移 |
| [E路径TiMem记忆](docs/superpowers/specs/2026-06-21-E-TiMem记忆系统-design.md) | L1/L2/L3 三级时序记忆 + 复杂度感知召回 |
| [FR覆盖分析](docs/superpowers/specs/FR-coverage-analysis.md) | 当前 FR 覆盖状态 (26/27 = 96%) |
| [Phase 3 用户画像](docs/superpowers/specs/2026-06-23-F-Phase3-用户画像深化-design.md) | 画像系统/冷启动引导/AI眼中的我/情绪日记/通感解码 |

---

## License

Private — All rights reserved.
