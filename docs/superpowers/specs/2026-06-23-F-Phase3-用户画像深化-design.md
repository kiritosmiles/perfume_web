# Phase 3：用户画像深化 + 记忆透明化 — 设计文档

> **状态**: 已确认
> **日期**: 2026-06-23
> **依赖**: Path D (用户系统) + Path E (TiMem 记忆系统) + Phase 2 (Agent Gate) 已完成

## 概述

在 Phase 1-2 核心推荐体验 + 用户系统 + 记忆系统基础上，Phase 3 聚焦于**用户画像深化**和**记忆透明化**——让 AI 更懂用户，也让用户看到 AI 对自己的理解。

| ID | 功能 | 对应 FR | 性质 | 预估 |
|----|------|---------|------|------|
| F1 | 用户画像系统 | FR-1.1 + FR-1.3 | 后端 + 前端 | 2h |
| F2 | 冷启动引导问卷 | FR-1.2 | 前端 + 后端 | 1h |
| F3 | AI 眼中的我 | FR-4.8 | 前端为主 | 1.5h |
| F4 | 情绪日记 | FR-4.9 | 后端 + 前端 | 2h |
| F5 | 抽象需求处理 | FR-5.8 | 后端 LLM | 0.5h |

F1-F5 互有依赖（F1 是 F3/F4 的基础），F5 独立。FR-3.10（调香师协作桥）是 B 端功能，不在 MVP 范围内。

---

## 设计决策汇总

| 决策点 | 选择 | 依据 |
|--------|------|------|
| 画像存储 | PostgreSQL `user_profiles` 表 (JSONB) | 与 TiMem L2/L3 同库，方便 JOIN |
| 画像更新策略 | 异步 + 批处理（每次 gen.complete 触发） | 不阻塞推荐流程 |
| 引导问卷 | 3 题场景化选择，每个选项背后预设 8-D 情绪向量 | 毫秒级，无需 LLM |
| 渐进画像 | 前 3 次对话轻量模式（仅记录情绪分布），第 4 次起完整画像 | 冷启动友好 |
| AI眼中的我 | 新页面 `/profile`，展示画像标签 + 情绪轨迹 + 偏好香调 | MemoryPage 的互补——此页侧重"总结"，MemoryPage 侧重"时间线" |
| 情绪日记 | L3 日级汇总 + 前端图表（情绪雷达图 + 趋势线） | 用 recharts（已在项目中） |
| 抽象需求 | 在现有 `llm_emotion.py` 中增加通感解码 prompt | 不新增文件，扩展现有实现 |

---

## F1: 用户画像系统 (FR-1.1 + FR-1.3)

### 目标

基于 TiMem 记忆系统自动构建和维护用户画像，含人格标签、情绪倾向、偏好香调三个维度。

### 数据模型

```sql
-- backend/alembic/versions/005_user_profiles.py (新建)
CREATE TABLE user_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    profile_data JSONB NOT NULL DEFAULT '{}',
    -- profile_data structure:
    -- {
    --   "personality_tags": ["清新自然", "低调优雅", ...],    // 人格标签 (≤5)
    --   "emotion_tendency": {"joy": 0.4, "calm": 0.3, ...},   // 情绪倾向分布
    --   "preferred_accords": ["citrus", "floral", ...],        // 偏好香调簇
    --   "preferred_notes": ["Bergamot", "Jasmine", ...],       // 偏好香原料
    --   "gift_history": [                                      // 送礼历史
    --     {"recipient": "妈妈", "occasion": "生日", "perfume": "..."}
    --   ],
    --   "session_count": 12,                                   // 会话计数
    --   "profile_level": "full"                                // "light" | "full"
    -- }
    conversation_count INTEGER NOT NULL DEFAULT 0,  -- 用于渐进画像判断
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 画像提取 Pipeline

```
gen.complete
    │
    ├── [异步] trigger_profile_update(user_id)
    │       │
    │       ├── 1. 从 memory_l2 汇总最近 N 条会话摘要
    │       ├── 2. LLM 提取画像标签 (≤5 个中文标签)
    │       ├── 3. 统计情绪分布 (直接平均 L2 中的 emotion_vector)
    │       ├── 4. 统计偏好香调 (从 recommendations 中提取 accord)
    │       └── 5. UPSERT user_profiles
    │
    └── [同步] 更新 conversation_count
```

### 渐进画像规则

| 会话次数 | 画像级别 | 行为 |
|:---:|:---:|------|
| 1-3 | `light` | 仅记录情绪分布，不触发完整画像提取 |
| 4+ | `full` | 每次 gen.complete 后异步触发完整画像提取 |
| 引导问卷后 | `full` (立即) | 跳过渐进等待，直接标记为完整画像 |

### 后端文件

| 文件 | 改动 |
|------|------|
| `backend/alembic/versions/005_user_profiles.py` (新建) | 建表 migration |
| `backend/app/services/profile.py` (新建) | 画像提取 pipeline |
| `backend/app/api/v1/profile.py` (新建) | GET/PUT /profile 端点 |
| `backend/app/api/v1/router.py` | 注册 profile router |
| `backend/app/sse/stream.py` | gen.complete 后触发异步画像更新 |

---

## F2: 冷启动引导问卷 (FR-1.2)

### 目标

新用户首次使用时，通过 3 道场景化选择题快速建立画像基线，避免冷启动困扰。

### 问卷设计 (3 题)

**Q1: 你平时更喜欢哪种氛围？**
| 选项 | 场景描述 | 映射情绪向量 |
|------|---------|-------------|
| 🌿 自然清新 | "户外的风、绿叶、干净的棉布" | joy:0.3, calm:0.5, excitement:0.1, nostalgia:0.1 |
| 🌹 优雅浪漫 | "烛光晚餐、花香、温柔的夜晚" | romance:0.6, joy:0.2, calm:0.1, nostalgia:0.1 |
| 🎭 个性独特 | "艺术展、小众咖啡馆、不一样的我" | excitement:0.4, melancholy:0.2, nostalgia:0.2, joy:0.1 |
| 🧘 沉静内敛 | "书店、茶室、独处的时光" | calm:0.5, melancholy:0.2, nostalgia:0.2, sadness:0.1 |

**Q2: 你对香水的态度是？**
| 选项 | 映射画像标签 |
|------|-------------|
| "日常必备，出门一定要喷" | 实用型，日常伴侣 |
| "特别场合才会用" | 仪式感型，场合驱动 |
| "喜欢收集不同的味道" | 探索者，香氛爱好者 |
| "刚开始了解香水" | 新手，好奇入门 |

**Q3: 有没有不喜欢的味道？** (可选)
| 选项 | 映射避讳香调 |
|------|-------------|
| 太甜的 | sweet |
| 太浓烈的 | spicy, leather |
| 太清冷的 | aquatic (降低权重) |
| 没有特别不喜欢的 | — |

### 交互设计

```
OnboardingModal (全屏半透明遮罩)
├── 进度条 (1/3 → 2/3 → 3/3)
├── 问题卡片 (framer-motion 滑入)
│   ├── 问题文案 (大字)
│   └── 选项列表 (大按钮 + emoji + 场景描述)
└── 「跳过」链接 (右下角，不显眼)
    → 跳过则标记 profile_level = "light"，等 4 次对话后自动升级
```

### 前端文件

| 文件 | 改动 |
|------|------|
| `packages/frontend/src/components/onboarding/OnboardingModal.tsx` (新建) | 3 题问卷模态框 |
| `packages/frontend/src/stores/profileStore.ts` (新建) | 画像状态管理 |
| `packages/frontend/src/lib/apiClient.ts` | 新增 `submitOnboarding(answers)` |

### 后端端点

- `POST /api/v1/profile/onboarding` — 接收问卷答案，计算初始画像，写入 user_profiles

---

## F3: AI 眼中的我 (FR-4.8)

### 目标

一个独立的"个人画像"页面，展示 AI 对用户的理解，用户可查看和感受记忆透明化。

### 页面设计

```
/profile 页面
├── 顶部横幅
│   ├── "AI 眼中的你" 标题
│   └── 最后更新时间
├── 画像卡片区 (2×2 grid)
│   ├── 人格标签卡片
│   │   └── 标签云 (≤5 个 pill)
│   ├── 情绪画像卡片
│   │   └── 情绪雷达图 (8 维)
│   ├── 偏好香调卡片
│   │   └── 香调簇饼图 / 进度条
│   └── 你的香氛人格卡片
│       └── 一句话总结 + 代表性香水名
├── 送礼档案卡片 (如果存在)
│   └── 送礼历史简单列表
└── 底部: "这些信息仅对你可见" + 「编辑偏好」按钮
```

### 数据来源

| 展示内容 | 数据来源 |
|---------|---------|
| 人格标签 | `user_profiles.profile_data.personality_tags` |
| 情绪雷达图 | `user_profiles.profile_data.emotion_tendency` |
| 偏好香调 | `user_profiles.profile_data.preferred_accords` |
| 香氛人格总结 | LLM 生成（基于画像 + 最近 10 次推荐），缓存 7 天 |
| 送礼历史 | `user_profiles.profile_data.gift_history` |

### 技术实现

- Recharts 雷达图 (RadarChart) + 进度条
- GET /profile 端点返回完整画像 JSON
- 香氛人格总结：首次访问时 LLM 生成 → 缓存 → 每周刷新

---

## F4: 情绪日记 (FR-4.9)

### 目标

基于 TiMem L3 日级记忆，为用户生成情绪周记和趋势可视化。

### 数据模型

```
现有 L3 表: memory_l3 (level='daily')
  - owner_type, owner_id, date, summary_text, emotion_vector, ...
```

### 功能

**情绪轨迹图**: 最近 30 天情绪变化折线图（主要情绪每天一个点）

**情绪雷达对比**: 本周 vs 上周情绪分布对比（叠加雷达图）

**周记生成**: 每周一自动生成上周情绪摘要

```
"本周回顾 (6/16 - 6/22)"
├── 主要情绪: 平静 → 兴奋（周五）→ 平静
├── 探索了 3 款新香调
├── 最常出现的香原料: 佛手柑、茉莉
└── AI 的一句话: "这周的你从周中的忙碌转向周末的松弛，香气选择也变得更轻盈了"
```

### 后端文件

| 文件 | 改动 |
|------|------|
| `backend/app/services/journal.py` (新建) | 周记生成 + 趋势分析 |
| `backend/app/api/v1/journal.py` (新建) | GET /journal/weekly, GET /journal/trend |
| `backend/app/api/v1/router.py` | 注册 journal router |
| `backend/app/services/scheduler.py` (新建/扩展) | 每周一凌晨触发生成（可复用 L3 cron 模式） |

### 前端文件

| 文件 | 改动 |
|------|------|
| `packages/frontend/src/routes/ProfilePage.tsx` (新建) | /profile 路由，整合 F3 + F4 |
| `packages/frontend/src/components/profile/EmotionRadar.tsx` (新建) | 情绪雷达图 |
| `packages/frontend/src/components/profile/EmotionTrend.tsx` (新建) | 情绪趋势折线图 |
| `packages/frontend/src/components/profile/PersonalityCard.tsx` (新建) | 人格标签卡片 |
| `packages/frontend/src/components/profile/WeeklyJournal.tsx` (新建) | 周记卡片 |
| `packages/frontend/src/App.tsx` | 添加 /profile 路由 |

---

## F5: 抽象需求处理 (FR-5.8)

### 目标

当用户输入抽象/超现实描述时（如"下雨的味道"、"梵高的星空"），LLM 将其解码为具体香调词汇，再喂入 GraphRAG。

### 实现方式

在 `backend/app/services/llm_emotion.py` 的 `resolve_emotion_from_text()` 中增加通感解码步骤：

```
用户输入: "我想要下雨的味道"
    │
    ├── 1. 常规情绪识别 (现有)
    │
    ├── 2. 通感检测: 关键词匹配 ("味道"、"感觉"、"像"、"颜色")
    │       检测到 → LLM 解码为香调词汇
    │       Prompt: "将用户的抽象描述解码为具体的香调/香原料词汇。\n
    │                输入: '下雨的味道'\n
    │                输出: ['臭氧', '湿润木质', '青草', '泥土']"
    │
    └── 3. 解码结果作为 GraphRAG 检索的引导种子节点
           (已在 search_fragrance_by_emotion 中支持 seed_notes 参数)
```

### 改动

| 文件 | 改动 |
|------|------|
| `backend/app/services/llm_emotion.py` | 增加 `_decode_synesthesia()` 函数，在 emotion result 中增加 `synesthesia_tokens` 字段 |
| `backend/app/sse/stream.py` | 将 synesthesia_tokens 传入 GraphRAG 搜索 |

此功能改动量小（~50 行），嵌入现有流程，无需新端点或新组件。

---

## 实施顺序

```
Step 1: F5 (抽象需求) — 改动最小，独立
Step 2: F1 迁移 + profile service + profile API (画像基础设施)
Step 3: F2 (引导问卷) — 依赖 F1 的 user_profiles 表和 /profile/onboarding 端点
Step 4: F3 (AI眼中的我) — 依赖 F1 的 GET /profile + profileStore
Step 5: F4 (情绪日记) — 依赖 L3 数据 + /journal 端点
```

---

## 文件统计

| 类别 | 新建 | 修改 | 合计 |
|------|:---:|:---:|:---:|
| Backend | 5 | 4 | 9 |
| Frontend | 6 | 2 | 8 |
| Migrations | 1 | 0 | 1 |
| Tests | 3 | 0 | 3 |
| **总计** | **15** | **6** | **21** |

---

## 全局约束

- 无新 Python/npm 依赖（recharts 已在项目中）
- 画像数据仅对用户本人可见（JWT 认证）
- 引导问卷仅触发一次（`profile_data.questionnaire_completed` 标记）
- 情绪日记周报在每周一凌晨异步生成，不阻塞任何请求
- 抽象需求解码复用现有 LLM 管线（llm_emotion.py 模式）

---

## 验证

```bash
# Backend tests
cd backend && python -m pytest tests/ -v -m "not e2e"  # ≥130 passed

# Frontend tests
cd packages/frontend && npx vitest run                    # ≥25 passed

# TypeScript
cd packages/frontend && npx tsc --noEmit                  # Zero errors

# Manual: profile
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/v1/profile
# → {personality_tags: [...], emotion_tendency: {...}, ...}

# Manual: synesthesia
curl "http://127.0.0.1:8000/api/v1/guest/sessions?text=下雨的味道"
# → chat.emotion.synesthesia_tokens: ["臭氧", "湿润木质", "青草"]
```
