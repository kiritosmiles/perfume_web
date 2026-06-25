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

| FR-2.5 | 情绪价值维度映射 | ✅ 完成 | compute_value_dimensions (8→6 deterministic) + SSE + Profile API + ProfilePage bar chart |
| FR-3.5 | AI配方生成（意图门控） | ✅ 完成 | 三分支完整: self_use(过敏原过滤) + gift(常见过敏原标注+收礼人字段) + explore(跳过安全档案+跨集群探索) |
| FR-5.7 | 会话意图检测 | ✅ 完成 | 3层检测(keyword<1ms → LLM ~800ms → default) + info_completeness维度输出 |
| FR-3.9 | 送礼场景推荐策略 | ✅ 完成 | gift=safe cluster priority + GIFT_STORY_TEMPLATES (8 emotions × 4 lines) |
| FR-5.11 | 信息完整性 Agent Gate | ✅ 完成 | agent_gate.py + gate.* SSE events + GateQuestionBanner组件 + 500ms硬边界 |
| FR-7.1 | 隐式反馈采集 | ✅ 完成 | useImplicitTracking hook + card_viewed/share_clicked/refine_used events |
| FR-7.2 | 显式反馈 | ✅ 完成 | ActionBar like/dislike + feedback API (202) + feedback PG表 |

| FR-1.1 | 用户画像建档 | ✅ 完成 | user_profiles表 + profile service + GET/POST /profile API |
| FR-1.2 | 冷启动引导问卷 | ✅ 完成 | OnboardingModal (3 questions) + POST /profile/onboarding |
| FR-1.3 | 渐进式画像构建 | ✅ 完成 | light(1-3次) → full(4+次) threshold + EMA emotion update |
| FR-4.8 | 用户记忆透明化 ("AI眼中的我") | ✅ 完成 | ProfilePage: personality tags + SVG radar chart + gift history |
| FR-5.8 | 抽象/超现实需求处理 | ✅ 完成 | llm_emotion.py synesthesia decoding → seed_notes → GraphRAG boost |
| FR-1.6 | 动态标签更新 | ✅ 完成 | extract_full_profile_llm async extraction every 5 convos, fire-and-forget from gen.complete |

| FR-4.9 | 主动回访与情绪日记 | ✅ 完成 | journal.py + GET /journal/trend + /journal/weekly + EmotionTrend + WeeklyJournal |
| FR-2.8 | 环境感知 | ✅ 完成 | environment.py 季节/天气/时段向量融合 (权重 0.1-0.2) + useEnvironment hook + Open-Meteo API |
| FR-3.8 | 推荐多样化 | ✅ 完成 | diversity 0-1 扰动搜索 + cross-style _diverse_top3 + random_style 精炼 + DiversitySelector UI |
| — | GraphRAG 热点缓存 | ✅ 完成 | Redis graphrag:* 缓存 (card-preset 36 种组合, TTL 1h) + cache_hit metadata |
| FR-3.10 | 调香师协作桥 | ⏳ Phase 4 | B端功能，非MVP范围 |
| FR-1.4 | 社交授权导入 | ⏳ Phase 4 | 第三方导入 |
| FR-1.5 | 三种 Session 模式 | ✅ 完成 | Identity/Context/Novelty 三模式 + SessionModeSelector UI + novelty强制diversity≥0.5 |
| FR-5.5 | 过渡动画与等待体验 | ⏳ Batch 3 | 精细化动画 (KnowledgeCardOverlay) |
| FR-5.9 | Agent 角色边界保护 | ✅ 完成 | LLM调用B异步安全旁路 + overstep/borderline/injection/hostile 五级判决 + 3次连续越界→转人工 |
| — | 配方骨架缓存 | ✅ 完成 | Redis skeleton:* 缓存 (card-preset, TTL 24h) + skeleton_cache_hit metadata + gen.copy缓存直出 |
| — | 免费/付费切割 | ✅ 完成 | users.feature_tier (free/premium) + tier配额差异化 + JWT tier claim + QuotaBar UI |

## 统计

| 类别 | 数量 | 占比 |
|------|:---:|:---:|
| ✅ 完成 | 33 | 94% |
| ⏳ 后MVP (Batch 3) | 2 | 6% |

**当前覆盖率: 33/35 FR = 94% (含 Batch 1+2 五项)**
*(注: FR-3.10 调香师协作桥 + FR-1.4 社交授权导入 本批次跳过；FR-5.5 过渡动画 留待 Batch 3)*
