-- 001 MVP Schema: PostgreSQL tables for perfume AI agent
-- Creates 5 tables + seed data for emotion_cards and scene_tags

-- Table 1: Temporary conversations (guest + authenticated users)
CREATE TABLE IF NOT EXISTS temp_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    browser_id VARCHAR(128) NOT NULL,
    temp_session_id VARCHAR(128),
    round INTEGER NOT NULL DEFAULT 0,
    role VARCHAR(8) NOT NULL CHECK (role IN ('user', 'agent')),
    content TEXT NOT NULL,
    emotion_tags JSONB DEFAULT '{}',
    recommendation JSONB DEFAULT '{}',
    safety_flags JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_temp_conv_browser_time
    ON temp_conversations (browser_id, created_at);

-- Table 2: Emotion cards (8 basic emotions with 8-dimension vectors)
CREATE TABLE IF NOT EXISTS emotion_cards (
    id INTEGER PRIMARY KEY,
    emoji VARCHAR(8) NOT NULL,
    label VARCHAR(32) NOT NULL,
    vector JSONB NOT NULL
);

INSERT INTO emotion_cards (id, emoji, label, vector) VALUES
    (1, '😊', '开心', '{"joy":0.9,"excitement":0.7,"calm":0.2,"romance":0.1,"sadness":0,"anxiety":0,"nostalgia":0,"melancholy":0}'),
    (2, '😢', '难过', '{"sadness":0.9,"melancholy":0.5,"nostalgia":0.3,"calm":0.1,"joy":0,"anxiety":0,"excitement":0,"romance":0}'),
    (3, '😰', '焦虑', '{"anxiety":0.9,"melancholy":0.4,"sadness":0.3,"calm":0.1,"joy":0,"excitement":0,"nostalgia":0,"romance":0}'),
    (4, '😌', '平静', '{"calm":0.9,"nostalgia":0.3,"joy":0.2,"melancholy":0.1,"sadness":0,"anxiety":0,"excitement":0,"romance":0}'),
    (5, '🎉', '兴奋', '{"excitement":0.9,"joy":0.8,"romance":0.3,"calm":0,"sadness":0,"anxiety":0,"nostalgia":0,"melancholy":0}'),
    (6, '🥺', '怀旧', '{"nostalgia":0.9,"melancholy":0.5,"calm":0.4,"romance":0.2,"joy":0,"sadness":0,"anxiety":0,"excitement":0}'),
    (7, '💕', '浪漫', '{"romance":0.9,"joy":0.6,"excitement":0.5,"nostalgia":0.3,"sadness":0,"anxiety":0,"calm":0,"melancholy":0}'),
    (8, '🌧️', '忧郁', '{"melancholy":0.9,"sadness":0.6,"nostalgia":0.4,"anxiety":0.3,"joy":0,"excitement":0,"calm":0,"romance":0}')
ON CONFLICT (id) DO NOTHING;

-- Table 3: Scene tags
CREATE TABLE IF NOT EXISTS scene_tags (
    id INTEGER PRIMARY KEY,
    emoji VARCHAR(8) NOT NULL,
    label VARCHAR(32) NOT NULL
);

INSERT INTO scene_tags (id, emoji, label) VALUES
    (1, '💼', '通勤工作'),
    (2, '💑', '约会之夜'),
    (3, '🏠', '宅家放松'),
    (4, '🎊', '聚会社交'),
    (5, '🎁', '挑选礼物'),
    (6, '🔍', '随便看看')
ON CONFLICT (id) DO NOTHING;

-- Table 4: Fragrance templates (knowledge base)
CREATE TABLE IF NOT EXISTS fragrance_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(128) NOT NULL,
    notes_top TEXT[],
    notes_middle TEXT[],
    notes_base TEXT[],
    mood_tags TEXT[],
    scene_tags TEXT[],
    story_copy TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_fragrance_mood_tags
    ON fragrance_templates USING GIN (mood_tags);

-- Table 5: Guest quota (one free session per browser)
CREATE TABLE IF NOT EXISTS guest_quota (
    browser_id VARCHAR(128) PRIMARY KEY,
    used BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '30 days')
);
