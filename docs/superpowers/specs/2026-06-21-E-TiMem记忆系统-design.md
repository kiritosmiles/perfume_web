# E 路径：TiMem 记忆系统 — 设计文档

> **状态**: 已确认  
> **日期**: 2026-06-21  
> **依赖**: D 路径（用户系统）已完成  
> **参考**: TiMem: Temporal-Hierarchical Memory Consolidation (arXiv:2601.02845)  

## 概述

基于 TiMem 时序分层记忆框架，将当前 TRD 的三层记忆架构升级为**三级时序记忆树 (TMT)**，实现会话内事实追踪、跨会话偏好持久化、日级行为模式识别。MVP 范围内裁剪为 L1-L3（片段→会话→日级），L4-L5 预留后续。

| ID | 层级 | 粒度 | 存储 | 整合方式 | 预估 |
|----|------|------|------|----------|------|
| E1 | L₁ 片段层 | 单轮对话 | Redis Hash | 写入同步 + LLM 异步 | 2h |
| E2 | L₂ 会话层 | 单次会话 | PG + 向量索引 | Redis Queue 异步 | 2h |
| E3 | L₃ 日级层 | 一天 | PG + 向量索引 | Cron 每日凌晨 | 2h |
| E4 | 复杂度感知召回 | 检索流水线 | — | 串行（emotion→recall→gen） | 2h |
| E5 | 记忆整合器 Prompt | LLM Prompt 工程 | — | 分层指令模板 | 1h |

### 设计决策汇总

| 决策点 | 选择 | 依据 |
|--------|------|------|
| MVP 范围 | L1-L3 三级（L4-L5 预留） | 平衡功能完整性与交付速度 |
| L1 存储 | Redis Hash（session TTL） | 低延迟，会话生命周期 |
| L2 存储 | PostgreSQL + pgvector 向量扩展 | 持久化，跨会话检索 |
| L3 存储 | PostgreSQL + pgvector | 与 L2 同表不同层级标记 |
| Embedding | bge-small-zh (~24MB, 768d) | 本地推理 ~5ms，中文优化 |
| L1 整合 | 写入同步 + LLM 异步（两段式） | 证据不丢，整合不阻塞 SSE |
| L2 整合 | Redis Queue 异步（会话结束时入队） | 不阻塞主流程 |
| L3 整合 | Cron 定时（每日凌晨 3am） | 无实时性要求 |
| 召回嵌入点 | emotion → recall → gen（串行） | 情绪向量作为检索锚点 |
| 召回算法 | 双通道：bge cosine (w=0.9) + ts_rank (w=0.1) | MVP 用 PG ts_rank 近似 BM25 |
| Guest 记忆 | L2/L3 表独立字段（user_id OR browser_id） | 与 temp_conversations 模式一致 |
| 整合 LLM 成本 | 服务端 Key（deepseek-chat） | 基础设施，不依赖用户 Key |
| chat.recall 前端 | 静默（不渲染 UI） | MVP 仅日志，具体记忆内容透出留给 MemoryPage |
| MemoryPage | 可读时间线（L2/L3 摘要列表） | 只读，无编辑/删除 |

---

## 数据结构

### L₁ 片段层 (Redis)

```
Key:   memory:L1:{session_id}:{round_num}
Type:  Hash
Fields:
  - text: str           # 第三人称事实摘要
  - embedding: bytes    # bge-small-zh 768d float32 → bytes
  - timestamp: str      # ISO 8601
  - round_num: int      # 会话内轮次序号
  - emotion_vector: str # JSON, 8维情绪向量
TTL:   与 session TTL 一致（会话结束后 1h 过期）
```

### L₂ 会话层 (PostgreSQL)

```sql
CREATE TABLE memory_l2 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    browser_id TEXT,                -- Guest 用户标识（注册前）
    session_id UUID NOT NULL,
    text TEXT NOT NULL,              -- 去重后的事件摘要（会话级压缩）
    embedding vector(768),           -- pgvector 扩展
    emotion_profile JSONB DEFAULT '{}',  -- 会话内情绪分布统计
    round_count INTEGER NOT NULL DEFAULT 0,  -- 原始对话轮数
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_memory_l2_owner CHECK (
        (user_id IS NOT NULL AND browser_id IS NULL)
        OR (user_id IS NULL AND browser_id IS NOT NULL)
    )
);
CREATE INDEX idx_memory_l2_user ON memory_l2 (user_id, created_at);
CREATE INDEX idx_memory_l2_browser ON memory_l2 (browser_id, created_at);
CREATE INDEX idx_memory_l2_embedding ON memory_l2 USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

> **Guest → User 迁移**：注册时 `UPDATE memory_l2 SET user_id=..., browser_id=NULL WHERE browser_id=$1`，与 `temp_conversations` 迁移逻辑一致。

### L₃ 日级层 (PostgreSQL)

```sql
CREATE TABLE memory_l3 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    browser_id TEXT,                -- Guest 用户标识（注册前）
    date DATE NOT NULL,
    text TEXT NOT NULL,              -- 日级偏好模式摘要
    embedding vector(768),
    preference_keywords TEXT[],       -- 提取的关键偏好词（香调、品牌、场景）
    session_count INTEGER NOT NULL DEFAULT 0,
    emotion_summary JSONB DEFAULT '{}',  -- 当日情绪汇总
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, date),
    UNIQUE (browser_id, date),
    CONSTRAINT chk_memory_l3_owner CHECK (
        (user_id IS NOT NULL AND browser_id IS NULL)
        OR (user_id IS NULL AND browser_id IS NOT NULL)
    )
);
CREATE INDEX idx_memory_l3_user ON memory_l3 (user_id, date);
CREATE INDEX idx_memory_l3_browser ON memory_l3 (browser_id, date);
CREATE INDEX idx_memory_l3_embedding ON memory_l3 USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

> 注意：两个 UNIQUE 约束不能同时生效（CHECK 保证互斥），实际行为是每个 owner 每天最多一条。

### 整合任务队列 (Redis)

```
Key:   memory:queue:L2          # L2 整合任务队列 (List)
Value: JSON { owner_type: "user"|"guest", owner_id, session_id, created_at }

Key:   memory:queue:L3          # L3 整合任务队列 (List)
Value: JSON { owner_type: "user"|"guest", owner_id, date, created_at }

Key:   memory:queue:L2:dead     # L2 死信队列 (List)
Key:   memory:queue:L3:dead     # L3 死信队列 (List)

# Worker 消费:
#   BRPOP memory:queue:L2 → 执行整合 → 写入 PG → ACK
#   整合失败 3 次 → RPUSH memory:queue:L2:dead → 日志 warn
#   BRPOP memory:queue:L3 → 同上
```

---

## 记忆整合器 (Memory Consolidator)

### 分层 Prompt 策略

**L₁ 片段整合 (两段式：写入同步 + 整合异步):**

**阶段 A：证据写入 (在线，<2ms，不阻塞 SSE)**
- 将原始对话文本 + emotion_vector 写入 Redis Hash（`memory:L1:{session_id}:{round_num}`）
- 不调用 LLM，纯 Redis 操作

**阶段 B：LLM 整合 (异步，gen.complete 后触发，不阻塞用户)**

```
System: 你是一个记忆编码器。将用户对话转为第三人称事实摘要。
输入：本轮用户输入 + Agent 回复
规则：
1. 保留：香调名称、品牌、产品名、情绪状态、场景、偏好反馈（喜欢/讨厌/太甜/太浓）
2. 排除：问候语、确认词、纯功能词
3. 时间：保持原始相对时间（不说日期）
4. 格式：纯句子，单一自然段，中文
5. 不重复同会话历史片段中已有的事实
6. 特别标记：如果用户表达了明确的喜欢/不喜欢 → 以"[偏好]"开头
输出：更新 Redis Hash 的 text 字段
```

> 分离理由：LLM 整合 ~500ms，若在 gen.complete 之前同步执行会阻塞最终事件发出，用户感知延迟。

**L₂ 会话整合 (异步，会话结束触发):**

```
System: 你是一个会话记忆整合器。合并多个片段为无冗余的会话摘要。
输入：本轮会话的全部 L1 片段列表 + 最近 3 次历史 L2 摘要
    （历史 L2 获取：SELECT text FROM memory_l2
     WHERE user_id=$1 OR browser_id=$1 ORDER BY created_at DESC LIMIT 3）
规则：
1. 去重：同一事实只保留一次
2. 合并：相关联的事实合并为一个事件（如"用户查看了TF乌木"+"用户说TF乌木太浓"→"用户对TF乌木不满意，认为过于浓郁"）
3. 偏好稳定性：标记反复出现的偏好（同一香调被提及≥2次 → 标注[稳定偏好]）
4. 情绪轨迹：概述会话内情绪变化（开始→结束）
5. 格式：2-4 个自然段，中文，按主题分组
```

**L₃ 日级整合 (定时，每日凌晨):**

```
System: 你是一个日级记忆整合器。从一天的交互中提取偏好模式。
输入：当日所有 L2 摘要 + 最近 7 天 L3 摘要
规则：
1. 模式识别：识别重复≥2天的行为模式 → 标注[日级模式]
2. 新鲜度标记：首次出现的新偏好 → 标注[新发现]
3. 季节性：识别与季节相关的偏好变化
4. 关键词提取：输出 3-8 个核心偏好关键词（香调、品牌、场景）
5. 格式：2-3 个自然段 + JSON 关键词列表，中文
```

---

## 复杂度感知召回 (Complexity-Aware Recall)

### 嵌入点：SSE 管线

```
原管线:
  chat.ack → chat.emotion → gen.start → gen.skeleton → gen.copy → gen.complete

新管线:
  chat.ack → chat.emotion → chat.recall → gen.start → gen.skeleton → gen.copy → gen.complete
               (50ms)        (500ms)      (200ms+)
```

**`chat.recall` 事件定义：**

```typescript
// 共享类型 packages/shared/src/sse/events.ts — 新增事件
| { type: "chat.recall"; generation_id: string;
    complexity: "simple" | "hybrid" | "complex";
    recalled_count: number;
    memory_sources: ("L1" | "L2" | "L3")[];
    latency_ms: number;
  }
```

> 前端处理：MVP 阶段静默（仅 console.debug 日志），不渲染 UI。具体记忆内容仅在 MemoryPage 透出。
```

### Step 1: 召回规划器 (1 次 LLM 调用)

```
System: 判断用户查询的复杂度，输出标签和关键词。
输入：用户原始文字 + 情绪识别结果

复杂度判断规则：
- 需要回忆历史偏好/习惯/性格 → complex
- 需要总结多个历史事实 → hybrid
- 简单事实询问 → simple

输出格式：JSON { complexity: "simple"|"hybrid"|"complex", keywords: [...] }
```

| 复杂度 | 搜索层级 | L1 预算 | L2 预算 | L3 预算 | 门控保留 |
|--------|----------|:---:|:---:|:---:|:---:|
| simple | L1+L2 | 20 | 4 | 0 | 3-8 条 |
| hybrid | L1+L2+L3 | 20 | 4 | 2 | 8-15 条 |
| complex | L1+L2+L3 | 20 | 8 | 4 | 15-25 条 |

### Step 2: 分层检索 (0 次 LLM 调用)

```python
# 双通道评分融合
score = 0.9 * cosine_similarity(query_emb, memory_emb) + 0.1 * pg_ts_rank(query_text, memory_text)
# MVP: BM25 用 PostgreSQL ts_rank + plainto_tsquery('simple') 近似，后续可换 paradedb/pg_bm25
# 权重依据 TiMem 论文（语义检索主导，关键词补充召回）

# 叶节点激活：L1 中取 top-K 片段
# 向上传播：沿时间包含关系收集祖先节点
```

### Step 3: 召回门控 (1 次 LLM 调用)

```
System: 你是一个记忆门控器。过滤与当前查询不相关或冗余的记忆。
输入：候选记忆列表 + 用户查询 + 复杂度标签
规则：
- simple: 激进过滤（仅直接相关，3-8 条）
- hybrid: 适度过滤（允许 1 度间接相关，8-15 条）
- complex: 宽松保留（广泛上下文，15-25 条）
输出：过滤后的记忆列表 + 拒绝理由摘要
```

### 上下文注入

召回结果注入 `gen.skeleton` 阶段的 LLM prompt：

```python
memory_context = format_recalled_memories(recalled_items)
# 注入到 generation.py 的 _stream_llm_skeleton() 和 _stream_llm_copy()
# 格式：
"""
## 用户历史记忆
- [L2 2026-06-20] 用户在下午咨询了木质柑橘调，偏好TF乌木但认为过于浓郁
- [L1 当前会话] [偏好] 用户喜欢清新的柠檬前调
- [L3 2026-06-19] [日级模式] 本周反复查看春夏香水，偏好转向柑橘调
"""
```

---

## MemoryPage — "AI 眼中的我"

### 后端 API

```
GET /api/v1/memory/timeline?limit=20&offset=0
Authorization: Bearer <token> (auth用户) 或 X-Browser-Id (guest)
Response:
{
  "items": [
    {
      "level": "L2" | "L3",
      "id": "uuid",
      "text": "用户对TF乌木不满意，认为过于浓郁...",
      "emotion_profile": { "primary": "calm", ... },
      "created_at": "2026-06-20T15:30:00Z",
      "metadata": { "round_count": 5, "preference_keywords": ["木质", "柑橘"] }
    }
  ],
  "stats": { "l1_count": 12, "l2_count": 3, "l3_count": 1 },
  "total": 4
}
```

> Guest 用户通过 `X-Browser-Id` header 认证（无需注册）。

### 前端路由

- `/memory` — ProtectedRoute 或 Guest 均可访问
- 时间线列表：按 `created_at` 倒序，每条显示层级标签（L2/L3）、创建时间、摘要文本、情绪标签
- 顶部统计卡片：L1/L2/L3 各几条
- 只读，无编辑/删除

---

## 文件清单

### 后端

| 文件 | 新建/修改 | 说明 |
|------|:--:|------|
| `backend/app/core/embedding.py` | 新建 | bge-small-zh 模型加载 + encode() |
| `backend/app/core/consolidator.py` | 新建 | L1/L2/L3 整合 Prompt + LLM 调用 |
| `backend/app/core/recall.py` | 新建 | 规划器 + 分层检索 + 门控流水线 |
| `backend/app/core/memory_queue.py` | 新建 | Redis Queue 生产者 + 消费者 |
| `backend/app/services/memory.py` | 新建 | 统一记忆 API（write/read/consolidate） |
| `backend/app/sse/stream.py` | 修改 | 添加 chat.recall 事件 + L1 证据写入 + L1 异步整合 |
| `backend/app/api/v1/guest.py` | 修改 | 会话结束时启动空闲计时器 → L2 入队（guest 路径） |
| `backend/app/api/v1/recommend.py` | 修改 | 会话结束时启动空闲计时器 → L2 入队（auth 路径） |
| `backend/app/api/v1/memory.py` | 新建 | GET /memory/timeline（MemoryPage 后端 API） |
| `backend/app/core/config.py` | 修改 | +BGE_MODEL_PATH, +RECALL_TOP_K 等 |
| `backend/alembic/versions/004_memory.py` | 新建 | memory_l2 + memory_l3 表 + pgvector 扩展 |
| `backend/pyproject.toml` | 修改 | +sentence-transformers + pgvector |
| `backend/scripts/consolidate_l3.py` | 新建 | L3 每日 cron 脚本 |
| `backend/scripts/worker_l2.py` | 新建 | L2 异步 worker |
| `backend/tests/test_memory.py` | 新建 | 记忆系统测试 |
| `docker/docker-compose.yml` | 修改 | postgres 镜像换 `pgvector/pgvector:pg15` |
| `docker/postgres/init/002_pgvector.sql` | 新建 | CREATE EXTENSION vector |

### 前端

| 文件 | 新建/修改 | 说明 |
|------|:--:|------|
| `packages/frontend/src/lib/apiClient.ts` | 修改 | +getMemoryTimeline API |
| `packages/frontend/src/routes/MemoryPage.tsx` | 新建 | "AI 眼中的我"记忆透明页 |
| `packages/frontend/src/App.tsx` | 修改 | +/memory 路由 |

---

## 调度流程图

```
时间轴 →

│ 用户发送消息
├── SSE: chat.ack
├── SSE: chat.emotion ──────── emotion 向量完成 (50ms)
├── SSE: chat.recall ──────── 规划器 → 检索 → 门控 (~510ms)
├── SSE: gen.skeleton ─────── 注入 memory_context (200ms)
├── SSE: gen.copy ──────────── 注入 memory_context (流式)
│
│  [L1 证据写入] ──────────── 同步：原始文本写入 Redis Hash (<2ms)
│
├── SSE: gen.complete
│  [L1 LLM 整合] ──────────── 异步：LLM 摘要 → 更新 Redis Hash text 字段
│
│  [会话空闲计时器] ───────── gen.complete 后启动 30s Redis TTL key
│  同一 session 新消息 → 重置计时器
│  计时器到期 → 触发 L2 整合
│  [L2 入队] ───────────────── RPUSH memory:queue:L2 {owner_type, owner_id, session_id}
│
│  Worker (后台进程):
│  [L2 消费] ───────────────── BRPOP → 整合 → INSERT memory_l2
│
│  每日 3am Cron:
│  [L3 消费] ───────────────── 检查当天有 session 的用户 → 整合 → INSERT memory_l3
```

---

## 回退策略

| 场景 | 行为 |
|------|------|
| bge-small-zh 不可用 | 降级到 LLM API Embedding（用现有 deepseek-chat） |
| L1 Redis 写入失败 | 日志 warn，不阻塞主流程（原子证据丢失但系统不崩溃） |
| L2 Queue 不可用 | 直接在会话结束时同步写入 PG（退化为阻塞模式） |
| L3 Cron 失败 | 每日重试 + 手动补跑脚本 |
| 召回召回门控超时 > 2s | 跳过记忆注入，仅用当前查询生成推荐 |
| pgvector 未安装 | SQL 回退：用 text LIKE 模糊匹配替代向量检索 |
| 新用户无历史记忆 | 跳过召回流水线，首次体验不受影响 |

## 不在范围

- L4 周级 + L5 画像层（后续 Path）
- Faiss / Milvus 外部向量数据库
- 冷归档层（S3 对象存储）
- 记忆删除/编辑 UI（记忆透明页只读）
- 送礼模式记忆（仅自用模式）
- 多用户记忆共享

---

## 性能预估

| 操作 | 预估延迟 | 说明 |
|------|----------|------|
| L1 证据写入 (Redis) | < 2ms | Redis HSET，不阻塞 gen.complete |
| L1 LLM 整合 | ~500ms | gen.complete 后异步执行，不阻塞主流程 |
| L2 会话整合 (LLM) | ~2s | 1 次 LLM，多片段输入，异步 |
| L3 日级整合 (LLM) | ~3s | 1 次 LLM，多摘要输入，Cron |
| bge-small-zh encode | ~5ms | 本地 CPU，768d |
| 召回规划器 (LLM) | ~200ms | 轻量 Prompt，JSON 输出 |
| 分层检索 (向量+ts_rank) | ~10ms | pgvector cosine + PostgreSQL ts_rank |
| 召回门控 (LLM) | ~300ms | 过滤+排序，短回答 |
| 召回总量 | ~510ms | 规划器 200ms + 检索 10ms + 门控 300ms |
| **用户感知增加** | **~510ms** | chat.recall 新事件，在 skeleton 之前 |
| GET /memory/timeline | <50ms | 简单 PG 查询，无 LLM |
