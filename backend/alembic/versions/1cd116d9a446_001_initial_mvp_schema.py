"""001_initial_mvp_schema

Revision ID: 1cd116d9a446
Revises:
Create Date: 2026-06-21 01:24:06.762285

Baseline migration — recreates current MVP schema state.
Matches docker/postgres/init/001-mvp-schema.sql + 002-seed-templates.sql.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1cd116d9a446"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Table 1: temp_conversations ──────────────────────────
    op.execute("""
        CREATE TABLE temp_conversations (
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
        )
    """)
    op.execute("""
        CREATE INDEX idx_temp_conv_browser_time
            ON temp_conversations (browser_id, created_at)
    """)

    # ── Table 2: emotion_cards ───────────────────────────────
    op.execute("""
        CREATE TABLE emotion_cards (
            id INTEGER PRIMARY KEY,
            emoji VARCHAR(8) NOT NULL,
            label VARCHAR(32) NOT NULL,
            vector JSONB NOT NULL
        )
    """)
    op.execute("""
        INSERT INTO emotion_cards (id, emoji, label, vector) VALUES
            (1, '😊', '开心', '{"joy":0.9,"excitement":0.7,"calm":0.2,"romance":0.1,"sadness":0,"anxiety":0,"nostalgia":0,"melancholy":0}'),
            (2, '😢', '难过', '{"sadness":0.9,"melancholy":0.5,"nostalgia":0.3,"calm":0.1,"joy":0,"anxiety":0,"excitement":0,"romance":0}'),
            (3, '😰', '焦虑', '{"anxiety":0.9,"melancholy":0.4,"sadness":0.3,"calm":0.1,"joy":0,"excitement":0,"nostalgia":0,"romance":0}'),
            (4, '😌', '平静', '{"calm":0.9,"nostalgia":0.3,"joy":0.2,"melancholy":0.1,"sadness":0,"anxiety":0,"excitement":0,"romance":0}'),
            (5, '🎉', '兴奋', '{"excitement":0.9,"joy":0.8,"romance":0.3,"calm":0,"sadness":0,"anxiety":0,"nostalgia":0,"melancholy":0}'),
            (6, '🥺', '怀旧', '{"nostalgia":0.9,"melancholy":0.5,"calm":0.4,"romance":0.2,"joy":0,"sadness":0,"anxiety":0,"excitement":0}'),
            (7, '💕', '浪漫', '{"romance":0.9,"joy":0.6,"excitement":0.5,"nostalgia":0.3,"sadness":0,"anxiety":0,"calm":0,"melancholy":0}'),
            (8, '🌧️', '忧郁', '{"melancholy":0.9,"sadness":0.6,"nostalgia":0.4,"anxiety":0.3,"joy":0,"excitement":0,"calm":0,"romance":0}')
    """)

    # ── Table 3: scene_tags ──────────────────────────────────
    op.execute("""
        CREATE TABLE scene_tags (
            id INTEGER PRIMARY KEY,
            emoji VARCHAR(8) NOT NULL,
            label VARCHAR(32) NOT NULL
        )
    """)
    op.execute("""
        INSERT INTO scene_tags (id, emoji, label) VALUES
            (1, '💼', '通勤工作'),
            (2, '💑', '约会之夜'),
            (3, '🏠', '宅家放松'),
            (4, '🎊', '聚会社交'),
            (5, '🎁', '挑选礼物'),
            (6, '🔍', '随便看看')
    """)

    # ── Table 4: fragrance_templates ─────────────────────────
    op.execute("""
        CREATE TABLE fragrance_templates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(128) NOT NULL,
            notes_top TEXT[],
            notes_middle TEXT[],
            notes_base TEXT[],
            mood_tags TEXT[],
            scene_tags TEXT[],
            story_copy TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE INDEX idx_fragrance_mood_tags
            ON fragrance_templates USING GIN (mood_tags)
    """)
    # Unique constraint on name (added post-init in 2026-06-20)
    op.execute("""
        ALTER TABLE fragrance_templates ADD CONSTRAINT uq_fragrance_name UNIQUE (name)
    """)

    # ── Table 5: guest_quota ─────────────────────────────────
    op.execute("""
        CREATE TABLE guest_quota (
            browser_id VARCHAR(128) PRIMARY KEY,
            used BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '30 days')
        )
    """)

    # ── Seed: 10 classic fragrances ──────────────────────────
    op.execute("""
        INSERT INTO fragrance_templates (name, notes_top, notes_middle, notes_base, mood_tags, scene_tags, story_copy) VALUES
        ('No.5 Chanel',
         ARRAY['醛香 Aldehydes','依兰 Ylang-Ylang','橙花 Neroli'],
         ARRAY['玫瑰 Rose','茉莉 Jasmine','鸢尾 Iris'],
         ARRAY['檀木 Sandalwood','香草 Vanilla','岩兰草 Vetiver'],
         ARRAY['romance','calm','nostalgia'],
         ARRAY['date','gift'],
         'A timeless icon. Aldehydic sparkle opens to a heart of rose and jasmine, grounded by sandalwood and vanilla. The scent of confidence.'),
        ('J''adore Dior',
         ARRAY['柑橘 Citrus','香柠檬 Bergamot','蜜瓜 Melon'],
         ARRAY['玫瑰 Rose','茉莉 Jasmine','铃兰 Lily-of-the-Valley'],
         ARRAY['麝香 Musk','黑莓 Blackberry','雪松 Cedar'],
         ARRAY['joy','romance','excitement'],
         ARRAY['date','party'],
         'A radiant bouquet. Juicy melon and bergamot dance with jasmine and rose, wrapped in soft musk. Modern femininity bottled.'),
        ('Light Blue Dolce & Gabbana',
         ARRAY['柠檬 Lemon','青苹果 Green Apple','风信子 Bellflower'],
         ARRAY['茉莉 Jasmine','竹子 Bamboo','白玫瑰 White Rose'],
         ARRAY['雪松 Cedar','琥珀 Amber','麝香 Musk'],
         ARRAY['joy','calm','excitement'],
         ARRAY['work','explore'],
         'A Mediterranean breeze. Crisp lemon and green apple meet airy jasmine and warm cedar. Effortless and sun-kissed.'),
        ('L''Eau d''Issey Issey Miyake',
         ARRAY['莲花 Lotus','小苍兰 Freesia','仙客来 Cyclamen'],
         ARRAY['百合 Lily','牡丹 Peony','康乃馨 Carnation'],
         ARRAY['麝香 Musk','琥珀 Amber','雪松 Cedar'],
         ARRAY['calm','nostalgia','romance'],
         ARRAY['home','gift'],
         'Water and flowers in harmony. Lotus rises from still water, touched by lily and soft musk. Pure, transparent, poetic.'),
        ('Shalimar Guerlain',
         ARRAY['佛手柑 Bergamot','柑橘 Citrus','柠檬 Lemon'],
         ARRAY['玫瑰 Rose','茉莉 Jasmine','鸢尾 Iris'],
         ARRAY['香草 Vanilla','零陵香豆 Tonka Bean','檀木 Sandalwood'],
         ARRAY['romance','nostalgia','melancholy'],
         ARRAY['date','gift'],
         'The original oriental. Bergamot brightens a heart of rose, then vanilla and tonka weave a warm, sensual trail. A legend since 1925.'),
        ('Black Orchid Tom Ford',
         ARRAY['黑加仑 Blackcurrant','依兰 Ylang-Ylang','佛手柑 Bergamot'],
         ARRAY['黑兰花 Black Orchid','莲花 Lotus','茉莉 Jasmine'],
         ARRAY['广藿香 Patchouli','琥珀 Amber','檀木 Sandalwood'],
         ARRAY['romance','melancholy','excitement'],
         ARRAY['party','date'],
         'Dark and magnetic. Black truffle and black orchid create an intoxicating bloom, deepened by patchouli and amber. Unforgettable.'),
        ('L''Homme Yves Saint Laurent',
         ARRAY['生姜 Ginger','佛手柑 Bergamot','柠檬 Lemon'],
         ARRAY['紫罗兰 Violet','罗勒 Basil','白胡椒 White Pepper'],
         ARRAY['雪松 Cedar','零陵香豆 Tonka Bean','麝香 Musk'],
         ARRAY['calm','excitement','joy'],
         ARRAY['work','explore'],
         'Modern elegance. Ginger and bergamot open with energy, violet and basil add sophistication, cedar anchors with quiet strength.'),
        ('Acqua di Giò Giorgio Armani',
         ARRAY['柑橘 Citrus','佛手柑 Bergamot','青柠 Lime'],
         ARRAY['茉莉 Jasmine','迷迭香 Rosemary','牡丹 Peony'],
         ARRAY['广藿香 Patchouli','雪松 Cedar','橡苔 Oakmoss'],
         ARRAY['joy','calm','excitement'],
         ARRAY['work','explore'],
         'The ocean breeze. Citrus and lime crash like waves, rosemary and jasmine float on salt air, patchouli grounds like sea-worn rock.'),
        ('La Vie Est Belle Lancôme',
         ARRAY['黑加仑 Blackcurrant','梨 Pear','佛手柑 Bergamot'],
         ARRAY['鸢尾 Iris','茉莉 Jasmine','橙花 Orange Blossom'],
         ARRAY['广藿香 Patchouli','零陵香豆 Tonka Bean','香草 Vanilla'],
         ARRAY['joy','romance','nostalgia'],
         ARRAY['gift','date'],
         'The beauty of life. Sweet blackcurrant and pear meet iris and orange blossom, wrapped in vanilla and patchouli. Pure happiness in a bottle.'),
        ('Sauvage Dior',
         ARRAY['佛手柑 Bergamot','粉红胡椒 Pink Pepper','四川花椒 Sichuan Pepper'],
         ARRAY['薰衣草 Lavender','天竺葵 Geranium','广藿香 Patchouli'],
         ARRAY['雪松 Cedar','琥珀 Ambroxan','麝香 Musk'],
         ARRAY['excitement','calm','anxiety'],
         ARRAY['work','party'],
         'Wild and fresh. Spicy bergamot and pepper burst open, lavender and geranium calm the storm, ambroxan and cedar leave a lasting mark.')
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS guest_quota CASCADE")
    op.execute("DROP TABLE IF EXISTS fragrance_templates CASCADE")
    op.execute("DROP TABLE IF EXISTS scene_tags CASCADE")
    op.execute("DROP TABLE IF EXISTS emotion_cards CASCADE")
    op.execute("DROP TABLE IF EXISTS temp_conversations CASCADE")
