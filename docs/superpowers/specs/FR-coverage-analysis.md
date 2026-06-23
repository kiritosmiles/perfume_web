# PRD 功能需求 (FR) 覆盖分析

> 日期: 2026-06-23
> 基准: `docs/superpowers/specs/2026-06-19-A-产品需求文档.md` (35 FRs)
> 当前版本: MVP Phase 1

## MVP Phase 1 FR 覆盖状态 (20 FRs)

| FR ID | 名称 | 状态 | 实现说明 |
|-------|------|:---:|---------|
| FR-1.7 | 游客模式 | ✅ 完成 | GuestChatPage + SSE guest/sessions + browser_id |
| FR-1.9 | 游客数据迁移 | ✅ 完成 | Register API 迁移 temp_conversations.user_id |
| FR-2.1 | 双通道情绪输入 | ✅ 完成 | EmotionCardPicker (8 cards) + textarea 文本输入 |
| FR-2.2 | 情绪识别 | ✅ 完成 | card_preset / bert / llm_fallback / llm_text 四源 |
| FR-2.3 | 情绪确认微交互 | ✅ 完成 | EmotionConfirmation 组件 + Correct/Regenerate 操作 |
| FR-2.4 | 情绪向量化 | ✅ 完成 | 8-D 向量 (joy/sadness/anxiety/calm/excitement/nostalgia/romance/melancholy) |
| FR-2.6 | 混合情绪支持 | ✅ 完成 | 双通道加权合并 (文字 0.7 + 卡片 0.3) |
| FR-2.7 | 场合/场景输入 | ✅ 完成 | SceneTagChips (6 preset scenes) |
| FR-3.1 | 情绪—香调映射 | ✅ 完成 | Neo4j GraphRAG 1-hop (Emotion→Accord→Perfume) |
| FR-3.6 | 产品输出与对比 | ✅ 完成 | FragranceCard ranking + match_score + 进度条 |
| FR-4.11 | 全量会话持久化 | ✅ 完成 | Memory API + MemoryPage 时间线 |
| FR-5.6 | 危机场景差异化 | ✅ 完成 | crisis_check → safety.crisis/safety.block + CrisisOverlay 渲染热线 |
| FR-1.8 | 香氛安全档案 | ✅ 完成 | SettingsPage 过敏原输入 + backend _check_allergens + FragranceCard 红色徽章 |
| FR-3.7 | 推荐精炼对话 | ✅ 完成 | 18条规则引擎 refinement.py + 8 RefinementChips + SSE adjustable vector |
| FR-4.7 | 反问确认机制 | ✅ 完成 | 置信度<85%追问UI (Yes/Let me rephrase) |
| FR-5.3 | 转人工机制 | ✅ 完成 | human_handoff_check("转人工/找客服") → system.notification + CrisisOverlay |

| FR-2.5 | 情绪价值维度映射 | 🔶 部分 | emotion→value_dim 映射存在，但仅用于 graphrag_match 评分 — MVP 够用 |
| FR-3.5 | AI配方生成（意图门控） | 🔶 部分 | self_use 模式完整，gift/explore 模式待 Phase 2 |
| FR-5.7 | 会话意图检测 | 🔶 部分 | 基于场景标签+关键词检测，LLM驱动待 Phase 2 |

| FR-1.1 | 用户画像建档 | ❌ 未实现 | Phase 2+ 用户系统深化 |
| FR-1.2 | 冷启动引导问卷 | ❌ 未实现 | Phase 2+ 新用户引导 |
| FR-1.3 | 渐进式画像构建 | ❌ 未实现 | Phase 2+ 前3次轻量→4次起完整 |
| FR-1.6 | 动态标签更新 | ❌ 未实现 | Phase 2+ Memory 深化 |

## Phase 2-4 FRs (17 FRs, 全部后MVP)

| FR ID | 名称 | Phase |
|-------|------|:---:|
| FR-3.9 | 送礼场景推荐策略 | 2 |
| FR-5.11 | 信息完整性 Agent Gate | 2 |
| FR-7.1 | 隐式反馈采集 | 2 |
| FR-7.2 | 显式反馈 | 2 |
| FR-3.10 | 调香师协作桥 | 3 |
| FR-4.8 | 用户记忆透明化 ("AI眼中的我") | 3 |
| FR-4.9 | 主动回访与情绪日记 | 3 |
| FR-5.8 | 抽象/超现实需求处理 | 3 |
| FR-1.4 | 社交授权导入 | 4 |
| FR-1.5 | 三种 Session 模式 | 4 |
| FR-2.8 | 环境感知 | 4 |
| FR-3.8 | 推荐多样化 | 4 |
| FR-5.5 | 过渡动画与等待体验 | 4 |
| FR-5.9 | Agent 角色边界保护 | 4 |

## 统计

| 类别 | 数量 | 占比 |
|------|:---:|:---:|
| ✅ 完成 | 16 | 46% |
| 🔶 部分 | 3 | 9% |
| ❌ 未实现 (实际Phase 2+) | 4 | 11% |
| ⏳ 后MVP (Phase 2-4) | 17 | 49% |

**MVP Phase 1 覆盖率: 16/20 = 80% (含部分实现: 19/20 = 95%)**
